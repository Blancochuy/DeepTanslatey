"""Translation service with multiple provider support and caching"""
from __future__ import annotations

from typing import Optional
from collections import OrderedDict
import hashlib
import threading
import json
import os
import time

try:
    from deep_translator import GoogleTranslator as GoogleDT
except Exception:
    GoogleDT = None

try:
    import deepl
except Exception:
    deepl = None

try:
    from langdetect import detect
    LANGDETECT_AVAILABLE = True
except Exception:
    LANGDETECT_AVAILABLE = False
    detect = None


class TranslationCache:
    """Thread-safe LRU cache for translations with O(1) operations and disk persistence"""
    
    def __init__(self, maxsize: int = 1000, cache_file: str = "translation_cache.json", ttl_seconds: int = 86400):  # 24 hours
        self.maxsize = maxsize
        self.cache_file = cache_file
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self._timestamps = {}  # Store timestamps for TTL
        self._lock = threading.Lock()
        self._load_from_disk()
    
    def _load_from_disk(self) -> None:
        """Load cache from disk if exists"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:  # Empty file
                        return
                    data = json.loads(content)
                    current_time = time.time()
                    for key, entry in data.items():
                        if isinstance(entry, dict) and 'value' in entry and 'timestamp' in entry:
                            # Check TTL
                            if current_time - entry['timestamp'] < self.ttl_seconds:
                                self._cache[key] = entry['value']
                                self._timestamps[key] = entry['timestamp']
                        elif isinstance(entry, str):  # Backward compatibility
                            self._cache[key] = entry
                            self._timestamps[key] = current_time
                # Trim to maxsize if loaded more
                while len(self._cache) > self.maxsize:
                    key, _ = self._cache.popitem(last=False)
                    self._timestamps.pop(key, None)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[WARN] Failed to load cache from disk: {e}")
                # Remove corrupted file
                try:
                    os.remove(self.cache_file)
                except Exception:
                    pass
    
    def _save_to_disk(self) -> None:
        """Save cache to disk asynchronously"""
        def save():
            try:
                data = {}
                with self._lock:
                    for key, value in self._cache.items():
                        data[key] = {
                            'value': value,
                            'timestamp': self._timestamps.get(key, time.time())
                        }
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[WARN] Failed to save cache to disk: {e}")
        
        # Save in background thread
        thread = threading.Thread(target=save, daemon=True)
        thread.start()
    
    def get(self, key: str) -> Optional[str]:
        """Get cached translation in O(1)"""
        with self._lock:
            if key in self._cache:
                # Check TTL
                if time.time() - self._timestamps.get(key, 0) > self.ttl_seconds:
                    # Expired, remove
                    del self._cache[key]
                    del self._timestamps[key]
                    return None
                # Move to end (most recently used) - O(1)
                self._cache.move_to_end(key)
                return self._cache[key]
            return None
    
    def set(self, key: str, value: str) -> None:
        """Cache a translation in O(1)"""
        with self._lock:
            current_time = time.time()
            if key in self._cache:
                # Update existing and move to end
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.maxsize:
                # Remove least recently used - O(1)
                old_key, _ = self._cache.popitem(last=False)
                self._timestamps.pop(old_key, None)
            
            self._cache[key] = value
            self._timestamps[key] = current_time
            
            # Save to disk periodically (every 10 sets)
            if len(self._cache) % 10 == 0:
                self._save_to_disk()
    
    def clear(self) -> None:
        """Clear cache"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            # Remove file
            try:
                if os.path.exists(self.cache_file):
                    os.remove(self.cache_file)
            except Exception:
                pass


class TranslationService:
    """Handles translation with multiple provider support and caching"""

    def __init__(
        self,
        mode: str,
        source_lang: str,
        target_lang: str,
        deepl_api_key: Optional[str],
        enable_cache: bool = True,
        auto_detect_lang: bool = True,
    ):
        self.mode = (mode or "none").lower()
        self.source = source_lang
        self.target = target_lang
        self.impl = None
        self.enable_cache = enable_cache
        self.cache = TranslationCache() if enable_cache else None
        self._last_request_time = 0
        self._min_interval = 0.05  # Reduced from 0.1 for batch processing
        self._batch_size = 10  # Maximum batch size for API calls
        self._batch_timeout = 0.5  # Wait up to 0.5s for batch to fill
        self._pending_batch = []
        self._batch_lock = threading.Lock()
        self._batch_timer = None
        self.auto_detect_lang = auto_detect_lang and LANGDETECT_AVAILABLE
        if auto_detect_lang and not LANGDETECT_AVAILABLE:
            print("[INFO] Language detection not available. Install: pip install langdetect")
        self._quality_metrics = {
            'deepl_requests': 0,
            'deepl_errors': 0,
            'google_requests': 0,
            'google_errors': 0,
            'cache_hits': 0,
            'total_requests': 0
        }
        self._init_impl(deepl_api_key)

    def _init_impl(self, deepl_api_key: Optional[str]) -> None:
        """Initialize translation providers with fallback support"""
        if self.mode == "none" or self.source == self.target:
            self.impl = None
            self.fallback_impl = None
            return

        # Try to initialize both providers for fallback
        self.impl = None
        self.fallback_impl = None
        self.preferred_provider = None

        # Try DeepL first (better quality)
        if deepl_api_key and deepl is not None:
            try:
                deepl_translator = deepl.Translator(deepl_api_key)
                # Test connection
                test_result = deepl_translator.translate_text("Hello", target_lang="ES")
                if test_result:
                    self.impl = deepl_translator
                    self.preferred_provider = "deepl"
                    print(f"[INFO] Using DeepL for translation ({self.source} -> {self.target})")
            except Exception as exc:
                print(f"[WARN] DeepL initialization failed: {exc}")

        # Try Google Translate as fallback or primary
        if GoogleDT is not None:
            try:
                google_translator = GoogleDT(source=self.source, target=self.target)
                # Test connection
                test_result = google_translator.translate("Hello")
                if test_result:
                    if self.impl is None:
                        self.impl = google_translator
                        self.preferred_provider = "google"
                        print(f"[INFO] Using Google Translate for translation ({self.source} -> {self.target})")
                    else:
                        self.fallback_impl = google_translator
                        print(f"[INFO] Google Translate available as fallback")
            except Exception as exc:
                print(f"[WARN] Google Translate initialization failed: {exc}")

        if self.impl is None:
            print("[ERROR] No translation providers available")
            print("[INFO] Install required packages: pip install deepl deep-translator")

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        # Use hash for long texts to save memory
        if len(text) > 100:
            return hashlib.md5(text.encode()).hexdigest()
        return text

    def _translate_with_fallback(self, text: str) -> str:
        """Translate with intelligent fallback between providers"""
        if not text.strip():
            return text

        self._quality_metrics['total_requests'] += 1

        # Try preferred provider first
        if self.impl:
            try:
                if self.preferred_provider == "deepl":
                    self._quality_metrics['deepl_requests'] += 1
                    result = self.impl.translate_text(
                        text,
                        source_lang=self.source.upper(),
                        target_lang=self.target.upper(),
                    )
                    translated = result.text if hasattr(result, "text") else str(result)
                    return translated
                elif self.preferred_provider == "google":
                    self._quality_metrics['google_requests'] += 1
                    translated = self.impl.translate(text)
                    return translated
                elif self.preferred_provider == "mock":
                    return self.impl.translate(text)
            except Exception as exc:
                if self.preferred_provider == "deepl":
                    self._quality_metrics['deepl_errors'] += 1
                elif self.preferred_provider == "google":
                    self._quality_metrics['google_errors'] += 1
                print(f"[WARN] {self.preferred_provider} translation failed: {exc}")

        # Try fallback provider
        if self.fallback_impl:
            try:
                self._quality_metrics['google_requests'] += 1  # Assuming fallback is Google
                translated = self.fallback_impl.translate(text)
                print(f"[INFO] Used fallback provider for translation")
                return translated
            except Exception as exc:
                self._quality_metrics['google_errors'] += 1
                print(f"[WARN] Fallback translation failed: {exc}")

        # No providers available
        return text

        if self.impl is None:
            print("[ERROR] No translation providers available")
            print("[INFO] Install required packages: pip install deepl deep-translator")

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        # Use hash for long texts to save memory
        if len(text) > 100:
            return hashlib.md5(text.encode()).hexdigest()
        return text

    def translate_batch(self, texts: list[str]) -> list[str]:
        """Translate multiple texts in batch for better performance"""
        if not texts or self.impl is None:
            return texts
        
        # Filter out empty texts and check cache
        results = []
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            if not text.strip():
                results.append(text)
                continue
                
            # Check cache first
            if self.enable_cache and self.cache:
                cache_key = self._get_cache_key(text)
                cached = self.cache.get(cache_key)
                if cached is not None:
                    results.append(cached)
                    continue
            
            results.append(None)  # Placeholder
            uncached_indices.append(i)
            uncached_texts.append(text)
        
        # Translate uncached texts in batches
        if uncached_texts:
            batch_results = self._translate_batch_api(uncached_texts)
            
            # Store results and update cache
            for (original_idx, translated) in zip(uncached_indices, batch_results):
                results[original_idx] = translated
                
                # Cache the result
                if self.enable_cache and self.cache and translated != texts[original_idx]:
                    cache_key = self._get_cache_key(texts[original_idx])
                    self.cache.set(cache_key, translated)
        
        return results
    
    def _translate_batch_api(self, texts: list[str]) -> list[str]:
        """Translate texts using API batch calls with fallback"""
        if not texts:
            return []
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_interval:
            time.sleep(self._min_interval - time_since_last)
        
        results = []
        for text in texts:
            translated = self._translate_with_fallback(text)
            results.append(translated)
        
        self._last_request_time = time.time()
        return results

    def _detect_language(self, text: str) -> Optional[str]:
        """Detect the language of the text"""
        if not self.auto_detect_lang or not detect:
            return None
        
        try:
            detected = detect(text)
            return detected
        except Exception:
            return None

    def translate(self, text: str) -> str:
        """Translate text using configured provider with caching"""
        if not text.strip() or self.impl is None:
            return text

        # Auto-detect language if enabled
        detected_lang = self._detect_language(text)
        if detected_lang and detected_lang == self.target:
            # Text is already in target language, no translation needed
            return text
        elif detected_lang and detected_lang != self.source:
            # Detected language differs from configured source
            print(f"[INFO] Detected language '{detected_lang}' differs from configured '{self.source}'")

        # Check cache first
        if self.enable_cache and self.cache:
            cache_key = self._get_cache_key(text)
            cached = self.cache.get(cache_key)
            if cached is not None:
                self._quality_metrics['cache_hits'] += 1
                return cached

        # For single translations, use batch processing with one item
        return self.translate_batch([text])[0]

    def get_quality_metrics(self) -> dict:
        """Get translation quality and performance metrics"""
        metrics = self._quality_metrics.copy()
        
        # Calculate rates
        total = metrics['total_requests']
        if total > 0:
            metrics['cache_hit_rate'] = metrics['cache_hits'] / total
            metrics['deepl_error_rate'] = metrics['deepl_errors'] / max(metrics['deepl_requests'], 1)
            metrics['google_error_rate'] = metrics['google_errors'] / max(metrics['google_requests'], 1)
        
        return metrics

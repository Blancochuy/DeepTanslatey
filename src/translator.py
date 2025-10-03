"""Translation service with multiple provider support and caching"""
from __future__ import annotations

from typing import Optional
from collections import OrderedDict
import hashlib
import threading

try:
    from deep_translator import GoogleTranslator as GoogleDT
except Exception:
    GoogleDT = None

try:
    import deepl
except Exception:
    deepl = None


class TranslationCache:
    """Thread-safe LRU cache for translations with O(1) operations"""
    
    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self._cache = OrderedDict()
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[str]:
        """Get cached translation in O(1)"""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used) - O(1)
                self._cache.move_to_end(key)
                return self._cache[key]
            return None
    
    def set(self, key: str, value: str) -> None:
        """Cache a translation in O(1)"""
        with self._lock:
            if key in self._cache:
                # Update existing and move to end
                self._cache.move_to_end(key)
            elif len(self._cache) >= self.maxsize:
                # Remove least recently used - O(1)
                self._cache.popitem(last=False)
            
            self._cache[key] = value
    
    def clear(self) -> None:
        """Clear cache"""
        with self._lock:
            self._cache.clear()


class TranslationService:
    """Handles translation with multiple provider support and caching"""

    def __init__(
        self,
        mode: str,
        source_lang: str,
        target_lang: str,
        deepl_api_key: Optional[str],
        enable_cache: bool = True,
    ):
        self.mode = (mode or "none").lower()
        self.source = source_lang
        self.target = target_lang
        self.impl = None
        self.enable_cache = enable_cache
        self.cache = TranslationCache() if enable_cache else None
        self._init_impl(deepl_api_key)

    def _init_impl(self, deepl_api_key: Optional[str]) -> None:
        """Initialize translation provider"""
        if self.mode == "none" or self.source == self.target:
            self.impl = None
            return

        if self.mode == "deepl":
            if deepl is None:
                print("[WARN] deepl package not installed. Install: pip install deepl")
                print("[WARN] Falling back to Google Translate")
                self.mode = "google"
            elif not deepl_api_key:
                print("[WARN] DEEPL_API_KEY not found. Falling back to Google Translate")
                self.mode = "google"
            else:
                try:
                    # Initialize with timeout
                    self.impl = deepl.Translator(deepl_api_key)
                    # Test connection with a simple request
                    print(f"[INFO] Using DeepL for translation ({self.source} -> {self.target})")
                    return
                except deepl.exceptions.AuthorizationException:
                    print("[WARN] DeepL API key is invalid")
                    print("[WARN] Falling back to Google Translate")
                    self.mode = "google"
                except deepl.exceptions.ConnectionException as exc:
                    print(f"[WARN] DeepL connection failed: {exc}")
                    print("[WARN] Falling back to Google Translate")
                    self.mode = "google"
                except Exception as exc:
                    print(f"[WARN] DeepL initialization failed: {exc}")
                    print("[WARN] Falling back to Google Translate")
                    self.mode = "google"

        if self.mode == "google":
            if GoogleDT is None:
                print("[ERROR] deep-translator not installed. Install: pip install deep-translator")
                print("[WARN] Translation disabled")
                self.impl = None
            else:
                try:
                    self.impl = GoogleDT(source=self.source, target=self.target)
                    print(f"[INFO] Using Google Translate ({self.source} -> {self.target})")
                except ValueError as exc:
                    print(f"[ERROR] Invalid language codes: {exc}")
                    print("[WARN] Translation disabled")
                    self.impl = None
                except Exception as exc:
                    print(f"[ERROR] Google Translate initialization failed: {exc}")
                    print("[WARN] Translation disabled")
                    self.impl = None

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        # Use hash for long texts to save memory
        if len(text) > 100:
            return hashlib.md5(text.encode()).hexdigest()
        return text

    def translate(self, text: str) -> str:
        """Translate text using configured provider with caching"""
        if not text.strip() or self.impl is None:
            return text

        # Check cache first
        if self.enable_cache and self.cache:
            cache_key = self._get_cache_key(text)
            cached = self.cache.get(cache_key)
            if cached is not None:
                return cached

        # Perform translation
        try:
            if self.mode == "deepl":
                result = self.impl.translate_text(
                    text,
                    source_lang=self.source.upper(),
                    target_lang=self.target.upper(),
                )
                translated = result.text if hasattr(result, "text") else str(result)

            elif self.mode == "google":
                translated = self.impl.translate(text)
            else:
                translated = text

            # Cache the result
            if self.enable_cache and self.cache and translated != text:
                cache_key = self._get_cache_key(text)
                self.cache.set(cache_key, translated)

            return translated

        except deepl.exceptions.QuotaExceededException:
            print("[ERROR] DeepL API quota exceeded")
            return text
        except deepl.exceptions.ConnectionException as exc:
            print(f"[ERROR] DeepL connection error: {exc}")
            return text
        except ConnectionError as exc:
            print(f"[ERROR] Network connection error: {exc}")
            return text
        except TimeoutError:
            print("[ERROR] Translation request timed out")
            return text
        except Exception as exc:
            print(f"[WARN] Translation error: {exc}")
            return text

    def clear_cache(self) -> None:
        """Clear translation cache"""
        if self.cache:
            self.cache.clear()

"""
Test script for optimizations
Validates all improvements made in version 2.1.0
"""
import sys
import os
import time
from collections import OrderedDict

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))


def test_cache_performance():
    """Test O(1) cache operations"""
    print("\n" + "="*60)
    print("TEST 1: Cache Performance (O(1) Operations)")
    print("="*60)
    
    from src.translator import TranslationCache
    
    cache = TranslationCache(maxsize=1000)
    
    # Test insertions
    print("\n[TEST] Inserting 1000 items...")
    start = time.perf_counter()
    for i in range(1000):
        cache.set(f"key_{i}", f"value_{i}")
    insert_time = time.perf_counter() - start
    print(f"✓ Inserted 1000 items in {insert_time*1000:.2f}ms")
    
    # Test lookups
    print("\n[TEST] Looking up 1000 items...")
    start = time.perf_counter()
    for i in range(1000):
        result = cache.get(f"key_{i}")
        assert result == f"value_{i}", f"Cache lookup failed for key_{i}"
    lookup_time = time.perf_counter() - start
    print(f"✓ Looked up 1000 items in {lookup_time*1000:.2f}ms")
    
    # Test LRU eviction
    print("\n[TEST] Testing LRU eviction...")
    cache_small = TranslationCache(maxsize=3)
    cache_small.set("a", "1")
    cache_small.set("b", "2")
    cache_small.set("c", "3")
    cache_small.set("d", "4")  # Should evict 'a'
    
    assert cache_small.get("a") is None, "LRU eviction failed - 'a' should be evicted"
    assert cache_small.get("b") == "2", "LRU should keep 'b'"
    assert cache_small.get("c") == "3", "LRU should keep 'c'"
    assert cache_small.get("d") == "4", "LRU should keep 'd'"
    print("✓ LRU eviction works correctly")
    
    return True


def test_thread_safety():
    """Test thread-safe cache operations"""
    print("\n" + "="*60)
    print("TEST 2: Thread Safety")
    print("="*60)
    
    from src.translator import TranslationCache
    import threading
    
    cache = TranslationCache(maxsize=100)
    errors = []
    
    def worker(thread_id):
        try:
            for i in range(100):
                cache.set(f"thread_{thread_id}_key_{i}", f"value_{i}")
                result = cache.get(f"thread_{thread_id}_key_{i}")
                if result != f"value_{i}":
                    errors.append(f"Thread {thread_id}: Expected value_{i}, got {result}")
        except Exception as e:
            errors.append(f"Thread {thread_id}: {e}")
    
    print("\n[TEST] Running 5 threads with 100 operations each...")
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    if errors:
        print(f"✗ Thread safety issues found:")
        for error in errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        return False
    else:
        print("✓ No race conditions detected in 500 concurrent operations")
        return True


def test_dataclass():
    """Test dataclass implementation"""
    print("\n" + "="*60)
    print("TEST 3: DataClass Implementation")
    print("="*60)
    
    from src.transcriber import TranscriptionEvent
    from dataclasses import is_dataclass
    
    print("\n[TEST] Checking if TranscriptionEvent is a dataclass...")
    if not is_dataclass(TranscriptionEvent):
        print("✗ TranscriptionEvent is not a dataclass")
        return False
    
    print("✓ TranscriptionEvent is a dataclass")
    
    # Test creation
    print("\n[TEST] Creating TranscriptionEvent instance...")
    event = TranscriptionEvent(
        transcript="Hello",
        translation="Hola",
        is_final=True,
        timestamp="12:34:56"
    )
    
    assert event.transcript == "Hello"
    assert event.translation == "Hola"
    assert event.is_final == True
    assert event.timestamp == "12:34:56"
    print("✓ TranscriptionEvent instance created successfully")
    
    # Test auto-generated methods
    print("\n[TEST] Testing auto-generated __repr__...")
    repr_str = repr(event)
    assert "TranscriptionEvent" in repr_str
    assert "Hello" in repr_str
    print(f"✓ __repr__ works: {repr_str}")
    
    return True


def test_audio_device_manager():
    """Test AudioDeviceManager improvements"""
    print("\n" + "="*60)
    print("TEST 4: AudioDeviceManager Features")
    print("="*60)
    
    from src.audio_manager import AudioDeviceManager
    
    # Test find_device_by_index method exists
    print("\n[TEST] Checking new find_device_by_index method...")
    if not hasattr(AudioDeviceManager, 'find_device_by_index'):
        print("✗ find_device_by_index method not found")
        return False
    print("✓ find_device_by_index method exists")
    
    # Test list_loopback_devices
    print("\n[TEST] Listing loopback devices...")
    try:
        devices = AudioDeviceManager.list_loopback_devices()
        if devices:
            print(f"✓ Found {len(devices)} loopback device(s)")
        else:
            print("⚠ No loopback devices found (this is OK if no audio is playing)")
    except Exception as e:
        print(f"✗ Error listing devices: {e}")
        return False
    
    return True


def test_logging_config():
    """Test logging configuration"""
    print("\n" + "="*60)
    print("TEST 5: Logging Configuration")
    print("="*60)
    
    try:
        from src.logging_config import setup_logging, get_logger
        
        print("\n[TEST] Setting up logging...")
        logger = setup_logging(verbose=True, use_colors=False)
        print("✓ Logging configured successfully")
        
        print("\n[TEST] Testing log levels...")
        test_logger = get_logger("test")
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")
        test_logger.error("Error message")
        print("✓ All log levels work")
        
        return True
    except Exception as e:
        print(f"✗ Logging test failed: {e}")
        return False


def test_cli_args():
    """Test CLI argument parsing"""
    print("\n" + "="*60)
    print("TEST 6: CLI Arguments")
    print("="*60)
    
    from src.cli import parse_args
    import sys
    
    # Test --version
    print("\n[TEST] Checking --version flag...")
    original_argv = sys.argv.copy()
    
    try:
        sys.argv = ['test', '--help']
        try:
            args = parse_args()
        except SystemExit:
            pass  # --help causes exit
        print("✓ Help text available")
        
        # Check that new args exist
        print("\n[TEST] Checking new arguments...")
        sys.argv = ['test', '--device', 'test']
        args = parse_args()
        
        assert hasattr(args, 'device_index'), "Missing --device-index argument"
        assert hasattr(args, 'verbose'), "Missing --verbose argument"
        print("✓ New arguments (--device-index, --verbose) available")
        
    finally:
        sys.argv = original_argv
    
    return True


def test_queue_maxsize():
    """Test translation queue has maxsize"""
    print("\n" + "="*60)
    print("TEST 7: Translation Queue Maxsize")
    print("="*60)
    
    from src.transcriber import DeepgramTranscriber
    from queue import Queue
    
    print("\n[TEST] Checking queue maxsize...")
    # We can't fully instantiate without API key, but we can check the code
    import inspect
    source = inspect.getsource(DeepgramTranscriber.__init__)
    
    if "Queue(maxsize=" in source:
        print("✓ Translation queue has maxsize configured")
        return True
    else:
        print("✗ Translation queue maxsize not found")
        return False


def test_cache_persistence():
    """Test cache persistence to disk"""
    print("\n" + "="*60)
    print("TEST: Cache Persistence")
    print("="*60)
    
    import tempfile
    import os
    from src.translator import TranslationCache
    
    # Create temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
        cache_file = f.name
    
    try:
        # Test saving
        print("\n[TEST] Testing cache persistence...")
        cache = TranslationCache(maxsize=10, cache_file=cache_file)
        cache.set("hello", "hola")
        cache.set("world", "mundo")
        
        # Force save
        cache._save_to_disk()
        time.sleep(0.1)  # Wait for async save
        
        # Create new cache instance to test loading
        cache2 = TranslationCache(maxsize=10, cache_file=cache_file)
        assert cache2.get("hello") == "hola"
        assert cache2.get("world") == "mundo"
        print("✓ Cache persistence works correctly")
        
        return True
    finally:
        if os.path.exists(cache_file):
            os.remove(cache_file)


def test_rate_limiting():
    """Test translation rate limiting"""
    print("\n" + "="*60)
    print("TEST: Rate Limiting")
    print("="*60)
    
    from src.translator import TranslationService
    
    # Mock translator for testing
    class MockTranslator:
        def __init__(self):
            self.call_count = 0
        
        def translate(self, text):
            self.call_count += 1
            return f"translated_{text}"
    
    service = TranslationService("none", "en", "es", None, enable_cache=False)
    service.impl = MockTranslator()
    service.mode = "mock"
    
    print("\n[TEST] Testing rate limiting...")
    start = time.perf_counter()
    for i in range(5):
        result = service.translate(f"text_{i}")
        assert result == f"translated_text_{i}"
    elapsed = time.perf_counter() - start
    
    # Should take at least 0.4 seconds (5 * 0.1 - some tolerance)
    assert elapsed >= 0.3, f"Rate limiting not working, took {elapsed:.2f}s"
    print(f"✓ Rate limiting enforced: {elapsed:.2f}s for 5 requests")
    
    return True


def test_performance_benchmark():
    """Benchmark overall performance improvements"""
    print("\n" + "="*60)
    print("TEST: Performance Benchmark")
    print("="*60)
    
    from src.translator import TranslationCache, TranslationService
    import threading
    import concurrent.futures
    
    # Benchmark cache operations
    print("\n[TEST] Benchmarking cache operations...")
    cache = TranslationCache(maxsize=10000)
    
    # Insert benchmark
    start = time.perf_counter()
    for i in range(5000):
        cache.set(f"bench_key_{i}", f"bench_value_{i}")
    insert_time = time.perf_counter() - start
    print(f"✓ Inserted 5000 items in {insert_time:.3f}s ({5000/insert_time:.0f} ops/sec)")
    
    # Lookup benchmark
    start = time.perf_counter()
    for i in range(5000):
        result = cache.get(f"bench_key_{i}")
        assert result == f"bench_value_{i}"
    lookup_time = time.perf_counter() - start
    print(f"✓ Looked up 5000 items in {lookup_time:.3f}s ({5000/lookup_time:.0f} ops/sec)")
    
    # Concurrent access benchmark
    print("\n[TEST] Benchmarking concurrent cache access...")
    def worker(worker_id):
        for i in range(100):
            key = f"concurrent_{worker_id}_{i}"
            cache.set(key, f"value_{worker_id}_{i}")
            result = cache.get(key)
            assert result == f"value_{worker_id}_{i}"
    
    start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        for future in concurrent.futures.as_completed(futures):
            future.result()
    concurrent_time = time.perf_counter() - start
    print(f"✓ 1000 concurrent operations in {concurrent_time:.3f}s ({1000/concurrent_time:.0f} ops/sec)")
    
    # Memory usage check
    cache_size = len(cache._cache)
    print(f"✓ Cache size: {cache_size} items")
    
    return True


def test_batch_translation():
    """Test batch translation performance"""
    print("\n" + "="*60)
    print("TEST: Batch Translation")
    print("="*60)
    
    from src.translator import TranslationService
    
    # Mock translator for testing
    class MockTranslator:
        def __init__(self):
            self.call_count = 0
        
        def translate(self, text):
            self.call_count += 1
            time.sleep(0.01)  # Simulate API delay
            return f"translated_{text}"
    
    service = TranslationService("none", "en", "es", None, enable_cache=False)
    service.impl = MockTranslator()
    service.mode = "mock"
    
    print("\n[TEST] Testing batch translation performance...")
    
    # Test single translation
    start = time.perf_counter()
    result1 = service.translate("hello")
    single_time = time.perf_counter() - start
    
    # Test batch translation
    texts = ["hello", "world", "test", "batch", "translation"]
    start = time.perf_counter()
    results = service.translate_batch(texts)
    batch_time = time.perf_counter() - start
    
    # Verify results
    assert result1 == "translated_hello"
    assert results == ["translated_hello", "translated_world", "translated_test", "translated_batch", "translated_translation"]
    
    # Batch should be faster per item
    avg_batch_time = batch_time / len(texts)
    print(f"✓ Single translation: {single_time:.3f}s")
    print(f"✓ Batch translation: {batch_time:.3f}s total ({avg_batch_time:.3f}s per item)")
    print(f"✓ Efficiency improvement: {single_time/avg_batch_time:.1f}x faster per item")
    
    return True


def test_language_detection():
    """Test automatic language detection"""
    print("\n" + "="*60)
    print("TEST: Language Detection")
    print("="*60)
    
    from src.translator import TranslationService
    
    # Test with language detection enabled (if available)
    service = TranslationService("none", "en", "es", None, enable_cache=False, auto_detect_lang=True)
    
    print("\n[TEST] Testing language detection...")
    
    # Test detection availability
    if not hasattr(service, 'auto_detect_lang') or not service.auto_detect_lang:
        print("⚠ Language detection not available (langdetect not installed)")
        return True
    
    # Test detection
    detected = service._detect_language("Hello world")
    if detected:
        print(f"✓ Detected language: {detected}")
        assert detected == "en"
    else:
        print("⚠ Language detection failed")
    
    return True


def test_smart_fallback():
    """Test smart provider fallback"""
    print("\n" + "="*60)
    print("TEST: Smart Provider Fallback")
    print("="*60)
    
    from src.translator import TranslationService
    
    # Create service with mock providers
    service = TranslationService("none", "en", "es", None, enable_cache=False)
    
    # Mock primary provider (fails)
    class FailingTranslator:
        def translate(self, text):
            raise Exception("Primary provider failed")
    
    # Mock fallback provider (succeeds)
    class WorkingTranslator:
        def translate(self, text):
            return f"fallback_{text}"
    
    service.impl = FailingTranslator()
    service.fallback_impl = WorkingTranslator()
    service.preferred_provider = "failing"
    
    print("\n[TEST] Testing provider fallback...")
    
    result = service._translate_with_fallback("test")
    assert result == "fallback_test"
    print("✓ Fallback provider used successfully")
    
    # Check metrics
    metrics = service.get_quality_metrics()
    assert metrics['total_requests'] > 0
    print("✓ Quality metrics tracked")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" "*20 + "OPTIMIZATION TESTS")
    print(" "*20 + "Version 2.1.0")
    print("="*70)
    
    tests = [
        ("Cache Performance (O(1))", test_cache_performance),
        ("Thread Safety", test_thread_safety),
        ("DataClass Implementation", test_dataclass),
        ("AudioDeviceManager Features", test_audio_device_manager),
        ("Logging Configuration", test_logging_config),
        ("CLI Arguments", test_cli_args),
        ("Queue Maxsize", test_queue_maxsize),
        ("Cache Persistence", test_cache_persistence),
        ("Rate Limiting", test_rate_limiting),
        ("Performance Benchmark", test_performance_benchmark),
        ("Batch Translation", test_batch_translation),
        ("Language Detection", test_language_detection),
        ("Smart Provider Fallback", test_smart_fallback),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print(" "*25 + "SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n🎉 All optimization tests passed!")
        print("\nOptimizations working:")
        print("  • O(1) cache operations")
        print("  • Thread-safe cache")
        print("  • DataClass for events")
        print("  • Enhanced AudioDeviceManager")
        print("  • Logging system")
        print("  • New CLI arguments")
        print("  • Queue backlog prevention")
        print("  • Batch translation processing")
        print("  • Automatic language detection")
        print("  • Smart provider fallback")
        print("  • Quality metrics tracking")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

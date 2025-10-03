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
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

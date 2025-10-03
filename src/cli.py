"""Command-line interface"""
import argparse
import sys

from . import __version__
from .audio_manager import AudioDeviceManager
from .transcriber import DeepgramTranscriber
from .config import Config
from .logging_config import setup_logging, get_logger

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Realtime audio transcription and translation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list-devices
  %(prog)s --device airpods --src en --tgt es
  %(prog)s --device discord --src en --tgt es --translator deepl
  %(prog)s --test-capture airpods
  %(prog)s --device-index 12 --src en --tgt es
        """
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--device", default="", help="Device name filter (e.g., 'airpods', 'discord')")
    parser.add_argument("--device-index", type=int, help="Device index (use --list-devices to see indices)")
    parser.add_argument("--src", default="en", help="Source language code (e.g., 'en', 'es', 'fr')")
    parser.add_argument("--tgt", default="es", help="Target language code for translation")
    parser.add_argument(
        "--translator",
        default="google",
        choices=["deepl", "google", "none"],
        help="Translation provider (default: google)",
    )
    parser.add_argument("--model", default="nova-2", help="Deepgram model (nova-2, nova, base)")
    parser.add_argument("--interim", action="store_true", default=True, help="Enable interim results (default)")
    parser.add_argument("--no-interim", dest="interim", action="store_false", help="Disable interim results")
    parser.add_argument(
        "--endpointing", 
        type=int, 
        default=300, 
        help="Silence ms to end utterance (default: 300, range: 10-2000)"
    )
    parser.add_argument("--list-devices", action="store_true", help="List available loopback devices")
    parser.add_argument("--test-capture", metavar="DEVICE", help="Test audio capture for 10 seconds")
    parser.add_argument("--gui", action="store_true", help="Launch GUI mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output (debug mode)")

    return parser.parse_args()


def main() -> int:
    """Main CLI entry point"""
    args = parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose, use_colors=True)
    
    config = Config()

    # Validate endpointing range
    if not 10 <= args.endpointing <= 2000:
        logger.error(f"Invalid endpointing value: {args.endpointing}")
        logger.error("Endpointing must be between 10 and 2000 milliseconds")
        return 1

    # GUI mode
    if args.gui:
        try:
            from .gui import run_gui
            run_gui()
            return 0
        except ImportError as e:
            print(f"[error] GUI not available: {e}")
            return 1

    # List devices
    if args.list_devices:
        logger.info("Available loopback devices:")
        logger.info("")
        devices = AudioDeviceManager.list_loopback_devices()

        if not devices:
            logger.info("  (none found - ensure audio is playing)")
        else:
            for idx, info in devices:
                logger.info(f"  [{idx:2d}] {info['name']}")
        logger.info("")
        return 0

    # Test capture
    if args.test_capture:
        if args.device_index is not None:
            device_index, device_info = AudioDeviceManager.find_device_by_index(args.device_index)
        else:
            device_index, device_info = AudioDeviceManager.find_device(args.test_capture)

        if device_index is None:
            logger.error(f"Device not found: {args.test_capture or args.device_index}")
            return 1

        success = AudioDeviceManager.test_capture(device_index, device_info)
        return 0 if success else 1

    # Check API key
    if not config.deepgram_api_key:
        logger.error("DEEPGRAM_API_KEY not found")
        logger.info("")
        logger.info("Set it in your environment:")
        logger.info("  PowerShell: $env:DEEPGRAM_API_KEY=\"your_key\"")
        logger.info("  CMD:        set DEEPGRAM_API_KEY=your_key")
        logger.info("  Or create a .env file with: DEEPGRAM_API_KEY=your_key")
        return 1

    # Find device - support both --device and --device-index
    if args.device_index is not None:
        logger.debug(f"Using device index: {args.device_index}")
        device_index, device_info = AudioDeviceManager.find_device_by_index(args.device_index)
    else:
        logger.debug(f"Searching for device: {args.device or '(any)'}")
        device_index, device_info = AudioDeviceManager.find_device(args.device)

    if device_index is None:
        logger.error("No loopback device found")
        if args.device:
            logger.error(f"Filter used: '{args.device}'")
        if args.device_index is not None:
            logger.error(f"Index used: {args.device_index}")
        logger.info("")
        logger.info("Tips:")
        logger.info("  - Ensure the app is playing audio")
        logger.info("  - Loopback devices only appear while audio is active")
        logger.info("  - Use --list-devices to see available devices")
        return 1

    # Start transcription
    transcriber = DeepgramTranscriber(
        deepgram_api_key=config.deepgram_api_key,
        source_language=args.src,
        target_language=args.tgt,
        translator_mode=args.translator,
        deepl_api_key=config.deepl_api_key,
        enable_interim=args.interim,
        model=args.model,
        endpointing_ms=args.endpointing,
    )

    transcriber.start(device_index, device_info)
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Realtime Audio Transcription & Translation

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

A fast, lightweight system for real-time audio transcription and translation using Deepgram AI and multiple translation providers.

## Features

- Real-time transcription using Deepgram's state-of-the-art speech recognition
- Multi-provider translation: Google Translate (free) or DeepL (premium)
- Translation caching for faster repeated translations
- Asynchronous translation for improved performance
- Windows WASAPI loopback capture (capture system audio)
- CLI and GUI modes - simple command-line or lightweight graphical interface
- Interim results for low-latency feedback
- Multi-language support

## Quick Start

### Prerequisites
- Python 3.8+
- Windows (for WASAPI loopback support)
- Deepgram API key ([get one free](https://console.deepgram.com/signup))

### Installation

```powershell
# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up API key
# Create a .env file in the project root:
echo DEEPGRAM_API_KEY=your_api_key_here > .env

# Optional: Add DeepL API key for premium translation
echo DEEPL_API_KEY=your_deepl_key >> .env
```

### Usage

#### GUI Mode (Recommended)
```powershell
python main.py --gui
```

#### CLI Mode
```powershell
# List available audio devices
python main.py --list-devices

# Basic transcription (English to Spanish)
python main.py --device airpods --src en --tgt es

# Using DeepL for translation
python main.py --device discord --src en --tgt es --translator deepl

# Test audio capture
python main.py --test-capture airpods

# Disable translation
python main.py --device discord --src en --translator none
```

## Project Structure

```
Translate/
├── src/
│   ├── __init__.py         # Package initialization
│   ├── config.py           # Configuration and settings
│   ├── audio_manager.py    # Audio device management
│   ├── translator.py       # Translation services with caching
│   ├── transcriber.py      # Deepgram transcription engine
│   ├── cli.py             # Command-line interface
│   └── gui.py             # Graphical user interface
├── main.py                # Original monolithic version
├── main.py                # New modular entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Performance Optimizations

The new version includes several optimizations:

1. **Translation Caching**: Avoids re-translating identical text
   - LRU cache with configurable size (default: 1000 entries)
   - Hash-based keys for long texts

2. **Asynchronous Translation**: Non-blocking translation
   - Background worker thread for translations
   - Queue-based processing
   - Doesn't block transcription pipeline

3. **Modular Architecture**: Better code organization
   - Separated concerns (audio, transcription, translation)
   - Easier to maintain and extend
   - Better memory management

## GUI Features

The lightweight GUI includes:

- Device selector with auto-detection
- Language configuration (source/target)
- Translation provider selection
- Model selection (nova-2, nova, base)
- Real-time transcript display
- Real-time translation display
- Session statistics
- Start/Stop controls

## Configuration

### Environment Variables
Create a `.env` file:
```env
DEEPGRAM_API_KEY=your_deepgram_key
DEEPL_API_KEY=your_deepl_key  # Optional
```

### Command-Line Options
```
--device FILTER      Device name filter (e.g., 'airpods', 'discord')
--src LANG          Source language code (e.g., 'en', 'es', 'fr')
--tgt LANG          Target language code for translation
--translator TYPE   Translation provider: google, deepl, none
--model MODEL       Deepgram model: nova-2, nova, base
--interim           Enable interim results (default)
--no-interim        Disable interim results
--endpointing MS    Silence ms to end utterance (default: 300)
--list-devices      List available loopback devices
--test-capture DEV  Test audio capture for 10 seconds
--gui               Launch GUI mode
```

## Supported Languages

Common language codes:
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `it` - Italian
- `pt` - Portuguese
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese

[See Deepgram docs](https://developers.deepgram.com/docs/languages-overview) for full list.

## Migration from Old Version

To migrate from `main.py` to the new modular version:

1. The new entry point is `main.py`
2. All command-line options remain the same
3. New `--gui` option for graphical interface
4. Performance improvements are automatic (caching, async translation)

Both versions can coexist. Test the new version:
```powershell
python main.py --device airpods --src en --tgt es
```

## Troubleshooting

### No devices found
- Ensure audio is playing (loopback devices only appear when active)
- Try `--list-devices` while playing audio

### Slow translation
- The new version includes caching - translations should speed up over time
- Consider using DeepL for better quality (requires API key)

### Import errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`

## License

See LICENSE file for details.

## Credits

- [Deepgram](https://deepgram.com/) - Speech recognition API
- [pyaudiowpatch](https://github.com/s0d3s/PyAudioWPatch) - WASAPI loopback support
- [deep-translator](https://github.com/nidhaloff/deep-translator) - Google Translate
- [DeepL](https://www.deepl.com/) - Premium translation API

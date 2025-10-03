"""
Realtime transcription and translation (Deepgram + selectable translator).
- Windows WASAPI loopback capture via pyaudiowpatch
- Low latency with interim results
- No GPU required; configure via CLI flags and .env

Quick start (PowerShell):
  1) python -m venv .venv
  2) .\.venv\Scripts\Activate.ps1
  3) pip install -r requirements.txt
  4) Set DEEPGRAM_API_KEY in environment or create .env file
  5) python main.py --device airpods --src en --tgt es --translator google

Usage examples:
  python main.py --list-devices
  python main.py --device airpods --src en --tgt es
  python main.py --device discord --src en --tgt es --translator deepl
  python main.py --test-capture airpods  # Test audio capture for 10 seconds
"""
"""Configuration and utility functions"""
import os
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def bool_str(value: bool) -> str:
    """Convert boolean to string for Deepgram API"""
    return "true" if value else "false"


def get_deepgram_api_key() -> Optional[str]:
    """Get Deepgram API key from environment"""
    return os.getenv("DEEPGRAM_API_KEY")


def get_deepl_api_key() -> Optional[str]:
    """Get DeepL API key from environment"""
    return os.getenv("DEEPL_API_KEY")


class Config:
    """Application configuration"""
    
    # Default values
    DEFAULT_SOURCE_LANG = "en"
    DEFAULT_TARGET_LANG = "es"
    DEFAULT_MODEL = "nova-2"
    DEFAULT_ENDPOINTING_MS = 300
    DEFAULT_FRAMES_PER_BUFFER = 960
    DEFAULT_TRANSLATOR = "google"
    
    # Audio settings
    AUDIO_FORMAT = "linear16"
    PREFERRED_CHANNELS = 2
    FALLBACK_CHANNELS = 1
    DEFAULT_FRAMES_PER_BUFFER = 480  # Reduced from 960 for lower latency (10ms vs 20ms)
    
    def __init__(self):
        self.deepgram_api_key = get_deepgram_api_key()
        self.deepl_api_key = get_deepl_api_key()

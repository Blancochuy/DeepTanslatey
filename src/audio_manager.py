"""Audio device management for loopback capture"""
from __future__ import annotations

import wave
from datetime import datetime
from typing import Optional

import pyaudiowpatch as pyaudio


class AudioDeviceManager:
    """Manages audio device discovery and validation"""

    @staticmethod
    def list_loopback_devices() -> list[tuple[int, dict]]:
        """List all available loopback devices"""
        audio = pyaudio.PyAudio()
        devices = []

        try:
            try:
                wasapi = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            except Exception:
                print("[error] WASAPI not available. Ensure pyaudiowpatch is installed:")
                print("        pip install pyaudiowpatch")
                return devices

            for i in range(wasapi["deviceCount"]):
                info = audio.get_device_info_by_host_api_device_index(wasapi["index"], i)
                name = info.get("name") or ""
                is_loop = bool(info.get("isLoopbackDevice") == 1 or "loopback" in name.lower())

                if is_loop and info.get("maxInputChannels", 0) > 0:
                    devices.append((info["index"], info))
        finally:
            audio.terminate()

        return devices

    @staticmethod
    def find_device(device_filter: str = "") -> tuple[Optional[int], Optional[dict]]:
        """Find a loopback device by filter string"""
        audio = pyaudio.PyAudio()

        try:
            try:
                wasapi = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            except Exception:
                print("[ERROR] WASAPI not available")
                return None, None

            chosen_index = None
            chosen_info = None
            default_device = None

            for i in range(wasapi["deviceCount"]):
                info = audio.get_device_info_by_host_api_device_index(wasapi["index"], i)
                name = (info.get("name") or "").lower()
                is_loop = bool(info.get("isLoopbackDevice") == 1 or "loopback" in name)

                if not is_loop or info.get("maxInputChannels", 0) <= 0:
                    continue

                # Check if this is the default device
                is_default = info.get("isDefaultDevice", False) or "default" in name
                
                if device_filter and device_filter.lower() not in name:
                    # Store first valid loopback as fallback
                    if chosen_index is None:
                        chosen_index = info["index"]
                        chosen_info = info
                    continue

                # Found matching device
                chosen_index = info["index"]
                chosen_info = info

                # Prefer default device if available
                if is_default:
                    default_device = (chosen_index, chosen_info)
                    break

            # Return default if found, otherwise first valid
            if default_device:
                return default_device
            return chosen_index, chosen_info
        finally:
            audio.terminate()

    @staticmethod
    def find_device_by_index(device_index: int) -> tuple[Optional[int], Optional[dict]]:
        """Find a device by its index directly"""
        audio = pyaudio.PyAudio()

        try:
            try:
                wasapi = audio.get_host_api_info_by_type(pyaudio.paWASAPI)
            except Exception:
                print("[ERROR] WASAPI not available")
                return None, None

            for i in range(wasapi["deviceCount"]):
                info = audio.get_device_info_by_host_api_device_index(wasapi["index"], i)
                
                if info["index"] == device_index:
                    is_loop = bool(info.get("isLoopbackDevice") == 1 or "loopback" in info.get("name", "").lower())
                    
                    if is_loop and info.get("maxInputChannels", 0) > 0:
                        return info["index"], info
                    else:
                        print(f"[ERROR] Device {device_index} is not a valid loopback device")
                        return None, None
            
            print(f"[ERROR] Device index {device_index} not found")
            return None, None
        finally:
            audio.terminate()

    @staticmethod
    def test_capture(device_index: int, device_info: dict, duration: int = 10) -> bool:
        """Test audio capture by recording to WAV file"""
        sample_rate = int(device_info.get("defaultSampleRate", 48000))
        channels = 2

        print(f"\n[TEST] Device: {device_info['name']}")
        print(f"[TEST] Sample rate: {sample_rate} Hz, Channels: {channels}")
        print(f"[TEST] Recording {duration} seconds...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_capture_{timestamp}.wav"

        audio = pyaudio.PyAudio()

        try:
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
            )
        except Exception as e:
            print(f"[ERROR] Failed to open stream: {e}")
            audio.terminate()
            return False

        wf = wave.open(filename, 'wb')
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(sample_rate)

        print("[TEST] Recording... (play audio now)")

        frames = int(sample_rate * duration / 1024)

        try:
            for i in range(frames):
                data = stream.read(1024, exception_on_overflow=False)
                wf.writeframes(data)

                progress = (i + 1) / frames
                bar_length = 40
                filled = int(bar_length * progress)
                bar = '#' * filled + '-' * (bar_length - filled)
                print(f'\r[{bar}] {progress*100:.0f}%', end='', flush=True)

            print(f"\n[TEST] Saved to: {filename}")
            print("[TEST] Open this file to verify audio was captured")
            return True

        except Exception as e:
            print(f"\n[ERROR] Capture failed: {e}")
            return False
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
            wf.close()


class AudioStream:
    """Wrapper for PyAudio stream with automatic fallback"""
    
    def __init__(self, device_index: int, device_info: dict, frames_per_buffer: int = 960):
        self.device_index = device_index
        self.device_info = device_info
        self.frames_per_buffer = frames_per_buffer
        self.sample_rate = int(device_info.get("defaultSampleRate", 48000))
        self.audio = None
        self.stream = None
        self.channels = 2
    
    def open(self) -> bool:
        """Open audio stream with automatic stereo/mono fallback"""
        self.audio = pyaudio.PyAudio()
        
        # Try stereo first
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=2,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.frames_per_buffer,
            )
            self.channels = 2
            return True
        except Exception as e:
            print(f"[warn] Stereo failed ({e}), trying mono...")
            
            # Fallback to mono
            try:
                self.stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.sample_rate,
                    input=True,
                    input_device_index=self.device_index,
                    frames_per_buffer=self.frames_per_buffer,
                )
                self.channels = 1
                return True
            except Exception as e2:
                print(f"[error] Failed to open audio stream: {e2}")
                self.audio.terminate()
                return False
    
    def read(self, num_frames: Optional[int] = None) -> bytes:
        """Read audio data from stream"""
        if not self.stream:
            raise RuntimeError("Stream not opened")
        
        frames = num_frames or self.frames_per_buffer
        return self.stream.read(frames, exception_on_overflow=False)
    
    def close(self) -> None:
        """Close audio stream"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()

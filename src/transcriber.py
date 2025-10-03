"""Deepgram transcription engine with optimizations"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional, Callable
from queue import Queue, Empty
from dataclasses import dataclass

from deepgram import DeepgramClient
from deepgram.core.events import EventType
from deepgram.extensions.types.sockets.listen_v1_control_message import ListenV1ControlMessage
from deepgram.extensions.types.sockets.listen_v1_results_event import ListenV1ResultsEvent

from .audio_manager import AudioStream
from .translator import TranslationService
from .config import bool_str, Config


@dataclass
class TranscriptionEvent:
    """Event data for transcription callbacks"""
    transcript: str
    translation: Optional[str]
    is_final: bool
    timestamp: str


class DeepgramTranscriber:
    """Main transcription engine with Deepgram and async translation"""

    def __init__(
        self,
        deepgram_api_key: str,
        source_language: str = "en",
        target_language: str = "es",
        translator_mode: str = "google",
        deepl_api_key: Optional[str] = None,
        enable_interim: bool = True,
        model: str = "nova-2",
        endpointing_ms: int = 300,
        on_transcription: Optional[Callable[[TranscriptionEvent], None]] = None,
    ) -> None:
        self.source_lang = source_language
        self.target_lang = target_language
        self.enable_interim = enable_interim
        self.model = model
        self.endpointing_ms = endpointing_ms
        self.on_transcription = on_transcription

        self.is_recording = False
        self.frames_per_buffer = Config.DEFAULT_FRAMES_PER_BUFFER

        # Translation with caching enabled
        self.translator = TranslationService(
            translator_mode,
            self.source_lang,
            self.target_lang,
            deepl_api_key,
            enable_cache=True,
        )

        self.client = DeepgramClient(api_key=deepgram_api_key)

        # Statistics
        self.transcription_count = 0
        self.bytes_sent = 0
        self.last_transcript = ""
        self.last_translation = ""
        
        # Async translation queue with max size to prevent backlog
        self.translation_queue = Queue(maxsize=100)
        self.translation_thread = None

    def _translation_worker(self) -> None:
        """Worker thread for async translations"""
        while self.is_recording or not self.translation_queue.empty():
            try:
                item = self.translation_queue.get(timeout=0.5)
                transcript, timestamp, callback = item
                
                # Perform translation
                translation = self.translator.translate(transcript)
                self.last_translation = translation
                
                # Trigger callback if provided
                if callback:
                    callback(transcript, translation, timestamp)
                
                self.translation_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                print(f"[error] Translation worker error: {e}")

    def start(self, device_index: int, device_info: dict) -> None:
        """Start transcription from audio device"""
        
        # Open audio stream
        audio_stream = AudioStream(device_index, device_info, self.frames_per_buffer)
        
        if not audio_stream.open():
            print("[error] Failed to open audio stream")
            return

        print("\n" + "=" * 70)
        print("REALTIME TRANSCRIPTION ACTIVE")
        print("=" * 70)
        print(f"Device           : {device_info['name']}")
        print(f"Source language  : {self.source_lang}")
        print(f"Target language  : {self.target_lang if self.translator.impl else 'none (no translation)'}")
        print(f"Model            : {self.model}")
        print(f"Sample rate      : {audio_stream.sample_rate} Hz")
        print(f"Channels         : {audio_stream.channels}")
        print(f"Interim results  : {'enabled' if self.enable_interim else 'disabled'}")
        print(f"Translation cache: enabled")
        print("=" * 70)
        print("\nListening... Press Ctrl+C to stop\n")

        # Start translation worker thread
        self.is_recording = True
        self.translation_thread = threading.Thread(
            target=self._translation_worker,
            name="translation-worker",
            daemon=True,
        )
        self.translation_thread.start()

        try:
            with self.client.listen.v1.connect(
                model=self.model,
                language=self.source_lang,
                smart_format=bool_str(True),
                interim_results=bool_str(self.enable_interim),
                punctuate=bool_str(True),
                encoding=Config.AUDIO_FORMAT,
                sample_rate=str(audio_stream.sample_rate),
                channels=str(audio_stream.channels),
                endpointing=str(self.endpointing_ms),
                vad_events=bool_str(True),
            ) as connection:

                connection.on(EventType.MESSAGE, self._build_message_handler())
                connection.on(EventType.ERROR, self._build_error_handler())
                connection.on(EventType.CLOSE, self._build_close_handler())

                listener_thread = threading.Thread(
                    target=connection.start_listening,
                    name="deepgram-listener",
                    daemon=True,
                )
                listener_thread.start()

                try:
                    while self.is_recording:
                        data = audio_stream.read()
                        connection.send_media(data)
                        self.bytes_sent += len(data)

                except KeyboardInterrupt:
                    print("\n\n[info] Stopping capture...")
                finally:
                    self.is_recording = False
                    try:
                        connection.send_control(ListenV1ControlMessage(type="CloseStream"))
                    except Exception:
                        pass
                    listener_thread.join(timeout=2.0)

        except Exception as e:
            print(f"\n[error] Transcription error: {e}")
        finally:
            self.is_recording = False
            
            # Wait for translation queue to finish
            if self.translation_thread:
                self.translation_thread.join(timeout=5.0)
            
            audio_stream.close()

            # Print summary
            self._print_summary()

    def _print_summary(self) -> None:
        """Print session summary"""
        print("\n" + "=" * 70)
        print("SESSION SUMMARY")
        print("=" * 70)
        print(f"Transcriptions   : {self.transcription_count}")
        print(f"Data sent        : {self.bytes_sent:,} bytes ({self.bytes_sent/1024/1024:.2f} MB)")
        if self.last_transcript:
            print(f"Last transcript  : {self.last_transcript[:60]}...")
        if self.last_translation:
            print(f"Last translation : {self.last_translation[:60]}...")
        print("=" * 70)

    def _build_message_handler(self):
        """Build message handler for Deepgram events"""
        def handler(event) -> None:
            if not isinstance(event, ListenV1ResultsEvent):
                return

            transcript = event.channel.alternatives[0].transcript.strip()
            if not transcript:
                return

            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            if event.is_final:
                self.transcription_count += 1
                self.last_transcript = transcript
                print(f"\n[{timestamp}] [TRANSCRIPT] {transcript}")

                # Trigger callback for transcript
                if self.on_transcription:
                    event_data = TranscriptionEvent(
                        transcript=transcript,
                        translation=None,
                        is_final=True,
                        timestamp=timestamp,
                    )
                    self.on_transcription(event_data)
                
                # Queue translation asynchronously
                if self.translator.impl is not None:
                    def handle_translation(trans: str, transl: str, ts: str):
                        print(f"[{ts}] [TRANSLATION] {transl}")
                        # Trigger callback with translation
                        if self.on_transcription:
                            translation_event = TranscriptionEvent(
                                transcript=trans,
                                translation=transl,
                                is_final=True,
                                timestamp=ts,
                            )
                            self.on_transcription(translation_event)
                    
                    # Use put_nowait to avoid blocking if queue is full
                    try:
                        self.translation_queue.put_nowait((transcript, timestamp, handle_translation))
                    except:
                        # Queue full, skip this translation to avoid backlog
                        print(f"[WARN] Translation queue full, skipping...")

            elif self.enable_interim:
                print(f"\r[{timestamp}] ... {transcript}   ", end="", flush=True)
                
                # Trigger callback for interim
                if self.on_transcription:
                    event_data = TranscriptionEvent(
                        transcript=transcript,
                        translation=None,
                        is_final=False,
                        timestamp=timestamp,
                    )
                    self.on_transcription(event_data)

        return handler

    def _build_error_handler(self):
        """Build error handler for Deepgram events"""
        def handler(error) -> None:
            print(f"\n[error] Deepgram error: {error}")

        return handler

    def _build_close_handler(self):
        """Build close handler for Deepgram events"""
        def handler(_unused) -> None:
            print("\n[info] Deepgram connection closed")

        return handler

    def stop(self) -> None:
        """Stop transcription"""
        self.is_recording = False

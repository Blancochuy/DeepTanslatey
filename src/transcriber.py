"""Deepgram transcription engine with optimizations"""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Optional, Callable
from queue import Queue, Empty
from dataclasses import dataclass
import time

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
        self.start_time = time.time()
        self.audio_read_times = []
        self.translation_times = []
        
        # Async translation queue with max size to prevent backlog
        self.translation_queue = Queue(maxsize=100)
        self.translation_thread = None
        
        # Keepalive mechanism
        self.keepalive_thread = None
        self.last_audio_time = 0

    def _translation_worker(self) -> None:
        """Worker thread for async batch translations"""
        batch_items = []
        
        while self.is_recording or not self.translation_queue.empty() or batch_items:
            try:
                # Collect items for batch processing
                while len(batch_items) < 5 and not self.translation_queue.empty():
                    try:
                        item = self.translation_queue.get_nowait()
                        batch_items.append(item)
                    except Empty:
                        break
                
                # Process batch if we have items
                if batch_items:
                    self._process_translation_batch(batch_items)
                    # Mark all items as done
                    for _ in batch_items:
                        self.translation_queue.task_done()
                    batch_items = []
                else:
                    # Wait for new items
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"[error] Translation worker error: {e}")
        
        # Process any remaining items
        if batch_items:
            self._process_translation_batch(batch_items)
            for _ in batch_items:
                self.translation_queue.task_done()

    def _process_translation_batch(self, batch_items: list) -> None:
        """Process a batch of translation requests"""
        if not batch_items:
            return
        
        # Extract texts and metadata
        texts = [item[0] for item in batch_items]
        timestamps = [item[1] for item in batch_items]
        callbacks = [item[2] for item in batch_items]
        
        # Perform batch translation
        translate_start = time.time()
        translations = self.translator.translate_batch(texts)
        translate_time = time.time() - translate_start
        
        # Record timing (average per item)
        avg_time = translate_time / len(translations)
        for _ in range(len(translations)):
            self.translation_times.append(avg_time)
        if len(self.translation_times) > 50:
            self.translation_times = self.translation_times[-50:]
        
        # Process results
        for i, (text, translation, timestamp, callback) in enumerate(zip(texts, translations, timestamps, callbacks)):
            self.last_translation = translation
            
            # Trigger callback if provided
            if callback:
                callback(text, translation, timestamp)
            
            # Mark queue item as done (for the first item, others weren't in queue)
            if i == 0:
                # Only the first item was actually from the queue
                pass
    
    def _keepalive_worker(self, connection) -> None:
        """Send keepalive packets during silence to prevent connection timeout"""
        import time
        silence_packet = b'\x00' * 1920  # 20ms of silence at 48kHz stereo
        
        while self.is_recording:
            try:
                time.sleep(5.0)  # Check every 5 seconds
                current_time = time.time()
                
                # If no audio sent in last 8 seconds, send keepalive
                if current_time - self.last_audio_time > 8.0:
                    connection.send_media(silence_packet)
                    # Don't update last_audio_time so we keep sending keepalives
            except Exception as e:
                # Connection might be closed, that's ok
                break

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
                
                # Start keepalive thread
                import time
                self.last_audio_time = time.time()
                self.keepalive_thread = threading.Thread(
                    target=self._keepalive_worker,
                    args=(connection,),
                    name="keepalive-worker",
                    daemon=True,
                )
                self.keepalive_thread.start()

                try:
                    while self.is_recording:
                        try:
                            read_start = time.time()
                            data = audio_stream.read()
                            read_time = time.time() - read_start
                            self.audio_read_times.append(read_time)
                            if len(self.audio_read_times) > 100:  # Keep last 100
                                self.audio_read_times.pop(0)
                            
                            if data:
                                connection.send_media(data)
                                self.bytes_sent += len(data)
                                self.last_audio_time = time.time()
                        except Exception as read_error:
                            print(f"\n[warn] Audio read error: {read_error}")
                            time.sleep(0.1)  # Brief pause before retry
                            continue

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
        total_time = time.time() - self.start_time
        avg_audio_read = sum(self.audio_read_times) / len(self.audio_read_times) if self.audio_read_times else 0
        avg_translation = sum(self.translation_times) / len(self.translation_times) if self.translation_times else 0
        
        print("\n" + "=" * 70)
        print("SESSION SUMMARY")
        print("=" * 70)
        print(f"Transcriptions   : {self.transcription_count}")
        print(f"Data sent        : {self.bytes_sent:,} bytes ({self.bytes_sent/1024/1024:.2f} MB)")
        print(f"Session time     : {total_time:.1f} seconds")
        print(f"Avg audio read   : {avg_audio_read*1000:.1f} ms")
        print(f"Avg translation  : {avg_translation*1000:.1f} ms")
        if self.transcription_count > 0:
            print(f"Transcripts/min  : {self.transcription_count / (total_time/60):.1f}")
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
        def handler(event) -> None:
            if self.is_recording:
                print("\n[warn] Deepgram connection closed unexpectedly!")
                print("[info] This may be due to:")
                print("  - Audio device stopped sending data")
                print("  - Network interruption")
                print("  - Deepgram timeout (no audio for 12+ seconds)")
            else:
                print("\n[info] Deepgram connection closed")

        return handler

    def stop(self) -> None:
        """Stop transcription"""
        self.is_recording = False

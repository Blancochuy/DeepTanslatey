"""Simple, lightweight GUI for transcription and translation"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
from typing import Optional

from .audio_manager import AudioDeviceManager
from .transcriber import DeepgramTranscriber, TranscriptionEvent
from .config import Config


class TranscriptionGUI:
    """Main GUI window"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Audio Transcription & Translation")
        self.root.geometry("800x600")
        
        self.config = Config()
        self.transcriber: Optional[DeepgramTranscriber] = None
        self.is_running = False
        self.device_index: Optional[int] = None
        self.device_info: Optional[dict] = None
        
        self._setup_ui()
        self._load_devices()
        
    def _setup_ui(self):
        """Setup UI components"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # === Controls Frame ===
        controls_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        controls_frame.columnconfigure(1, weight=1)
        
        # Device selection
        ttk.Label(controls_frame, text="Audio Device:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.device_combo = ttk.Combobox(controls_frame, state="readonly")
        self.device_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        
        # Language settings
        lang_frame = ttk.Frame(controls_frame)
        lang_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(lang_frame, text="From:").pack(side=tk.LEFT, padx=(0, 5))
        self.source_lang = ttk.Combobox(lang_frame, width=10, values=["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh"])
        self.source_lang.set("en")
        self.source_lang.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(lang_frame, text="To:").pack(side=tk.LEFT, padx=(0, 5))
        self.target_lang = ttk.Combobox(lang_frame, width=10, values=["es", "en", "fr", "de", "it", "pt", "ja", "ko", "zh"])
        self.target_lang.set("es")
        self.target_lang.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(lang_frame, text="Translator:").pack(side=tk.LEFT, padx=(0, 5))
        self.translator_mode = ttk.Combobox(lang_frame, width=12, values=["google", "deepl", "none"], state="readonly")
        self.translator_mode.set("google")
        self.translator_mode.pack(side=tk.LEFT)
        
        # Model and options
        options_frame = ttk.Frame(controls_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(options_frame, text="Model:").pack(side=tk.LEFT, padx=(0, 5))
        self.model = ttk.Combobox(options_frame, width=12, values=["nova-2", "nova", "base"], state="readonly")
        self.model.set("nova-2")
        self.model.pack(side=tk.LEFT, padx=(0, 20))
        
        self.interim_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Show interim results", variable=self.interim_var).pack(side=tk.LEFT)
        
        # Start/Stop button
        self.start_button = ttk.Button(controls_frame, text="Start", command=self._toggle_transcription)
        self.start_button.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        
        # === Status Bar ===
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.status_label = ttk.Label(status_frame, text="Ready", foreground="gray")
        self.status_label.pack(side=tk.LEFT)
        
        self.stats_label = ttk.Label(status_frame, text="", foreground="gray")
        self.stats_label.pack(side=tk.RIGHT)
        
        # === Transcript Display ===
        transcript_frame = ttk.LabelFrame(main_frame, text="Transcript", padding="5")
        transcript_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)
        
        self.transcript_text = scrolledtext.ScrolledText(
            transcript_frame,
            wrap=tk.WORD,
            height=10,
            font=("Segoe UI", 10),
            bg="#f5f5f5",
        )
        self.transcript_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # === Translation Display ===
        translation_frame = ttk.LabelFrame(main_frame, text="Translation", padding="5")
        translation_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        translation_frame.columnconfigure(0, weight=1)
        translation_frame.rowconfigure(0, weight=1)
        
        self.translation_text = scrolledtext.ScrolledText(
            translation_frame,
            wrap=tk.WORD,
            height=10,
            font=("Segoe UI", 10),
            bg="#f0f8ff",
        )
        self.translation_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # === Clear Button ===
        clear_button = ttk.Button(main_frame, text="Clear All", command=self._clear_text)
        clear_button.grid(row=4, column=0, sticky=tk.E, pady=(5, 0))
        
    def _load_devices(self):
        """Load available audio devices"""
        devices = AudioDeviceManager.list_loopback_devices()
        
        if not devices:
            self.device_combo['values'] = ["No devices found - play audio to detect"]
            self.device_combo.current(0)
            self.device_combo.config(state="disabled")
        else:
            device_names = [f"[{idx}] {info['name']}" for idx, info in devices]
            self.device_combo['values'] = device_names
            self.device_combo.current(0)
            
    def _toggle_transcription(self):
        """Start or stop transcription"""
        if not self.is_running:
            self._start_transcription()
        else:
            self._stop_transcription()
            
    def _start_transcription(self):
        """Start transcription in background thread"""
        # Validate settings
        if not self.config.deepgram_api_key:
            self._show_error("DEEPGRAM_API_KEY not found in environment")
            return
            
        device_text = self.device_combo.get()
        if not device_text or "No devices" in device_text:
            self._show_error("No audio device selected")
            return
        
        # Extract device index
        try:
            self.device_index = int(device_text.split("]")[0].strip("["))
        except:
            self._show_error("Invalid device selection")
            return
            
        # Find device info
        devices = AudioDeviceManager.list_loopback_devices()
        self.device_info = None
        for idx, info in devices:
            if idx == self.device_index:
                self.device_info = info
                break
                
        if not self.device_info:
            self._show_error("Device not found")
            return
        
        # Create transcriber
        self.transcriber = DeepgramTranscriber(
            deepgram_api_key=self.config.deepgram_api_key,
            source_language=self.source_lang.get(),
            target_language=self.target_lang.get(),
            translator_mode=self.translator_mode.get(),
            deepl_api_key=self.config.deepl_api_key,
            enable_interim=self.interim_var.get(),
            model=self.model.get(),
            on_transcription=self._on_transcription,
        )
        
        # Start in background thread
        self.is_running = True
        self.start_button.config(text="Stop")
        self.status_label.config(text="Running...", foreground="green")
        
        # Disable controls
        self.device_combo.config(state="disabled")
        self.source_lang.config(state="disabled")
        self.target_lang.config(state="disabled")
        self.translator_mode.config(state="disabled")
        self.model.config(state="disabled")
        
        def run_transcriber():
            try:
                self.transcriber.start(self.device_index, self.device_info)
            except Exception as e:
                self.root.after(0, lambda: self._show_error(f"Error: {e}"))
            finally:
                self.root.after(0, self._stop_transcription)
        
        thread = threading.Thread(target=run_transcriber, daemon=True)
        thread.start()
        
    def _stop_transcription(self):
        """Stop transcription"""
        if self.transcriber:
            self.transcriber.stop()
            
        self.is_running = False
        self.start_button.config(text="Start")
        self.status_label.config(text="Stopped", foreground="gray")
        
        # Re-enable controls
        self.device_combo.config(state="readonly")
        self.source_lang.config(state="normal")
        self.target_lang.config(state="normal")
        self.translator_mode.config(state="readonly")
        self.model.config(state="readonly")
        
        # Update stats
        if self.transcriber:
            self.stats_label.config(
                text=f"Total: {self.transcriber.transcription_count} transcriptions, "
                     f"{self.transcriber.bytes_sent/1024/1024:.2f} MB"
            )
        
    def _on_transcription(self, event: TranscriptionEvent):
        """Handle transcription event from background thread"""
        def update_ui():
            if event.is_final:
                # Add to transcript if it's new
                if event.translation is None:
                    # This is the original transcript
                    self.transcript_text.insert(tk.END, f"[{event.timestamp}] {event.transcript}\n")
                    self.transcript_text.see(tk.END)
                else:
                    # This is a translation update
                    self.translation_text.insert(tk.END, f"[{event.timestamp}] {event.translation}\n")
                    self.translation_text.see(tk.END)
                
                # Update stats
                if self.transcriber:
                    self.stats_label.config(
                        text=f"{self.transcriber.transcription_count} transcriptions"
                    )
            else:
                # Show interim in status
                self.status_label.config(text=f"... {event.transcript[:50]}", foreground="orange")
        
        # Schedule UI update on main thread
        self.root.after(0, update_ui)
        
    def _clear_text(self):
        """Clear all text areas"""
        self.transcript_text.delete(1.0, tk.END)
        self.translation_text.delete(1.0, tk.END)
        self.stats_label.config(text="")
        
    def _show_error(self, message: str):
        """Show error message"""
        self.status_label.config(text=f"Error: {message}", foreground="red")


def run_gui():
    """Run the GUI application"""
    root = tk.Tk()
    app = TranscriptionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()

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

        # Set window size and position
        window_width = 900
        window_height = 700

        # Center window on screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(800, 600)  # Minimum size
        self.root.maxsize(1400, 1000)  # Maximum size

        self.config = Config()
        self.transcriber: Optional[DeepgramTranscriber] = None
        self.is_running = False
        self.device_index: Optional[int] = None
        self.device_info: Optional[dict] = None

        # Animation state
        self._pulse_id = None
        self._fade_queue = []

        self._setup_ui()
        self._setup_keyboard_shortcuts()
        self._load_devices()

    def _setup_ui(self):
        """Setup UI components"""
        # Configure styles
        style = ttk.Style()
        style.configure('Big.TButton', font=('Segoe UI', 11, 'bold'), padding=10)
        style.configure('Status.TLabel', font=('Segoe UI', 10))

        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)  # Transcript area
        main_frame.rowconfigure(4, weight=1)  # Translation area

        # === Controls Frame ===
        controls_frame = ttk.LabelFrame(main_frame, text=" Settings ", padding="15")
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        controls_frame.columnconfigure(1, weight=1)

        # Device selection
        ttk.Label(controls_frame, text="Audio Device:", font=('Segoe UI', 10)).grid(row=0, column=0, sticky=tk.W, pady=8)
        self.device_combo = ttk.Combobox(controls_frame, state="readonly", font=('Segoe UI', 10))
        self.device_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=8)

        # Language settings
        lang_frame = ttk.Frame(controls_frame)
        lang_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)

        ttk.Label(lang_frame, text="From:", font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.source_lang = ttk.Combobox(lang_frame, width=10, font=('Segoe UI', 10),
                                        values=["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh"])
        self.source_lang.set("en")
        self.source_lang.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(lang_frame, text="To:", font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.target_lang = ttk.Combobox(lang_frame, width=10, font=('Segoe UI', 10),
                                        values=["es", "en", "fr", "de", "it", "pt", "ja", "ko", "zh"])
        self.target_lang.set("es")
        self.target_lang.pack(side=tk.LEFT, padx=(0, 20))

        ttk.Label(lang_frame, text="Translator:", font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.translator_mode = ttk.Combobox(lang_frame, width=12, font=('Segoe UI', 10),
                                            values=["google", "deepl", "none"], state="readonly")
        self.translator_mode.set("google")
        self.translator_mode.pack(side=tk.LEFT)

        # Model and options
        options_frame = ttk.Frame(controls_frame)
        options_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)

        ttk.Label(options_frame, text="Model:", font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.model = ttk.Combobox(options_frame, width=12, font=('Segoe UI', 10),
                                  values=["nova-2", "nova", "base"], state="readonly")
        self.model.set("nova-2")
        self.model.pack(side=tk.LEFT, padx=(0, 20))

        self.interim_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Show interim results",
                       variable=self.interim_var).pack(side=tk.LEFT)

        # Start/Stop button with bigger style
        self.start_button = ttk.Button(controls_frame, text="▶ Start Recording",
                                      command=self._toggle_transcription,
                                      style='Big.TButton')
        self.start_button.grid(row=3, column=0, columnspan=2, pady=(15, 0), sticky=(tk.W, tk.E))

        # === Status Bar ===
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Status indicator dot
        self.status_dot = tk.Canvas(status_frame, width=12, height=12, bg=self.root['bg'], highlightthickness=0)
        self.status_dot.pack(side=tk.LEFT, padx=(0, 8))
        self.status_dot_id = self.status_dot.create_oval(2, 2, 10, 10, fill="gray", outline="")

        self.status_label = ttk.Label(status_frame, text="Ready to start",
                                      foreground="#666666", style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT)

        self.stats_label = ttk.Label(status_frame, text="",
                                     foreground="#666666", style='Status.TLabel')
        self.stats_label.pack(side=tk.RIGHT)

        # === Separator ===
        ttk.Separator(main_frame, orient='horizontal').grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # === Transcript Display ===
        transcript_frame = ttk.LabelFrame(main_frame, text=" Transcript ", padding="10")
        transcript_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        transcript_frame.columnconfigure(0, weight=1)
        transcript_frame.rowconfigure(0, weight=1)

        # Configure text tags for styling
        self.transcript_text = scrolledtext.ScrolledText(
            transcript_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#2c3e50",
            relief=tk.FLAT,
            padx=10,
            pady=10,
            spacing1=0,
            spacing2=0,
            spacing3=4,
        )
        self.transcript_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Tags for styling
        self.transcript_text.tag_configure("timestamp", foreground="#7f8c8d", font=("Segoe UI", 9))
        self.transcript_text.tag_configure("text", foreground="#2c3e50", font=("Segoe UI", 11))
        self.transcript_text.tag_configure("interim", foreground="#95a5a6", font=("Segoe UI", 10, "italic"))

        # === Translation Display ===
        translation_frame = ttk.LabelFrame(main_frame, text=" Translation ", padding="10")
        translation_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        translation_frame.columnconfigure(0, weight=1)
        translation_frame.rowconfigure(0, weight=1)

        self.translation_text = scrolledtext.ScrolledText(
            translation_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            bg="#f8f9fa",
            fg="#34495e",
            relief=tk.FLAT,
            padx=10,
            pady=10,
            spacing1=0,
            spacing2=0,
            spacing3=4,
        )
        self.translation_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Tags for styling
        self.translation_text.tag_configure("timestamp", foreground="#7f8c8d", font=("Segoe UI", 9))
        self.translation_text.tag_configure("text", foreground="#34495e", font=("Segoe UI", 11))

        # === Action Buttons ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, sticky=(tk.E), pady=(5, 0))

        ttk.Button(button_frame, text="Refresh Devices", command=self._load_devices).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Clear All", command=self._clear_text).pack(side=tk.LEFT)

    def _setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Enter to start/stop
        self.root.bind('<Return>', lambda e: self._toggle_transcription())
        # Ctrl+L to clear
        self.root.bind('<Control-l>', lambda e: self._clear_text())
        # Ctrl+R to refresh devices
        self.root.bind('<Control-r>', lambda e: self._load_devices())
        # Escape to stop if running
        self.root.bind('<Escape>', lambda e: self._stop_transcription() if self.is_running else None)

    def _animate_status_dot(self, color1: str, color2: str):
        """Animate status dot with subtle pulse"""
        if self._pulse_id:
            self.root.after_cancel(self._pulse_id)

        def pulse(step=0):
            if not self.is_running:
                return

            # Simple two-color alternation for subtle pulse
            current_color = color1 if step % 2 == 0 else color2
            self.status_dot.itemconfig(self.status_dot_id, fill=current_color)

            self._pulse_id = self.root.after(800, lambda: pulse(step + 1))

        if self.is_running:
            pulse()

    def _stop_animation(self):
        """Stop status dot animation"""
        if self._pulse_id:
            self.root.after_cancel(self._pulse_id)
            self._pulse_id = None

    def _fade_in_text(self, widget, text: str, tag: str = None):
        """Add text with subtle fade-in effect (lightweight)"""
        # Simple insert with immediate display (no complex fade for performance)
        widget.insert(tk.END, text, tag)
        widget.see(tk.END)

    def _update_status(self, text: str, color: str, dot_color: str):
        """Update status with smooth transition"""
        self.status_label.config(text=text, foreground=color)
        self.status_dot.itemconfig(self.status_dot_id, fill=dot_color)

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
        self.start_button.config(text="■ Stop Recording")
        self._update_status("Recording...", "#27ae60", "#27ae60")

        # Start pulse animation
        self._animate_status_dot("#27ae60", "#2ecc71")

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

        # Stop animation
        self._stop_animation()

        self.is_running = False
        self.start_button.config(text="▶ Start Recording")
        self._update_status("Stopped", "#95a5a6", "gray")

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
                    timestamp_text = f"[{event.timestamp}] "
                    self.transcript_text.insert(tk.END, timestamp_text, "timestamp")
                    self._fade_in_text(self.transcript_text, f"{event.transcript}\n", "text")
                else:
                    # This is a translation update
                    timestamp_text = f"[{event.timestamp}] "
                    self.translation_text.insert(tk.END, timestamp_text, "timestamp")
                    self._fade_in_text(self.translation_text, f"{event.translation}\n", "text")

                # Update stats
                if self.transcriber:
                    self.stats_label.config(
                        text=f"{self.transcriber.transcription_count} transcriptions"
                    )
            else:
                # Show interim in status with different color
                preview = event.transcript[:60] + "..." if len(event.transcript) > 60 else event.transcript
                self._update_status(f"Listening: {preview}", "#3498db", "#3498db")

        # Schedule UI update on main thread
        self.root.after(0, update_ui)

    def _clear_text(self):
        """Clear all text areas"""
        self.transcript_text.delete(1.0, tk.END)
        self.translation_text.delete(1.0, tk.END)
        self.stats_label.config(text="")

    def _show_error(self, message: str):
        """Show error message"""
        self._update_status(f"Error: {message}", "#e74c3c", "#e74c3c")
        # Auto-clear error after 5 seconds
        self.root.after(5000, lambda: self._update_status("Ready to start", "#666666", "gray") if not self.is_running else None)


def run_gui():
    """Run the GUI application"""
    root = tk.Tk()
    app = TranscriptionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()

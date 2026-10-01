"""
Regex statement options for debug menu
"""

import tkinter as tk
from tkinter import ttk

from .base import DebugOption


class RegexSection(DebugOption):
    """Section that stores a free-form regex statement string."""

    SECTION_NAME = "Regex Statement"

    def create(self):
        self.frame = ttk.Frame(self.parent, style="DebugSection.TFrame")
        self.frame.columnconfigure(0, weight=1)

        input_frame = tk.Frame(self.frame, bg=self.config.dark_bg)
        input_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 6))
        input_frame.columnconfigure(0, weight=1)

        self.regex_text = tk.Text(
            input_frame,
            bg="#111111",
            fg="white",
            insertbackground="white",
            relief="flat",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#2a2a2a",
            highlightcolor="#3a3a3a",
            font=("Consolas", 9),
            height=3,
            wrap="word"
        )
        self.regex_text.grid(row=0, column=0, sticky="ew", padx=(0, 0), pady=(0, 6))

        existing_value = str(getattr(self.config, "regex_statement", ""))
        if existing_value:
            self.regex_text.insert("1.0", existing_value)

        btn_save = ttk.Button(
            self.frame,
            text="Save Regex Statement",
            command=self._save_regex_statement,
            style="Debug.TButton",
            cursor="hand2"
        )
        btn_save.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        return self.frame

    def _save_regex_statement(self):
        raw = self.regex_text.get("1.0", "end-1c")
        self.config.regex_statement = raw
        self.config.save_debug_options()
        print("Regex statement saved.")

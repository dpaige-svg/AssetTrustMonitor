"""
Trash management options for debug menu
"""
import tkinter as tk
from tkinter import ttk

from ..toggle_switch import ToggleSwitch
from .base import DebugOption


class TrashSection(DebugOption):
    """Trash management section with toggle and button"""
    SECTION_NAME = "Asset Management"
    
    def __init__(self, parent, config, managers):
        super().__init__(parent, config, managers)
        # self.auto_trash_state = None
    
    def get_required_managers(self):
        return ['file_monitor']
    
    def create(self):
        """Create trash management section with modern styling"""
        self.frame = ttk.Frame(self.parent, style="DebugSection.TFrame")
        self.frame.columnconfigure(0, weight=1)

        # Auto Remove Toggle Row
        toggle_frame = tk.Frame(self.frame, bg=self.config.dark_bg)
        toggle_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 6))
        toggle_frame.columnconfigure(0, weight=1)

        lbl_auto = tk.Label(toggle_frame, text="Auto-clean Trash", 
                          bg=self.config.dark_bg, fg="white", 
                          font=("Segoe UI", 9), anchor="w")
        lbl_auto.grid(row=0, column=0, sticky="w", padx=(2, 0))

        # Read the value directly from config
        initial_value = str(getattr(self.config, "auto_clean_trash", "false")).lower() == "true"
        self.auto_trash_state = initial_value

        # Create toggle switch
        toggle = ToggleSwitch(toggle_frame, value=initial_value, command=self._toggle_auto_trash, 
                            bg=self.config.dark_bg, width=38, height=20)
        toggle.grid(row=0, column=1, sticky="e", padx=(0, 2))

        # Remove from Trash Button - Full width for sleek look
        btn_trash = ttk.Button(self.frame, text="Empty Trash", command=self._remove_from_trash,
                             style="Debug.TButton", cursor="hand2")

        btn_trash.grid(row=1, column=0, sticky="ew", padx=0, pady=0)

        return self.frame
    
    def _toggle_auto_trash(self, value):
        """Toggle auto trash cleaning setting"""
        # self.auto_trash_state = value
        self.config.auto_clean_trash = "true" if value else "false"
        self.config.save_debug_options()
        print(f"Auto clean trash set to: {self.config.auto_clean_trash}")

    def _remove_from_trash(self):
        """Remove .rbxm files from Recycle Bin"""
        if self.managers.get('file_monitor'):
            if self.managers['file_monitor'].empty_recycle_bin():
                # We can't easily know how many were deleted without parsing stdout, 
                # but the script runs.
                pass
        else:
            print("File monitor not available")
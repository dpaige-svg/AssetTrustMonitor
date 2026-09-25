"""
Restart options for debug menu
"""
import tkinter as tk
from tkinter import ttk
from .base import DebugOption


class RestartSection(DebugOption):
    """Restart buttons section"""
    SECTION_NAME = "Service Control"
    
    def get_required_managers(self):
        return ['studio_manager', 'rojo_server']
    
    def create(self):
        """Create restart buttons with modern layout"""
        self.frame = ttk.Frame(self.parent, style="DebugSection.TFrame")
        
        # Configure columns for uniform sizing
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)

        # Row 1: Studio and Rojo (Side by Side)
        btn_studio = ttk.Button(self.frame, text="Restart Studio", command=self._restart_studio,
                              style="Debug.TButton", cursor="hand2")
        btn_studio.grid(row=0, column=0, padx=(0, 2), pady=(0, 4), sticky="ew")

        btn_rojo = ttk.Button(self.frame, text="Restart Rojo", command=self._restart_rojo,
                            style="Debug.TButton", cursor="hand2")
        btn_rojo.grid(row=0, column=1, padx=(2, 0), pady=(0, 4), sticky="ew")

        # Row 2: Restart Both (Full Width)
        btn_both = ttk.Button(self.frame, text="Restart Both", command=self._restart_both,
                            style="Debug.TButton", cursor="hand2")
        btn_both.grid(row=1, column=0, columnspan=2, padx=0, pady=0, sticky="ew")

        return self.frame

        return self.frame
    
    def _restart_studio(self):
        """Refresh Roblox Studio instance"""
        if 'studio_manager' in self.managers:
            self.managers['studio_manager'].restart()
    
    def _restart_rojo(self):
        """Refresh Rojo server instance"""
        if 'rojo_server' in self.managers:
            self.managers['rojo_server'].restart()
    
    def _restart_both(self):
        """Refresh both Roblox Studio and Rojo server"""
        self._restart_studio()
        self._restart_rojo()
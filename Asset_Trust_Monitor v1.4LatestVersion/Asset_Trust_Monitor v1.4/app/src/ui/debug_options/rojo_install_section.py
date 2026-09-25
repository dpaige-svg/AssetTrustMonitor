"""
Rojo installation options for debug menu
"""
import tkinter as tk
from tkinter import ttk
from .base import DebugOption


class RojoInstallSection(DebugOption):
    """Rojo installation section"""
    SECTION_NAME = "Development Tools"
    
    def get_required_managers(self):
        return ['update_manager', 'studio_manager', 'rojo_server']
    
    def create(self):
        """Create Rojo installation button with modern styling"""
        self.frame = ttk.Frame(self.parent, style="DebugSection.TFrame")
        
        # Rojo install button with icon
        btn_install = ttk.Button(self.frame, text="Reinstall Rojo", command=self._reinstall_rojo,
                               style="Debug.TButton", cursor="hand2")
        
        btn_install.grid(row=0, column=0, padx=8, pady=4, sticky="")
        
        # Configure grid weights for centering
        self.frame.grid_columnconfigure(0, weight=1)
        
        return self.frame
    
    def _reinstall_rojo(self):
        """Perform fresh install of the current Rojo version"""
        if 'update_manager' in self.managers:
            self.managers['update_manager'].rebuild_rokit_and_plugin(  
                studio_manager=self.managers.get('studio_manager'),
                rojo_server=self.managers.get('rojo_server'),
                show_success_message=True
            )
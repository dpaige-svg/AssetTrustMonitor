"""
Maintenance options for debug menu (Cache & Tools)
"""
from tkinter import ttk

from .base import DebugOption


class MaintenanceSection(DebugOption):
    """Maintenance section combining cache and tools"""
    SECTION_NAME = "Maintenance"
    
    def get_required_managers(self):
        return ['cache_manager', 'update_manager', 'studio_manager', 'rojo_server']
    
    def create(self):
        """Create maintenance buttons in a compact layout"""
        self.frame = ttk.Frame(self.parent, style="DebugSection.TFrame")
        
        # Configure columns for 2-column layout
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        
        # Clear Cache Button
        btn_cache = ttk.Button(self.frame, text="Clear Cache", command=self._clear_cache,
                             style="Debug.TButton", cursor="hand2")
        btn_cache.grid(row=0, column=0, padx=(0, 4), pady=0, sticky="ew")
        
        # Reinstall Rojo Button
        btn_install = ttk.Button(self.frame, text="Reinstall Rojo", command=self._reinstall_rojo,
                               style="Debug.TButton", cursor="hand2")
        btn_install.grid(row=0, column=1, padx=(4, 0), pady=0, sticky="ew")
        
        return self.frame
    
    def _clear_cache(self):
        """Clear application software cache"""
        if 'cache_manager' in self.managers:
            self.managers['cache_manager'].clear_cache()

    def _reinstall_rojo(self):
        """Perform fresh install of the current Rojo version"""
        if 'update_manager' in self.managers:
            self.managers['update_manager'].rebuild_rokit_and_plugin(  
                studio_manager=self.managers.get('studio_manager'),
                rojo_server=self.managers.get('rojo_server'),
                show_success_message=True
            )

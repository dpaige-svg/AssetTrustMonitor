"""
Cache management options for debug menu
"""
from tkinter import ttk

from .base import DebugOption


class CacheSection(DebugOption):
    """Cache management section"""
    SECTION_NAME = "Cache Management"
    
    def get_required_managers(self):
        return ['cache_manager']
    
    def create(self):
        """Create cache management button with modern styling"""
        self.frame = ttk.Frame(self.parent, style="DebugSection.TFrame")
        
        # Cache button with icon
        btn_cache = ttk.Button(self.frame, text="Clear Cache", command=self._clear_cache,
                             style="Debug.TButton", cursor="hand2")
        
        btn_cache.grid(row=0, column=0, padx=8, pady=4, sticky="")
        
        # Configure grid weights for centering
        self.frame.grid_columnconfigure(0, weight=1)
        
        return self.frame
    
    def _clear_cache(self):
        """Clear application software cache"""
        if 'cache_manager' in self.managers:
            self.managers['cache_manager'].clear_cache()
#!/usr/bin/env python3

"""
Asset Trust Monitor - Restructured Main Entry Point

Clean architecture with organized modules.
"""

import sys
import os
from tkinter import messagebox

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Core modules
from src.core import Config, CacheManager  # type: ignore

# Managers (setup/installation)
from src.managers import RokitManager, UpdateManager, RojoManager, LuneManager, PluginManager, UIManager  # type: ignore

# Services (runtime operations)
from src.services import RojoServer, StudioManager, FileMonitor  # type: ignore

# UI components
from src.ui import SystemTray, DebugMenu  # type: ignore

# Utilities
from src.core.utils import Utils  # type: ignore

class AssetTrustMonitor:
    """Main application orchestrator"""
    
    def __init__(self):
        print("Asset Trust Monitor Started")
        
        # Core configuration (singleton)
        self.config = Config()
        
        # Managers (tools setup)
        self.rokit_mgr = RokitManager(self.config)
        self.update_mgr = UpdateManager(self.config)
        self.rojo_mgr = RojoManager(self.config)
        self.lune_mgr = LuneManager(self.config)
        self.plugin_mgr = PluginManager(self.config)
        self.utils = Utils(default_cwd=self.config.rojo_cwd)
        self.cache_manager = CacheManager()
        
        # Services (runtime)
        self.rojo_server = RojoServer(self.config)
        self.studio_manager = StudioManager(self.config)
        self.file_monitor = FileMonitor(self.config, self.rojo_server, self.lune_mgr)
        
        # Debug menu
        self.debug_menu = DebugMenu(self.config, self.studio_manager, self.rojo_server, self.update_mgr, self.cache_manager, self.file_monitor, parent=None)
        
        
        # UI components (initialized later)
        self.ui = None
        self.tray = None
    
    def setup_tools(self):
        """Install and configure all required tools"""
        print("Setting up tools...")
        
        # Install Rokit and tools
        if not self.rokit_mgr.install_tools():
            messagebox.showerror("Error", "Failed to install tools")
            return False
        
        print("Tools installed")
        
        # Install Rojo plugin
        if not self.plugin_mgr.install_rojo_plugin():
            messagebox.showerror("Error", "Failed to install Rojo plugin")
            return False
        
        print("Rojo plugin installed")
        return True
    
    def start_services(self):
        """Start all background services"""
        print("Starting services...")
        
        # Start Rojo server
        if not self.rojo_server.start():
            messagebox.showerror("Error", "Failed to start Rojo server")
            return False
        
        # Start monitorings
        self.rojo_server.start_status_monitoring()
        self.file_monitor.start_asset_counting()
        
        print("Services started")
        return True
    
    def start_studio(self):
        """Open Roblox Studio"""
        if not self.studio_manager.start():
            print("Failed to start Roblox Studio (continuing anyway)")
        return True
    
    def initialize_ui(self):
        """Initialize user interface"""
        self.ui = UIManager(
            self.config,
            self.file_monitor,
            self.rojo_server,
            self.cleanup,
            studio_manager=self.studio_manager,
            enable_debug_menu=True
        )
        
        self.tray = SystemTray(self.ui.root, cleanup_callback=self.cleanup)
        self.ui.set_system_tray(self.tray)
        
        return True
    
    def run(self):
        """Main application entry point"""
        
        try:
            # Setup phase
            if not self.utils.retry_function(self.setup_tools, retries=3, delay=2):
                print("Failed to setup tools, rebuilding dependencies...")
                if not self.update_mgr.rebuild_rokit_and_plugins():
                    print("Rebuild failed, exiting")
                    sys.exit(1)

            # Start services
            if not self.utils.retry_function(self.start_services, retries=3, delay=2):
                print("Failed to start services, rebuilding dependencies...")
                if not self.update_mgr.rebuild_rokit_and_plugins():
                    print("Rebuild failed, exiting")
                    sys.exit(1)
            
            # Start Studio
            if not self.utils.retry_function(self.start_studio, retries=3, delay=2):
                print("Failed to start Roblox Studio, rebuilding dependencies...")
                if not self.update_mgr.rebuild_rokit_and_plugins():
                    print("Rebuild failed, exiting")
                    sys.exit(1)
            
            # Initialize UI
            if not self.utils.retry_function(self.initialize_ui, retries=3, delay=2):
                print("Failed to initialize UI, rebuilding dependencies...")
                if not self.update_mgr.rebuild_rokit_and_plugins():
                    print("Rebuild failed, exiting")
                    sys.exit(1)
            
            # Run GUI
            print("✓ All systems initialized - launching GUI...")
            self.ui.run()
            
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            self.cleanup()
        except Exception as e:
            print(f"Fatal error: {e}")
            messagebox.showerror("Fatal Error", str(e))
            self.cleanup()
            sys.exit(1)
    
    def cleanup(self):
        """Cleanup before exit"""
        print("Cleaning up...")
        
        if self.file_monitor:
            self.file_monitor.stop_monitoring()
        
        if self.rojo_server:
            self.rojo_server.stop()
            
        if self.studio_manager:
            self.studio_manager.stop()

        if self.tray:
            self.tray.stop()
        
        print("Cleanup complete")

def main():
    """Application entry point"""
    app = AssetTrustMonitor()
    app.run()


if __name__ == "__main__":
    main()

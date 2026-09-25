#!/usr/bin/env python3
"""
Asset Trust Monitor - Main Entry Point

Author: Gevan Sims
Compatibility: Windows and macOS  
Created: 10/8/2025

Modular Asset Trust Monitor with clean class-based architecture.
"""

import sys
import os
import platform
import subprocess
from tkinter import messagebox

# Import Modules
from src.config import Config
from src.rokit_manager import RokitManager
from src.rojo_server import RojoServer
from src.file_monitor import FileMonitor
from src.ui_manager import UIManager
from src.system_tray import SystemTray
from src.studio_manager import StudioManager

class AssetTrustMonitor:
    """Main application class that orchestrates all components"""
    
    def __init__(self):
        print("Asset Trust Monitor Started")
        
        # Initialize configuration
        self.config = Config()
        
        # Initialize managers
        self.rokit_manager = RokitManager(self.config)
        self.rojo_server = RojoServer(self.config)
        self.file_monitor = FileMonitor(self.config, self.rojo_server)
        self.studio_manager = StudioManager(self.config)
        
        # UI components (initialized later)
        self.ui_manager = None
        self.system_tray = None
        
    def initialize_tools(self):
        """Setup and verify all required tools"""
        print("Setting up Rokit toolchain...")
        
        # Install and configure Rokit
        if not self.rokit_manager.check_and_install_rokit():
            messagebox.showerror("Error", "Failed to install or configure Rokit")
            return False
        
        print("Rokit Installed")
        
        # Integrate Lune and Rojo
        if not self.rokit_manager.integrate_lune_with_rojo():
            messagebox.showerror("Error", "Failed to integrate Lune with Rojo")
            return False
        
        print("Lune and Rojo Integrated")
        
        # Check Rojo plugin
        if not self.rojo_server.check_plugin_installed():
            messagebox.showerror("Error", "Failed to install Rojo plugin")
            return False
        
        print("Rojo Plugin Installed")
        
        return True
    
    def start_roblox_studio(self):
        """Open Roblox Studio with the project file"""
        return self.studio_manager.start()
    
    def start_services(self):
        """Start background services"""
        # Start Rojo server
        if not self.rojo_server.start():
            messagebox.showerror("Error", "Failed to start Rojo server")
            return False
        
        print("Rojo Server Started")
        
        # Start status monitoring
        self.rojo_server.start_status_monitoring()
        
        # Start asset counting
        self.file_monitor.start_asset_counting()
        
        return True
    
    def initialize_ui(self):
        """Initialize user interface components"""
        self.ui_manager = UIManager(
            self.config,
            self.file_monitor,
            self.rojo_server,
            self._cleanup,
            studio_manager=self.studio_manager,
        )
        
        # Create system tray
        self.system_tray = SystemTray(self.ui_manager.root, cleanup_callback=self._cleanup)
        
        # Connect system tray to UI manager
        self.ui_manager.set_system_tray(self.system_tray)
        
        return True
    
    def run(self):
        """Main application entry point"""
        try:
            # Initialize tools and services
            if not self.initialize_tools():
                sys.exit(1)
            
            # Start Roblox Studio
            if not self.start_roblox_studio():
                # Continue even if Studio fails to open
                print("Failed to start Roblox Studio")
                pass
            
            # Start background services
            if not self.start_services():
                print("Failed to start background services")
                sys.exit(1)
            
            # Initialize and run UI
            if not self.initialize_ui():
                sys.exit(1)
            
            # Start the main GUI loop
            self.ui_manager.run()
            
        except KeyboardInterrupt:
            print("\nApplication interrupted by user")
            self._cleanup()
        except Exception as e:
            print(f"Fatal error: {e}")
            messagebox.showerror("Fatal Error", f"Application failed to start: {e}")
            self._cleanup()
            sys.exit(1)
    
    def _cleanup(self):
        """Clean up resources before exit"""
        print("Cleaning up...")
        
        if self.file_monitor:
            self.file_monitor.stop_monitoring()
        
        if self.rojo_server:
            self.rojo_server.stop()

        # Close Roblox Studio if it was opened
        if self.studio_manager:
            self.studio_manager.stop()
        
        if self.system_tray:
            self.system_tray.stop()
        
        print("Cleanup complete")
        

def main():
    """Application entry point"""
    app = AssetTrustMonitor()
    app.run()

if __name__ == "__main__":
    main()
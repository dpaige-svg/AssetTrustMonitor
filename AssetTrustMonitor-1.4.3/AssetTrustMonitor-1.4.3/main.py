#!/usr/bin/env python3

"""
Asset Trust Monitor - Restructured Main Entry Point

Clean architecture with organized modules.
"""

import sys
import os
import ctypes
import atexit
from tkinter import messagebox

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def _load_application_modules():
    """Load the established application only after startup validation succeeds."""
    global Config, CacheManager, install_stdio_capture
    global RokitManager, UpdateManager, RojoManager, LuneManager, PluginManager, UIManager
    global RojoServer, StudioManager, FileMonitor, SystemTray, DebugMenu, Utils

    from src.core import Config, CacheManager, install_stdio_capture  # type: ignore
    from src.managers import (  # type: ignore
        RokitManager, UpdateManager, RojoManager, LuneManager, PluginManager, UIManager,
    )
    from src.services import RojoServer, StudioManager, FileMonitor  # type: ignore
    from src.ui import SystemTray, DebugMenu  # type: ignore
    from src.core.utils import Utils  # type: ignore


def _configure_tcl_tk_env():
    """Set Tcl/Tk environment paths when running from a virtual environment."""
    base_prefix = getattr(sys, "base_prefix", sys.prefix)
    tcl_root = os.path.join(base_prefix, "tcl")
    tcl_library = os.path.join(tcl_root, "tcl8.6")
    tk_library = os.path.join(tcl_root, "tk8.6")

    if os.path.isdir(tcl_library) and "TCL_LIBRARY" not in os.environ:
        os.environ["TCL_LIBRARY"] = tcl_library
    if os.path.isdir(tk_library) and "TK_LIBRARY" not in os.environ:
        os.environ["TK_LIBRARY"] = tk_library


def _show_error_dialog(title, message):
    """Show an error dialog with a Windows API fallback if Tk cannot initialize."""
    try:
        messagebox.showerror(title, message)
        return
    except Exception:
        pass

    try:
        ctypes.windll.user32.MessageBoxW(None, str(message), str(title), 0x10)
    except Exception:
        print(f"{title}: {message}", file=sys.stderr)


def _set_console_visibility(visible: bool):
    """Show or hide the Windows console window when available."""
    if os.name != "nt":
        return

    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if not hwnd:
            return

        sw_show = 5
        sw_hide = 0
        ctypes.windll.user32.ShowWindow(hwnd, sw_show if visible else sw_hide)
    except Exception:
        pass

class AssetTrustMonitor:
    """Main application orchestrator"""
    
    def __init__(self, *, debug_startup=False):
        print("Asset Trust Monitor Started")
        self.debug_startup = debug_startup
        self._cleanup_done = False
        atexit.register(self.cleanup)
        
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
            _show_error_dialog("Error", "Failed to install tools")
            return False
        
        print("Tools installed")
        
        # Install Rojo plugin
        if not self.plugin_mgr.install_rojo_plugin():
            _show_error_dialog("Error", "Failed to install Rojo plugin")
            return False

        if not self.plugin_mgr.is_rojo_installed():
            _show_error_dialog("Error", "Rojo plugin verification failed after installation")
            return False
        
        print("Rojo plugin installed")

        # Install bundled local mirror plugin
        if not self.plugin_mgr.install_local_mirror_plugin():
            _show_error_dialog("Error", "Failed to install local mirror plugin")
            return False

        if not self.plugin_mgr.is_local_mirror_plugin_installed():
            _show_error_dialog("Error", "Local mirror plugin verification failed after installation")
            return False

        print("Local mirror plugin installed")
        return True
    
    def start_services(self):
        """Start all background services"""
        print("Starting services...")
        
        # Start Rojo server
        if not self.rojo_server.start():
            _show_error_dialog("Error", "Failed to start Rojo server")
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
            # Keep console hidden by default; only reveal on hard-failure paths.
            _set_console_visibility(False)

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

            gui_rendered = False
            try:
                self.ui.root.update_idletasks()
                self.ui.root.update()
                gui_rendered = bool(self.ui.root.winfo_exists() and self.ui.root.winfo_viewable())
            except Exception as render_error:
                print(f"GUI pre-render check failed: {render_error}")
            
            # Run GUI
            print("All systems initialized - launching GUI...")
            _set_console_visibility(False)
            self.ui.run()
            
        except KeyboardInterrupt:
            print("\nInterrupted by user")
            _set_console_visibility(False)
            self.cleanup()
        except SystemExit:
            _set_console_visibility(False)
            raise
        except Exception as e:
            _set_console_visibility(False)
            print(f"Fatal error: {e}")
            _show_error_dialog("Fatal Error", str(e))
            self.cleanup()
            sys.exit(1)
    
    def cleanup(self):
        """Staged shutdown: stop each service independently so one failure
        does not prevent the rest from being torn down."""
        if self._cleanup_done:
            return
        self._cleanup_done = True

        print("Shutting down...")

        steps = [
            ("file monitor",   lambda: self.file_monitor.stop_monitoring()  if self.file_monitor  else None),
            ("rojo server",    lambda: self.rojo_server.stop()               if self.rojo_server   else None),
            ("studio manager", lambda: self.studio_manager.stop()            if self.studio_manager else None),
            ("system tray",    lambda: self.tray.stop()                      if self.tray          else None),
        ]

        for name, fn in steps:
            try:
                fn()
                print(f"  OK: {name} stopped")
            except Exception as e:
                print(f"  ERROR: {name} stop failed: {e}")

        print("Shutdown complete.")

def main():
    """Application entry point"""
    _set_console_visibility(False)
    _configure_tcl_tk_env()
    debug_startup = "--debug-startup" in sys.argv
    failure_stage = None
    for argument in sys.argv[1:]:
        if argument.startswith("--test-startup-error=") and debug_startup:
            try:
                failure_stage = int(argument.split("=", 1)[1])
            except ValueError:
                failure_stage = 1

    try:
        from src.startup import run_startup_sequence

        def create_application():
            _load_application_modules()
            install_stdio_capture()
            return AssetTrustMonitor(debug_startup=debug_startup)

        qt_application, startup_result, app = run_startup_sequence(
            debug=debug_startup,
            failure_stage=failure_stage,
            application_factory=create_application,
            enforce_single_instance=True,
        )
    except Exception as error:
        _show_error_dialog("Startup Error", f"AssetTrustMonitor could not start:\n\n{error}")
        return 1

    if not startup_result.success:
        return 1

    if app is None:
        _show_error_dialog("Startup Error", "Application initialization returned no instance")
        return 1
    app.run()
    del qt_application
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

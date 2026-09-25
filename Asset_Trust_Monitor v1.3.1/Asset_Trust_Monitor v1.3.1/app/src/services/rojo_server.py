#!/usr/bin/env python3
"""
Rojo Server Management

Handles Rojo server lifecycle and monitoring.
"""

import platform
import subprocess
import threading
import time
import os
from tkinter import messagebox

from ..core.config import Config
from ..core.utils import Utils
from ..core.process_manager import ProcessManager


class RojoServer:
    """Manages Rojo server operations"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.utils = Utils(default_cwd=self.config.rojo_cwd)
        self.process_mgr = ProcessManager(self.utils)
        self.is_windows = platform.system() == 'Windows'
        
        self.process = None
        self.pid = None
        self._running = False
        self._status_callbacks = []
    
    def _clean_corrupted_files(self):
        """Scan workspace for corrupted .rbxm files and remove them"""
        try:
            workspace_path = os.path.join(self.config.rojo_cwd, "src", "Workspace")
            if not os.path.exists(workspace_path):
                return

            for filename in os.listdir(workspace_path):
                if filename.endswith(".rbxm"):
                    filepath = os.path.join(workspace_path, filename)
                    try:
                        # Check file size
                        if os.path.getsize(filepath) == 0:
                            print(f"Removing empty asset: {filename}")
                            os.remove(filepath)
                            continue
                            
                        # Check header
                        with open(filepath, 'rb') as f:
                            header = f.read(8)
                            # Check for binary header signature <roblox!
                            if not header.startswith(b'<roblox!'):
                                print(f"Removing corrupted asset (invalid header): {filename}")
                                f.close()
                                os.remove(filepath)
                    except Exception as e:
                        print(f"Error checking file {filename}: {e}")
        except Exception as e:
            print(f"Error cleaning workspace: {e}")

    def start(self):
        """Start the Rojo server"""
        # Clean up corrupted files before starting
        self._clean_corrupted_files()

        if self._running:
            # Double check if it's actually running
            if self.is_running():
                print("Rojo server already running")
                return True
            else:
                # It was marked running but isn't, so proceed to start
                self._running = False
        
        try:
            # Try to find absolute path to rojo for reliability
            rojo_cmd = 'rojo'
            if self.config.tool_exists('rojo'):
                rojo_cmd = self.config.get_tool_executable('rojo')

            if self.is_windows:
                self.process = subprocess.Popen(
                    [rojo_cmd, 'serve'], 
                    cwd=self.config.rojo_cwd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            elif platform.system() == 'Darwin':
                # On macOS, try to run in a new Terminal window to match Windows behavior
                # and avoid tracking issues with blocking pipes
                try:
                    cwd = os.path.abspath(self.config.rojo_cwd)
                    # Create a command that runs rojo and keeps terminal open
                    # We use 'exec' so the shell is replaced by rojo, making tracking easier if we could get the PID
                    script = f'tell application "Terminal" to do script "cd \\"{cwd}\\" && \\"{rojo_cmd}\\" serve"'
                    
                    # Run osascript
                    subprocess.run(['osascript', '-e', script], check=True)
                    
                    # Give it a moment to start
                    time.sleep(1)
                    
                    # Find the PID of the rojo process
                    # We use pgrep to look for 'rojo'
                    # -n selects the newest (most recently started) matching process
                    try:
                        # Use -f to match full command line which helps identify 'rojo serve'
                        pid_output = subprocess.check_output(['pgrep', '-n', '-f', 'rojo'])
                        self.pid = int(pid_output.strip())
                        self._running = True
                        print(f"Rojo server started in Terminal (PID: {self.pid})")
                        
                        # We don't have a Popen object for the external process, 
                        # but we have the PID for tracking
                        self.process = None 
                        return True
                    except subprocess.CalledProcessError:
                        print("Rojo server started but PID could not be found")
                        self._running = True # Assume running even if we missed PID
                        self.pid = None
                        self.process = None
                        return True
                        
                except Exception as e:
                    print(f"Failed to launch in Terminal, falling back to background: {e}")
                    # Fallback to background execution with no pipes to avoid freezing
                    self.process = subprocess.Popen(
                        [rojo_cmd, 'serve'],
                        cwd=self.config.rojo_cwd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
            else:
                self.process = subprocess.Popen(
                    [rojo_cmd, 'serve'],
                    cwd=self.config.rojo_cwd,
                    stdout=subprocess.DEVNULL, # Use DEVNULL to avoid blocking reads
                    stderr=subprocess.DEVNULL
                )
            
            self.pid = self.process.pid
            self._running = True
            print(f"Rojo server started (PID: {self.pid})")
            return True
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start Rojo server: {e}")
            return False
    
    def stop(self):
        """Stop the Rojo server"""
        # terminate all rojo processes
        # We ignore the result because if it fails, it likely means no process was running
        process_name = "rojo.exe" if self.is_windows else "rojo"
        self.process_mgr.terminate_process_by_name(process_name)
        
        # If we have a specific PID, try to kill it directly as well to be safe
        if self.pid:
            self.process_mgr.kill_process(self.pid)
        
        # Always clear state
        self._running = False
        self.pid = None
        self.process = None
        print("Rojo server stopped")
        
        return True
    
    def restart(self):
        """Restart the Rojo server"""
        print("Restarting Rojo server...")
        self.stop()
        return self.start()
    
    def is_running(self):
        """Check if server is running"""
        if not self.pid:
            return False
        
        # Check by PID and name to ensure we're tracking the right process
        # and not the parent application or a recycled PID
        process_name = "rojo.exe" if self.is_windows else "rojo"
        is_running = self.process_mgr.is_process_running(self.pid, process_name=process_name)

        # Only print non-empty output, and do not block
        if self.process and self.process.stdout:
            try:
                # Use non-blocking read if possible, or skip reading here
                output = self.process.stdout.read().decode().strip()
                if output:
                    print(f"Rojo server output: {output}")
            except Exception:
                pass
        
        if not is_running and self._running:
            print(f"Rojo server PID {self.pid} no longer running")
            self.pid = None
            self._running = False
        
        return is_running
    
    def add_status_callback(self, callback):
        """Add status change callback"""
        self._status_callbacks.append(callback)
    
    def start_status_monitoring(self):
        """Start background status monitoring"""
        def monitor_loop():
            while True:
                time.sleep(5)
                try:
                    is_running = self.is_running()
                    for callback in self._status_callbacks:
                        callback(is_running)
                except Exception as e:
                    print(f"Error in status monitoring: {e}")
        
        threading.Thread(target=monitor_loop, daemon=True).start()

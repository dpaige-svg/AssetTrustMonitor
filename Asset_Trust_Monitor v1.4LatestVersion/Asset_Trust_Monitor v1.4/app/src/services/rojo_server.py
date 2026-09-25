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
import requests
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

    def _windows_hidden_popen_kwargs(self):
        """Return Popen kwargs that keep console windows hidden on Windows."""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        return {
            "startupinfo": startupinfo,
            "creationflags": creation_flags,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }

    def _find_folder_in_rojo_payload(self, payload, expected_name):
        """Recursively search Rojo API payload for a folder named expected_name."""
        if isinstance(payload, dict):
            name = payload.get("Name") or payload.get("name")
            class_name = payload.get("ClassName") or payload.get("className")
            children = payload.get("Children") or payload.get("children")

            if name == expected_name and class_name == "Folder" and isinstance(children, list):
                return True

            for value in payload.values():
                if self._find_folder_in_rojo_payload(value, expected_name):
                    return True

        elif isinstance(payload, list):
            for item in payload:
                if self._find_folder_in_rojo_payload(item, expected_name):
                    return True

        return False

    def _query_rojo_for_asset_folder(self, expected_folder_name):
        """Try known Rojo API read shapes to locate the expected folder."""
        endpoint_candidates = [
            "http://127.0.0.1:34872/api/read/Workspace/WorkSpace",
            "http://127.0.0.1:34872/api/read/Workspace",
            "http://127.0.0.1:34872/api/read/game/Workspace/WorkSpace",
            "http://127.0.0.1:34872/api/read/game/Workspace",
        ]

        param_candidates = [
            "game/Workspace/WorkSpace",
            "game/Workspace",
            "Workspace/WorkSpace",
            "Workspace",
        ]

        for url in endpoint_candidates:
            try:
                response = requests.get(url, timeout=1.0)
                if response.status_code != 200:
                    continue
                payload = response.json()
                if self._find_folder_in_rojo_payload(payload, expected_folder_name):
                    return True
            except Exception:
                continue

        for path in param_candidates:
            try:
                response = requests.get("http://127.0.0.1:34872/api/read", params={"path": path}, timeout=1.0)
                if response.status_code != 200:
                    continue
                payload = response.json()
                if self._find_folder_in_rojo_payload(payload, expected_folder_name):
                    return True
            except Exception:
                continue

        return False

    def verify_workspace_asset(self, asset_filename, timeout_seconds=4.0):
        """Verify an asset was inserted by checking Rojo web data and workspace file presence."""
        expected_folder_name = os.path.splitext(asset_filename)[0]
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            try:
                if self._query_rojo_for_asset_folder(expected_folder_name):
                    return True
            except Exception:
                pass

            workspace_path = os.path.join(self.config.workspace_folder, asset_filename)
            if os.path.isfile(workspace_path):
                return True

            time.sleep(0.25)

        return False
    
    def _clean_corrupted_files(self):
        """Scan workspace for malformed Roblox model files and remove them."""
        try:
            workspace_path = os.path.join(self.config.rojo_cwd, "src", "Workspace")
            if not os.path.exists(workspace_path):
                return

            for filename in os.listdir(workspace_path):
                if filename.endswith((".rbxm", ".rbxmx")):
                    filepath = os.path.join(workspace_path, filename)
                    try:
                        # Check file size
                        if os.path.getsize(filepath) == 0:
                            print(f"Removing empty asset: {filename}")
                            os.remove(filepath)
                            continue
                            
                        # Check header
                        with open(filepath, 'rb') as f:
                            header = f.read(128)
                            normalized_header = header.lstrip()
                            expected_prefixes = (b'<roblox!',) if filename.endswith('.rbxm') else (b'<?xml', b'<roblox')
                            if not normalized_header.startswith(expected_prefixes):
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
                popen_kwargs = self._windows_hidden_popen_kwargs()
                self.process = subprocess.Popen(
                    [rojo_cmd, 'serve'],
                    cwd=self.config.rojo_cwd,
                    **popen_kwargs
                )
            elif platform.system() == 'Darwin':
                # Run in background for consistent PID tracking and clean shutdown.
                self.process = subprocess.Popen(
                    [rojo_cmd, 'serve'],
                    cwd=self.config.rojo_cwd,
                    start_new_session=True,
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
        # Prefer tracked PID shutdown first for accurate process ownership.
        if self.pid:
            if platform.system() == 'Darwin':
                self.process_mgr.graceful_kill_group(self.pid, process_name='rojo', timeout=4)
            else:
                self.process_mgr.kill_process(self.pid)

        # Fallback: terminate by process name if anything remained.
        process_name = "rojo.exe" if self.is_windows else "rojo"
        self.process_mgr.terminate_process_by_name(process_name)

        # Extra macOS fallback for command-line variants.
        if platform.system() == 'Darwin':
            self.process_mgr.terminate_process_by_name("rojo serve")
            self.process_mgr.terminate_process_by_name("/rojo serve")
        
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

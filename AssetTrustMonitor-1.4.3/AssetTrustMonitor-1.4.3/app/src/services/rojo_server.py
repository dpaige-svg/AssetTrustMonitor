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
        self._log_file = None
        self._running = False
        self._status_callbacks = []
        self._stop_requested = False
        self._restart_attempts = 0
        self._max_restart_attempts = 3
        self._started_at = None
        self._restart_lock = threading.Lock()
        self._using_existing_server = False

    def _windows_hidden_popen_kwargs(self, output_stream):
        """Return Popen kwargs that keep console windows hidden on Windows."""
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        return {
            "startupinfo": startupinfo,
            "creationflags": creation_flags,
            "stdout": output_stream,
            "stderr": subprocess.STDOUT,
        }

    def _open_log_file(self):
        """Open the persistent Rojo output log for the next server launch."""
        log_path = os.path.join(self.config.datastore_folder, "rojo-server.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"\n[{timestamp}] Starting: rojo serve\n")
        return log_file

    def _close_log_file(self):
        """Close the current Rojo output log handle, if any."""
        if self._log_file:
            try:
                self._log_file.close()
            except (OSError, ValueError) as error:
                print(f"Could not close Rojo log: {error}")
            self._log_file = None

    def _wait_for_startup(self, timeout_seconds=5.0):
        """Wait until the launched process is alive and its HTTP server responds."""
        deadline = time.time() + timeout_seconds
        health_url = "http://127.0.0.1:34872/"
        last_error = "Rojo did not become ready before the startup timeout"

        while time.time() < deadline:
            exit_code = self.process.poll()
            if exit_code is not None:
                return False, f"Rojo exited during startup with code {exit_code}"

            try:
                response = requests.get(health_url, timeout=0.5)
                if response.status_code == 200:
                    return True, None
                last_error = f"Rojo health check returned HTTP {response.status_code}"
            except requests.RequestException as error:
                last_error = f"Rojo health check failed: {error}"

            time.sleep(0.1)

        return False, last_error

    def _compatible_server_is_available(self):
        """Return True when port 34872 serves this Asset Trust project."""
        try:
            response = requests.get("http://127.0.0.1:34872/", timeout=0.75)
            if response.status_code != 200:
                return False

            project_name = os.path.splitext(os.path.basename(self.config.rbxl_file_path))[0]
            return "Rojo Live Server" in response.text and project_name in response.text
        except requests.RequestException:
            return False

    def _describe_port_owner(self, port=34872):
        """Return a best-effort description of the process listening on a port."""
        try:
            if self.is_windows:
                result = self.utils.run_command(
                    ["netstat", "-ano", "-p", "tcp"],
                )
                for line in result.stdout.splitlines():
                    columns = line.split()
                    if len(columns) < 5 or columns[3].upper() != "LISTENING":
                        continue
                    if not columns[1].rsplit(":", 1)[-1] == str(port):
                        continue

                    owner_pid = columns[-1]
                    task = self.utils.run_command(
                        ["tasklist", "/FI", f"PID eq {owner_pid}", "/FO", "CSV", "/NH"],
                    )
                    process_name = task.stdout.strip().split(",", 1)[0].strip('"')
                    return f"port {port} is already owned by PID {owner_pid} ({process_name})"
            else:
                result = subprocess.run(
                    ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
                    capture_output=True,
                    text=True,
                    timeout=3,
                )
                lines = result.stdout.splitlines()
                if len(lines) > 1:
                    columns = lines[1].split()
                    return f"port {port} is already owned by PID {columns[1]} ({columns[0]})"
        except (OSError, subprocess.SubprocessError, IndexError):
            return None

        return None

    def _clean_up_failed_start(self):
        """Terminate only the process created by the current failed start attempt."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except (OSError, subprocess.SubprocessError):
                if self.pid:
                    self.process_mgr.kill_process(self.pid)

        self.process = None
        self.pid = None
        self._using_existing_server = False
        self._running = False
        self._started_at = None
        self._close_log_file()

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
            except (requests.RequestException, ValueError):
                continue

        for path in param_candidates:
            try:
                response = requests.get("http://127.0.0.1:34872/api/read", params={"path": path}, timeout=1.0)
                if response.status_code != 200:
                    continue
                payload = response.json()
                if self._find_folder_in_rojo_payload(payload, expected_folder_name):
                    return True
            except (requests.RequestException, ValueError):
                continue

        return False

    def verify_workspace_asset(self, asset_filename, timeout_seconds=4.0, stop_event=None):
        """Verify an asset was inserted by checking Rojo web data and workspace file presence."""
        expected_folder_name = os.path.splitext(asset_filename)[0]
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            if stop_event and stop_event.is_set():
                return False
            if self._query_rojo_for_asset_folder(expected_folder_name):
                return True

            workspace_path = os.path.join(self.config.workspace_folder, asset_filename)
            if os.path.isfile(workspace_path):
                return True

            if stop_event:
                if stop_event.wait(0.25):
                    return False
            else:
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

    def start(self, automatic=False):
        """Start the Rojo server"""
        if not automatic:
            self._stop_requested = False
            self._restart_attempts = 0

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

        # A previous app instance may have left this same project server alive.
        # Reuse it instead of launching a duplicate that immediately exits due
        # to the fixed port already being occupied.
        if self._compatible_server_is_available():
            self.process = None
            self.pid = None
            self._using_existing_server = True
            self._running = True
            self._started_at = time.time()
            print("Using compatible Rojo server already running on port 34872")
            return True
        
        try:
            # Try to find absolute path to rojo for reliability
            rojo_cmd = 'rojo'
            if self.config.tool_exists('rojo'):
                rojo_cmd = self.config.get_tool_executable('rojo')

            self._close_log_file()
            self._log_file = self._open_log_file()

            if self.is_windows:
                popen_kwargs = self._windows_hidden_popen_kwargs(self._log_file)
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
                    stdout=self._log_file,
                    stderr=subprocess.STDOUT
                )
            else:
                self.process = subprocess.Popen(
                    [rojo_cmd, 'serve'],
                    cwd=self.config.rojo_cwd,
                    stdout=self._log_file,
                    stderr=subprocess.STDOUT
                )
            
            self.pid = self.process.pid
            self._using_existing_server = False
            self._running = True

            ready, startup_error = self._wait_for_startup()
            if not ready:
                port_owner = self._describe_port_owner()
                if port_owner:
                    startup_error = f"{startup_error}; {port_owner}"
                if self._log_file:
                    self._log_file.write(f"Startup validation failed: {startup_error}\n")
                self._clean_up_failed_start()
                print(f"Failed to start Rojo server: {startup_error}")
                return False

            self._started_at = time.time()
            print(f"Rojo server started and ready (PID: {self.pid})")
            return True
            
        except Exception as e:
            self._clean_up_failed_start()
            if automatic:
                print(f"Automatic Rojo restart failed: {e}")
            else:
                messagebox.showerror("Error", f"Failed to start Rojo server: {e}")
            return False
    
    def stop(self):
        """Stop the Rojo server"""
        self._stop_requested = True

        # Only stop the process launched by this instance. On Windows,
        # ProcessManager uses taskkill /T for the tracked PID so any child
        # created by the Rokit shim is included without affecting other Rojo
        # servers owned by the user.
        if self.pid:
            if platform.system() == 'Darwin':
                self.process_mgr.graceful_kill_group(self.pid, process_name='rojo', timeout=4)
            else:
                self.process_mgr.graceful_kill(self.pid, process_name='rojo', timeout=4)
        
        # Always clear state
        self._running = False
        self.pid = None
        self.process = None
        self._using_existing_server = False
        self._started_at = None
        self._close_log_file()
        print("Rojo server stopped")
        
        return True
    
    def restart(self):
        """Restart the Rojo server"""
        print("Restarting Rojo server...")
        self.stop()
        return self.start()
    
    def is_running(self):
        """Check if server is running"""
        if self._using_existing_server:
            is_running = self._compatible_server_is_available()
            if not is_running:
                self._using_existing_server = False
                self._running = False
            return is_running

        if not self.pid:
            return False

        # The owned Popen handle is authoritative and avoids launching tasklist
        # or ps on every status poll. Fall back to PID/name validation only for
        # legacy/adopted state where no process handle is available.
        if self.process is not None:
            is_running = self.process.poll() is None
        else:
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
            self._close_log_file()
        
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

                    if is_running and self._started_at and time.time() - self._started_at >= 30:
                        self._restart_attempts = 0

                    if not is_running and not self._stop_requested:
                        with self._restart_lock:
                            if self._restart_attempts < self._max_restart_attempts:
                                self._restart_attempts += 1
                                print(
                                    "Rojo stopped unexpectedly; automatic restart "
                                    f"{self._restart_attempts}/{self._max_restart_attempts}"
                                )
                                is_running = self.start(automatic=True)
                            elif self._restart_attempts == self._max_restart_attempts:
                                print(
                                    "Rojo automatic restart limit reached; "
                                    "manual restart is required"
                                )
                                self._restart_attempts += 1

                    for callback in self._status_callbacks:
                        callback(is_running)
                except Exception as e:
                    print(f"Error in status monitoring: {e}")
        
        threading.Thread(target=monitor_loop, daemon=True).start()

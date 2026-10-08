#!/usr/bin/env python3
"""
Rojo Server Management

Handles Rojo server lifecycle and monitoring.
"""

import os
import platform
import re
import subprocess
import threading
import time
from tkinter import messagebox

import requests

from ..core.config import Config
from ..core.process_manager import ProcessManager
from ..core.utils import Utils


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
        self.last_error = ""

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

    def _wait_for_startup(self, timeout_seconds=12.0):
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

            project_name = os.path.splitext(os.path.basename(self.config.rbxl_file_path))[0].lower()
            response_text = response.text.lower()
            return "rojo" in response_text and project_name in response_text
        except requests.RequestException:
            return False

    def _get_port_owner(self, port=34872):
        """Return ``(pid, process_name)`` for the listener, when identifiable."""
        try:
            if self.is_windows:
                result = self.utils.run_command(["netstat", "-ano", "-p", "tcp"])
                for line in result.stdout.splitlines():
                    columns = line.split()
                    if len(columns) < 5 or columns[3].upper() != "LISTENING":
                        continue
                    if columns[1].rsplit(":", 1)[-1] != str(port):
                        continue
                    owner_pid = int(columns[-1])
                    task = self.utils.run_command(
                        ["tasklist", "/FI", f"PID eq {owner_pid}", "/FO", "CSV", "/NH"]
                    )
                    process_name = task.stdout.strip().split(",", 1)[0].strip('"')
                    return owner_pid, process_name
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
                    return int(columns[1]), columns[0]
        except (OSError, subprocess.SubprocessError, IndexError, TypeError, ValueError):
            pass
        return None

    def _stop_stale_compatible_server(self):
        """Replace an old AssetTrustMonitor server that points at another folder."""
        owner = self._get_port_owner()
        if not owner:
            self.last_error = "A compatible Rojo server is already running, but its owner could not be identified"
            return False

        owner_pid, process_name = owner
        if process_name.lower() not in {"rojo", "rojo.exe"}:
            self.last_error = (
                f"Port 34872 is owned by PID {owner_pid} ({process_name}), not by Rojo"
            )
            return False

        print(
            "Replacing stale Rojo server on port 34872 so the current "
            "AssetTrustMonitor folder owns live sync"
        )
        if not self.process_mgr.graceful_kill(owner_pid, process_name=process_name, timeout=2):
            self.last_error = f"Could not stop stale Rojo server PID {owner_pid}"
            return False

        deadline = time.time() + 3
        while time.time() < deadline:
            if self._get_port_owner() is None:
                return True
            time.sleep(0.1)

        self.last_error = "The stale Rojo server did not release port 34872"
        return False

    def _describe_port_owner(self, port=34872):
        """Return a best-effort description of the process listening on a port."""
        owner = self._get_port_owner(port)
        if not owner:
            return None
        owner_pid, process_name = owner
        return f"port {port} is already owned by PID {owner_pid} ({process_name})"

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
        """Locate an asset folder in either the Rojo 7.7+ or legacy API."""
        # Rojo 7.7 changed every API response from JSON to MessagePack and
        # changed /api/read to address instances by ID. String keys and values
        # remain UTF-8 in MessagePack, so extracting the root ID and checking
        # the returned tree for the exact asset name does not require another
        # runtime dependency.
        try:
            info_response = requests.get("http://127.0.0.1:34872/api/rojo", timeout=1.0)
            if info_response.status_code == 200:
                root_marker = info_response.content.find(b"rootInstanceId")
                if root_marker >= 0:
                    root_match = re.search(
                        rb"[0-9a-fA-F]{32}", info_response.content[root_marker:]
                    )
                    if root_match:
                        root_id = root_match.group(0).decode("ascii")
                        tree_response = requests.get(
                            f"http://127.0.0.1:34872/api/read/{root_id}", timeout=1.0
                        )
                        if tree_response.status_code == 200:
                            encoded_name = expected_folder_name.encode("utf-8")
                            if encoded_name in tree_response.content:
                                return True
        except (requests.RequestException, UnicodeError):
            pass

        # Rojo 7.6 and earlier returned JSON and accepted path-based reads.
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
        """Verify that the running Rojo service parsed the expected asset folder."""
        expected_folder_name = os.path.splitext(asset_filename)[0]
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            if stop_event and stop_event.is_set():
                return False
            if self._query_rojo_for_asset_folder(expected_folder_name):
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
                    except Exception as e:  # noqa: BLE001
                        print(f"Error checking file {filename}: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"Error cleaning workspace: {e}")

    def start(self, automatic=False):
        """Start the Rojo server"""
        self.last_error = ""
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

        # A previous version may have left the same named project server alive
        # from a different extracted folder. Reusing it would make Studio watch
        # the old folder while this instance writes assets into the new one.
        if self._compatible_server_is_available():
            if not self._stop_stale_compatible_server():
                print(f"Failed to replace stale Rojo server: {self.last_error}")
                return False
        
        try:
            project_file = os.path.join(self.config.rojo_cwd, "default.project.json")
            if not os.path.isfile(project_file):
                raise FileNotFoundError(f"Rojo project file is missing: {project_file}")

            # Try to find absolute path to rojo for reliability
            rojo_cmd = 'rojo'
            if self.config.tool_exists('rojo'):
                rojo_cmd = self.config.get_tool_executable('rojo')

            self._close_log_file()
            self._log_file = self._open_log_file()

            if self.is_windows:
                popen_kwargs = self._windows_hidden_popen_kwargs(self._log_file)
                self.process = subprocess.Popen(
                    [rojo_cmd, 'serve', 'default.project.json', '--port', '34872'],
                    cwd=self.config.rojo_cwd,
                    **popen_kwargs
                )
            elif platform.system() == 'Darwin':
                # Run in background for consistent PID tracking and clean shutdown.
                self.process = subprocess.Popen(
                    [rojo_cmd, 'serve', 'default.project.json', '--port', '34872'],
                    cwd=self.config.rojo_cwd,
                    start_new_session=True,
                    stdout=self._log_file,
                    stderr=subprocess.STDOUT
                )
            else:
                self.process = subprocess.Popen(
                    [rojo_cmd, 'serve', 'default.project.json', '--port', '34872'],
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
                self.last_error = startup_error
                print(f"Failed to start Rojo server: {startup_error}")
                return False

            self._started_at = time.time()
            print(f"Rojo server started and ready (PID: {self.pid})")
            return True
            
        except Exception as e:  # noqa: BLE001
            self._clean_up_failed_start()
            self.last_error = str(e) or e.__class__.__name__
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
    
    def restart(self, suppress_dialogs=False):
        """Restart Rojo and restore automatic health monitoring state."""
        print("Restarting Rojo server...")
        self.stop()
        self._stop_requested = False
        self._restart_attempts = 0
        return self.start(automatic=suppress_dialogs)
    
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
            except Exception:  # noqa: BLE001, S110
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
                except Exception as e:  # noqa: BLE001
                    print(f"Error in status monitoring: {e}")
        
        threading.Thread(target=monitor_loop, daemon=True).start()

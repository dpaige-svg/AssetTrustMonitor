#!/usr/bin/env python3
"""
File Monitoring and Asset Processing

Handles Downloads folder monitoring and asset processing.
"""

import csv
import json
import os
import re
import shutil
import threading
import time
from datetime import datetime
from tkinter import messagebox

from send2trash import send2trash

from ..core.config import Config


class FileMonitor:
    """Monitors and processes asset files"""

    MAX_AUTO_IMPORT_BYTES = 64 * 1024 * 1024
    
    def __init__(self, config=None, rojo_server=None, lune_manager=None):
        self.config = config or Config()
        self.rojo_server = rojo_server
        self.lune_manager = lune_manager
        self.monitoring = False
        self.monitor_thread = None
        self.processing_thread = None
        self.asset_count = 0
        self._count_callbacks = []
        self._processed_asset_callbacks = []
        self.last_verified_asset_filename = None
        self.last_asset_display_name = "Waiting for asset..."
        self.last_asset_verified = False
        self.move_thread = None
        self._stop_event = threading.Event()
        self._signal_sync_thread = None
        self._asset_count_thread = None
        self._signal_lock = threading.Lock()
        self._pipeline_lock = threading.Lock()
        self._import_log_lock = threading.Lock()
        self._last_signal_source = None
        self._asset_dir_signature = None
        self._initialize_signal_module()
        self._start_signal_sync_loop()

    def _record_import_result(self, filename, display_name, successful, stage, reason=""):
        """Persist one final pipeline outcome and update lifetime totals."""
        status = "success" if successful else "failed"
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        stats_path = self.config.import_stats_path
        history_path = self.config.import_history_path

        with self._import_log_lock:
            try:
                os.makedirs(self.config.datastore_folder, exist_ok=True)
                stats = {"successful": 0, "failed": 0, "total": 0}
                try:
                    with open(stats_path, encoding="utf-8") as stream:
                        loaded = json.load(stream)
                    if isinstance(loaded, dict):
                        for key in stats:
                            value = loaded.get(key, 0)
                            if isinstance(value, int) and value >= 0:
                                stats[key] = value
                except (OSError, json.JSONDecodeError, TypeError, ValueError):
                    # A damaged summary must not prevent the append-only history
                    # from recording the current result.
                    pass

                result_key = "successful" if successful else "failed"
                stats[result_key] += 1
                stats["total"] = stats["successful"] + stats["failed"]
                stats["last_result"] = {
                    "timestamp": timestamp,
                    "filename": filename,
                    "display_name": display_name,
                    "status": status,
                    "stage": stage,
                    "reason": str(reason),
                }

                temporary_path = f"{stats_path}.tmp"
                with open(temporary_path, "w", encoding="utf-8", newline="\n") as stream:
                    json.dump(stats, stream, indent=2, ensure_ascii=False)
                os.replace(temporary_path, stats_path)

                history_exists = os.path.isfile(history_path) and os.path.getsize(history_path) > 0
                with open(history_path, "a", encoding="utf-8", newline="") as stream:
                    writer = csv.writer(stream)
                    if not history_exists:
                        writer.writerow(("timestamp", "filename", "display_name", "status", "stage", "reason"))
                    writer.writerow((timestamp, filename, display_name, status, stage, str(reason)))

                print(
                    "Asset import result: "
                    f"{status} ({stats['successful']} successful, {stats['failed']} failed)"
                )
            except (OSError, TypeError, ValueError) as error:
                print(f"Could not record asset import result for {filename}: {error}")

    def get_import_stats(self):
        """Return persistent successful, failed, and total import counts."""
        try:
            with self._import_log_lock, open(self.config.import_stats_path, encoding="utf-8") as stream:
                stats = json.load(stream)
            if isinstance(stats, dict):
                return {
                    "successful": int(stats.get("successful", 0)),
                    "failed": int(stats.get("failed", 0)),
                    "total": int(stats.get("total", 0)),
                }
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
        return {"successful": 0, "failed": 0, "total": 0}

    def _escape_lua_string(self, value):
        return str(value).replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

    def _write_signal_module(self, asset_file_name=None, asset_display_name=None, verified=None):
        """Write shared signal data consumed by the Studio plugin through Rojo sync."""
        try:
            os.makedirs(os.path.dirname(self.config.signal_module_path), exist_ok=True)

            if asset_file_name is None:
                asset_file_name = self.last_verified_asset_filename or ""
            else:
                self.last_verified_asset_filename = asset_file_name or None

            if asset_display_name is None:
                asset_display_name = self.last_asset_display_name or "Waiting for asset..."
            else:
                self.last_asset_display_name = asset_display_name or "Waiting for asset..."

            if verified is None:
                verified = self.last_asset_verified
            else:
                self.last_asset_verified = bool(verified)

            rojo_active = False
            try:
                if self.rojo_server:
                    rojo_active = bool(self.rojo_server.is_running())
            except (OSError, RuntimeError):
                rojo_active = False

            regex_value = getattr(self.config, "regex_statement", "")

            source = (
                "return {\n"
                f"    assetFileName = \"{self._escape_lua_string(asset_file_name)}\",\n"
                f"    currentAsset = \"{self._escape_lua_string(asset_display_name)}\",\n"
                f"    regexStatement = \"{self._escape_lua_string(regex_value)}\",\n"
                f"    verifiedByApp = {str(bool(verified)).lower()},\n"
                f"    rojoActive = {str(bool(rojo_active)).lower()},\n"
                f"    updatedAt = \"{self._escape_lua_string(datetime.now().strftime('%Y-%m-%d %I:%M %p'))}\"\n"
                "}\n"
            )

            with self._signal_lock:
                if source == self._last_signal_source:
                    return
                with open(self.config.signal_module_path, 'w', encoding='utf-8', newline='\n') as f:
                    f.write(source)
                self._last_signal_source = source
        except OSError as e:
            print(f"Failed to write signal module: {e}")

    def _initialize_signal_module(self):
        """Ensure signal module exists and starts with current status snapshot."""
        if not os.path.isfile(self.config.signal_module_path):
            self._write_signal_module("", "Waiting for asset...", False)
        else:
            self._write_signal_module()

    def _start_signal_sync_loop(self):
        """Keep plugin signal status fresh (especially Rojo active/deactive state)."""
        if self._signal_sync_thread and self._signal_sync_thread.is_alive():
            return

        def _sync_loop():
            while not self._stop_event.is_set():
                self._write_signal_module()
                self._stop_event.wait(2)

        self._signal_sync_thread = threading.Thread(target=_sync_loop, daemon=True)
        self._signal_sync_thread.start()

    def _timestamp_parts(self):
        """Return filename-safe and display-friendly timestamp strings."""
        now = datetime.now()
        hour_12 = str(int(now.strftime("%I")))
        date_part = now.strftime("%Y-%m-%d")
        minute_ampm = now.strftime("%M%p")
        minute_ampm_display = now.strftime("%M %p")

        filename_stamp = f"{date_part}_{hour_12}-{minute_ampm}"
        display_stamp = f"{date_part} {hour_12}:{minute_ampm_display}"
        return filename_stamp, display_stamp

    def _detect_model_extension(self, file_path):
        """Infer the correct Roblox model extension from file contents."""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(128).lstrip()

            # Binary Roblox models deliberately begin with ``<roblox!``;
            # check that signature before the broader XML ``<roblox`` root.
            if header.startswith(b'<roblox!'):
                return '.rbxm'
            if header.startswith((b'<?xml', b'<roblox')):
                return '.rbxmx'
        except OSError as e:
            print(f"Error detecting asset format for {os.path.basename(file_path)}: {e}")

        return '.rbxm'

    def _build_timestamped_name(self, base_hash, model_extension):
        """Build a unique timestamped asset filename in 12-hour format."""
        timestamp_for_file, timestamp_for_display = self._timestamp_parts()
        base_name = f"{base_hash}_{timestamp_for_file}"
        candidate = f"{base_name}{model_extension}"

        counter = 2
        while os.path.exists(os.path.join(self.config.processing_folder, candidate)):
            candidate = f"{base_name}_{counter}{model_extension}"
            counter += 1

        return candidate, timestamp_for_display

    def _format_asset_display_name(self, base_hash, timestamp_display, max_length=64):
        """Format display name so toast text remains readable without harsh cutoff."""
        full = f"{base_hash} | {timestamp_display}"
        if len(full) <= max_length:
            return full

        head = full[:36]
        tail = full[-22:]
        return f"{head}...{tail}"

    def _notify_processed_asset(self, asset_display_name, verified):
        """Notify subscribers that an asset reached the local Rojo source tree."""
        for callback in self._processed_asset_callbacks:
            try:
                callback(asset_display_name, verified)
            except Exception as e:  # noqa: BLE001
                print(f"Error in processed asset callback: {e}")

    def flag_current_asset(self):
        """Duplicate the most recent verified asset into processing/FLAGGED-ASSETS."""
        if not self.last_verified_asset_filename:
            return False, "No verified asset available to flag"

        source_candidates = [
            os.path.join(self.config.workspace_folder, self.last_verified_asset_filename),
            os.path.join(self.config.assets_folder, self.last_verified_asset_filename),
        ]

        source_path = next((p for p in source_candidates if os.path.isfile(p)), None)
        if not source_path:
            return False, "Current asset file could not be located"

        os.makedirs(self.config.flagged_assets_folder, exist_ok=True)
        destination_name = self.last_verified_asset_filename
        destination_path = os.path.join(self.config.flagged_assets_folder, destination_name)

        base, ext = os.path.splitext(destination_name)
        counter = 2
        while os.path.exists(destination_path):
            destination_name = f"{base}_{counter}{ext}"
            destination_path = os.path.join(self.config.flagged_assets_folder, destination_name)
            counter += 1

        try:
            shutil.copy2(source_path, destination_path)
            print(f"Flagged asset saved: {destination_name}")
            return True, destination_path
        except (OSError, shutil.Error) as e:
            return False, f"Failed to flag asset: {e}"

    def clear_flagged_assets(self):
        """Clear only the flagged assets folder."""
        return self._clean_folder(self.config.flagged_assets_folder, count=True)

    def _display_name_from_processed_filename(self, filename, max_length=64):
        """Convert timestamped filename into a friendly display label."""
        base = os.path.splitext(filename)[0]
        match = re.match(r"^(?P<hash>.{32})_(?P<date>\d{4}-\d{2}-\d{2})_(?P<hour>\d{1,2})-(?P<minute>\d{2})(?P<ampm>AM|PM)(?:_\d+)?$", base)

        if not match:
            return base

        base_hash = match.group("hash")
        date_part = match.group("date")
        hour = match.group("hour")
        minute = match.group("minute")
        ampm = match.group("ampm")

        display_stamp = f"{date_part} {hour}:{minute} {ampm}"
        return self._format_asset_display_name(base_hash, display_stamp, max_length=max_length)
    
    def start_monitoring(self):
        """Start monitoring downloads folder"""
        if self.monitoring:
            return False
        
        self._stop_event.clear()
        self.monitoring = True
        self._start_signal_sync_loop()
        self.start_asset_counting()
        if not self.monitor_thread or not self.monitor_thread.is_alive():
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
        print("File monitoring started")
        if not self.processing_thread or not self.processing_thread.is_alive():
            self.processing_thread = threading.Thread(target=self.scanProcessingFolder, daemon=True)
            self.processing_thread.start()
        print("Processing folder scanning started")
        return True
    
    
    def stop_monitoring(self):
        """Stop monitoring and briefly wait for interruptible workers to exit."""
        self.monitoring = False
        self._stop_event.set()

        # Use one shared, short deadline so shutdown time does not grow with
        # the number of worker threads. Long external work remains daemonized.
        deadline = time.monotonic() + 0.5
        current_thread = threading.current_thread()
        workers = (
            self.monitor_thread,
            self.processing_thread,
            self._signal_sync_thread,
            self._asset_count_thread,
            self.move_thread,
        )
        for worker in workers:
            if not worker or worker is current_thread or not worker.is_alive():
                continue
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            worker.join(remaining)

        print("File monitoring stopped")
        return True
    
    def is_monitoring(self):
        """Check if monitoring is active"""
        return self.monitoring
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        try:
            existing_files = set(os.listdir(self.config.downloads_path))
        except OSError:
            existing_files = set()

        # Process matching files that were downloaded before the Start button
        # was pressed. Previously these were marked as seen and skipped forever.
        for file in existing_files:
            if self._stop_event.is_set() or not self.monitoring:
                return
            if self._is_asset_candidate(file):
                self._move_file(file)

        try:
            seen = set(os.listdir(self.config.downloads_path))
        except OSError:
            seen = set()
        
        while self.monitoring and not self._stop_event.is_set():
            self._stop_event.wait(1)
            if self._stop_event.is_set() or not self.monitoring:
                break

            try:
                current = set(os.listdir(self.config.downloads_path))
            except OSError:
                continue
            new_files = current - seen
            
            for file in new_files:
                if self._is_asset_candidate(file):
                    self._move_file(file)
            
            seen = current

    def scanProcessingFolder(self):
        """Scan processing folder for Roblox model files to process."""
        while not self._stop_event.is_set():
            self._stop_event.wait(0.5)
            if self._stop_event.is_set():
                break
            try:
                files = os.listdir(self.config.processing_folder)
                model_files = [f for f in files if f.endswith((".rbxm", ".rbxmx"))]
                
                for processed_file in model_files:
                    if self._stop_event.is_set():
                        return
                    full_path = os.path.join(self.config.processing_folder, processed_file)
                    display_name = self._display_name_from_processed_filename(processed_file)

                    with self._pipeline_lock:
                        try:
                            file_size = os.path.getsize(full_path)
                            if file_size <= 0 or file_size > self.MAX_AUTO_IMPORT_BYTES:
                                reason = f"unsafe file size ({file_size} bytes)"
                                print(
                                    f"Automatic import skipped for {processed_file}: "
                                    f"{reason}"
                                )
                                self._write_signal_module(processed_file, display_name, False)
                                self._record_import_result(
                                    processed_file, display_name, False, "validation", reason
                                )
                                continue

                            self._sanitize_rbxm(full_path)
                            lune_success = bool(
                                self.lune_manager
                                and self.lune_manager.run_init_script(processed_file)
                            )
                            if not lune_success:
                                self._write_signal_module(processed_file, display_name, False)
                                self._record_import_result(
                                    processed_file,
                                    display_name,
                                    False,
                                    "lune_processing",
                                    "Lune could not deserialize or safely prepare the model",
                                )
                                continue

                            if self.rojo_server:
                                verified = self.rojo_server.verify_workspace_asset(
                                    processed_file,
                                    stop_event=self._stop_event,
                                )
                            else:
                                verified = os.path.isfile(
                                    os.path.join(self.config.workspace_folder, processed_file)
                                )

                            self._write_signal_module(processed_file, display_name, verified)
                            if verified:
                                self.last_verified_asset_filename = processed_file
                                self._record_import_result(
                                    processed_file,
                                    display_name,
                                    True,
                                    "rojo_verification",
                                    "Asset reached the Rojo workspace and passed verification",
                                )
                                self._notify_processed_asset(display_name, True)
                            else:
                                self._record_import_result(
                                    processed_file,
                                    display_name,
                                    False,
                                    "rojo_verification",
                                    "Asset was processed but Rojo workspace verification failed",
                                )
                        except (OSError, RuntimeError, ValueError) as error:
                            print(f"Asset isolated after processing failure ({processed_file}): {error}")
                            self._write_signal_module(processed_file, display_name, False)
                            self._record_import_result(
                                processed_file, display_name, False, "pipeline", str(error)
                            )
                        finally:
                            # Originals remain in Assets. Never retry a rejected file in a loop.
                            try:
                                if os.path.isfile(full_path):
                                    os.remove(full_path)
                            except OSError as cleanup_error:
                                print(f"Could not clear rejected processing file {processed_file}: {cleanup_error}")

            except Exception as e:  # noqa: BLE001
                print(f"Error scanning processing folder: {e}")

    def _sanitize_rbxm(self, file_path):
        """
        Sanitize .rbxm file by renaming incompatible properties.
        Handles both Binary (.rbxm) and XML (.rbxmx) formats.
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(128)
                f.seek(0)
                data = f.read()

            normalized_header = header.lstrip()

            # Some XML assets start with an XML declaration before the <roblox> root.
            if normalized_header.startswith((b'<?xml', b'<roblox')):
                print(f"Sanitizing XML file: {os.path.basename(file_path)}")
                try:
                    text_data = data.decode('utf-8', errors='ignore')
                    
                    # List of properties that might cause ContentIdToContent migration errors
                    problematic_props = ["MetalnessMap", "NormalMap", "RoughnessMap", "ColorMap", "TexturePack", "TexturePackMetadata"]
                    
                    modified = False
                    for prop in problematic_props:
                        # Regex to remove the entire BinaryString block for these properties
                        pattern = f'<BinaryString name="{prop}">.*?</BinaryString>'
                        
                        if re.search(pattern, text_data, re.DOTALL):
                            print(f"Removing incompatible property: {prop}")
                            text_data = re.sub(pattern, '', text_data, flags=re.DOTALL)
                            modified = True

                    # Some downloaded animation assets encode the Tags property with an
                    # unsupported XML value type. Removing the property is safer than
                    # letting Rojo/Lune reject the entire model.
                    def _strip_invalid_tags_property(match):
                        nonlocal modified
                        tag_name = match.group('tag')
                        if tag_name == 'SharedString':
                            return match.group(0)

                        print(f"Removing incompatible property type for Tags: {tag_name}")
                        modified = True
                        return ''

                    text_data = re.sub(
                        r'<(?P<tag>[A-Za-z0-9_]+)\s+name="Tags">.*?</(?P=tag)>',
                        _strip_invalid_tags_property,
                        text_data,
                        flags=re.DOTALL,
                    )
                    
                    if modified:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(text_data)
                            f.flush()
                            os.fsync(f.fileno())
                        print("XML Sanitization complete.")
                        return

                except (OSError, UnicodeError) as e:
                    print(f"Error processing XML data: {e}")
                    
        except OSError as e:
            print(f"Error sanitizing {file_path}: {e}")

    
    def _move_file(self, filename):
        """Process a new file"""
        file_path = os.path.join(self.config.downloads_path, filename)
        
        if not os.path.isfile(file_path):
            return
        
        name, extension = os.path.splitext(filename)
        
        if not self._is_asset_candidate(filename):
            return
        
        # Strip duplicate counter if present to get clean hash
        name = re.sub(r' \(\d+\)$', '', name)
        
        try:
            with self._pipeline_lock:
                model_extension = self._detect_model_extension(file_path)
                # Generate unique timestamp-based filename (12-hour clock).
                new_name, display_stamp = self._build_timestamped_name(name, model_extension)
                processing_path = os.path.join(self.config.processing_folder, new_name)

                # Move and preserve the original before the processing thread can see it.
                if not self._safe_move(file_path, processing_path):
                    if self._stop_event.is_set():
                        return
                    messagebox.showerror("Error", f"Failed to move {filename}")
                    return

                shutil.copy2(processing_path, self.config.assets_folder)

                # Only clear the watched tree after the durable Assets copy exists.
                self._clean_folder(self.config.workspace_folder)

                display_name = self._format_asset_display_name(name, display_stamp)
                print(f"Queued asset: {display_name}")


        
        except (OSError, shutil.Error) as e:
            messagebox.showerror("Error", f"Error processing {filename}: {e}")
    
    def clean_assets(self):
        """Clean all asset folders"""
        deleted = 0
        folders = [
            self.config.assets_folder,
            self.config.workspace_folder,
            self.config.processing_folder
        ]
        
        for folder in folders:
            deleted += self._clean_folder(folder, count=True)
        
        return deleted
    
    
    def _clean_folder(self, folder_path, count=False):
        """Clean a folder"""
        deleted = 0
        
        if os.path.exists(folder_path):
            for file in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file)
                if os.path.isfile(file_path):
                    try:
                        if self.config.auto_clean_trash == "true":
                            os.remove(file_path)
                        else:
                            send2trash(file_path)
                        deleted += 1
                    except Exception as e:  # noqa: BLE001
                        print(f"Error deleting {file}: {e}")
        
        return deleted if count else None

    def empty_recycle_bin(self):
        """Empty .rbxm files from Recycle Bin (Windows) or Trash (macOS)"""
        import platform
        import subprocess

        try:
            system = platform.system()

            if system == "Windows":
                # PowerShell script to delete .rbxm files from Recycle Bin
                # Using -Confirm:$false to suppress confirmation prompts
                cmd = [
                    "powershell", "-Command",
                    "$shell = New-Object -ComObject Shell.Application; "
                    "$bin = $shell.NameSpace(10); "
                    "$items = $bin.Items(); "
                    "foreach ($item in $items) { "
                    "  if ($item.Name -like '*.rbxm') { "
                    "    Remove-Item -Path $item.Path -Force -Confirm:$false -ErrorAction SilentlyContinue; "
                    "  } "
                    "}"
                ]
                # Safe access to CREATE_NO_WINDOW for cross-platform compatibility
                creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                subprocess.run(cmd, check=True, creationflags=creation_flags)
                return True

            elif system == "Darwin":
                # macOS: remove .rbxm files from Trash
                trash_path = os.path.expanduser("~/.Trash")
                if os.path.exists(trash_path):
                    # Using os.walk instead of subprocess/find to avoid potential permission/path issues
                    for root, dirs, files in os.walk(trash_path):
                        for file in files:
                            if file.lower().endswith(".rbxm"):
                                try:
                                    file_path = os.path.join(root, file)
                                    os.remove(file_path)
                                except OSError as e:
                                    print(f"Failed to delete {file} from Trash: {e}")
                    return True
            
            return False

        except Exception as e:  # noqa: BLE001
            print(f"Error emptying recycle bin: {e}")
            return False
    
    def _is_temp_or_incomplete(self, filename):
        """Check if file is temp/incomplete download"""
        temp_exts = {".crdownload", ".part", ".tmp", ".download"}
        name, ext = os.path.splitext(filename)
        
        if ext.lower() in temp_exts:
            return True
        if filename.startswith("~$") or filename.startswith("."):
            return True
        
        return False

    def _is_asset_candidate(self, filename):
        """Return whether a Downloads entry should enter the asset pipeline."""
        if self._is_temp_or_incomplete(filename):
            return False

        name, extension = os.path.splitext(filename)
        extension = extension.lower()

        # Browser-downloaded asset hashes arrive without an extension. Also
        # accept normal Roblox model files so manually downloaded/exported
        # models are not silently ignored.
        if extension in (".rbxm", ".rbxmx"):
            return True
        if extension:
            return False

        return bool(re.match(r'^.{32}( \(\d+\))?$', name))
    
    def _safe_move(self, src, dst, retries=5, delay=0.5):
        """Move file with retry logic"""
        for attempt in range(retries):
            try:
                shutil.move(src, dst)
                return True
            except (OSError, shutil.Error) as e:
                if attempt == retries - 1:
                    print(f"Move failed after {retries} attempts: {e}")
                    return False
                if self._stop_event.wait(delay):
                    return False
    
    def get_asset_count(self):
        """
        Get the count of unique assets in the assets folder.
        
        Assets are grouped by their 32-character hash.
        For each hash, files are grouped into sessions based on modification time.
        Files added within 10 minutes of the previous file in the group are considered part of the same asset instance.
        
        Returns:
            int: Number of unique asset sessions found.
        """
        if not os.path.exists(self.config.assets_folder):
            return 0
        
        try:
            asset_files = os.listdir(self.config.assets_folder)
            assets_by_hash = {}
            
            for f in asset_files:
                if f.endswith((".rbxm", ".rbxmx")):
                    # Get hash
                    base_name = f[:32] if len(f) >= 32 else f
                    
                    # Get mtime
                    file_path = os.path.join(self.config.assets_folder, f)
                    try:
                        mtime = os.path.getmtime(file_path)
                    except OSError:
                        continue
                    
                    if base_name not in assets_by_hash:
                        assets_by_hash[base_name] = []
                    assets_by_hash[base_name].append(mtime)
            
            total_count = 0
            
            for base_name, times in assets_by_hash.items():
                if not times:
                    continue
                    
                times.sort()
                
                # Count clusters
                clusters = 1
                last_time = times[0]
                
                for t in times[1:]:
                    # If this file is more than 10 minutes (600s) after the previous one
                    if t - last_time > 600:
                        clusters += 1
                    last_time = t
                
                total_count += clusters
            
            return total_count
        except OSError as e:
            print(f"Error counting assets: {e}")
            return 0
    
    def add_count_callback(self, callback):
        """Add callback for count changes"""
        self._count_callbacks.append(callback)

    def add_processed_asset_callback(self, callback):
        """Add callback for verified processed assets."""
        self._processed_asset_callbacks.append(callback)
    
    def start_asset_counting(self):
        """Start background asset counting"""
        if self._asset_count_thread and self._asset_count_thread.is_alive():
            return

        def count_loop():
            while not self._stop_event.is_set():
                self._stop_event.wait(3)
                if self._stop_event.is_set():
                    break
                try:
                    try:
                        directory_stat = os.stat(self.config.assets_folder)
                        directory_signature = directory_stat.st_mtime_ns
                    except OSError:
                        directory_signature = None

                    if directory_signature == self._asset_dir_signature:
                        continue

                    new_count = self.get_asset_count()
                    self._asset_dir_signature = directory_signature
                    if new_count != self.asset_count:
                        self.asset_count = new_count
                        for callback in self._count_callbacks:
                            callback(new_count)
                except Exception as e:  # noqa: BLE001
                    print(f"Error in asset counting: {e}")
        
        self._asset_count_thread = threading.Thread(target=count_loop, daemon=True)
        self._asset_count_thread.start()

    

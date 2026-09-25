#!/usr/bin/env python3
"""
File Monitoring and Asset Processing

Handles Downloads folder monitoring and asset processing.
"""

import os
import threading
import time
import shutil
import re
from send2trash import send2trash
from tkinter import messagebox

from ..core.config import Config
from ..core.utils import Utils


class FileMonitor:
    """Monitors and processes asset files"""
    
    def __init__(self, config=None, rojo_server=None, lune_manager=None):
        self.config = config or Config()
        self.rojo_server = rojo_server
        self.lune_manager = lune_manager
        self.monitoring = False
        self.monitor_thread = None
        self.processing_thread = None
        self.asset_count = 0
        self._count_callbacks = []
        self.move_thread = None
    
    def start_monitoring(self):
        """Start monitoring downloads folder"""
        if self.monitoring:
            return False
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("File monitoring started")
        self.processing_thread = threading.Thread(target=self.scanProcessingFolder, daemon=True)
        self.processing_thread.start()
        print("Processing folder scanning started")
        return True
    
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.monitoring = False
        print("File monitoring stopped")
        return True
    
    def is_monitoring(self):
        """Check if monitoring is active"""
        return self.monitoring
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        seen = set(os.listdir(self.config.downloads_path))
        
        while self.monitoring:
            time.sleep(1)
            current = set(os.listdir(self.config.downloads_path))
            new_files = current - seen
            
            for file in new_files:
                if not self._is_temp_or_incomplete(file):
                    self._move_file(file)
            
            seen = current

    def scanProcessingFolder(self):
        """Scan processing folder for .rbxm files to process"""
        while True:
            time.sleep(.1)
            try:
                files = os.listdir(self.config.processing_folder)
                rbxm_files = [f for f in files if f.endswith(".rbxm")]
                
                if rbxm_files:
                    # Sanitize files before Lune processing
                    for file in rbxm_files:
                        self._sanitize_rbxm(os.path.join(self.config.processing_folder, file))

                    # Process with Lune (script handles all files in the folder)
                    if self.lune_manager and self.lune_manager.run_init_script():
                        self._clean_folder(self.config.processing_folder)
                    else:
                        # If script fails, clean folder to prevent infinite error loops
                        self._clean_folder(self.config.processing_folder)

            except Exception as e:
                print(f"Error scanning processing folder: {e}")

    def _sanitize_rbxm(self, file_path):
        """
        Sanitize .rbxm file by renaming incompatible properties.
        Handles both Binary (.rbxm) and XML (.rbxmx) formats.
        """
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)
                f.seek(0)
                data = f.read()

            # Check if XML
            if header.startswith(b'<roblox'):
                print(f"Sanitizing XML file: {os.path.basename(file_path)}")
                try:
                    text_data = data.decode('utf-8', errors='ignore')
                    
                    # List of properties that might cause ContentIdToContent migration errors
                    problematic_props = ["MetalnessMap", "NormalMap", "RoughnessMap", "ColorMap", "TexturePack", "TexturePackMetadata"]
                    
                    modified = False
                    import re
                    for prop in problematic_props:
                        # Regex to remove the entire BinaryString block for these properties
                        pattern = f'<BinaryString name="{prop}">.*?</BinaryString>'
                        
                        if re.search(pattern, text_data, re.DOTALL):
                            print(f"Removing incompatible property: {prop}")
                            text_data = re.sub(pattern, '', text_data, flags=re.DOTALL)
                            modified = True
                    
                    if modified:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(text_data)
                            f.flush()
                            os.fsync(f.fileno())
                        print("XML Sanitization complete.")
                        return

                except Exception as e:
                    print(f"Error processing XML data: {e}")
                    
        except Exception as e:
            print(f"Error sanitizing {file_path}: {e}")

    
    def _move_file(self, filename):
        """Process a new file"""
        file_path = os.path.join(self.config.downloads_path, filename)
        
        if not os.path.isfile(file_path):
            return
        
        name, extension = os.path.splitext(filename)
        
        # Check if 32-character asset file (allowing for duplicate counters like " (1)")
        should_process = (extension == "") and bool(re.match(r'^.{32}( \(\d+\))?$', name))
        
        if not should_process:
            return
        
        # Strip duplicate counter if present to get clean hash
        name = re.sub(r' \(\d+\)$', '', name)
        
        try:
            # Generate unique filename
            new_name = name + Utils.generate_random_string(6) + ".rbxm"
            processing_path = os.path.join(self.config.processing_folder, new_name)
            
            # Move to processing folder
            if not self._safe_move(file_path, processing_path):
                messagebox.showerror("Error", f"Failed to move {filename}")
                return
            
            # Clean workspace
            self._clean_folder(self.config.workspace_folder)
            
            # Copy to assets
            shutil.copy(processing_path, self.config.assets_folder)


        
        except Exception as e:
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
                    except Exception as e:
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
                                except Exception as e:
                                    print(f"Failed to delete {file} from Trash: {e}")
                    return True
            
            return False

        except Exception as e:
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
    
    def _safe_move(self, src, dst, retries=5, delay=0.5):
        """Move file with retry logic"""
        for attempt in range(retries):
            try:
                shutil.move(src, dst)
                return True
            except Exception as e:
                if attempt == retries - 1:
                    print(f"Move failed after {retries} attempts: {e}")
                    return False
                time.sleep(delay)
    
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
                if f.endswith(".rbxm"):
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
        except Exception as e:
            print(f"Error counting assets: {e}")
            return 0
    
    def add_count_callback(self, callback):
        """Add callback for count changes"""
        self._count_callbacks.append(callback)
    
    def start_asset_counting(self):
        """Start background asset counting"""
        def count_loop():
            while True:
                time.sleep(3)
                try:
                    new_count = self.get_asset_count()
                    if new_count != self.asset_count:
                        self.asset_count = new_count
                        for callback in self._count_callbacks:
                            callback(new_count)
                except Exception as e:
                    print(f"Error in asset counting: {e}")
        
        threading.Thread(target=count_loop, daemon=True).start()

    
#!/usr/bin/env python3
"""
File Monitoring and Processing for Asset Trust Monitor

Handles monitoring Downloads folder, processing files, and asset management.
"""

import os
import threading
import time
import shutil
from send2trash import send2trash
from tkinter import messagebox
from .utils import Utils

class FileMonitor:
    """Monitors file system and processes new assets"""
    
    def __init__(self, config, rojo_server=None):
        self.config = config
        self.rojo_server = rojo_server
        self.monitoring = False
        self.monitor_thread = None
        self.asset_count = 0
        self._count_callbacks = []
    
    def start_monitoring(self):
        """Start monitoring downloads folder"""
        if self.monitoring:
            return False
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        return True
    
    def stop_monitoring(self):
        """Stop monitoring downloads folder"""
        self.monitoring = False
        return True
    
    def is_monitoring(self):
        """Check if currently monitoring"""
        return self.monitoring
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        seen = set(os.listdir(self.config.downloads_path))
        
        while self.monitoring:
            time.sleep(1)
            current = set(os.listdir(self.config.downloads_path))
            new_files = current - seen

            for file in new_files:
                # Skip temp/incomplete files immediately
                if self._is_temp_or_incomplete(file):
                    continue

                self._process_file(file)

            seen = current
    
    def _process_file(self, filename):
        """Process a new file found in downloads"""
        file_path = os.path.join(self.config.downloads_path, filename)
        
        if not os.path.isfile(file_path):
            return
        
        name, extension = os.path.splitext(filename)
        
        # Ignore common temp/incomplete download patterns
        if self._is_temp_or_incomplete(filename):
            return
        
        # Check if this is a 32-character asset file
        should_process = len(name) == 32 and extension == ""
        
        # Handle duplicate files (e.g., "asset (1).ext")
        if len(name) > 32:
            name = name[:32]
            should_process = True
        
        if not should_process:
            return
        
        try:

            # Generate unique filename to prevent overwrites
            new_name = name + Utils.generate_random_string(6) + ".rbxm"
            processing_path = os.path.join(self.config.processing_folder, new_name)
            
            # Move file to processing folder (supports cross-volume moves)
            if not self._safe_move(file_path, processing_path):
                messagebox.showerror("Error", f"Failed to move {filename} to processing folder.")
                return
            
            # Clean workspace before processing
            self._clean_workspace()
            
            # Copy to assets folder
            shutil.copy(processing_path, self.config.assets_folder)
            
            # Process with Lune script if Rojo server available
            if self.rojo_server and self.rojo_server.run_lune_script():
                self._clean_processing_folder()
            else:
                messagebox.showerror("Error", "Error processing file with Lune script. Clearing processing folder.")
                print("Error processing file with Lune script. Clearing processing folder.")
                self._clean_processing_folder()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error processing {filename}: {e}")
    
    def clean_assets(self):
        """Clean all asset-related folders"""
        deleted = 0
        folders = [
            self.config.assets_folder, 
            self.config.workspace_folder, 
            self.config.processing_folder
        ]
        
        for folder in folders:
            if os.path.exists(folder):
                for file in os.listdir(folder):
                    file_path = os.path.join(folder, file)
                    if os.path.isfile(file_path):
                        try:
                            send2trash(file_path)
                            deleted += 1
                        except Exception as e:
                            messagebox.showerror("Error", f"Error deleting {file}: {e}")
        
        return deleted
    
    def _clean_workspace(self):
        """Clean workspace folder before copying new assets"""
        if os.path.exists(self.config.workspace_folder):
            for file in os.listdir(self.config.workspace_folder):
                file_path = os.path.join(self.config.workspace_folder, file)
                if os.path.isfile(file_path):
                    try:
                        send2trash(file_path)
                    except Exception as e:
                        print(f"Error deleting workspace file {file}: {e}")
    
    def _clean_processing_folder(self):
        """Clean processing folder"""
        if os.path.exists(self.config.processing_folder):
            for file in os.listdir(self.config.processing_folder):
                file_path = os.path.join(self.config.processing_folder, file)
                if os.path.isfile(file_path):
                    try:
                        send2trash(file_path)
                    except Exception as e:
                        print(f"Error deleting processing file {file}: {e}")

    def _is_temp_or_incomplete(self, filename: str) -> bool:
        """Return True if file looks like a temp/incomplete download."""
        temp_exts = {".crdownload", ".part", ".tmp", ".download"}
        name, ext = os.path.splitext(filename)
        # Chrome/Edge use .crdownload; Firefox uses .part
        if ext.lower() in temp_exts:
            return True
        # Office-type temp files or hidden partials
        if filename.startswith("~$") or filename.startswith("."):
            return True
        return False

    def _wait_for_stability(self, path: str, checks: int = 3, interval: float = .5, max_wait: int = 10) -> bool:
        """Wait until file size and mtime remain stable across a few checks.
        Returns True if stable within max_wait seconds.
        """
        waited = 0.0
        while waited < max_wait:
            sizes = []
            mtimes = []
            for _ in range(checks):
                try:
                    stat = os.stat(path)
                    sizes.append(stat.st_size)
                    mtimes.append(stat.st_mtime)
                except FileNotFoundError:
                    return False
                time.sleep(interval)
                waited += interval
            if len(set(sizes)) == 1 and len(set(mtimes)) == 1 and sizes[0] > 0:
                return True
        return False

    def _safe_move(self, src: str, dst: str, retries: int = 5, delay: float = 0.5) -> bool:
        """Move file with small retry/backoff to handle transient locks."""
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
        """Get count of unique assets (excluding duplicates)"""
        if not os.path.exists(self.config.assets_folder):
            return 0
        
        try:
            asset_files = os.listdir(self.config.assets_folder)
            unique_assets = set()
            
            for f in asset_files:
                if f.endswith(".rbxm"):
                    # Extract first 32 characters (the original hash before random suffix)
                    base_name = f[:32] if len(f) >= 32 else f
                    unique_assets.add(base_name)
            
            return len(unique_assets)
        except Exception as e:
            print(f"Error counting assets: {e}")
            return 0
    
    def add_count_callback(self, callback):
        """Add callback for asset count changes"""
        self._count_callbacks.append(callback)
    
    def start_asset_counting(self):
        """Start background thread to monitor asset count"""
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
                    time.sleep(1)
        
        threading.Thread(target=count_loop, daemon=True).start()
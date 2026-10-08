#!/usr/bin/env python3
"""
cache Management for Asset Trust Monitor

Clears certain cache files to ensure fresh data is used.
"""

import os
import shutil

    
class CacheManager:

    def clear_cache(self):
        """Wrapper to clear all cache"""
        self.clear_all_pycache()

    def clear_all_pycache(self):
        """Clear all __pycache__ directories in the main parenting folder"""
        main_folder = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        for root, dirs, files in os.walk(main_folder):
            for dir_name in dirs:
                if dir_name == "__pycache__":
                    pycache_path = os.path.join(root, dir_name)
                    try:
                        shutil.rmtree(pycache_path)
                        print(f"Cleared cache: {pycache_path}")
                    except (OSError, shutil.Error) as e:
                        print(f"Failed to clear cache at {pycache_path}: {e}")

    def clear_specific_cache(self, cache_paths):
        """Clear specific cache directories provided in cache_paths list"""
        for cache_path in cache_paths:
            if os.path.exists(cache_path):
                try:
                    shutil.rmtree(cache_path)
                    print(f"Cleared cache: {cache_path}")
                except (OSError, shutil.Error) as e:
                    print(f"Failed to clear cache at {cache_path}: {e}")
            else:
                print(f"Cache path does not exist: {cache_path}")


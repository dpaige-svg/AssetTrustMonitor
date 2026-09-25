#!/usr/bin/env python3
"""
Button Components for Asset Trust Monitor

Handles button widgets using image icons instead of unicode text.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import os
import math

class ButtonManager:
    """Manages button widgets and their actions"""
    
    def __init__(self, parent_frame, file_monitor, studio_manager, update_manager, rojo_server, config, icons=None, on_debug=None, style_manager=None):
        """
        Initialize button manager
        
        Args:
            parent_frame: The tkinter frame to place buttons in
            file_monitor: FileMonitor instance for controlling monitoring
            studio_manager: StudioManager instance for managing studio
            update_manager: UpdateManager instance for managing updates
            rojo_server: RojoServer instance for managing Rojo server
            config: Config instance for styling
            icons: Dictionary with icon references {'start': icon, 'stop': icon, 'trash': icon, 'debug': icon}
            on_debug: Callback for debug button
            style_manager: StyleManager instance for accessing styles
        """
        self.frame = parent_frame
        self.file_monitor = file_monitor
        self.studio_manager = studio_manager
        self.update_manager = update_manager
        self.rojo_server = rojo_server
        self.config = config
        self.icons = icons or {}
        self.on_debug = on_debug
        self.style = style_manager.style if style_manager else None

        # Load icon images
        self._load_icons()

        # Button widgets - using images instead of text

        self.btn_start = ttk.Button(
            self.frame,
            image=self.start_icon,
            takefocus=0,
            command=self._toggle_monitoring,
            style="Start_Theme.TButton"
        )
        self.btn_start.grid(column=0, row=0, padx=2, pady=2)

        self.btn_stop = ttk.Button(
            self.frame,
            image=self.stop_icon,
            takefocus=0,
            command=self._toggle_monitoring,
            style="Start_Theme.TButton"
        )
        # Do not grid stop button initially

        self.btn_clean = ttk.Button(
            self.frame,
            image=self.trash_icon,
            takefocus=0,
            command=self._clean_assets,
            style="Start_Theme.TButton"
        )
        self.btn_clean.grid(column=1, row=0, padx=2, pady=2)

        self.btn_debug = ttk.Button(
            self.frame,
            image=self.debug_icon,
            takefocus=0,
            command=self.on_debug,
            style="Start_Theme.TButton"
        )
        self.btn_debug.grid(column=2, row=0, padx=2, pady=2)

        # Track monitoring state
        self.is_monitoring = False

    def _load_icons(self):
        """Load button icons from PNG files"""
        # Use icons_path directly instead of get_icon_path which adds .ico extension
        icons_path = self.config.icons_path
        
        # Load search icon
        try:
            search_img = Image.open(os.path.join(icons_path, "search.png"))
            search_img = search_img.resize((16, 16), Image.Resampling.LANCZOS)
            self.start_icon = ImageTk.PhotoImage(search_img)
        except Exception as e:
            print(f"Could not load search icon: {e}")
            self.start_icon = None

        # Load stop icon
        try:
            stop_img = Image.open(os.path.join(icons_path, "stop.png"))
            stop_img = stop_img.resize((16, 16), Image.Resampling.LANCZOS)
            self.stop_icon = ImageTk.PhotoImage(stop_img)
        except Exception as e:
            print(f"Could not load stop icon: {e}")
            self.stop_icon = None

        # Load trash icon (create recycle icon programmatically)
        try:
            # Create a 16x16 transparent image
            recycle_img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            
            # Create a base arrow pointing right, positioned at the top
            base_arrow = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            d = ImageDraw.Draw(base_arrow)
            
            # Draw arrow components for the loop
            # Shaft: Shorter horizontal bar to create gaps
            d.polygon([(5, 3), (9, 3), (9, 5), (5, 5)], fill='white')
            # Head: Triangle at the end
            d.polygon([(9, 1), (12, 4), (9, 7)], fill='white')
            
            # Composite rotated versions to form the recycle loop
            # Arrow 1 (0 deg)
            recycle_img.alpha_composite(base_arrow)
            
            # Arrow 2 (120 deg clockwise -> -120 deg)
            rot1 = base_arrow.rotate(-120, center=(8, 8), resample=Image.Resampling.BICUBIC)
            recycle_img.alpha_composite(rot1)
            
            # Arrow 3 (240 deg clockwise -> -240 deg)
            rot2 = base_arrow.rotate(-240, center=(8, 8), resample=Image.Resampling.BICUBIC)
            recycle_img.alpha_composite(rot2)
            
            self.trash_icon_pil = recycle_img  # Keep reference to PIL image
            self.trash_icon = ImageTk.PhotoImage(recycle_img)
        except Exception as e:
            print(f"Could not create recycle icon: {e}")
            self.trash_icon = None

        # Load debug icon (create gear icon programmatically)
        try:
            # Create a 16x16 transparent image
            gear_img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            draw = ImageDraw.Draw(gear_img)
            
            # Draw gear - simplified design
            # Outer circle with teeth
            draw.ellipse([2, 2, 14, 14], fill='white')
            
            # Teeth (8 triangular teeth)
            for i in range(8):
                angle = i * 45
                # Calculate tooth position
                import math
                x1 = 8 + 6 * math.cos(math.radians(angle - 15))
                y1 = 8 + 6 * math.sin(math.radians(angle - 15))
                x2 = 8 + 8 * math.cos(math.radians(angle))
                y2 = 8 + 8 * math.sin(math.radians(angle))
                x3 = 8 + 6 * math.cos(math.radians(angle + 15))
                y3 = 8 + 6 * math.sin(math.radians(angle + 15))
                draw.polygon([(x1, y1), (x2, y2), (x3, y3)], fill='white')
            
            # Inner circle (hole)
            draw.ellipse([5, 5, 11, 11], fill=(0, 0, 0, 0))
            
            self.debug_icon_pil = gear_img  # Keep reference to PIL image
            self.debug_icon = ImageTk.PhotoImage(gear_img)
        except Exception as e:
            print(f"Could not create gear icon: {e}")
            self.debug_icon = None
        # Debug button measurements and calculate proper centering
        # The following block is removed because it referenced undefined variables (button, button_name, unicode_text).
        # If you need button measurement debugging, use the _adjust_button_style_for_centering method instead.

    def _adjust_button_style_for_centering(self, button, text, button_name):
        """Adjust button for perfect centering using precise measurements and consistent sizing"""
        try:
            # Force UI update to get accurate dimensions
            self.frame.update_idletasks()
            
            # Get current button dimensions
            actual_width = button.winfo_width()
            actual_height = button.winfo_height()
            
            # Ensure minimum width for consistency (add padding if needed)
            min_width = 100  # Increased minimum pixel width for better emoji display
            if actual_width < min_width:
                extra_padding = (min_width - actual_width) // 2
                current_padding = button.cget("padding") or (0, 0, 0, 0)
                if isinstance(current_padding, str):
                    current_padding = (0, 0, 0, 0)
                left_pad, top_pad, right_pad, bottom_pad = current_padding
                button.configure(padding=(left_pad + extra_padding, top_pad, right_pad + extra_padding, bottom_pad))
                # Update after padding change
                self.frame.update_idletasks()
                actual_width = button.winfo_width()
                actual_height = button.winfo_height()
            
            # Get precise font from style
            font = None
            if self.style:
                style_name = button.cget("style") or "Start_Theme.TButton"
                try:
                    font_tuple = self.style.lookup(style_name, "font")
                    if font_tuple:
                        from tkinter import font as tkfont
                        font = tkfont.Font(font=font_tuple)
                except:
                    pass
            
            # Fallback font if style lookup fails
            if not font:
                from tkinter import font as tkfont
                font = tkfont.Font(family="Arial", size=10, weight="normal")
            
            # Measure text dimensions precisely
            text_width = font.measure(text)
            text_height = font.metrics("linespace")
            
            # Calculate centering offsets
            width_offset = (actual_width - text_width) // 2
            height_offset = (actual_height - text_height) // 2
            
            # Ensure non-negative padding values
            left_pad = max(0, width_offset)
            right_pad = max(0, actual_width - text_width - left_pad)
            top_pad = max(0, height_offset) 
            bottom_pad = max(0, actual_height - text_height - top_pad)
            
            # Apply precise padding for perfect centering
            button.configure(padding=(left_pad, top_pad, right_pad, bottom_pad))
            
            print(f"✅ {button_name}: {actual_width}x{actual_height} → Text: {text_width}x{text_height} → Padding: L{left_pad},R{right_pad},T{top_pad},B{bottom_pad}")
            
            return {
                'dimensions': (actual_width, actual_height),
                'text_size': (text_width, text_height),
                'padding': (left_pad, top_pad, right_pad, bottom_pad),
                'centered': True
            }
            
        except Exception as e:
            print(f"❌ Error centering {button_name}: {e}")
            # Fallback: basic padding
            button.configure(padding=(15, 8, 15, 8))
            return None

    def _toggle_monitoring(self):
        """Toggle file monitoring on/off, update button visibility, and start/stop scanner"""
        self.is_monitoring = not self.is_monitoring
        if self.is_monitoring:
            self.btn_start.grid_remove()
            self.btn_stop.grid(column=0, row=0, padx=2, pady=2)
            
            if self.file_monitor:
                self.file_monitor.start_monitoring()
        else:
            self.btn_stop.grid_remove()
            self.btn_start.grid(column=0, row=0, padx=2, pady=2)
            
            if self.file_monitor:
                self.file_monitor.stop_monitoring()
    
    def _clean_assets(self):
        """Clean all assets"""
        deleted = self.file_monitor.clean_assets()
        messagebox.showinfo("Cleaned", f"{deleted} files moved to trash.")

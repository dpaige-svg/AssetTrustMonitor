#!/usr/bin/env python3
"""
Button Components for Asset Trust Monitor

Handles button widgets using image icons instead of unicode text.
"""

import platform
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageTk


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
            text="Start",
            compound="left",
            takefocus=0,
            command=self._toggle_monitoring,
            style="Start_Theme.TButton"
        )
        self.btn_start.grid(column=0, row=0, padx=2, pady=2)

        self.btn_stop = ttk.Button(
            self.frame,
            image=self.stop_icon,
            text="Stop",
            compound="left",
            takefocus=0,
            command=self._toggle_monitoring,
            style="Start_Theme.TButton"
        )
        # Do not grid stop button initially

        self.btn_copy = ttk.Button(
            self.frame,
            image=self.copy_icon,
            text="RegEx",
            compound="left",
            takefocus=0,
            command=self._copy_regex_statement,
            style="Start_Theme.TButton"
        )
        self.btn_copy.grid(column=1, row=0, padx=2, pady=2)

        self.btn_clean = ttk.Button(
            self.frame,
            image=self.trash_icon,
            text="Trash",
            compound="left",
            takefocus=0,
            command=self._clean_assets,
            style="Start_Theme.TButton"
        )
        self.btn_clean.grid(column=2, row=0, padx=2, pady=2)

        self.btn_debug = ttk.Button(
            self.frame,
            image=self.debug_icon,
            text="Debug",
            compound="left",
            takefocus=0,
            command=self.on_debug,
            style="Start_Theme.TButton"
        )
        self.btn_debug.grid(column=3, row=0, padx=2, pady=2)

        # Track monitoring state
        self.is_monitoring = False

    def _load_icons(self):
        """Load button icons from PNG files"""
        try:
            # Start icon: simple play triangle
            play_img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            draw_play = ImageDraw.Draw(play_img)
            draw_play.polygon([(5, 3), (13, 8), (5, 13)], fill='white')
            self.start_icon = ImageTk.PhotoImage(play_img)

            # Stop icon: traditional filled square
            stop_img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            draw_stop = ImageDraw.Draw(stop_img)
            draw_stop.rectangle([4, 4, 12, 12], fill='white')
            self.stop_icon = ImageTk.PhotoImage(stop_img)

            # Copy icon: two overlapping sheets
            copy_img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            draw_copy = ImageDraw.Draw(copy_img)
            draw_copy.rectangle([6, 3, 13, 12], outline='white', width=2)
            draw_copy.rectangle([3, 6, 10, 15], outline='white', width=2)
            self.copy_icon = ImageTk.PhotoImage(copy_img)

            # Trash icon: simple trash can
            trash_img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            draw_trash = ImageDraw.Draw(trash_img)
            draw_trash.rectangle([4, 5, 12, 13], outline='white', width=2)
            draw_trash.rectangle([3, 3, 13, 5], fill='white')
            draw_trash.line([(6, 2), (10, 2)], fill='white', width=2)
            draw_trash.line([(7, 7), (7, 11)], fill='white', width=1)
            draw_trash.line([(9, 7), (9, 11)], fill='white', width=1)
            self.trash_icon_pil = trash_img
            self.trash_icon = ImageTk.PhotoImage(trash_img)

            # Debug icon: simple bug glyph for recognizable debugging action
            debug_img = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
            draw_debug = ImageDraw.Draw(debug_img)
            draw_debug.ellipse([4, 6, 12, 14], outline='white', width=2)
            draw_debug.ellipse([6, 3, 10, 7], outline='white', width=2)
            draw_debug.line([(7, 2), (6, 0)], fill='white', width=1)
            draw_debug.line([(9, 2), (10, 0)], fill='white', width=1)
            draw_debug.line([(4, 8), (2, 7)], fill='white', width=1)
            draw_debug.line([(4, 11), (2, 12)], fill='white', width=1)
            draw_debug.line([(12, 8), (14, 7)], fill='white', width=1)
            draw_debug.line([(12, 11), (14, 12)], fill='white', width=1)
            self.debug_icon_pil = debug_img
            self.debug_icon = ImageTk.PhotoImage(debug_img)
        except Exception as e:  # noqa: BLE001
            print(f"Could not create button icons: {e}")
            self.start_icon = None
            self.stop_icon = None
            self.copy_icon = None
            self.trash_icon = None
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
                except (tk.TclError, ValueError):
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
            
            print(f"OK: {button_name}: {actual_width}x{actual_height} - Text: {text_width}x{text_height} - Padding: L{left_pad},R{right_pad},T{top_pad},B{bottom_pad}")
            
            return {
                'dimensions': (actual_width, actual_height),
                'text_size': (text_width, text_height),
                'padding': (left_pad, top_pad, right_pad, bottom_pad),
                'centered': True
            }
            
        except Exception as e:  # noqa: BLE001
            print(f"Error centering {button_name}: {e}")
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

    def _copy_regex_statement(self):
        """Copy persisted regex statement to clipboard."""
        value = str(getattr(self.config, "regex_statement", ""))
        root = self.frame.winfo_toplevel()

        if not value:
            print("No regex statement saved to copy.")
            return

        try:
            root.clipboard_clear()
            root.clipboard_append(value)
            # macOS can require a full update cycle for clipboard ownership to stick.
            root.update()
            print("Regex statement copied to clipboard.")
        except Exception as e:  # noqa: BLE001
            if platform.system() == "Darwin":
                try:
                    subprocess.run(["pbcopy"], input=value, text=True, check=True)
                    print("Regex statement copied to clipboard.")
                    return
                except Exception as pb_err:  # noqa: BLE001
                    print(f"Could not copy regex statement: {pb_err}")
                    return

            print(f"Could not copy regex statement: {e}")
    
    def _clean_assets(self):
        """Clean all assets"""
        deleted = self.file_monitor.clean_assets()
        messagebox.showinfo("Cleaned", f"{deleted} files moved to trash.")

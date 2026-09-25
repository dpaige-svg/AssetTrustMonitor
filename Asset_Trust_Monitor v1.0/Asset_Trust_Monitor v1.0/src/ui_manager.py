#!/usr/bin/env python3
"""
UI Management for Asset Trust Monitor

Handles GUI creation, styling, and user interactions.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import io
from PIL import Image, ImageTk

from .system_tray import SystemTray
from .studio_manager import StudioManager


class UIManager:
    """Manages the main GUI interface"""
    
    def __init__(self, config, file_monitor, rojo_server, cleanup_callback=None, studio_manager=None):
        self.config = config
        self.file_monitor = file_monitor
        self.rojo_server = rojo_server
        self.cleanup_callback = cleanup_callback
        # StudioManager instance for accessing/manipulating Roblox Studio
        self.studio_manager = studio_manager
        
        self.root = None
        self.start_icon = None
        self.stop_icon = None
        self.trash_icon = None
        self.title_icon = None
        
        # UI Components
        self.btn_start = None
        self.btn_clean = None
        self.lbl_status = None
        self.lbl_count = None
        
        self._setup_ui()
        self._setup_callbacks()
    
    def _setup_ui(self):
        """Initialize the main UI"""
        self.root = tk.Tk()
        self.root.title("Asset Trust Monitor")
        self.root.geometry(self.config.window_size)
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        
        self._setup_custom_title_bar()
        self._setup_styles()
        self._create_main_frame()
        self._load_icons()
        self._create_widgets()
    
    def _setup_custom_title_bar(self):
        """Setup custom title bar"""
        self.root.overrideredirect(True)
        
        # Title bar frame
        title_bar = tk.Frame(self.root, bg=self.config.title_bar_bg, relief='flat', bd=1)
        title_bar.pack(fill='x')
        
        # Title bar dragging functionality
        def start_move(event):
            self.root.x = event.x
            self.root.y = event.y
        
        def stop_move(event):
            self.root.x = None
            self.root.y = None
        
        def on_move(event):
            if hasattr(self.root, 'x') and self.root.x is not None:
                deltax = event.x - self.root.x
                deltay = event.y - self.root.y
                x = self.root.winfo_x() + deltax
                y = self.root.winfo_y() + deltay
                self.root.geometry(f"+{x}+{y}")
        
        # Bind dragging events
        title_bar.bind("<ButtonPress-1>", start_move)
        title_bar.bind("<ButtonRelease-1>", stop_move)
        title_bar.bind("<B1-Motion>", on_move)
        
        # Title text with tray-style icon (convert PIL Image -> Tk PhotoImage and keep a reference)
        tray_pil_image = SystemTray._create_icon_image(self)
        try:
            tray_pil_image = tray_pil_image.resize((20, 20), Image.Resampling.LANCZOS)
        except Exception:
            tray_pil_image = tray_pil_image.resize((20, 20), Image.LANCZOS)
        self.title_icon = ImageTk.PhotoImage(tray_pil_image)
        title_label = tk.Label(title_bar, image=self.title_icon,
                             bg=self.config.title_bar_bg, fg='white')
        # Prevent garbage collection of the image by keeping a reference on the widget
        title_label.image = self.title_icon
        title_label.pack(side='left', padx=10, pady=0)

        '''title_header = tk.Label(title_bar, text="AT Monitor",
                             bg=self.config.title_bar_bg, fg='white', font=("Segoe UI", 6, "bold"))
        title_header.pack(side='left', padx=0, pady=0)'''

        #Make the title label draggable too
        title_label.bind("<ButtonPress-1>", start_move)
        title_label.bind("<ButtonRelease-1>", stop_move)
        title_label.bind("<B1-Motion>", on_move)

        # Close button
        close_btn = ttk.Button(title_bar, text='X', command=self._close_application, 
                               style="TLabel")
        close_btn.pack(side='right', padx=5, pady=2)
        
        # Minimize button (will be connected to system tray later)
        minimize_btn = ttk.Button(title_bar, text='—', command=self._minimize_window,
                               style="TLabel")
        minimize_btn.pack(side='right', padx=5, pady=2)

        refresh_btn = ttk.Button(title_bar, text='⟳', command=self._refresh_status,
                               style="TLabel")
        refresh_btn.pack(side='right', padx=5, pady=2)

    def _setup_styles(self):
        """Configure UI styles and themes"""
        style = ttk.Style()
        style.theme_use("clam")
        
        # Button styles
        style.configure("Start_Theme.TButton",
                       font=("Segoe UI", 10, "bold"),
                       padding=(0, 5, 0, 5),
                       background=self.config.dark_bg,
                       foreground="white",
                       borderwidth=1,
                       relief="flat")
        
        style.configure("TFrame", 
                       background=self.config.dark_bg, 
                       relief="flat", 
                       padding=1)
        
        style.map("TButton",
                 background=[("active", "#212121"), ("pressed", "#212121")],
                 foreground=[("active", "white"), ("pressed", "white")])
        
        style.configure("TLabel", 
                       background=self.config.title_bar_bg,
                       foreground="white",
                       borderwidth=1,
                       relief="flat",
                       bd=0)
        style.map("TLabel",
            background=[
                ("active", self.config.title_bar_bg),
                ("pressed", self.config.title_bar_bg),
                ("!disabled", self.config.title_bar_bg)
            ],
            foreground=[
                ("active", "black"),
                ("pressed", "black"),
                ("!disabled", "white")
            ]
        )

    def _create_main_frame(self):
        """Create the main content frame"""
        self.frame = ttk.Frame(self.root, style="TFrame")
        self.frame.pack(expand=True, fill="both")
        
        # Configure grid weights
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
    
    def _load_icons(self):
        """Load and process icon files"""
        def load_icon(icon_name):
            """Load and process an icon file, converting black pixels to grey"""
            try:
                icon_path = self.config.get_icon_path(icon_name)
                
                icon_img = Image.open(icon_path)
                icon_img = icon_img.resize((20, 20), Image.Resampling.LANCZOS)
                
                # Convert ICO to RGBA mode first to ensure proper PNG conversion
                icon_img = icon_img.convert('RGBA')
                pixels = icon_img.load()
                width, height = icon_img.size
                
                for x in range(width):
                    for y in range(height):
                        r, g, b, a = pixels[x, y]
                        if r < 128 and g < 128 and b < 128 and a > 0:
                            pixels[x, y] = (180, 180, 180, a)
                
                # Convert PIL image to PhotoImage via BytesIO
                bio = io.BytesIO()
                icon_img.save(bio, format='PNG')
                bio.seek(0)
                return tk.PhotoImage(data=bio.getvalue())
            except Exception as e:
                print(f"Could not load {icon_name} icon: {e}")
                return None
        
        # Load all icons
        self.start_icon = load_icon("search")
        self.stop_icon = load_icon("stop")
        self.trash_icon = load_icon("trash")
    
    def _create_widgets(self):
        """Create all UI widgets"""
        # Start/Stop button
        if self.start_icon:
            self.btn_start = ttk.Button(self.frame, image=self.start_icon, 
                                      takefocus=0, command=self._toggle_monitoring, 
                                      style="Start_Theme.TButton")
            self.btn_start.image = self.start_icon
        else:
            self.btn_start = ttk.Button(self.frame, text="Start", 
                                      takefocus=0, command=self._toggle_monitoring, 
                                      style="Start_Theme.TButton")
        
        self.btn_start.grid(column=0, row=0, padx=3, pady=10, sticky="ew")
        
        # Trash button
        if self.trash_icon:
            self.btn_clean = ttk.Button(self.frame, image=self.trash_icon, 
                                      takefocus=0, command=self._clean_assets, 
                                      style="Start_Theme.TButton")
            self.btn_clean.image = self.trash_icon
        else:
            self.btn_clean = ttk.Button(self.frame, text="Trash Assets", 
                                      takefocus=0, command=self._clean_assets, 
                                      style="Start_Theme.TButton")
        
        self.btn_clean.grid(column=1, row=0, padx=3, pady=10, sticky="ew")
        
        # Asset count labels
        lbl_title = ttk.Label(self.frame, text="Assets:", 
                            background=self.config.dark_bg, foreground="white", 
                            font=("Segoe UI", 12))
        lbl_title.grid(column=0, row=1, padx=5, pady=0, sticky="e")
        
        self.lbl_count = ttk.Label(self.frame, text="0", 
                                 background=self.config.dark_bg, 
                                 foreground=self.config.accent_color, 
                                 font=("Segoe UI", 12))
        self.lbl_count.grid(column=1, row=1, padx=5, pady=0, sticky="w")
        
        # Server status labels
        server_title = ttk.Label(self.frame, text="Rojo Server:", 
                               background=self.config.dark_bg, foreground="white", 
                               font=("Segoe UI", 9))
        server_title.grid(column=0, row=2, padx=0, pady=0, sticky="e")
        
        self.lbl_status = ttk.Label(self.frame, text="Unknown", 
                                  background=self.config.dark_bg, foreground="yellow", 
                                  font=("Segoe UI", 9))
        self.lbl_status.grid(column=1, row=2, padx=0, pady=0, sticky="w")
    
    def _setup_callbacks(self):
        """Setup callbacks for monitoring updates"""
        # Server status callback
        def update_status(is_running):
            if is_running:
                self.root.after(0, lambda: self.lbl_status.config(text="Running", foreground="lightgreen"))
            else:
                self.root.after(0, lambda: self.lbl_status.config(text="Stopped", foreground="red"))
        
        # Asset count callback
        def update_count(count):
            self.root.after(0, lambda: self.lbl_count.config(text=str(count)))
        
        # Register callbacks
        self.rojo_server.add_status_callback(update_status)
        self.file_monitor.add_count_callback(update_count)
    
    def _toggle_monitoring(self):
        """Toggle file monitoring on/off"""
        if self.file_monitor.is_monitoring():
            # Stop monitoring
            self.file_monitor.stop_monitoring()
            if self.start_icon:
                self.btn_start.configure(image=self.start_icon)
                self.btn_start.image = self.start_icon
            else:
                self.btn_start.configure(text="Start")
        else:
            # Start monitoring
            self.file_monitor.start_monitoring()
            if self.stop_icon:
                self.btn_start.configure(image=self.stop_icon)
                self.btn_start.image = self.stop_icon
            else:
                self.btn_start.configure(text="Stop")
    
    def _refresh_status(self):
        """Refresh Rojo server and Roblox Studio manually"""
        self.studio_manager.restart()
        self.rojo_server.restart()


    def _clean_assets(self):
        """Clean all assets"""
        deleted = self.file_monitor.clean_assets()
        messagebox.showinfo("Cleaned", f"{deleted} files moved to trash.")
    
    def _minimize_window(self):
        """Minimize window to system tray"""
        self.system_tray._toggle_window()

    def _close_application(self):
        """Close the application properly"""
        # Call main app cleanup if available
        if self.cleanup_callback:
            self.cleanup_callback()
        
        # Cancel any pending tkinter operations
        self.root.after_cancel("all")
        
        # Quit and destroy the window
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the GUI main loop"""
        print("GUI Initialized - Application Ready!")
        self.root.mainloop()
    
    def set_system_tray(self, system_tray):
        """Connect system tray for minimize functionality"""
        self.system_tray = system_tray
        # Update minimize button to use system tray
        # This can be expanded to properly integrate with system tray
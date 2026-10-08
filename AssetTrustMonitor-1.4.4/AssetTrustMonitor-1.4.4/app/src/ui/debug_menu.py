import tkinter as tk
from tkinter import ttk

from ..core.log_bus import get_log_bus
from .debug_options import DEBUG_SECTIONS
from .styles import StyleManager
from .title_bar import TitleBar


class DebugMenu:

    def __init__(self, config, studio_manager, rojo_server, update_manager, cache_manager, file_monitor=None, parent=None):
        self.config = config
        self.studio_manager = studio_manager
        self.rojo_server = rojo_server
        self.update_manager = update_manager
        self.cache_manager = cache_manager
        self.file_monitor = file_monitor
        self.parent = parent
        self.window = None
        self.is_open = False
        self.log_bus = get_log_bus()
        self.log_text = None
        self._log_listener = None
        
    def toggle(self):
        """Toggle the debug menu window"""
        if self.is_open:
            self.close()
        else:
            self.open()
    
    def open(self):
        """Open the debug menu"""
        if not self.is_open:
            self._create_window()
    
    def _setup_styles(self):
        """Configure UI styles and themes"""
        # Use shared StyleManager
        self.style_manager = StyleManager(self.window, self.config)
        
        # Define modern style for debug menu buttons
        style = ttk.Style(self.window)
        style.configure("Debug.TButton", 
                   font=("Segoe UI", 9, "normal"),
                   padding=(8, 4),
                   background="#2D2D2D",
                   foreground="#F0F0F0",
                   borderwidth=0,
                   relief="flat",
                   anchor="center")
        
        style.map("Debug.TButton",
                background=[("active", "#3A3A3A"), ("pressed", "#454545")],
                foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")])
        
        # Section frame style
        style.configure("DebugSection.TFrame",
                       background=self.config.dark_bg,
                       relief="flat",
                       borderwidth=0)
        
        # Section label style
        style.configure("DebugSection.TLabel",
                       font=("Segoe UI", 10, "bold"),
                       background=self.config.dark_bg,
                       foreground="#4A9EFF",
                       padding=(0, 2))
        
        # Scrollbar styling - modern dark theme (not used with custom scrollbar)
        # Keeping for potential future use

    def close(self):
        """Close the debug menu window"""
        if self.window and self.is_open:
            if self._log_listener:
                self.log_bus.unsubscribe(self._log_listener)
                self._log_listener = None
            self.window.destroy()
            self.window = None
            self.is_open = False
    
    def _create_window(self):
        """Create the debug menu window with custom title bar"""
        self.window = tk.Toplevel() if self.parent else tk.Tk()
        self._setup_styles()
        self.window.title("Debug")
        self.window.geometry("700x520")
        self.window.configure(bg=self.config.title_bar_bg)
        try:
            # Use 1 instead of True for better compatibility
            self.window.attributes("-topmost", 1)
        except Exception:  # noqa: BLE001, S110
            pass
        self.window.resizable(False, False)
        
        # Add custom title bar
        self.title_bar = TitleBar(
            parent_window=self.window,
            config=self.config,
            show_icon=True,
            show_version_dropdown=True,
            show_minimize=False,
            show_close=True,
            title_text="Debug",
            on_close=self._on_close,
            studio_manager=self.studio_manager,
            rojo_server=self.rojo_server,
            update_manager=self.update_manager
        )
        
        # Create scrollable container
        self._create_scrollable_content()

        # Add live log console
        self._create_log_console()
        
        self.is_open = True

        # Re-enforce borderless styling after map on platforms that may restore decorations.
        self.window.bind("<Map>", self._on_window_map, add="+")
        
        # Handle window close event
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_window_map(self, event=None):
        """Ensure custom title bar stays borderless when window is shown."""
        try:
            if hasattr(self, 'title_bar') and self.title_bar:
                self.window.after(0, lambda: self.title_bar.set_borderless(True))
        except Exception:  # noqa: BLE001, S110
            pass

    def _create_scrollable_content(self):
        """Create scrollable content area with custom modern scrollbar"""
        # Create main container frame
        container = ttk.Frame(self.window, style="TFrame")
        container.pack(fill='both', expand=True, padx=15, pady=(10, 6))
        
        # Create canvas for content
        self.canvas = tk.Canvas(container, bg=self.config.dark_bg, highlightthickness=0)
        
        # Create floating scrollbar (no background frame, just the thumb)
        self.scrollbar_thumb = tk.Canvas(container, 
                                       bg=self.config.dark_bg, 
                                       highlightthickness=0,
                                       width=12, height=40)
        
        # Draw initial scrollbar thumb
        self._draw_scrollbar_thumb()
        
        # Bind scrollbar events
        self.scrollbar_thumb.bind("<Button-1>", self._start_scroll)
        self.scrollbar_thumb.bind("<B1-Motion>", self._drag_scroll)
        
        # Position scrollbar flush to the right edge
        self.scrollbar_thumb.place(relx=1.0, x=-15, y=0, anchor="ne", height=0)  # Initial height 0, will be updated
        
        # Pack canvas
        self.canvas.pack(side="left", fill="both", expand=True)
        
        # Create scrollable frame inside canvas
        self.scrollable_frame = ttk.Frame(self.canvas, style="TFrame")
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self._update_scroll_region()
        )
        
        # Create window in canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Update window width when canvas resizes
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Configure canvas scrolling
        self.canvas.configure(yscrollcommand=self._update_scrollbar_position)

        # Bind mousewheel scrolling (requires scrollable_frame to exist).
        self._bind_mousewheel()
        
        # Create debug options in scrollable frame
        self._create_debug_options(self.scrollable_frame)

    def _create_log_console(self):
        """Create a terminal-like dark log console that receives stdout/stderr."""
        log_container = ttk.Frame(self.window, style="TFrame")
        log_container.pack(fill='both', expand=False, padx=15, pady=(0, 10))

        header = tk.Label(
            log_container,
            text="Application Output",
            bg=self.config.dark_bg,
            fg="white",
            font=("Consolas", 10, "bold"),
            anchor="w"
        )
        header.pack(fill='x', padx=10, pady=(4, 4))

        terminal_frame = tk.Frame(log_container, bg="#111111", bd=1, relief="flat", highlightthickness=1, highlightbackground="#2a2a2a")
        terminal_frame.pack(fill='both', expand=True, padx=10, pady=(0, 4))

        self.log_text = tk.Text(
            terminal_frame,
            bg="#111111",
            fg="#d7d7d7",
            insertbackground="#d7d7d7",
            font=("Consolas", 9),
            relief="flat",
            borderwidth=0,
            wrap="word",
            height=12
        )
        self.log_text.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=8)

        text_scroll = ttk.Scrollbar(terminal_frame, orient='vertical', command=self.log_text.yview)
        text_scroll.pack(side='right', fill='y', padx=(0, 6), pady=6)
        self.log_text.configure(yscrollcommand=text_scroll.set)

        self.log_text.tag_configure("stdout", foreground="#d7d7d7")
        self.log_text.tag_configure("stderr", foreground="#ff7b72")

        # Load existing log history so startup events are visible.
        for stream_name, message in self.log_bus.get_entries():
            self._append_log(stream_name, message)

        def _listener(stream_name, message):
            if self.window and self.window.winfo_exists():
                try:
                    self.window.after(0, lambda: self._append_log(stream_name, message))
                except Exception:  # noqa: BLE001, S110
                    pass

        self._log_listener = _listener
        self.log_bus.subscribe(self._log_listener)

    def _append_log(self, stream_name, message):
        """Append a log message into the terminal widget."""
        if not self.log_text or not self.log_text.winfo_exists() or not message:
            return

        self.log_text.insert("end", message, stream_name)
        self.log_text.see("end")

    def _draw_scrollbar_thumb(self):
        """Draw the modern rounded scrollbar thumb"""
        self.scrollbar_thumb.delete("all")
        
        # Create rounded rectangle for thumb
        width = 12
        height = self.scrollbar_thumb.winfo_height() or 40
        radius = 6
        
        # Ensure minimum height
        height = max(height, 20)
        
        # Draw the rounded rectangle as a single smooth shape
        # Main body
        self.scrollbar_thumb.create_rectangle(radius, 0, width-radius, height, 
                                            fill="#333333", outline="")
        
        # Top rounded cap
        self.scrollbar_thumb.create_oval(0, 0, radius*2, radius*2, 
                                       fill="#333333", outline="")
        
        # Bottom rounded cap  
        self.scrollbar_thumb.create_oval(0, height-radius*2, radius*2, height, 
                                       fill="#333333", outline="")
        
        # Fill the middle section to ensure smooth connection
        self.scrollbar_thumb.create_rectangle(radius, radius, width-radius, height-radius, 
                                            fill="#333333", outline="")

    def _update_scroll_region(self):
        """Update the canvas scroll region when content changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._update_scrollbar()

    def _on_canvas_configure(self, event):
        """Handle canvas resize"""
        # Update scrollable frame width to match canvas
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        # Update scrollbar
        self._update_scrollbar()

    def _update_scrollbar(self, *args):
        """Update scrollbar visibility and position"""
        try:
            # Get canvas dimensions
            canvas_height = self.canvas.winfo_height()
            scroll_region = self.canvas.cget("scrollregion")
            
            if scroll_region:
                # Parse scroll region
                coords = [int(x) for x in scroll_region.split()]
                content_height = coords[3] - coords[1]
                
                if content_height > canvas_height:
                    # Calculate thumb size and position
                    thumb_height = max(30, (canvas_height / content_height) * canvas_height)
                    self.scrollbar_thumb.configure(height=thumb_height)
                    self._draw_scrollbar_thumb()
                    
                    # Position scrollbar flush to right edge
                    self.scrollbar_thumb.place(relx=1.0, x=-15, y=0, anchor="ne", height=thumb_height)
                    self._update_scrollbar_position()
                else:
                    # Hide scrollbar
                    self.scrollbar_thumb.place_forget()
            else:
                self.scrollbar_thumb.place_forget()
        except (tk.TclError, AttributeError, IndexError):
            pass  # Ignore errors during initialization

    def _update_scrollbar_position(self, *args):
        """Update scrollbar thumb position based on canvas scroll"""
        try:
            # Get current scroll position
            scroll_info = self.canvas.yview()
            scroll_top = scroll_info[0]
            
            # Calculate thumb position
            canvas_height = self.canvas.winfo_height()
            thumb_height = self.scrollbar_thumb.winfo_height()
            
            # Available space for thumb movement (canvas height minus thumb height)
            track_height = canvas_height - thumb_height
            thumb_y = scroll_top * track_height
            
            # Position scrollbar at the calculated Y position, flush to right edge
            self.scrollbar_thumb.place(relx=1.0, x=-15, y=thumb_y, anchor="ne", height=thumb_height)
            
        except (tk.TclError, AttributeError, IndexError):
            pass  # Ignore errors during initialization

    def _start_scroll(self, event):
        """Start scrollbar drag"""
        self.scroll_start_y = event.y
        self.canvas_start_y = self.canvas.yview()[0]

    def _drag_scroll(self, event):
        """Handle scrollbar drag"""
        try:
            # Calculate drag distance
            drag_distance = event.y - self.scroll_start_y
            
            # Get canvas height and thumb height
            canvas_height = self.canvas.winfo_height()
            thumb_height = self.scrollbar_thumb.winfo_height()
            
            # Calculate scroll amount
            scroll_fraction = drag_distance / (canvas_height - thumb_height)
            
            # Apply scroll
            new_scroll = self.canvas_start_y + scroll_fraction
            new_scroll = max(0, min(1, new_scroll))
            
            self.canvas.yview_moveto(new_scroll)
            
        except (tk.TclError, AttributeError, ZeroDivisionError):
            pass

    def _mousewheel_scroll(self, event):
        """Handle mouse wheel scrolling"""
        # Linux X11 wheel events
        if hasattr(event, "num"):
            if event.num == 4:
                self.canvas.yview_scroll(-1, "units")
                return
            if event.num == 5:
                self.canvas.yview_scroll(1, "units")
                return

        delta = getattr(event, "delta", 0)
        if delta == 0:
            return

        # macOS often sends small deltas; Windows usually sends multiples of 120.
        if abs(delta) >= 120:
            units = int(-delta / 120)
        else:
            units = -1 if delta > 0 else 1

        if units == 0:
            units = -1 if delta > 0 else 1

        self.canvas.yview_scroll(units, "units")

    def _bind_mousewheel(self):
        """Bind mousewheel to canvas scrolling"""
        def _is_descendant_of_canvas(widget):
            current = widget
            while current is not None:
                if current == self.canvas:
                    return True
                current = getattr(current, "master", None)
            return False

        def _on_mousewheel(event):
            target = None
            try:
                if hasattr(event, "x_root") and hasattr(event, "y_root"):
                    target = self.window.winfo_containing(event.x_root, event.y_root)
            except Exception:  # noqa: BLE001
                target = None

            if target is None:
                target = getattr(event, "widget", None)

            # Only scroll debug options when pointer is over the scrollable canvas region.
            if target is not None and _is_descendant_of_canvas(target):
                self._mousewheel_scroll(event)

        # Bind on toplevel so wheel events from nested child widgets are captured reliably.
        self.window.bind("<MouseWheel>", _on_mousewheel, add="+")
        self.window.bind("<Button-4>", _on_mousewheel, add="+")
        self.window.bind("<Button-5>", _on_mousewheel, add="+")

    def _create_debug_options(self, parent):
        """Grid layout for debug options - modular sections with modern styling"""
        
        # Configure grid columns and rows for scrollable parent
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        # Allow rows to expand - configure more rows for scrolling
        for i in range(20):  # Increased for more sections
            parent.rowconfigure(i, weight=0)

        # Prepare managers dict for sections
        managers = {
            'studio_manager': self.studio_manager,
            'rojo_server': self.rojo_server,
            'update_manager': self.update_manager,
            'cache_manager': self.cache_manager,
            'file_monitor': self.file_monitor,
        }

        current_row = 0
        
        # Add each section independently with modern styling
        for section_class in DEBUG_SECTIONS:
            try:
                # Create container first
                container = ttk.Frame(parent, style="DebugSection.TFrame")
                container.grid(row=current_row, column=0, columnspan=2, 
                             sticky="ew", pady=(10, 5) if current_row > 0 else (5, 5))
                
                # Configure container grid
                container.grid_rowconfigure(1, weight=1)
                container.grid_columnconfigure(0, weight=1)
                
                # Add section label
                section_name = getattr(section_class, 'SECTION_NAME', 
                                     section_class.__name__.replace('Section', '').replace('Section', ' Options'))
                
                # Use tk.Label for guaranteed seamless background
                section_label = tk.Label(container, text=section_name, 
                                       bg=self.config.dark_bg,
                                       fg="white",
                                       font=("Segoe UI", 10, "bold"),
                                       anchor="w")
                section_label.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 5))
                
                # Create section with container as parent
                section = section_class(container, self.config, managers)
                section_frame = section.create()
                
                # Place section content in container
                section_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
                
                current_row += 1
                
            except Exception as e:  # noqa: BLE001
                print(f"[DebugMenu] Failed to create {section_class.__name__}: {e}")
                # Continue with other sections
        
    
    def _on_close(self):
        """Handle window close event"""
        self.is_open = False
        if self.window:
            self.window.destroy()
            self.window = None

#!/usr/bin/env python3
"""
Style Configuration for Asset Trust Monitor

Handles UI styling and themes for tkinter widgets.
"""

from tkinter import ttk


class StyleManager:
    """Manages UI styles and themes"""
    
    def __init__(self, root_window, config):
        """
        Initialize style manager
        
        Args:
            root_window: Root tkinter window
            config: Config instance with color settings
        """
        self.root = root_window
        self.config = config
        self.style = ttk.Style()
        
        self._setup_styles()
    
    def _setup_styles(self):
        """Configure UI styles and themes"""
        self.style.theme_use("clam")
        
        self._configure_button_styles()
        self._configure_frame_styles()
        self._configure_label_styles()
        self._configure_combobox_styles()
    
    def _configure_button_styles(self):
        """Configure button styles"""
        # Use a clean font for better emoji rendering (normal weight, not bold)
        icon_font = ("Arial", 10, "normal")  # Smaller font for compact design
        try:
            import platform
            if platform.system() == "Darwin":
                icon_font = ("SF Pro Display", 12, "normal")  # macOS system font
            elif platform.system() == "Linux":
                icon_font = ("Ubuntu", 12, "normal")
        except Exception:
            pass
        self.style.configure(
            "Start_Theme.TButton",
            font=icon_font,
            padding=(2, 2, 2, 2),  # Slightly more vertical padding for better proportions
            background=self.config.dark_bg,
            foreground="#B4B4B4",
            borderwidth=1,
            relief="flat",
            justify="center",
            anchor="center",
            width=8,
            height=4
        )
        
        self.style.map(
            "TButton",
            background=[("active", "#212121"), ("pressed", "#212121")],
            foreground=[("active", "white"), ("pressed", "white")]
        )

        # Title Bar Button Style
        self.style.configure(
            "TitleBar.TButton",
            background=self.config.title_bar_bg,
            foreground="white",
            borderwidth=0,
            relief="flat",
            padding=(5, 2)
        )
        
        self.style.map(
            "TitleBar.TButton",
            background=[("active", "#3a3a3a"), ("pressed", "#3a3a3a")],
            foreground=[("active", "white"), ("pressed", "white")]
        )

        # Close button — red on hover so it's clearly identifiable
        self.style.configure(
            "TitleBar.Close.TButton",
            background=self.config.title_bar_bg,
            foreground="white",
            borderwidth=0,
            relief="flat",
            padding=(5, 2)
        )
        self.style.map(
            "TitleBar.Close.TButton",
            background=[("active", "#c0392b"), ("pressed", "#922b21")],
            foreground=[("active", "white"), ("pressed", "white")]
        )
        
        # Image Button Style for transparent appearance
        self.style.configure(
            "Image.TButton",
            background=self.config.dark_bg,
            foreground='white',
            borderwidth=0,
            relief="flat",
            padding=(0, 0)
        )
        
        self.style.map(
            "Image.TButton",
            background=[("active", self.config.dark_bg), ("pressed", self.config.dark_bg)],
            foreground=[("active", "grey"), ("pressed", "grey")]
        )
    
    def _configure_frame_styles(self):
        """Configure frame styles"""
        self.style.configure(
            "TFrame", 
            background=self.config.dark_bg, 
            relief="flat", 
            borderwidth=0
        )
    
    def _configure_label_styles(self):
        """Configure label styles"""
        # Use a monochrome font for Unicode icons (works on both Mac and Windows)
        icon_font = ("Segoe UI Symbol", 10)
        try:
            import platform
            if platform.system() == "Darwin":
                icon_font = ("Arial Unicode MS", 10)
        except Exception:
            pass
        self.style.configure(
            "TLabel", 
            background=self.config.title_bar_bg,
            foreground="white",
            borderwidth=1,
            relief="flat",
            bd=0,
            font=icon_font,
            anchor="center",
            justify="center"
        )
        
        self.style.map(
            "TLabel",
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
    
    def _configure_combobox_styles(self):
        """Configure combobox styles"""
        # Titlebar combobox field styling (this affects the main input area)
        self.style.configure(
            "Titlebar.TCombobox",
            fieldbackground=self.config.title_bar_bg,
            background=self.config.title_bar_bg,
            foreground="white",
            arrowcolor="white",
            arrowsize=10,
            bordercolor=self.config.title_bar_bg,
            borderwidth=0,
            darkcolor=self.config.title_bar_bg,
            lightcolor=self.config.title_bar_bg,
            relief="flat",
            padding=2,
            selectbackground=self.config.title_bar_bg,
            selectforeground="white"
        )
        
        # Map states to keep borders hidden and remove selection highlight
        self.style.map(
            "Titlebar.TCombobox",
            fieldbackground=[("readonly", self.config.title_bar_bg), ("focus", self.config.title_bar_bg)],
            background=[("readonly", self.config.title_bar_bg), ("active", self.config.title_bar_bg)],
            selectbackground=[("readonly", self.config.title_bar_bg), ("focus", self.config.title_bar_bg)],
            selectforeground=[("readonly", "white"), ("focus", "white")],
            bordercolor=[("readonly", self.config.title_bar_bg), ("focus", self.config.title_bar_bg)],
            darkcolor=[("readonly", self.config.title_bar_bg), ("focus", self.config.title_bar_bg)],
            lightcolor=[("readonly", self.config.title_bar_bg), ("focus", self.config.title_bar_bg)]
        )
        
        # Configure combobox dropdown listbox base styling
        self.root.option_add('*TCombobox*Listbox.background', self.config.dark_bg)
        self.root.option_add('*TCombobox*Listbox.foreground', 'white')
        self.root.option_add('*TCombobox*Listbox.selectBackground', '#2A2A2A')
        self.root.option_add('*TCombobox*Listbox.selectForeground', 'white')
        self.root.option_add('*TCombobox*Listbox.borderWidth', 0)
        self.root.option_add('*TCombobox*Listbox.highlightThickness', 0)
        self.root.option_add('*TCombobox*Listbox.highlightBackground', self.config.dark_bg)
        self.root.option_add('*TCombobox*Listbox.highlightColor', self.config.dark_bg)
        self.root.option_add('*TCombobox*Listbox.relief', 'flat')
        
        # Configure the popdown frame background
        self.root.option_add('*TCombobox.popdown.f.background', self.config.dark_bg)
        self.root.option_add('*TCombobox*Popdown*background', self.config.dark_bg)
        
        # Scrollbar styling
        self.style.configure('Titlebar.TCombobox.Vertical.TScrollbar',
                           background="#373737",
                           troughcolor=self.config.dark_bg,
                           borderwidth=0,
                           bordercolor=self.config.dark_bg,
                           relief='flat',
                           width=8,
                           arrowsize=0)
        
        self.style.map('Titlebar.TCombobox.Vertical.TScrollbar',
                      background=[('active', '#4A4A4A'), 
                                 ('pressed', '#4A4A4A'),
                                 ('!active', "#373737")],
                      bordercolor=[('active', self.config.dark_bg),
                                  ('!active', self.config.dark_bg)])
        
        # Remove scrollbar arrows
        self.style.layout('Titlebar.TCombobox.Vertical.TScrollbar', [
            ('Vertical.Scrollbar.trough', {
                'sticky': 'ns',
                'children': [
                    ('Vertical.Scrollbar.thumb', {
                        'expand': '1',
                        'sticky': 'nswe'
                    })
                ]
            })
        ])
    
    def apply_combobox_dropdown_style(self, combobox_widget, _retry_count=0):
        """
        Apply custom styling to a combobox dropdown after creation.
        This must be called after the combobox is created.
        
        Args:
            combobox_widget: The ttk.Combobox widget to style
        """
        try:
            widget_path = str(combobox_widget)
            if not widget_path:
                return

            # Popdown internals are lazily created. If not ready yet, retry shortly.
            popdown = self.root.tk.call('ttk::combobox::PopdownWindow', widget_path)
            frame_path = f"{popdown}.f"
            scrollbar_path = f"{frame_path}.sb"
            listbox_path = f"{frame_path}.l"

            widgets_ready = all(
                self.root.tk.call('winfo', 'exists', path) == '1'
                for path in (popdown, frame_path, scrollbar_path, listbox_path)
            )
            if not widgets_ready:
                if _retry_count < 5:
                    self.root.after(120, lambda: self.apply_combobox_dropdown_style(combobox_widget, _retry_count + 1))
                return

            # The popdown is a toplevel - remove its border completely.
            # Note: Don't use -background on toplevel as it's not supported on Windows.
            self.root.tk.call(popdown, 'configure', '-relief', 'flat', '-bd', 0, '-borderwidth', 0, '-highlightthickness', 0)

            # Configure the scrollbar style.
            self.root.tk.call(scrollbar_path, 'configure', '-style', 'Titlebar.TCombobox.Vertical.TScrollbar')

            # Configure the frame with background color.
            try:
                self.root.tk.call(
                    frame_path,
                    'configure',
                    '-background', self.config.dark_bg,
                    '-relief', 'flat',
                    '-bd', 0,
                    '-borderwidth', 0,
                    '-highlightthickness', 0,
                )
            except Exception:
                pass

            # Configure the listbox - remove border and highlight, darker hover color.
            self.root.tk.call(
                listbox_path,
                'configure',
                '-background', self.config.dark_bg,
                '-foreground', 'white',
                '-selectbackground', '#2A2A2A',
                '-selectforeground', 'white',
                '-relief', 'flat',
                '-bd', 0,
                '-borderwidth', 0,
                '-highlightthickness', 0,
                '-highlightbackground', self.config.dark_bg,
                '-highlightcolor', self.config.dark_bg,
            )
            
        except Exception as e:
            # Popup internals are timing-sensitive; only log once retries are exhausted.
            if _retry_count >= 5:
                print(f"Could not apply combobox dropdown style: {e}")

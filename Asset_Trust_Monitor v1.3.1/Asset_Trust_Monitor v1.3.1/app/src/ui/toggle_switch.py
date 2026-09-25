"""
Toggle switch widget for debug menu
"""
import tkinter as tk


class ToggleSwitch(tk.Canvas):
    """Modern Toggle Switch (Red/Green)"""
    def __init__(self, parent, value=False, command=None, width=40, height=20, bg="#1E1E1E", **kwargs):
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.value = value
        self.command = command
        self.width = width
        self.height = height

        self.bind("<Button-1>", self._on_click)
        self._update_visuals()

    def destroy(self):
        super().destroy()

    def _on_click(self, event):
        self.value = not self.value
        self._update_visuals()
        if self.command:
            self.command(self.value)

    def _update_visuals(self, *args):
        try:
            if not self.winfo_exists():
                return
            self.delete("all")
            state = bool(self.value)

            # Colors
            fill_color = "#4CAF50" if state else "#F44336"  # Green / Red
            circle_color = "white"

            # Draw track
            radius = self.height / 2
            self.create_oval(0, 0, self.height, self.height, fill=fill_color, outline="")
            self.create_oval(self.width - self.height, 0, self.width, self.height, fill=fill_color, outline="")
            self.create_rectangle(radius, 0, self.width - radius, self.height, fill=fill_color, outline="")

            # Draw knob
            padding = 2
            knob_radius = radius - padding
            if state:
                cx = self.width - radius
            else:
                cx = radius

            self.create_oval(cx - knob_radius, padding, cx + knob_radius, self.height - padding, fill=circle_color, outline="")
        except tk.TclError:
            pass
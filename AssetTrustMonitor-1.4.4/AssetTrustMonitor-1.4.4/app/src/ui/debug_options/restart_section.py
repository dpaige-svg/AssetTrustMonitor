"""
Restart options for debug menu
"""
import queue
import threading
from tkinter import ttk

from .base import DebugOption


class RestartSection(DebugOption):
    """Restart buttons section"""
    SECTION_NAME = "Service Control"

    def __init__(self, parent, config, managers):
        super().__init__(parent, config, managers)
        self._busy = False
        self._buttons = []
        self._results = queue.Queue()
    
    def get_required_managers(self):
        return ['studio_manager', 'rojo_server']
    
    def create(self):
        """Create restart buttons with modern layout"""
        self.frame = ttk.Frame(self.parent, style="DebugSection.TFrame")
        
        # Configure columns for uniform sizing
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)

        # Row 1: Studio and Rojo (Side by Side)
        btn_studio = ttk.Button(self.frame, text="Restart Studio", command=self._restart_studio,
                              style="Debug.TButton", cursor="hand2")
        btn_studio.grid(row=0, column=0, padx=(0, 2), pady=(0, 4), sticky="ew")

        btn_rojo = ttk.Button(self.frame, text="Restart Rojo", command=self._restart_rojo,
                            style="Debug.TButton", cursor="hand2")
        btn_rojo.grid(row=0, column=1, padx=(2, 0), pady=(0, 4), sticky="ew")

        # Row 2: Restart Both (Full Width)
        btn_both = ttk.Button(self.frame, text="Restart Both", command=self._restart_both,
                            style="Debug.TButton", cursor="hand2")
        btn_both.grid(row=1, column=0, columnspan=2, padx=0, pady=0, sticky="ew")

        self._buttons = [btn_studio, btn_rojo, btn_both]

        return self.frame
    
    def _restart_studio(self):
        """Refresh Roblox Studio instance"""
        self._start_restart("Studio", self._restart_studio_worker)
    
    def _restart_rojo(self):
        """Refresh Rojo server instance"""
        self._start_restart("Rojo", self._restart_rojo_worker)
    
    def _restart_both(self):
        """Refresh both Roblox Studio and Rojo server"""
        self._start_restart("Rojo and Studio", self._restart_both_worker)

    def _restart_studio_worker(self):
        manager = self.managers.get('studio_manager')
        return bool(manager and manager.stop() and manager.start(show_errors=False))

    def _restart_rojo_worker(self):
        server = self.managers.get('rojo_server')
        return bool(server and server.restart(suppress_dialogs=True))

    def _restart_both_worker(self):
        studio = self.managers.get('studio_manager')
        server = self.managers.get('rojo_server')
        if not studio or not server:
            return False

        studio_stopped = studio.stop()
        rojo_started = server.restart(suppress_dialogs=True)
        studio_started = rojo_started and studio.start(show_errors=False)
        return bool(studio_stopped and rojo_started and studio_started)

    def _start_restart(self, label, operation):
        """Run blocking process work off the Tk thread and prevent double-clicks."""
        if self._busy:
            print("A restart is already in progress")
            return

        self._busy = True
        for button in self._buttons:
            button.configure(state="disabled")
        print(f"Restarting {label}...")

        def worker():
            try:
                self._results.put((label, bool(operation()), None))
            except Exception as error:  # noqa: BLE001
                self._results.put((label, False, error))

        threading.Thread(target=worker, daemon=True).start()
        self.frame.after(100, self._poll_restart_result)

    def _poll_restart_result(self):
        try:
            label, success, error = self._results.get_nowait()
        except queue.Empty:
            if self.frame.winfo_exists():
                self.frame.after(100, self._poll_restart_result)
            return

        self._busy = False
        if self.frame.winfo_exists():
            for button in self._buttons:
                button.configure(state="normal")

        if success:
            print(f"{label} restarted successfully")
        elif error:
            print(f"Failed to restart {label}: {error}")
        else:
            print(f"Failed to restart {label}; check the Rojo server log for details")

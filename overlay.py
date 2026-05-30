from __future__ import annotations

import threading
import time
import tkinter as tk


def show_alert_overlay(message: str, duration_seconds: int = 4) -> None:
    """Best-effort overlay. Fail silently if tkinter/UI is unavailable."""

    def _run() -> None:
        try:
            root = tk.Tk()
            root.title("Anti-Burnout Alert")
            root.attributes("-topmost", True)
            root.attributes("-fullscreen", True)
            root.configure(bg="black")

            label = tk.Label(
                root,
                text=message,
                fg="#ff2d55",
                bg="black",
                font=("Segoe UI", 36, "bold"),
                wraplength=1400,
                justify="center",
            )
            label.pack(expand=True)

            # Flash effect
            start = time.time()

            def _tick() -> None:
                elapsed = time.time() - start
                if elapsed >= duration_seconds:
                    root.destroy()
                    return
                current = label.cget("fg")
                label.configure(fg="white" if current == "#ff2d55" else "#ff2d55")
                root.after(350, _tick)

            root.after(100, _tick)
            root.mainloop()
        except Exception:
            return

    threading.Thread(target=_run, daemon=True).start()
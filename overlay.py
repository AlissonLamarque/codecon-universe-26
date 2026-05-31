from __future__ import annotations

import threading
import time
import tkinter as tk


def show_intervention_popup(message: str, duration_seconds: float = 1.2) -> None:
    """
    Show a small topmost popup before enforcing relax mode.
    Best effort: if UI fails, returns quickly without crashing monitor loop.
    """

    done = threading.Event()
    body_text = (message or "Voce esta produtivo demais. Hora de descansar.").strip()
    adaptive_seconds = min(3.8, 0.9 + (len(body_text) / 52.0))
    final_seconds = max(float(duration_seconds), adaptive_seconds)

    def _run() -> None:
        try:
            root = tk.Tk()
            root.title("Anti-Burnout")
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.configure(bg="#0b1220")

            width = 560
            height = 180
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            x = max(10, int((screen_w - width) / 2))
            y = max(10, int((screen_h - height) / 2))
            root.geometry(f"{width}x{height}+{x}+{y}")

            card = tk.Frame(root, bg="#111827", bd=2, relief="solid")
            card.pack(fill="both", expand=True, padx=2, pady=2)

            top_row = tk.Frame(card, bg="#111827")
            top_row.pack(fill="x", padx=14, pady=(10, 6))

            avatar = tk.Canvas(top_row, width=42, height=42, bg="#111827", highlightthickness=0)
            avatar.create_oval(2, 2, 40, 40, fill="#e11d48", outline="")
            avatar.create_text(21, 21, text="AB", fill="white", font=("Segoe UI", 10, "bold"))
            avatar.pack(side="left")

            title = tk.Label(
                top_row,
                text="Agente Anti-Burnout",
                fg="#f8fafc",
                bg="#111827",
                font=("Segoe UI", 12, "bold"),
            )
            title.pack(side="left", padx=(10, 0))

            body = tk.Label(
                card,
                text=body_text,
                fg="#e5e7eb",
                bg="#111827",
                font=("Segoe UI", 11),
                wraplength=520,
                justify="left",
                anchor="w",
            )
            body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

            duration_ms = max(500, int(final_seconds * 1000))
            root.after(duration_ms, root.destroy)
            root.mainloop()
        except Exception:
            pass
        finally:
            done.set()

    threading.Thread(target=_run, daemon=True).start()
    done.wait(timeout=max(1.3, final_seconds + 0.9))


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

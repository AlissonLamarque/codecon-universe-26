from __future__ import annotations

import threading
import time
import tkinter as tk

_SIDE_NOTE_LOCK = threading.Lock()
_SIDE_NOTE_TOKEN = 0


def _next_side_note_token() -> int:
    global _SIDE_NOTE_TOKEN
    with _SIDE_NOTE_LOCK:
        _SIDE_NOTE_TOKEN += 1
        return _SIDE_NOTE_TOKEN


def _is_side_note_token_current(token: int) -> bool:
    with _SIDE_NOTE_LOCK:
        return token == _SIDE_NOTE_TOKEN


def _spawn_intervention_popup(
    message: str,
    *,
    duration_seconds: float,
    offset_x: int = 0,
    offset_y: int = 0,
    flash: bool = False,
) -> threading.Event:
    done = threading.Event()
    body_text = (message or "Voce esta produtivo demais. Hora de descansar.").strip()
    adaptive_seconds = min(4.8, 0.9 + (len(body_text) / 52.0))
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
            x = int((screen_w - width) / 2) + int(offset_x)
            y = int((screen_h - height) / 2) + int(offset_y)
            x = max(8, min(x, max(8, screen_w - width - 8)))
            y = max(8, min(y, max(8, screen_h - height - 8)))
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

            if flash:
                def _flash_tick() -> None:
                    if not root.winfo_exists():
                        return
                    fg = body.cget("fg")
                    body.configure(fg="#fca5a5" if fg == "#e5e7eb" else "#e5e7eb")
                    root.after(220, _flash_tick)

                root.after(120, _flash_tick)

            duration_ms = max(500, int(final_seconds * 1000))
            root.after(duration_ms, root.destroy)
            root.mainloop()
        except Exception:
            pass
        finally:
            done.set()

    threading.Thread(target=_run, daemon=True).start()
    return done


def show_intervention_popup(message: str, duration_seconds: float = 1.2) -> None:
    """
    Show a small topmost popup before enforcing relax mode.
    Best effort: if UI fails, returns quickly without crashing monitor loop.
    """
    done = _spawn_intervention_popup(
        message,
        duration_seconds=duration_seconds,
    )
    done.wait(timeout=max(1.3, float(duration_seconds) + 1.0))


def show_intervention_popup_storm(
    message: str,
    *,
    copies: int,
    duration_seconds: float = 1.2,
    stagger_seconds: float = 0.12,
    flash: bool = True,
    wait_first: bool = True,
) -> None:
    """
    Spawn multiple intervention popups with slight positional offsets.
    Useful for chaos escalation demos.
    """
    total = max(1, min(6, int(copies)))
    offsets = [
        (0, 0),
        (-140, -80),
        (140, -80),
        (-140, 80),
        (140, 80),
        (0, -120),
    ]

    events: list[threading.Event] = []
    for idx in range(total):
        dx, dy = offsets[idx % len(offsets)]
        ev = _spawn_intervention_popup(
            message,
            duration_seconds=duration_seconds,
            offset_x=dx,
            offset_y=dy,
            flash=flash and idx > 0,
        )
        events.append(ev)
        if idx < total - 1 and stagger_seconds > 0:
            time.sleep(float(stagger_seconds))

    if wait_first and events:
        events[0].wait(timeout=max(1.3, float(duration_seconds) + 1.0))


def show_side_alert_note(
    message: str,
    *,
    duration_seconds: float = 16.0,
    right_margin: int = 22,
    top_ratio: float = 0.16,
    title: str = "Espirito de Epicuro",
    subtitle: str = "Ataraxia assistida",
) -> None:
    """
    Show a persistent right-side note with the latest intervention text.
    New calls replace previous notes.
    """
    token = _next_side_note_token()
    body_text = (message or "Descanso obrigatorio em andamento.").strip()

    def _run() -> None:
        try:
            root = tk.Tk()
            root.title("Anti-Burnout Note")
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.configure(bg="#0b1220")
            try:
                root.attributes("-alpha", 0.97)
            except Exception:
                pass

            width = 440
            height = 220
            screen_w = root.winfo_screenwidth()
            screen_h = root.winfo_screenheight()
            x = max(8, screen_w - width - max(8, int(right_margin)))
            y = max(8, min(int(screen_h * max(0.05, min(0.8, top_ratio))), screen_h - height - 8))
            root.geometry(f"{width}x{height}+{x}+{y}")

            card = tk.Frame(root, bg="#0f172a", bd=2, relief="solid")
            card.pack(fill="both", expand=True, padx=2, pady=2)

            top_row = tk.Frame(card, bg="#0f172a")
            top_row.pack(fill="x", padx=12, pady=(10, 6))

            avatar = tk.Canvas(top_row, width=34, height=34, bg="#0f172a", highlightthickness=0)
            avatar.create_oval(2, 2, 32, 32, fill="#e11d48", outline="")
            avatar.create_text(17, 17, text="AB", fill="white", font=("Segoe UI", 8, "bold"))
            avatar.pack(side="left")

            title = tk.Label(
                top_row,
                text=(title or "Espirito de Epicuro").strip(),
                fg="#f8fafc",
                bg="#0f172a",
                font=("Segoe UI", 10, "bold"),
            )
            title.pack(side="left", padx=(8, 0))

            subtitle = tk.Label(
                card,
                text=(subtitle or "Ataraxia assistida").strip(),
                fg="#93c5fd",
                bg="#0f172a",
                font=("Segoe UI", 9),
                anchor="w",
                justify="left",
            )
            subtitle.pack(fill="x", padx=12, pady=(0, 6))

            body = tk.Label(
                card,
                text=body_text,
                fg="#e5e7eb",
                bg="#0f172a",
                font=("Segoe UI", 10),
                wraplength=400,
                justify="left",
                anchor="nw",
            )
            body.pack(fill="both", expand=True, padx=12, pady=(0, 12))

            start = time.time()

            def _tick() -> None:
                if not root.winfo_exists():
                    return
                if not _is_side_note_token_current(token):
                    root.destroy()
                    return
                elapsed = time.time() - start
                if elapsed >= max(1.5, float(duration_seconds)):
                    root.destroy()
                    return
                root.after(220, _tick)

            root.after(180, _tick)
            root.mainloop()
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def dismiss_side_alert_note() -> None:
    """
    Dismiss current side alert note (if any).
    Next call to show_side_alert_note will create a fresh note.
    """
    _next_side_note_token()


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

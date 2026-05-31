from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk


@dataclass
class LaunchOptions:
    enabled: bool
    dev_mode: bool
    panic_mode: bool
    overlay_enabled: bool


PALETTE = {
    "root_bg": "#0b1220",
    "card_bg": "#f8fafc",
    "border": "#dbe1ea",
    "title": "#0f172a",
    "muted": "#475569",
    "accent": "#2563eb",
    "accent_soft": "#dbeafe",
    "ok": "#16a34a",
    "ok_hover": "#15803d",
    "cancel": "#64748b",
    "cancel_hover": "#475569",
}


def _center_window(root: tk.Tk, width: int, height: int) -> None:
    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = int((screen_w - width) / 2)
    y = int((screen_h - height) / 2)
    root.geometry(f"{width}x{height}+{x}+{y}")


def _apply_hover(btn: tk.Button, normal_bg: str, hover_bg: str) -> None:
    btn.configure(bg=normal_bg, activebackground=hover_bg)
    btn.bind("<Enter>", lambda _e: btn.configure(bg=hover_bg))
    btn.bind("<Leave>", lambda _e: btn.configure(bg=normal_bg))


def show_launcher(
    *,
    default_dev_mode: bool = True,
    default_panic_mode: bool = False,
    default_overlay_enabled: bool = True,
    default_enabled: bool = True,
) -> LaunchOptions | None:
    """
    Returns LaunchOptions when user clicks Start.
    Returns None when user closes/cancels launcher.
    """
    result: dict[str, LaunchOptions | None] = {"value": None}

    root = tk.Tk()
    root.title("Anti-Burnout Launcher")
    root.resizable(False, False)
    root.configure(bg=PALETTE["root_bg"])

    shell = tk.Frame(root, bg=PALETTE["root_bg"], padx=18, pady=18)
    shell.pack(fill="both", expand=True)

    card = tk.Frame(
        shell,
        bg=PALETTE["card_bg"],
        highlightthickness=1,
        highlightbackground=PALETTE["border"],
        bd=0,
        padx=18,
        pady=16,
    )
    card.pack(fill="both", expand=True)

    head = tk.Frame(card, bg=PALETTE["card_bg"])
    head.pack(fill="x", pady=(0, 10))

    badge = tk.Canvas(head, width=44, height=44, bg=PALETTE["card_bg"], highlightthickness=0, bd=0)
    badge.create_oval(2, 2, 42, 42, fill=PALETTE["accent"], outline="")
    badge.create_text(22, 22, text="AB", fill="white", font=("Segoe UI", 10, "bold"))
    badge.pack(side="left")

    head_text = tk.Frame(head, bg=PALETTE["card_bg"])
    head_text.pack(side="left", padx=(10, 0))

    title = tk.Label(
        head_text,
        text="Anti-Burnout",
        font=("Segoe UI", 17, "bold"),
        fg=PALETTE["title"],
        bg=PALETTE["card_bg"],
    )
    title.pack(anchor="w")

    subtitle = tk.Label(
        head_text,
        text="Choose startup profile. You can still tweak everything in tray.",
        font=("Segoe UI", 9),
        fg=PALETTE["muted"],
        bg=PALETTE["card_bg"],
    )
    subtitle.pack(anchor="w")

    profile_var = tk.StringVar(value="dev" if default_dev_mode else ("panic" if default_panic_mode else "live"))
    enabled_var = tk.BooleanVar(value=default_enabled)
    overlay_var = tk.BooleanVar(value=default_overlay_enabled)
    panic_var = tk.BooleanVar(value=default_panic_mode)

    profile_frame = tk.LabelFrame(
        card,
        text="Startup Profile",
        padx=10,
        pady=8,
        font=("Segoe UI", 9, "bold"),
        fg=PALETTE["title"],
        bg=PALETTE["card_bg"],
        bd=1,
    )
    profile_frame.pack(fill="x", pady=(0, 10))

    radio_style = {
        "bg": PALETTE["card_bg"],
        "fg": PALETTE["title"],
        "activebackground": PALETTE["card_bg"],
        "activeforeground": PALETTE["title"],
        "selectcolor": PALETTE["card_bg"],
        "font": ("Segoe UI", 9),
        "anchor": "w",
        "justify": "left",
    }

    tk.Radiobutton(
        profile_frame,
        text="Dev safe (does not block VSCode/terminal)",
        variable=profile_var,
        value="dev",
        **radio_style,
    ).pack(anchor="w")
    tk.Radiobutton(
        profile_frame,
        text="Live normal (blocks productive apps in rest mode)",
        variable=profile_var,
        value="live",
        **radio_style,
    ).pack(anchor="w")
    tk.Radiobutton(
        profile_frame,
        text="Panic demo (forces intervention on VSCode)",
        variable=profile_var,
        value="panic",
        **radio_style,
    ).pack(anchor="w")

    options_frame = tk.LabelFrame(
        card,
        text="Startup Options",
        padx=10,
        pady=8,
        font=("Segoe UI", 9, "bold"),
        fg=PALETTE["title"],
        bg=PALETTE["card_bg"],
        bd=1,
    )
    options_frame.pack(fill="x", pady=(0, 10))

    check_style = {
        "bg": PALETTE["card_bg"],
        "fg": PALETTE["title"],
        "activebackground": PALETTE["card_bg"],
        "activeforeground": PALETTE["title"],
        "selectcolor": PALETTE["card_bg"],
        "font": ("Segoe UI", 9),
        "anchor": "w",
        "justify": "left",
    }
    tk.Checkbutton(options_frame, text="Start active", variable=enabled_var, **check_style).pack(anchor="w")
    tk.Checkbutton(options_frame, text="Enable Windows notifications", variable=overlay_var, **check_style).pack(anchor="w")
    tk.Checkbutton(options_frame, text="Start panic mode ON", variable=panic_var, **check_style).pack(anchor="w")

    preview_box = tk.Frame(card, bg=PALETTE["accent_soft"], bd=0, padx=12, pady=10)
    preview_box.pack(fill="x", pady=(0, 10))
    preview_title = tk.Label(
        preview_box,
        text="Startup Preview",
        font=("Segoe UI", 9, "bold"),
        fg=PALETTE["accent"],
        bg=PALETTE["accent_soft"],
    )
    preview_title.pack(anchor="w")
    preview_var = tk.StringVar(value="")
    preview_body = tk.Label(
        preview_box,
        textvariable=preview_var,
        font=("Segoe UI", 9),
        fg=PALETTE["title"],
        bg=PALETTE["accent_soft"],
        justify="left",
        anchor="w",
        wraplength=560,
    )
    preview_body.pack(anchor="w", pady=(2, 0))

    def _update_preview(*_args) -> None:
        profile = profile_var.get()
        if profile == "dev":
            profile_line = "Profile: Dev safe (VSCode/terminal allowlisted)"
        elif profile == "panic":
            profile_line = "Profile: Panic demo (aggressive VSCode intervention)"
        else:
            profile_line = "Profile: Live normal (rest-mode enforcement)"

        enabled_line = "Engine: ON at startup" if enabled_var.get() else "Engine: OFF at startup"
        notif_line = "Notifications: ON" if overlay_var.get() else "Notifications: OFF"
        panic_line = "Panic switch: ON" if panic_var.get() else "Panic switch: OFF"
        preview_var.set(f"{profile_line}\n{enabled_line} | {notif_line} | {panic_line}")

    profile_var.trace_add("write", _update_preview)
    enabled_var.trace_add("write", _update_preview)
    overlay_var.trace_add("write", _update_preview)
    panic_var.trace_add("write", _update_preview)
    _update_preview()

    foot = tk.Label(
        card,
        text="Tip: Toggle Dev/Panic/Notifications later from tray icon.",
        font=("Segoe UI", 8),
        fg=PALETTE["muted"],
        bg=PALETTE["card_bg"],
    )
    foot.pack(anchor="w", pady=(0, 8))

    btn_frame = tk.Frame(card, bg=PALETTE["card_bg"])
    btn_frame.pack(fill="x")

    def _on_start() -> None:
        profile = profile_var.get()
        if profile == "dev":
            dev_mode = True
            panic_mode = panic_var.get()
        elif profile == "panic":
            dev_mode = False
            panic_mode = True
        else:
            dev_mode = False
            panic_mode = panic_var.get()

        result["value"] = LaunchOptions(
            enabled=enabled_var.get(),
            dev_mode=dev_mode,
            panic_mode=panic_mode,
            overlay_enabled=overlay_var.get(),
        )
        root.destroy()

    def _on_cancel() -> None:
        result["value"] = None
        root.destroy()

    cancel_btn = tk.Button(
        btn_frame,
        text="Cancel",
        width=14,
        command=_on_cancel,
        bd=0,
        fg="white",
        font=("Segoe UI", 9, "bold"),
        cursor="hand2",
    )
    _apply_hover(cancel_btn, PALETTE["cancel"], PALETTE["cancel_hover"])
    cancel_btn.pack(side="right", padx=(8, 0))

    start_btn = tk.Button(
        btn_frame,
        text="Launch",
        width=14,
        command=_on_start,
        bd=0,
        fg="white",
        font=("Segoe UI", 9, "bold"),
        cursor="hand2",
    )
    _apply_hover(start_btn, PALETTE["ok"], PALETTE["ok_hover"])
    start_btn.pack(side="right")

    # Fit-to-content with safety minimums so controls are not clipped on high DPI.
    root.update_idletasks()
    target_w = max(640, root.winfo_reqwidth() + 18)
    target_h = max(500, root.winfo_reqheight() + 18)
    _center_window(root, target_w, target_h)

    root.bind("<Return>", lambda _e: _on_start())
    root.bind("<Escape>", lambda _e: _on_cancel())
    start_btn.focus_set()

    root.protocol("WM_DELETE_WINDOW", _on_cancel)
    root.mainloop()
    return result["value"]

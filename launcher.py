from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk


@dataclass
class LaunchOptions:
    enabled: bool
    dev_mode: bool
    panic_mode: bool
    overlay_enabled: bool


def _center_window(root: tk.Tk, width: int, height: int) -> None:
    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = int((screen_w - width) / 2)
    y = int((screen_h - height) / 2)
    root.geometry(f"{width}x{height}+{x}+{y}")


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

    title = tk.Label(root, text="Anti-Burnout", font=("Segoe UI", 16, "bold"))
    title.pack(pady=(14, 2))

    subtitle = tk.Label(
        root,
        text="Choose startup profile. You can still change settings in tray.",
        font=("Segoe UI", 9),
    )
    subtitle.pack(pady=(0, 10))

    profile_var = tk.StringVar(value="dev" if default_dev_mode else ("panic" if default_panic_mode else "live"))
    enabled_var = tk.BooleanVar(value=default_enabled)
    overlay_var = tk.BooleanVar(value=default_overlay_enabled)
    panic_var = tk.BooleanVar(value=default_panic_mode)

    profile_frame = tk.LabelFrame(root, text="Startup profile", padx=10, pady=8)
    profile_frame.pack(fill="x", padx=14, pady=(0, 10))

    tk.Radiobutton(
        profile_frame,
        text="Dev safe (does not block VSCode/terminal)",
        variable=profile_var,
        value="dev",
    ).pack(anchor="w")
    tk.Radiobutton(
        profile_frame,
        text="Live normal (blocks productive apps in rest mode)",
        variable=profile_var,
        value="live",
    ).pack(anchor="w")
    tk.Radiobutton(
        profile_frame,
        text="Panic demo (forces intervention on VSCode)",
        variable=profile_var,
        value="panic",
    ).pack(anchor="w")

    options_frame = tk.LabelFrame(root, text="Startup options", padx=10, pady=8)
    options_frame.pack(fill="x", padx=14, pady=(0, 10))

    tk.Checkbutton(options_frame, text="Start active", variable=enabled_var).pack(anchor="w")
    tk.Checkbutton(options_frame, text="Enable overlay alerts", variable=overlay_var).pack(anchor="w")
    tk.Checkbutton(options_frame, text="Start panic mode ON", variable=panic_var).pack(anchor="w")

    foot = tk.Label(
        root,
        text="Tip: Toggle Dev/Panic/Overlay later from tray icon.",
        font=("Segoe UI", 8),
    )
    foot.pack(pady=(2, 8))

    btn_frame = tk.Frame(root)
    btn_frame.pack(fill="x", pady=(0, 12))

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

    tk.Button(btn_frame, text="Start", width=14, command=_on_start).pack(side="left", padx=6)
    tk.Button(btn_frame, text="Cancel", width=14, command=_on_cancel).pack(side="left", padx=6)

    # Fit-to-content with safety minimums so controls are not clipped on high DPI.
    root.update_idletasks()
    target_w = max(460, root.winfo_reqwidth() + 16)
    target_h = max(420, root.winfo_reqheight() + 16)
    _center_window(root, target_w, target_h)

    root.protocol("WM_DELETE_WINDOW", _on_cancel)
    root.mainloop()
    return result["value"]

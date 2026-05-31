from __future__ import annotations

import threading
import time
import tkinter as tk

from meme_messages import get_meme_for_app, get_random_meme


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


# ---------------------------------------------------------------------------
# Overlay fullscreen de descanso com mensagens meme rotativas
# ---------------------------------------------------------------------------

class RestOverlayController:
    """
    Controla o overlay fullscreen de descanso compulsório.
    Exibe mensagens meme rotativas e impede interação com o desktop.

    Uso:
        controller = show_rest_overlay(duration_seconds=60)
        # O overlay fecha sozinho após a duração, ou:
        controller.close()  # fecha antecipadamente
    """

    def __init__(self) -> None:
        self._root: tk.Tk | None = None
        self._closed = threading.Event()
        self._meme_label: tk.Label | None = None

    @property
    def is_closed(self) -> bool:
        return self._closed.is_set()

    def close(self) -> None:
        """Fecha o overlay de forma thread-safe."""
        if self._root and not self._closed.is_set():
            try:
                self._root.after(0, self._root.destroy)
            except Exception:
                pass

    def wait(self, timeout: float | None = None) -> None:
        """Bloqueia até o overlay fechar."""
        self._closed.wait(timeout=timeout)


def show_rest_overlay(
    duration_seconds: int = 60,
    app_name: str | None = None,
) -> RestOverlayController:
    """
    Exibe um overlay fullscreen de descanso com mensagens meme dinâmicas.

    Args:
        duration_seconds: Duração em segundos do overlay.
        app_name: Nome do processo produtivo detectado (opcional).
                  Se fornecido, algumas mensagens serão contextuais.

    Returns:
        RestOverlayController para controlar o ciclo de vida do overlay.

    Integração com main.py / monitor_loop:
        Chame esta função quando a fase mudar para REST_FORCED:

            elif transition == "ENTER_REST":
                rest_overlay = show_rest_overlay(
                    duration_seconds=cycle.current_rest_seconds(),
                    app_name=last_blocked_app,
                )
    """
    controller = RestOverlayController()

    # Intervalo de rotação das mensagens meme (segundos)
    MEME_ROTATION_INTERVAL_MS = 6000

    def _run() -> None:
        try:
            root = tk.Tk()
            controller._root = root
            root.title("Método Comodoro™ — Descanso Obrigatório")
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-fullscreen", True)
            root.configure(bg="#0a0a0f")

            # Impedir fechamento via Alt+F4 ou teclas
            root.protocol("WM_DELETE_WINDOW", lambda: None)
            root.bind("<Key>", lambda e: "break")
            root.bind("<Escape>", lambda e: "break")
            root.focus_force()

            # ---- Layout ----
            # Container principal com margem
            main_frame = tk.Frame(root, bg="#0a0a0f")
            main_frame.place(relx=0.5, rely=0.5, anchor="center")

            # Título
            title_label = tk.Label(
                main_frame,
                text="🛋️  DESCANSO COMPULSÓRIO ATIVADO  🛋️",
                fg="#e11d48",
                bg="#0a0a0f",
                font=("Segoe UI", 32, "bold"),
            )
            title_label.pack(pady=(0, 10))

            # Subtítulo com "pulsação"
            subtitle_label = tk.Label(
                main_frame,
                text="Método Comodoro™ — 90% descanso, 10% fingindo que trabalha",
                fg="#6b7280",
                bg="#0a0a0f",
                font=("Segoe UI", 14),
            )
            subtitle_label.pack(pady=(0, 40))

            # Separador visual
            separator = tk.Frame(main_frame, bg="#1f2937", height=2)
            separator.pack(fill="x", padx=100, pady=(0, 40))

            # Label da mensagem meme (o protagonista)
            meme_label = tk.Label(
                main_frame,
                text=get_meme_for_app(app_name),
                fg="#f8fafc",
                bg="#0a0a0f",
                font=("Segoe UI", 22),
                wraplength=1200,
                justify="center",
            )
            meme_label.pack(pady=(0, 50))
            controller._meme_label = meme_label

            # Timer de contagem regressiva
            timer_label = tk.Label(
                main_frame,
                text="",
                fg="#374151",
                bg="#0a0a0f",
                font=("Segoe UI", 12),
            )
            timer_label.pack(pady=(0, 0))

            # Rodapé
            footer_label = tk.Label(
                root,
                text="Powered by Ministério da Dopamina  •  Divisão de Prevenção ao Overwork",
                fg="#1f2937",
                bg="#0a0a0f",
                font=("Segoe UI", 10),
            )
            footer_label.pack(side="bottom", pady=20)

            # ---- Animações ----
            start_time = time.time()

            def _rotate_meme() -> None:
                """Troca a frase meme exibida no overlay."""
                if controller.is_closed:
                    return
                try:
                    new_msg = get_meme_for_app(app_name)
                    meme_label.configure(text=new_msg)
                except Exception:
                    pass
                root.after(MEME_ROTATION_INTERVAL_MS, _rotate_meme)

            def _pulse_subtitle() -> None:
                """Efeito de pulsação suave no subtítulo."""
                if controller.is_closed:
                    return
                try:
                    current = subtitle_label.cget("fg")
                    subtitle_label.configure(
                        fg="#9ca3af" if current == "#6b7280" else "#6b7280"
                    )
                except Exception:
                    pass
                root.after(2000, _pulse_subtitle)

            def _update_timer() -> None:
                """Atualiza o timer de contagem regressiva."""
                if controller.is_closed:
                    return
                elapsed = time.time() - start_time
                remaining = max(0, duration_seconds - elapsed)
                if remaining <= 0:
                    root.destroy()
                    return
                mins, secs = divmod(int(remaining), 60)
                timer_label.configure(
                    text=f"Liberdade produtiva em {mins:02d}:{secs:02d}"
                )
                root.after(1000, _update_timer)

            # Kick off animations
            root.after(MEME_ROTATION_INTERVAL_MS, _rotate_meme)
            root.after(2000, _pulse_subtitle)
            root.after(100, _update_timer)

            # Auto-destroy após a duração
            root.after(duration_seconds * 1000, root.destroy)

            root.mainloop()
        except Exception:
            pass
        finally:
            controller._root = None
            controller._closed.set()

    threading.Thread(target=_run, daemon=True).start()
    return controller

import threading
import tkinter as tk
from app_state import AppState

class TimerOverlayController:
    """
    Controla a janela flutuante com o timer e modo atual.
    Baseado no antiburnout_timer.py.
    """
    def __init__(self, state: AppState):
        self.state = state
        self._root = None
        self._is_active = False

    @property
    def is_active(self) -> bool:
        return self._is_active

    def start(self):
        if self._is_active:
            return
        self._is_active = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        try:
            self._root = tk.Tk()
            self._root.title("Antiburnout Timer")
            self._root.attributes("-topmost", True)
            self._root.geometry("250x90")
            self._root.configure(bg="#FFFFFF")
            self._root.resizable(False, False)

            # Quando clicar no X, apenas desativa o timer na state
            def on_close():
                if self.state.snapshot().get("timer_overlay_enabled", False):
                    self.state.toggle_timer_overlay()

            self._root.protocol("WM_DELETE_WINDOW", on_close)

            # Paleta de Cores
            bg_color = "#FFFFFF"     # Branco
            fg_color = "#000000"     # Preto
            work_color = "#D32F2F"   # Vermelho
            rest_color = "#757575"   # Cinza
            
            # Frame para criar uma borda bonitinha
            frame = tk.Frame(self._root, bg=bg_color, highlightbackground="#E0E0E0", highlightthickness=2)
            frame.pack(fill="both", expand=True)

            label_mode = tk.Label(frame, text="", font=("Segoe UI", 14, "bold"), bg=bg_color, fg=rest_color)
            label_mode.pack(pady=(10, 0))
            
            label_time = tk.Label(frame, text="", font=("Segoe UI", 20, "bold"), bg=bg_color, fg=fg_color)
            label_time.pack()

            def format_time(seconds):
                mins, secs = divmod(max(0, int(seconds)), 60)
                return f"{mins:02d}:{secs:02d}"

            def update():
                snap = self.state.snapshot()
                
                # Se o app fechar ou o usuario desativar o overlay
                if not snap.get("running", True) or not snap.get("timer_overlay_enabled", False):
                    self._root.destroy()
                    self._root = None
                    self._is_active = False
                    return

                # Verifica se o timer principal do app está ativo e se o tempo não está pausado
                # Mostra "PAUSADO" se enabled=False
                if not snap.get("enabled", True):
                    label_mode.config(text="PAUSADO", fg=fg_color)
                    label_time.config(text=format_time(snap.get("phase_remaining", 0)))
                else:
                    phase = snap.get("phase", "REST_FORCED")
                    if phase == "REST_FORCED":
                        label_mode.config(text="Modo Descanso", fg=rest_color)
                    else:
                        label_mode.config(text="Modo Trabalho", fg=work_color)
                    
                    label_time.config(text=format_time(snap.get("phase_remaining", 0)))
                
                if self._root:
                    # Atualiza a cada 500ms para maior precisão visual e sincronia com a tray
                    self._root.after(500, update)

            self._root.after(100, update)
            self._root.mainloop()
        except Exception:
            self._is_active = False

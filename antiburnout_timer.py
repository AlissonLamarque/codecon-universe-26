import tkinter as tk
import pystray
from PIL import Image, ImageDraw
import threading

# Configurações de tempo para teste: 
# 90% descanso e 10% trabalho (reduzidos para facilitar o teste).
TEMPO_DESCANSO = 90  # 90 segundos
TEMPO_TRABALHO = 10  # 10 segundos

class AntiburnoutApp:
    def __init__(self):
        # 1. Configuração da Janela Principal (Tkinter)
        self.root = tk.Tk()
        self.root.title("Antiburnout")
        
        # Mantém a janela sempre no topo das outras
        self.root.attributes("-topmost", True)
        
        # Geometria e estilo
        self.root.geometry("250x90")
        self.root.configure(bg="#2E3440")
        self.root.resizable(False, False)

        # Trata o evento de fechar pelo "X" da janela
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # Variáveis de Estado
        self.is_active = True
        self.is_resting = True
        self.time_left = TEMPO_DESCANSO

        # Paleta de Cores
        self.bg_color = "#2E3440"
        self.fg_color = "#ECEFF4"
        self.work_color = "#BF616A" # Vermelho
        self.rest_color = "#A3BE8C" # Verde
        
        # Elementos da UI
        self.label_mode = tk.Label(self.root, text="Modo Descanso", font=("Helvetica", 14, "bold"), bg=self.bg_color, fg=self.rest_color)
        self.label_mode.pack(pady=(10, 0))
        
        self.label_time = tk.Label(self.root, text=self.format_time(self.time_left), font=("Helvetica", 18), bg=self.bg_color, fg=self.fg_color)
        self.label_time.pack()

        # 2. Inicialização das Threads
        self.setup_tray()
        self.update_timer()

    def format_time(self, seconds):
        """Formata os segundos no formato MM:SS"""
        mins, secs = divmod(seconds, 60)
        return f"{mins:02d}:{secs:02d}"

    def update_timer(self):
        """Lógica do temporizador - roda no mainloop do tkinter"""
        if self.is_active:
            if self.time_left > 0:
                self.time_left -= 1
            else:
                # Alterna os modos quando o tempo chega a zero
                self.is_resting = not self.is_resting
                self.time_left = TEMPO_DESCANSO if self.is_resting else TEMPO_TRABALHO
                
                # Atualiza a UI para refletir o modo atual
                if self.is_resting:
                    self.label_mode.config(text="Modo Descanso", fg=self.rest_color)
                else:
                    self.label_mode.config(text="Modo Trabalho", fg=self.work_color)
            
            # Atualiza o display do tempo
            self.label_time.config(text=self.format_time(self.time_left))
            
        # CRÍTICO (Thread-Safe Tkinter): 
        # O método `.after(milissegundos, callback)` agenda a execução da função
        # na fila de eventos da thread principal (onde o Tkinter está rodando).
        # É a forma 100% segura de criar um loop no tkinter sem travar a interface.
        self.root.after(1000, self.update_timer)

    def on_tray_toggle(self, icon, item):
        """Callback acionado pelo item do menu no System Tray"""
        # Esta função é executada na Thread do Pystray (não na do Tkinter).
        self.is_active = not self.is_active
        
        # CRÍTICO (Ponte Pystray -> Tkinter):
        # Nunca modifique a interface (ex: root.withdraw()) diretamente de outra thread.
        # Usamos `root.after(0, função)` para enviar um comando para a thread do Tkinter
        # executar a modificação na UI de forma segura assim que possível.
        if self.is_active:
            self.root.after(0, self.root.deiconify) # Mostra e restaura a janela
        else:
            self.root.after(0, self.root.withdraw)  # Esconde a janela

    def hide_window(self):
        """Esconde a janela quando clica no X, para que fique apenas na bandeja"""
        self.is_active = False
        self.root.withdraw()
        # Atualiza o icone (para que o checkbox no menu mude)
        self.icon.update_menu()

    def quit_app(self, icon=None, item=None):
        """Encerra a aplicação por completo"""
        # Para a thread do ícone
        if icon:
            icon.stop()
        
        # CRÍTICO (Ponte Pystray -> Tkinter):
        # Envia de forma segura o comando de destruição para a thread do Tkinter
        self.root.after(0, self.root.destroy)

    def setup_tray(self):
        """Configura o ícone na bandeja do sistema usando pystray"""
        # Gera uma imagem simples para o ícone (verde/cinza)
        image = Image.new('RGB', (64, 64), color=self.rest_color)
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill=self.bg_color)

        # Configura o menu que aparecerá ao clicar com botão direito
        menu = pystray.Menu(
            # O parâmetro 'checked' cria um toggle/checkbox dinâmico
            pystray.MenuItem(
                "Ativar/Desativar Timer", 
                self.on_tray_toggle, 
                checked=lambda item: self.is_active
            ),
            pystray.MenuItem("Sair", self.quit_app)
        )
        
        self.icon = pystray.Icon("Antiburnout", image, "Antiburnout", menu)
        
        # CRÍTICO (Tratamento de Threads):
        # icon.run() é bloqueante. Se chamarmos isso na main thread, o root.mainloop() 
        # do Tkinter nunca será executado, e a janela não aparecerá.
        # Portanto, isolamos o pystray em uma thread do tipo 'daemon' (que morre
        # quando o programa principal for fechado).
        tray_thread = threading.Thread(target=self.icon.run, daemon=True)
        tray_thread.start()

    def run(self):
        """Inicia o loop principal de eventos do Tkinter"""
        # root.mainloop() bloqueia e gerencia todos os eventos da janela
        self.root.mainloop()

if __name__ == "__main__":
    app = AntiburnoutApp()
    app.run()

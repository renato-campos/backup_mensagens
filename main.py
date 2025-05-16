import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys
import os
import platform  # Para detectar o sistema operacional
import tkinter.font as tkFont # Para manipulação de fontes

try:
    from ttkthemes import ThemedTk
    HAS_TTKTHEMES = True
except ImportError:
    HAS_TTKTHEMES = False

# --- Constantes ---
# Obtém o diretório onde o script main.py (ou main.exe) está localizado
SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__))
# Assume que a pasta 'imagens' está no mesmo nível que main.exe
ICON_PATH = os.path.join(SCRIPT_DIR, 'imagens', 'email.ico')
# Diretório para arquivos de ajuda (PDFs), também no mesmo nível que main.exe
HELP_DIR = os.path.join(SCRIPT_DIR, 'docs')

# --- Funções para Lançar Executáveis ---
def launch_executable(executable_name: str):
    """Lança um executável (.exe) filho."""
    # SCRIPT_DIR aqui se refere ao diretório onde main.exe está.
    # Assumimos que os outros .exe estão no mesmo diretório.
    executable_path = os.path.join(SCRIPT_DIR, executable_name)
    
    print(f"DEBUG: Tentando lançar executável: {executable_path}") # Para depuração

    if not os.path.exists(executable_path):
        messagebox.showerror(
            "Erro de Execução", f"Executável não encontrado:\n{executable_path}")
        return

    try:
        # Lança o executável diretamente.
        # Popen é usado para que o painel principal não congele.
        subprocess.Popen([executable_path])
    except FileNotFoundError: # Deve ser pego pelo os.path.exists, mas por segurança
        messagebox.showerror(
            "Erro de Execução", f"Arquivo não encontrado ao tentar executar:\n{executable_path}")
    except PermissionError:
        messagebox.showerror(
            "Erro de Permissão", f"Sem permissão para executar:\n{executable_path}")
    except Exception as e:
        messagebox.showerror("Erro de Execução",
                             f"Falha ao lançar {executable_name}:\n{e}")

def open_help_pdf(pdf_filename: str):
    """Abre um arquivo PDF de ajuda usando o visualizador padrão do sistema."""
    pdf_path = os.path.join(HELP_DIR, pdf_filename)
    print(f"DEBUG: Tentando abrir ajuda: {pdf_path}") # Para depuração
    print(f"DEBUG: PDF existe? {os.path.exists(pdf_path)}") # Para depuração

    if not os.path.exists(pdf_path):
        messagebox.showerror(
            "Erro de Ajuda", f"Arquivo de ajuda não encontrado:\n{pdf_path}")
        return

    try:
        current_platform = platform.system()
        if current_platform == "Windows":
            os.startfile(pdf_path)
        elif current_platform == "Darwin":  # macOS
            subprocess.run(['open', pdf_path], check=True)
        else:  # Linux e outros Unix-like
            subprocess.run(['xdg-open', pdf_path], check=True)
    except FileNotFoundError:
        messagebox.showerror(
            "Erro de Execução", f"Não foi possível encontrar o comando para abrir PDF no seu sistema ({current_platform}).")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Erro de Execução",
                             f"Falha ao abrir o arquivo de ajuda '{pdf_filename}':\n{e}")
    except Exception as e:
        messagebox.showerror(
            "Erro de Ajuda", f"Ocorreu um erro inesperado ao tentar abrir o PDF '{pdf_filename}':\n{e}")

# --- Configuração da GUI ---
class MainApp:
    def __init__(self, root_window):
        self.root = root_window
        root_window.title("Painel de Controle - Backup Mensagens")

        try:
            if os.path.exists(ICON_PATH):
                root_window.iconbitmap(ICON_PATH)
            else:
                print(f"Aviso: Ícone não encontrado em {ICON_PATH}")
        except tk.TclError:
            print(f"Aviso: Não foi possível carregar o ícone {ICON_PATH}.")

        style = ttk.Style(root_window)
        font_family = "Segoe UI"
        if font_family not in tkFont.families():
            font_family = "Arial" # Fallback
        base_font_size = 10
        title_font_size = 16

        if not (HAS_TTKTHEMES and isinstance(root_window, ThemedTk) and root_window.tk.call("ttk::style", "theme", "use") != ""):
            current_themes = style.theme_names()
            theme_to_set = 'clam' if 'clam' in current_themes else ('vista' if platform.system() == "Windows" and 'vista' in current_themes else ('alt' if 'alt' in current_themes else 'default'))
            try:
                style.theme_use(theme_to_set)
            except tk.TclError:
                print(f"Aviso: Falha ao aplicar o tema ttk '{theme_to_set}'.")
        
        style.configure("TButton", font=(font_family, base_font_size, "bold"), padding=(15, 8))
        style.configure("Help.TButton", font=(font_family, base_font_size - 1), padding=(8, 5))
        style.configure("Title.TLabel", font=(font_family, title_font_size, "bold"))
        style.configure("TLabel", font=(font_family, base_font_size))
        style.configure("TFrame", background=style.lookup('TLabel', 'background'))

        main_frame = ttk.Frame(root_window, padding="20 20 20 20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        root_window.columnconfigure(0, weight=1)
        root_window.rowconfigure(0, weight=1)

        title_label = ttk.Label(main_frame, text="Ferramentas de Gerenciamento de Mensagens", style="Title.TLabel")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 30), sticky=tk.N)

        # Formato: (Texto do Botão, Nome do EXECUTÁVEL Filho, Nome do Arquivo PDF de Ajuda)
        scripts_to_launch = [
            ("Arquivar E-mails (Pasta Padrão)", "arquiva_email.exe", "Leiame - Arquiva e-mail automático.pdf"),
            ("Arquivar E-mails (GUI - Pasta Única)", "arquiva_email_gui.exe", "Leiame - Arquiva e-mail GUI.pdf"),
            ("Centralizar Arquivos (Raiz)", "arquiva_raiz.exe", "Leiame - Arquivo raiz.pdf"),
            ("Arquivar E-mails (Subpastas)", "arquiva_subpastas.exe", "Leiame - Arquiva e-mail Subpastas.pdf"),
            ("Renomear Arquivos .eml", "renomear_eml.exe", "Leiame - Renomeando e-mails eml.pdf"),
            ("Comparar Conteúdo de Pastas", "pastas_diff.exe", "Leiame - Diferenças entre as pastas.pdf"),
            ("Relatório de Contagem de Mensagens", "relatorio_mensagens.exe", "Leiame - Relatório de Mensagens.pdf"),
        ]

        for i, (button_text, exe_filename, help_pdf_filename) in enumerate(scripts_to_launch):
            script_button = ttk.Button(main_frame, text=button_text,
                                       command=lambda ex=exe_filename: launch_executable(ex),
                                       width=40)
            script_button.grid(row=i + 1, column=0, pady=8, padx=(10, 5), sticky=tk.EW)

            help_button = ttk.Button(main_frame, text="Ajuda", style="Help.TButton",
                                     command=lambda pdf=help_pdf_filename: open_help_pdf(pdf),
                                     width=10)
            help_button.grid(row=i + 1, column=1, pady=8, padx=(5, 10), sticky=tk.EW)

        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.grid(row=len(scripts_to_launch) + 1, column=0, columnspan=2, sticky='ew', pady=20)

        exit_button = ttk.Button(main_frame, text="Sair", command=root_window.quit, width=15)
        exit_button.grid(row=len(scripts_to_launch) + 2, column=0, columnspan=2, pady=(20, 0))

        self.center_window()

    def center_window(self):
        self.root.update_idletasks()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        center_x = int((screen_width / 2) - (window_width / 2))
        center_y = int((screen_height / 2) - (window_height / 2))
        self.root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        self.root.resizable(False, False)

if __name__ == "__main__":
    # A lógica de despacho foi removida, main.py sempre inicia a GUI.
    if HAS_TTKTHEMES:
        try:
            main_root = ThemedTk(theme="arc") 
        except tk.TclError: 
            main_root = tk.Tk()
    else:
        main_root = tk.Tk()
    
    app = MainApp(main_root)
    main_root.mainloop()

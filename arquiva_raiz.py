import shutil
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import tkinter as tk
from tkinter import filedialog, messagebox

# --- Constantes ---
# Limite prático para caminhos no Windows para evitar problemas com funções padrão.
# MAX_PATH (260) - 1 para o caractere nulo.
EFFECTIVE_MAX_PATH = 259
SAFE_PATH_MARGIN = 10  # Margem de segurança para evitar atingir o limite exato
LOG_FOLDER_NAME = "ERROS"  # Nome da pasta de logs
# Nomes de pastas a ignorar (em minúsculas)
DEFAULT_EXCLUDED_FOLDERS = ["erros", "anos anteriores"]
FALLBACK_SANITIZED_FILENAME = "arquivo_renomeado"
# Máximo de tentativas para resolver nomes duplicados
MAX_DUPLICATE_RESOLUTION_ATTEMPTS = 10
# --- Fim Constantes ---


class FileMover:
    """
    Move e renomeia arquivos de subpastas para uma pasta raiz,
    sanitizando nomes e tratando conflitos e limites de comprimento de caminho.
    """

    def __init__(self, root_folder_path: str, log_folder_name: str = LOG_FOLDER_NAME):
        """
        Inicializa o FileMover.

        Args:
            root_folder_path: Caminho para a pasta raiz onde os arquivos serão centralizados.
            log_folder_name: Nome da pasta onde os logs serão salvos (dentro da root_folder_path).
        """
        self.root_folder: Path = Path(root_folder_path).resolve()
        self.log_folder: Path = self.root_folder / log_folder_name
        self.setup_logger()
        self.excluded_folders_lower: List[str] = [
            f.lower() for f in DEFAULT_EXCLUDED_FOLDERS]
        self.summary_message: str = ""

    def process_files_in_root(self) -> None:
        """Processa arquivos: move de subpastas para a raiz e renomeia (sanitiza/trunca) arquivos na raiz e os movidos."""
        if not self.root_folder.exists() or not self.root_folder.is_dir():
            self.logger.error(
                f"Pasta raiz não encontrada ou não é um diretório: {self.root_folder}")
            return

        processed_files_count = 0
        renamed_files_count = 0
        moved_files_count = 0
        error_count = 0
        max_allowed_path_len = EFFECTIVE_MAX_PATH - SAFE_PATH_MARGIN

        # Itera por todas as pastas, incluindo a raiz (`topdown=True` permite modificar `dir_names`)
        for current_root_str, dir_names, file_names in os.walk(str(self.root_folder), topdown=True):
            current_root_path = Path(current_root_str)

            # Remove pastas excluídas da lista `dir_names` para não entrar nelas
            dir_names[:] = [
                d_name for d_name in dir_names
                if d_name.lower() not in self.excluded_folders_lower and
                (current_root_path / d_name).resolve() != self.log_folder.resolve()
            ]

            for original_filename in file_names:
                source_path = current_root_path / original_filename

                # Ignora arquivos dentro da pasta de log (comparando pais resolvidos)
                if source_path.parent.resolve() == self.log_folder.resolve():
                    continue

                # 1. Aplica sanitização ao nome do arquivo
                sanitized_filename = self._sanitize_filename(original_filename)
                sanitization_occurred = (
                    original_filename != sanitized_filename)
                if sanitization_occurred:
                    self.logger.info(
                        f"Sanitizando nome: '{original_filename}' -> '{sanitized_filename}' (Origem: '{current_root_path}')")

                # 2. Aplica truncamento inicial ao nome sanitizado, considerando o destino (root_folder)
                current_final_filename = self._truncate_filename(
                    self.root_folder, sanitized_filename, max_allowed_path_len)

                potential_destination_path = self.root_folder / current_final_filename

                # 3. Pula se o arquivo já está na raiz e o nome final é o mesmo (nenhuma ação necessária)
                if current_root_path == self.root_folder and source_path == potential_destination_path:
                    continue

                # 4. Verifica se já existe um arquivo com o nome final no destino (root_folder)
                #    e resolve conflitos adicionando timestamp e re-truncando se necessário.
                destination_path = potential_destination_path
                num_attempts = 0
                original_conflicting_filename_part = current_final_filename  # Para logs mais claros

                while destination_path.exists() and num_attempts < MAX_DUPLICATE_RESOLUTION_ATTEMPTS:
                    num_attempts += 1
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                    base_name, ext = Path(original_conflicting_filename_part).stem, Path(
                        original_conflicting_filename_part).suffix

                    name_with_timestamp = f"{base_name}_{timestamp}{ext}"

                    current_final_filename = self._truncate_filename(
                        self.root_folder, name_with_timestamp, max_allowed_path_len
                    )
                    destination_path = self.root_folder / current_final_filename

                    if num_attempts == 1:  # Loga na primeira tentativa de renomeação por duplicidade
                        self.logger.warning(
                            f"Conflito de nome em '{self.root_folder}' para '{original_conflicting_filename_part}'. "
                            f"Tentando renomear para '{current_final_filename}' (Origem: '{source_path}')")

                if destination_path.exists():  # Ainda existe após MAX_ATTEMPTS
                    self.logger.error(
                        f"Não foi possível encontrar um nome único para '{original_conflicting_filename_part}' "
                        f"em '{self.root_folder}' após {num_attempts} tentativas. Pulando '{source_path}'.")
                    error_count += 1
                    current_final_filename = None  # Marca para pular este arquivo

                if current_final_filename is None:
                    continue

                # destination_path já está atualizado pelo loop acima ou é o potential_destination_path

                # 5. Executa a ação: Mover (se veio de subpasta) ou Renomear (se já estava na raiz)
                try:
                    if current_root_path == self.root_folder:
                        # Renomeia o arquivo dentro da pasta raiz, se o nome mudou
                        if source_path != destination_path:
                            source_path.rename(destination_path)
                            renamed_files_count += 1
                            processed_files_count += 1
                    else:
                        # Move o arquivo da subpasta para a raiz
                        shutil.move(str(source_path), str(destination_path))
                        moved_files_count += 1
                        processed_files_count += 1

                except (OSError, shutil.Error) as e:
                    action_verb = "renomear" if current_root_path == self.root_folder else "mover"
                    self.logger.error(
                        f"Erro ao {action_verb} '{source_path}' para '{destination_path}': {e}")
                    error_count += 1

        summary_message = "-" * 30 + "\n"
        if processed_files_count > 0:
            summary_message += "Processamento concluído:\n"
            if renamed_files_count > 0:
                summary_message += f"- {renamed_files_count} arquivos renomeados na pasta raiz.\n"
            if moved_files_count > 0:
                summary_message += f"- {moved_files_count} arquivos movidos das subpastas para a raiz.\n"
        else:
            summary_message += "Nenhum arquivo precisou ser movido ou renomeado.\n"

        if error_count > 0:
            summary_message += f"\nAtenção: Ocorreram {error_count} erros durante a operação. Verifique o log em '{self.log_folder}'.\n"
        else:
            log_file_exists = False
            if self.log_folder.exists():
                log_file_exists = any(f.name.startswith(
                    "process_root_log_") for f in self.log_folder.iterdir() if f.is_file())

            if log_file_exists:
                summary_message += f"\nOperação concluída. Logs de sanitização, truncamento ou renomeação por duplicidade podem ter sido gerados em '{self.log_folder}'.\n"
            else:
                summary_message += "\nOperação concluída sem erros ou necessidade de alterações nos nomes dos arquivos.\n"

        self.summary_message = summary_message

        if moved_files_count > 0:
            empty_folders_message = self.remove_empty_folders()
            self.summary_message += "\n" + empty_folders_message
        else:
            self.summary_message += "\nNenhuma pasta vazia para remover (nenhum arquivo foi movido)."

    def remove_empty_folders(self) -> str:
        """Remove pastas vazias APENAS das subpastas de onde os arquivos foram movidos."""
        message = "Verificando pastas vazias para remoção...\n"
        removed_count = 0
        error_remove_count = 0

        # Itera de baixo para cima (`topdown=False`) para remover subpastas antes das pastas pai
        # Usamos os.walk aqui porque Path.rglob('*').iterdir() não tem topdown=False nativamente
        # e a lógica de remoção de baixo para cima é crucial.
        for current_root_str, dir_names, _ in os.walk(str(self.root_folder), topdown=False):
            current_root_path = Path(current_root_str)

            dir_names[:] = [
                d_name for d_name in dir_names
                if d_name.lower() not in self.excluded_folders_lower and
                (current_root_path / d_name).resolve() != self.log_folder.resolve()
            ]

            if current_root_path.resolve() == self.root_folder.resolve() or \
               current_root_path.resolve() == self.log_folder.resolve():
                continue

            if current_root_path.name.lower() not in self.excluded_folders_lower:
                try:
                    # Verifica se está realmente vazia
                    if not any(current_root_path.iterdir()):
                        current_root_path.rmdir()
                        self.logger.info(
                            f"Pasta vazia removida: {current_root_path}")
                        removed_count += 1
                except OSError as e:
                    self.logger.error(
                        f"Erro ao verificar ou remover a pasta '{current_root_path}': {e}")
                    error_remove_count += 1

        if removed_count > 0:
            message += f"Remoção de pastas vazias concluída. {removed_count} pastas removidas.\n"
        else:
            message += "Nenhuma pasta vazia encontrada para remover.\n"

        if error_remove_count > 0:
            message += f"Atenção: Ocorreram {error_remove_count} erros durante a remoção de pastas vazias. Verifique o log.\n"

        return message

    def setup_logger(self) -> None:
        """Configura o logger para registrar eventos importantes."""
        self.log_folder.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_file = self.log_folder / f"process_root_log_{timestamp}.log"

        self.logger = logging.getLogger(
            f"{__name__}.{id(self)}")  # Nome único para o logger
        if not self.logger.hasHandlers():
            self.logger.setLevel(logging.INFO)
            file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Remove ou substitui caracteres inválidos, o prefixo 'msg ',
        espaços extras e normaliza números no início do nome.
        """
        sanitized = re.sub(r'^msg\s+', '', filename, flags=re.IGNORECASE)
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)
        sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)
        sanitized = sanitized.strip()

        match = re.match(r'^(\d+)(.*)', sanitized)
        if match:
            number_str, rest_of_name = match.groups()
            try:  # Adicionado try-except para números muito grandes que não cabem em int
                number = int(number_str)
                sanitized = str(number) + rest_of_name
            except ValueError:
                # Se o número for muito grande, mantenha como string, mas remova zeros à esquerda se houver mais de um dígito e começar com zero
                if len(number_str) > 1 and number_str.startswith('0'):
                    sanitized = number_str.lstrip('0') + rest_of_name
                else:  # Mantém o número original se for um único '0' ou não começar com '0'
                    sanitized = number_str + rest_of_name

        if not sanitized:
            self.logger.warning(
                f"Nome do arquivo '{filename}' resultou em vazio após sanitização. Usando fallback.")
            sanitized = FALLBACK_SANITIZED_FILENAME
        return sanitized

    def _truncate_filename(self, target_folder: Path, filename: str, max_full_path_len: int) -> str:
        """
        Trunca o nome do arquivo (preservando a extensão) se o caminho completo
        (target_folder / filename) exceder max_full_path_len.
        """
        base, ext = Path(filename).stem, Path(filename).suffix
        potential_full_path = target_folder / filename

        if len(str(potential_full_path)) <= max_full_path_len:
            return filename

        len_of_folder_path_str = len(str(target_folder))
        len_of_separator = 1
        len_of_extension = len(ext)

        available_len_for_base = max_full_path_len - \
            (len_of_folder_path_str + len_of_separator + len_of_extension)

        if available_len_for_base <= 0:
            self.logger.error(
                f"Não é possível criar um nome de arquivo válido para '{filename}' na pasta '{target_folder}' "
                f"devido ao limite de comprimento ({max_full_path_len}). O caminho da pasta base já é muito longo. "
                f"Disponível para base: {available_len_for_base}")
            # Retorna um nome minimamente truncado se possível, ou o original se nem isso for possível
            # Isso é um caso extremo.
            if len(ext) < max_full_path_len - (len_of_folder_path_str + len_of_separator):
                # Tenta pelo menos retornar a extensão se houver espaço
                minimal_base_len = max_full_path_len - \
                    (len_of_folder_path_str + len_of_separator + len_of_extension)
                # Se não há espaço nem para 1 char da base
                if minimal_base_len < 1 and len(base) > 0:
                    # Retorna algo como "_ext" ou apenas "_"
                    return f"_{ext}" if ext else "_"
                elif minimal_base_len < 1 and len(base) == 0:
                    return "_"  # Se base e ext são vazios
            return filename  # Fallback para o nome original se a situação for irrecuperável aqui

        if available_len_for_base < len(base):
            self.logger.warning(
                f"Nome do arquivo truncado devido ao limite de comprimento do caminho: '{filename}' -> "
                f"'{base[:available_len_for_base]}{ext}' em '{target_folder}'")
            truncated_base = base[:available_len_for_base]
            return f"{truncated_base}{ext}"

        # Se não precisou truncar a base (já coberto pelo primeiro if, mas como segurança)
        return filename


def select_folder() -> Optional[str]:
    """Abre uma janela para o usuário selecionar uma pasta."""
    root_tk = tk.Tk()
    root_tk.withdraw()
    folder_selected = filedialog.askdirectory(title="Selecione a Pasta Raiz")
    root_tk.destroy()
    return folder_selected


def main() -> None:
    """Função principal para executar o processo de movimentação e sanitização de arquivos."""
    # Necessário para que as caixas de diálogo do tkinter funcionem corretamente
    # mesmo que a janela principal não seja exibida ou seja destruída rapidamente.
    root_for_dialogs = tk.Tk()
    root_for_dialogs.withdraw()

    messagebox.showinfo("Seleção de Pasta",
                        "Selecione a pasta raiz para centralizar e sanitizar os arquivos...",
                        parent=root_for_dialogs)  # Garante que a messagebox fique no topo

    root_folder_str = select_folder()

    if not root_folder_str:
        messagebox.showinfo("Operação Cancelada",
                            "Nenhuma pasta selecionada. Encerrando.",
                            parent=root_for_dialogs)
        root_for_dialogs.destroy()
        return

    root_folder_path = Path(root_folder_str)
    if not root_folder_path.exists() or not root_folder_path.is_dir():
        messagebox.showerror("Erro",
                             f"ERRO: A pasta selecionada {root_folder_path} não foi encontrada ou não é um diretório.",
                             parent=root_for_dialogs)
        root_for_dialogs.destroy()
        return

    log_path_display = root_folder_path / LOG_FOLDER_NAME
    info_message = f"Pasta raiz selecionada: {root_folder_path}\n"
    info_message += f"Os logs de erros e alterações serão salvos em: {log_path_display}\n"
    info_message += "Iniciando o processo..."

    messagebox.showinfo("Processo Iniciado", info_message,
                        parent=root_for_dialogs)
    root_for_dialogs.destroy()  # Destruir a root temporária dos dialogs iniciais

    # Precisamos importar os aqui porque FileMover ainda usa os.walk internamente
    # Se FileMover for totalmente migrado para não usar os.walk, esta importação pode ser removida.
    # TODO: Avaliar a substituição completa de os.walk em FileMover se Path.glob/rglob for suficiente.
    global os
    import os

    mover = FileMover(root_folder_str)
    mover.process_files_in_root()

    log_files_exist = False
    if mover.log_folder.exists():
        log_files_exist = any(f.name.startswith("process_root_log_") and f.name.endswith(
            ".log") for f in mover.log_folder.iterdir() if f.is_file())

    final_message = mover.summary_message + "\n\n"
    if log_files_exist:
        final_message += f"Verifique o(s) arquivo(s) de log em '{mover.log_folder}' para detalhes sobre erros ou alterações realizadas nos nomes dos arquivos."
    else:
        final_message += "Nenhum erro ou alteração significativa foi registrada durante o processo."

    show_auto_close_message(final_message, 10000)


def show_auto_close_message(message: str, timeout: int) -> None:
    """
    Exibe uma mensagem que se fecha automaticamente após o tempo especificado.
    """
    msg_root = tk.Tk()
    msg_root.title("Processamento Concluído")

    window_width = 500
    window_height = 300  # Ajustado para melhor visualização da mensagem
    screen_width = msg_root.winfo_screenwidth()
    screen_height = msg_root.winfo_screenheight()
    x_coordinate = int((screen_width - window_width) / 2)
    y_coordinate = int((screen_height - window_height) / 2)
    msg_root.geometry(
        f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

    frame = tk.Frame(msg_root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    countdown_var = tk.StringVar()

    title_label = tk.Label(
        frame, text="Processamento Concluído", font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))

    # Usar um Text widget para melhor formatação e scrollbar se necessário
    msg_text_area = tk.Text(frame, wrap=tk.WORD, height=10,
                            width=60, relief=tk.FLAT, background=msg_root.cget('bg'))
    msg_text_area.insert(tk.END, message)
    msg_text_area.config(state=tk.DISABLED)  # Torna o texto não editável
    msg_text_area.pack(pady=10, fill=tk.BOTH, expand=True)

    countdown_label = tk.Label(frame, textvariable=countdown_var, fg="gray")
    countdown_label.pack(pady=(10, 0))

    close_button = tk.Button(
        frame, text="Fechar Manualmente", command=msg_root.destroy)
    close_button.pack(pady=10)

    def update_countdown(remaining: int) -> None:
        if not msg_root.winfo_exists():  # Verifica se a janela ainda existe
            return
        if remaining <= 0:
            if msg_root.winfo_exists():
                msg_root.destroy()
            return
        countdown_var.set(f"Esta janela fechará em {remaining} segundos")
        msg_root.after(1000, update_countdown, remaining - 1)

    msg_root.after(0, update_countdown, timeout // 1000)
    msg_root.after(timeout, lambda: msg_root.destroy()
                   if msg_root.winfo_exists() else None)
    msg_root.mainloop()


if __name__ == "__main__":
    main()

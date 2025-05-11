import shutil
import email
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import tkinter as tk_module # Alias to avoid conflict
from tkinter import filedialog, messagebox

# --- Constantes ---
EFFECTIVE_MAX_PATH = 259  # Limite prático para caminhos no Windows (MAX_PATH (260) - 1 para nulo)
SAFE_PATH_MARGIN = 10     # Margem de segurança para evitar atingir o limite exato
LOG_FOLDER_NAME = "ERROS" # Nome da pasta de logs
FALLBACK_SANITIZED_FILENAME = "arquivo_renomeado"
MAX_DUPLICATE_RESOLUTION_ATTEMPTS = 10 # Máximo de tentativas para resolver nomes duplicados
LOG_FILENAME_PREFIX = "archive_failures_subfolders_" # Prefixo específico para este script
DEFAULT_EXCLUDED_FOLDERS = ["anos anteriores", "erros"] # Nomes de pastas a ignorar (em minúsculas)
# --- Fim Constantes ---


class FileArchiver:
    """Arquiva arquivos de uma pasta e suas subpastas para uma estrutura de pastas baseada em data."""

    def __init__(self, watch_folder_str: str, archive_root_str: str, log_folder_name: str = LOG_FOLDER_NAME):
        """
        Inicializa o FileArchiver para processamento recursivo.

        Args:
            watch_folder_str: Caminho da pasta raiz a ser monitorada e processada.
            archive_root_str: Caminho da pasta raiz onde a estrutura de arquivamento (Ano/Mês) será criada.
                              Normalmente, é o mesmo que watch_folder_str para este script.
            log_folder_name: Nome da pasta de log (será criada dentro de archive_root_str).
        """
        self.watch_folder: Path = Path(watch_folder_str).resolve()
        self.archive_root: Path = Path(archive_root_str).resolve() # Geralmente o mesmo que watch_folder
        self.log_folder: Path = self.archive_root / log_folder_name
        self.setup_logger()
        self.excluded_folders_lower: List[str] = [f.lower() for f in DEFAULT_EXCLUDED_FOLDERS]

        # --- Counters and Summary ---
        self.moved_files_count = 0
        self.renamed_in_place_count = 0
        self.error_count = 0
        self.created_folders_count = 0
        self.summary_message = ""
        # --- End Counters and Summary ---

    def setup_logger(self) -> None:
        """Configura o logger para registrar apenas erros."""
        try:
            self.log_folder.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            log_file = self.log_folder / f"{LOG_FILENAME_PREFIX}{timestamp}.log"

            self.logger = logging.getLogger(
                f"{__name__}.subpastas.{id(self)}")  # Unique logger name
            self.logger.propagate = False  # Prevent propagation if root logger exists
            self.logger.setLevel(logging.ERROR)

            # Remove handlers existentes para evitar duplicação
            if self.logger.hasHandlers():
                self.logger.handlers.clear()

            file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
            file_handler.setLevel(logging.ERROR)

            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - Arquivo: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

        except Exception as e:
            critical_error_msg = f"ERRO CRÍTICO: Não foi possível configurar o logger em {self.log_folder}. Erro: {e}"
            print(critical_error_msg)
            self.logger = logging.getLogger(f'null_subpastas.{id(self)}')
            if not self.logger.hasHandlers():
                self.logger.addHandler(logging.NullHandler())
            try: # Tenta logar o erro crítico se o logger, mesmo nulo, permitir
                self.logger.error(critical_error_msg)
            except Exception: # pylint: disable=broad-except
                pass # Ignora se nem isso funcionar
            self.error_count += 1

    def process_files_recursively(self) -> None:
        """Processa arquivos recursivamente a partir da watch_folder e gera uma mensagem de resumo."""
        if not self.watch_folder.exists() or not self.watch_folder.is_dir():
            error_msg = f"{self.watch_folder} - Motivo: Pasta de monitoramento não encontrada."
            self.logger.error(error_msg)
            self.error_count += 1
            self.summary_message = f"Erro Crítico: Pasta de monitoramento '{self.watch_folder}' não encontrada."
            return

        if not self.archive_root.exists() or not self.archive_root.is_dir():
            error_msg = f"{self.archive_root} - Motivo: Pasta raiz de arquivamento não encontrada."
            self.logger.error(error_msg)
            self.error_count += 1
            self.summary_message = f"Erro Crítico: Pasta raiz de arquivamento '{self.archive_root}' não encontrada."
            return

        # Reset counters for this run, mas mantém erros de setup do logger
        initial_error_count = self.error_count
        self.moved_files_count = 0
        self.renamed_in_place_count = 0
        self.created_folders_count = 0
        # Não resetar self.error_count totalmente para manter erros de setup do logger

        self.process_folder(self.watch_folder)
        self.error_count = initial_error_count + (self.error_count - initial_error_count) # Garante que erros de processamento sejam somados

        # --- Generate Summary Message ---
        summary = "-" * 30 + "\n"
        actions_taken = False
        if self.moved_files_count > 0 or self.renamed_in_place_count > 0 or self.created_folders_count > 0:
            summary += f"Processamento concluído:\n"
            actions_taken = True
            if self.moved_files_count > 0:
                summary += f"- {self.moved_files_count} arquivos movidos para pastas de ano/mês corretas.\n"
            if self.renamed_in_place_count > 0:
                summary += f"- {self.renamed_in_place_count} arquivos renomeados (sanitizados/truncados) no local.\n"
            if self.created_folders_count > 0:
                summary += f"- {self.created_folders_count} novas pastas de ano/mês criadas.\n"
        else:
            if self.error_count == 0:
                summary += "Nenhum arquivo precisou ser movido ou renomeado. Organização e nomes já estavam corretos.\n"
            else:
                summary += "Nenhuma ação de movimentação ou renomeio foi concluída com sucesso (verifique os erros).\n"

        if self.error_count > 0:
            summary += f"\nAtenção: Ocorreram {self.error_count} erros durante a operação. Verifique o log em '{self.log_folder}'.\n"
        elif actions_taken:
            summary += "\nOperação concluída sem erros registrados.\n"

        self.summary_message = summary
        # --- End Generate Summary Message ---

    def process_folder(self, current_folder_path: Path) -> None:
        """Processa recursivamente os itens em uma pasta."""
        try:
            if not current_folder_path.is_dir(): # Verificação extra
                self.logger.error(
                    f"{current_folder_path} - Motivo: Pasta não encontrada ou não é um diretório.")
                self.error_count += 1
                return

            for item_path in current_folder_path.iterdir():
                try:
                    if item_path.is_dir():
                        if item_path.name.lower() not in self.excluded_folders_lower and \
                           item_path.resolve() != self.log_folder.resolve():
                            self.process_folder(item_path) # Chamada recursiva
                    elif item_path.is_file():
                        if item_path.name.lower().endswith(".ffs_db"): # Ignora .ffs_db
                            continue
                        self.process_file(item_path)
                except OSError as e_item:
                    self.logger.error(
                        f"{item_path.name} (em {item_path.parent}) - Motivo: Erro ao acessar item. Detalhes: {e_item}")
                    self.error_count += 1
                except Exception as e_gen_item:
                    self.logger.error(
                        f"{item_path.name} (em {item_path.parent}) - Motivo: Erro inesperado ao processar item. Detalhes: {e_gen_item}")
                    self.error_count += 1
        except OSError as e:
            self.logger.error(
                f"{current_folder_path} - Motivo: Erro ao acessar ou listar pasta. Detalhes: {e}")
            self.error_count += 1
        except Exception as e:
            self.logger.error(
                f"{current_folder_path} - Motivo: Erro inesperado ao processar pasta. Detalhes: {e}")
            self.error_count += 1

    def process_file(self, file_path: Path) -> None:
        """Processa um único arquivo, determinando seu tipo e chamando a função apropriada."""
        try:
            if file_path.suffix.lower() == ".eml":
                self.process_eml_file(file_path)
            else:
                self.process_other_file(file_path)
        except Exception as e:
            self.logger.error(
                f"{file_path.name} (em {file_path.parent}) - Motivo: Erro inesperado durante o processamento inicial. Detalhes: {e}")
            self.error_count += 1

    def process_eml_file(self, eml_path: Path) -> None:
        """Processa arquivos .eml para extrair data e mover."""
        msg: Optional[email.message.Message] = None
        try:
            with eml_path.open('r', encoding='utf-8') as f:
                msg = email.message_from_file(f)
        except UnicodeDecodeError:
            try:
                with eml_path.open('r', encoding='latin-1') as f:
                    msg = email.message_from_file(f)
            except Exception as e:
                self.logger.error(
                    f"{eml_path.name} - Motivo: Falha ao ler o arquivo (tentativas UTF-8 e Latin-1). Detalhes: {e}")
                self.error_count += 1
                return
        except FileNotFoundError:
            self.logger.error(
                f"{eml_path.name} - Motivo: Arquivo não encontrado (pode ter sido movido/excluído).")
            self.error_count += 1
            return
        except OSError as e: # Erros de permissão, etc.
            self.logger.error(
                f"{eml_path.name} - Motivo: Erro de sistema ao ler o arquivo. Detalhes: {e}")
            self.error_count += 1
            return
        except Exception as e: # Outros erros de leitura
            self.logger.error(
                f"{eml_path.name} - Motivo: Falha genérica ao ler o arquivo. Detalhes: {e}")
            self.error_count += 1
            return

        if not msg:
            self.logger.error(
                f"{eml_path.name} - Motivo: Não foi possível interpretar o conteúdo do e-mail após leitura.")
            self.error_count += 1
            return

        date_str = msg.get("Date")
        date_obj = self._parse_date(date_str, eml_path)

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        target_archive_folder = self.archive_root / year / year_month

        try:
            self.move_file_to_archive(eml_path, target_archive_folder)
        except Exception as e:
            self.logger.error(
                f"{eml_path.name} - Motivo: Erro ao determinar pasta de destino ou iniciar movimentação. Detalhes: {e}")
            self.error_count += 1

    def _parse_date(self, date_str: Optional[str], file_path_for_log: Path) -> datetime:
        """Tenta analisar a string de data. Retorna datetime.now() e loga erro em caso de falha."""
        if not date_str:
            return datetime.now()

        formats_to_try = [
            "%a, %d %b %Y %H:%M:%S %z",    # e.g., Tue, 15 Nov 1994 08:12:31 -0700
            "%a, %d %b %Y %H:%M:%S %Z",    # e.g., Tue, 15 Nov 1994 08:12:31 PST
            "%d %b %Y %H:%M:%S %z",        # e.g., 15 Nov 1994 08:12:31 -0700
            "%d %b %Y %H:%M:%S %Z",        # e.g., 15 Nov 1994 08:12:31 PST
            "%Y-%m-%d %H:%M:%S",           # ISO-like
        ]

        try:
            cleaned_date_str_util = re.sub(r'\s*\([^)]*\)\s*$', '', date_str).strip()
            parsed_dt = email.utils.parsedate_to_datetime(cleaned_date_str_util)
            if parsed_dt:
                return parsed_dt
        except Exception:
            pass

        for fmt in formats_to_try:
            try:
                cleaned_date_str_strptime = re.sub(r'\s*\([^)]*\)\s*$', '', date_str).strip()
                return datetime.strptime(cleaned_date_str_strptime, fmt)
            except ValueError:
                continue

        self.logger.error(
            f"{file_path_for_log.name} - Motivo: Falha ao interpretar data '{date_str}'. Usando data/hora atual.")
        self.error_count += 1
        return datetime.now()

    def process_other_file(self, file_path: Path) -> None:
        """Processa outros tipos de arquivo usando data de modificação."""
        try:
            modification_time = file_path.stat().st_mtime
            date_obj = datetime.fromtimestamp(modification_time)
        except FileNotFoundError:
            self.logger.error(
                f"{file_path.name} - Motivo: Arquivo não encontrado ao obter data de modificação.")
            self.error_count += 1
            return
        except OSError as e:
            self.logger.error(
                f"{file_path.name} - Motivo: Falha ao obter data de modificação. Detalhes: {e}")
            self.error_count += 1
            return

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        target_archive_folder = self.archive_root / year / year_month

        try:
            self.move_file_to_archive(file_path, target_archive_folder)
        except Exception as e:
            self.logger.error(
                f"{file_path.name} - Motivo: Erro ao determinar pasta de destino ou iniciar movimentação. Detalhes: {e}")
            self.error_count += 1

    def _sanitize_filename(self, filename: str) -> str:
        """Remove ou substitui caracteres inválidos, o prefixo 'msg ' e normaliza números."""
        sanitized = re.sub(r'^msg\s+', '', filename, flags=re.IGNORECASE)
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)
        sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)
        sanitized = sanitized.strip()

        match = re.match(r'^(\d+)(.*)', sanitized)
        if match:
            number_str, rest_of_name = match.groups()
            try:
                number = int(number_str)
                sanitized = str(number) + rest_of_name
            except ValueError: # Para números muito grandes
                if len(number_str) > 1 and number_str.startswith('0'):
                    sanitized = number_str.lstrip('0') + rest_of_name
                else:
                    sanitized = number_str + rest_of_name
        
        if not sanitized:
            self.logger.error(
                f"Nome do arquivo '{filename}' resultou em vazio após sanitização. Usando fallback '{FALLBACK_SANITIZED_FILENAME}'.")
            self.error_count +=1 # Considerar erro se o nome se tornar vazio
            sanitized = FALLBACK_SANITIZED_FILENAME
        return sanitized

    def _truncate_filename(self, target_folder: Path, filename: str, max_full_path_len: int) -> str:
        """Trunca o nome do arquivo (preservando a extensão) se o caminho completo exceder max_full_path_len."""
        file_path_obj = Path(filename)
        base, ext = file_path_obj.stem, file_path_obj.suffix
        potential_full_path = target_folder / filename

        if len(str(potential_full_path)) <= max_full_path_len:
            return filename

        len_of_folder_path_str = len(str(target_folder))
        len_of_separator = 1
        len_of_extension = len(ext)

        available_len_for_base = max_full_path_len - (len_of_folder_path_str + len_of_separator + len_of_extension)

        if available_len_for_base <= 0:
            self.logger.error(
                f"Não é possível criar nome para '{filename}' em '{target_folder}' (limite: {max_full_path_len}). "
                f"Caminho da pasta base muito longo. Disponível para base: {available_len_for_base}")
            self.error_count += 1
            # Tenta um fallback mínimo
            if len(ext) < max_full_path_len - (len_of_folder_path_str + len_of_separator):
                minimal_base_len = max_full_path_len - (len_of_folder_path_str + len_of_separator + len_of_extension)
                if minimal_base_len < 1 and len(base) > 0: return f"_{ext}" if ext else "_"
                if minimal_base_len < 1 and len(base) == 0: return "_"
            return filename # Retorna original se o fallback também falhar

        if available_len_for_base < len(base):
            # self.logger.warning(f"Nome truncado: '{filename}' -> '{base[:available_len_for_base]}{ext}' em '{target_folder}'") # Opcional
            return f"{base[:available_len_for_base]}{ext}"
        
        return filename # Não precisou truncar a base

    def move_file_to_archive(self, source_path: Path, target_destination_folder: Path) -> None:
        """
        Move ou renomeia o arquivo para a pasta de destino, tratando sanitização,
        truncamento e duplicados. Decide entre mover, renomear no local ou ignorar.
        """
        if not source_path.exists():
            return

        created_folders_this_call = 0
        try:
            if not target_destination_folder.parent.exists() and target_destination_folder.parent != self.archive_root:
                target_destination_folder.parent.mkdir(parents=True, exist_ok=True)
                self.created_folders_count += 1
                created_folders_this_call +=1
            
            if not target_destination_folder.exists():
                target_destination_folder.mkdir(parents=True, exist_ok=True)
                if created_folders_this_call == 0 or target_destination_folder.parent != self.archive_root:
                     self.created_folders_count += 1
        except OSError as e:
            self.logger.error(
                f"{source_path.name} - Motivo: Erro ao criar pasta de destino '{target_destination_folder}'. Detalhes: {e}")
            self.error_count += 1
            return

        original_filename = source_path.name
        sanitized_filename = self._sanitize_filename(original_filename)
        max_allowed_path = EFFECTIVE_MAX_PATH - SAFE_PATH_MARGIN
        
        desired_filename_in_target = self._truncate_filename(
            target_destination_folder, sanitized_filename, max_allowed_path)

        current_target_filename = desired_filename_in_target
        destination_path = target_destination_folder / current_target_filename
        num_attempts = 0

        # Loop para resolver conflitos se o destino existe E NÃO é o mesmo arquivo de origem
        while destination_path.exists() and not source_path.samefile(destination_path) \
              and num_attempts < MAX_DUPLICATE_RESOLUTION_ATTEMPTS:
            num_attempts += 1
            if num_attempts == 1: # Loga apenas na primeira tentativa
                self.logger.error(
                    f"{source_path.name} - Motivo: Conflito com arquivo existente em '{target_destination_folder}' para nome '{desired_filename_in_target}'. Tentando renomear.")
            
            base_name_orig, ext_orig = Path(desired_filename_in_target).stem, Path(desired_filename_in_target).suffix
            if not base_name_orig: # Caso o nome original seja apenas uma extensão ou vazio
                base_name_orig = FALLBACK_SANITIZED_FILENAME.split('.')[0]

            if num_attempts <= MAX_DUPLICATE_RESOLUTION_ATTEMPTS / 2: # Tenta com contador primeiro
                name_with_counter = f"{base_name_orig}_{num_attempts}{ext_orig}"
                current_target_filename = self._truncate_filename(
                    target_destination_folder, name_with_counter, max_allowed_path)
            else: # Depois tenta com timestamp
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                name_with_timestamp = f"{base_name_orig}_{timestamp}{ext_orig}"
                current_target_filename = self._truncate_filename(
                    target_destination_folder, name_with_timestamp, max_allowed_path)
            destination_path = target_destination_folder / current_target_filename

        # Verifica se o conflito foi resolvido ou se o arquivo original já está no local com o nome de destino
        if destination_path.exists() and not source_path.samefile(destination_path):
            self.logger.error(
                f"{source_path.name} - Motivo: Conflito de nome irresolúvel em '{target_destination_folder}' para '{desired_filename_in_target}' "
                f"após {num_attempts} tentativas. Arquivo não movido/renomeado.")
            self.error_count += 1
            return

        # Se o arquivo de origem já está no caminho de destino final (mesmo arquivo, mesmo nome), não faz nada.
        if source_path.resolve() == destination_path.resolve():
            return

        try:
            if not source_path.exists(): # Re-check source existence
                self.logger.warning(
                    f"{source_path.name} - Arquivo de origem desapareceu antes da ação final para '{destination_path}'.")
                return

            if source_path.parent.resolve() == destination_path.parent.resolve():
                source_path.rename(destination_path)
                self.renamed_in_place_count += 1
            else:
                shutil.move(str(source_path), str(destination_path))
                self.moved_files_count += 1
        except Exception as e:
            action_verb = "renomear" if source_path.parent.resolve() == destination_path.parent.resolve() else "mover"
            self.logger.error(
                f"{source_path.name} - Motivo: Falha ao {action_verb} para '{destination_path}'. Detalhes: {e}")
            self.error_count += 1


def select_folder() -> Optional[str]:
    """Abre uma janela para o usuário selecionar uma pasta."""
    root_tk = tk_module.Tk()
    root_tk.withdraw()
    folder_selected = filedialog.askdirectory(
        title="Selecione a Pasta para Arquivar")
    root_tk.destroy()
    return folder_selected


def show_auto_close_message(message: str, timeout: int) -> None:
    """
    Exibe uma mensagem que se fecha automaticamente após o tempo especificado.
    """
    msg_root = tk_module.Tk()
    msg_root.title("Processamento Concluído")

    window_width = 500
    window_height = 350
    screen_width = msg_root.winfo_screenwidth()
    screen_height = msg_root.winfo_screenheight()
    x_coordinate = int((screen_width - window_width) / 2)
    y_coordinate = int((screen_height - window_height) / 2)
    msg_root.geometry(
        f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
    msg_root.resizable(False, False)

    frame = tk_module.Frame(msg_root, padx=20, pady=20)
    frame.pack(fill=tk_module.BOTH, expand=True)

    countdown_var = tk_module.StringVar()
    
    title_label = tk_module.Label(
        frame, text="Processamento Concluído", font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))

    msg_frame = tk_module.Frame(frame)
    msg_frame.pack(pady=10, fill=tk_module.BOTH, expand=True)

    scrollbar = tk_module.Scrollbar(msg_frame)
    scrollbar.pack(side=tk_module.RIGHT, fill=tk_module.Y)

    msg_text = tk_module.Text(
        msg_frame,
        wrap=tk_module.WORD,
        yscrollcommand=scrollbar.set,
        padx=5,
        pady=5,
        height=10,
        borderwidth=0,
        highlightthickness=0,
        bg=msg_root.cget('bg')
    )
    msg_text.insert(tk_module.END, message)
    msg_text.config(state=tk_module.DISABLED)
    msg_text.pack(side=tk_module.LEFT, fill=tk_module.BOTH, expand=True)
    scrollbar.config(command=msg_text.yview)

    countdown_label = tk_module.Label(frame, textvariable=countdown_var, fg="gray")
    countdown_label.pack(pady=(10, 0))

    close_button = tk_module.Button(frame, text="Fechar Agora",
                             command=msg_root.destroy, width=15)
    close_button.pack(pady=10)

    def update_countdown(remaining: int) -> None:
        if not msg_root.winfo_exists():
            return
        if remaining <= 0:
            if msg_root.winfo_exists(): msg_root.destroy()
            return
        countdown_var.set(f"Esta janela fechará em {remaining} segundos")
        if msg_root.winfo_exists():
            msg_root.after(1000, update_countdown, remaining - 1)

    if msg_root.winfo_exists():
        msg_root.after(0, update_countdown, timeout // 1000)
    msg_root.mainloop()


def main() -> None:
    """Função principal para configurar e executar o arquivador de arquivos recursivo."""
    temp_root = tk_module.Tk()
    temp_root.withdraw()
    messagebox.showinfo("Seleção de Pasta",
                        "Selecione a pasta onde os arquivos (.eml e outros) serão organizados em subpastas de Ano/Mês.")
    temp_root.destroy()

    watch_folder_str = select_folder()
    if not watch_folder_str:
        temp_root = tk_module.Tk()
        temp_root.withdraw()
        messagebox.showinfo("Operação Cancelada",
                            "Nenhuma pasta selecionada. Encerrando.")
        temp_root.destroy()
        return

    watch_folder_path = Path(watch_folder_str)
    archive_root_path = watch_folder_path # Arquiva dentro da própria estrutura
    log_folder_display_path = archive_root_path / LOG_FOLDER_NAME

    temp_root = tk_module.Tk()
    temp_root.withdraw()
    info_message = f"Pasta selecionada: {watch_folder_path}\n"
    info_message += f"Os arquivos serão movidos para subpastas Ano/Mês dentro dela.\n"
    info_message += f"Logs de erros serão salvos em: {log_folder_display_path}\n\n"
    info_message += "Iniciando o processo de arquivamento..."
    messagebox.showinfo("Processo Iniciado", info_message)
    temp_root.destroy()

    archiver = FileArchiver(watch_folder_str, str(archive_root_path))
    archiver.process_files_recursively()

    final_message = archiver.summary_message
    log_files_found: List[Path] = []
    if archiver.log_folder.exists():
        try:
            log_files_found = sorted(
                [f for f in archiver.log_folder.iterdir() if f.is_file() and \
                 f.name.startswith(LOG_FILENAME_PREFIX) and f.name.endswith(".log")],
                reverse=True
            )
        except OSError:
            final_message += f"\nAviso: Não foi possível verificar a pasta de logs '{archiver.log_folder}'."

    if log_files_found:
        final_message += f"\nVerifique o(s) arquivo(s) de log em '{archiver.log_folder}' para detalhes sobre erros:"
        latest_log_name = log_files_found[0].name
        final_message += f"\n- {latest_log_name}"
        if len(log_files_found) > 1:
            final_message += f" (e {len(log_files_found) - 1} outro(s))"
    elif archiver.error_count > 0:
        final_message += f"\nForam encontrados {archiver.error_count} erros, mas o arquivo de log pode não ter sido criado corretamente em '{archiver.log_folder}'."

    show_auto_close_message(final_message, 7000) # 7 segundos


if __name__ == "__main__":
    main()

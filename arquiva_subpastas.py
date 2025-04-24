import os
import shutil
import email
import logging
import re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox  # Added messagebox

# Definir constantes
MAX_PATH_LENGTH = 255
SAFE_FILENAME_MARGIN = 10


class FileArchiver:
    def __init__(self, watch_folder, archive_root, log_folder):
        self.watch_folder = watch_folder
        # No arquiva_subpastas, archive_root é geralmente o mesmo que watch_folder
        self.archive_root = archive_root
        self.log_folder = log_folder
        self.setup_logger()
        # Pastas a serem ignoradas durante o processamento recursivo
        self.excluded_folders = ["anos anteriores", "erros"]

        # --- Counters and Summary ---
        self.moved_files_count = 0
        self.error_count = 0
        self.created_folders_count = 0
        self.summary_message = ""
        # --- End Counters and Summary ---

    # setup_logger substituído pela versão focada em erros

    def setup_logger(self):
        """Configura o logger para registrar apenas erros."""
        try:
            if not os.path.exists(self.log_folder):
                os.makedirs(self.log_folder)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            log_file = os.path.join(
                # Nome do arquivo alterado
                self.log_folder, f"archive_failures_{timestamp}.log")

            self.logger = logging.getLogger(
                __name__ + '_subpastas')  # Unique logger name
            self.logger.propagate = False  # Prevent propagation if root logger exists
            # Nível de log definido para ERROR
            self.logger.setLevel(logging.ERROR)

            if self.logger.hasHandlers():
                self.logger.handlers.clear()

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            # Nível do handler também definido para ERROR
            file_handler.setLevel(logging.ERROR)

            formatter = logging.Formatter(
                # Formato ajustado
                "%(asctime)s - %(levelname)s - Arquivo: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

        except Exception as e:
            # Keep print for critical setup error, but also try to log if possible
            critical_error_msg = f"ERRO CRÍTICO: Não foi possível configurar o logger em {self.log_folder}. Erro: {e}"
            print(critical_error_msg)
            # Use a fallback null logger
            self.logger = logging.getLogger('null_subpastas')
            if not self.logger.hasHandlers():
                self.logger.addHandler(logging.NullHandler())
            self.logger.error(critical_error_msg)  # Log the critical error too
            self.error_count += 1  # Count this as an error

    # process_files adaptado para chamar process_folder e gerar sumário

    def process_files(self):
        """Processa arquivos recursivamente e gera uma mensagem de resumo."""
        if not os.path.exists(self.watch_folder):
            error_msg = f"{self.watch_folder} - Motivo: Pasta de monitoramento não encontrada."
            self.logger.error(error_msg)
            print(
                f"ERRO: Pasta de monitoramento não encontrada: {self.watch_folder}")
            self.error_count += 1
            self.summary_message = f"Erro Crítico: Pasta de monitoramento '{self.watch_folder}' não encontrada."
            return

        if not os.path.exists(self.archive_root):
            error_msg = f"{self.archive_root} - Motivo: Pasta raiz de arquivamento não encontrada."
            self.logger.error(error_msg)
            print(
                f"ERRO: Pasta raiz de arquivamento não encontrada: {self.archive_root}")
            self.error_count += 1
            self.summary_message = f"Erro Crítico: Pasta raiz de arquivamento '{self.archive_root}' não encontrada."
            return

        # Reset counters for this run
        self.moved_files_count = 0
        # Keep error_count if logger setup failed
        # self.error_count = 0
        self.created_folders_count = 0

        # Inicia o processo recursivo a partir da pasta raiz/monitorada
        self.process_folder(self.watch_folder)

        # --- Generate Summary Message ---
        summary = "-" * 30 + "\n"
        if self.moved_files_count > 0 or self.created_folders_count > 0:
            summary += f"Processamento concluído:\n"
            if self.moved_files_count > 0:
                summary += f"- {self.moved_files_count} arquivos arquivados em pastas de ano/mês.\n"
            if self.created_folders_count > 0:
                summary += f"- {self.created_folders_count} novas pastas de ano/mês criadas.\n"
        else:
            summary += "Nenhum arquivo precisou ser movido ou pasta criada.\n"

        if self.error_count > 0:
            summary += f"\nAtenção: Ocorreram {self.error_count} erros durante a operação. Verifique o log em '{self.log_folder}'.\n"
        else:
            # Verifica se algum log foi gerado (mesmo sem erros fatais)
            log_file_exists = any(fname.startswith("archive_failures_") for fname in os.listdir(
                self.log_folder)) if os.path.exists(self.log_folder) else False
            if log_file_exists:
                # Should not happen if error_count is 0, but check anyway
                summary += f"\nOperação concluída. Logs de erro podem ter sido gerados em '{self.log_folder}'.\n"
            else:
                summary += "\nOperação concluída sem erros registrados.\n"

        self.summary_message = summary
        # --- End Generate Summary Message ---

    # process_folder adaptado para remover logging INFO e contar erros

    def process_folder(self, folder_path):
        try:
            # Check if folder exists before listing
            if not os.path.isdir(folder_path):
                self.logger.error(
                    f"{folder_path} - Motivo: Pasta não encontrada ou não é um diretório.")
                self.error_count += 1
                return

            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                try:
                    if os.path.isdir(item_path):
                        # Exclui pastas especificadas (case-insensitive) e a pasta de log
                        if item.lower() not in self.excluded_folders and item_path != self.log_folder:
                            # Chamada recursiva para subpastas
                            self.process_folder(item_path)
                    elif os.path.isfile(item_path):
                        # Ignora .ffs_db silenciosamente
                        if item_path.lower().endswith(".ffs_db"):
                            continue
                        self.process_file(item_path)
                except OSError as e_item:
                    # Loga erro se não conseguir verificar tipo (isdir/isfile) ou acessar item
                    self.logger.error(
                        f"{item_path} - Motivo: Erro ao acessar item. Detalhes: {e_item}")
                    self.error_count += 1
                except Exception as e_gen_item:
                    # Loga erro genérico ao processar item
                    self.logger.error(
                        f"{item_path} - Motivo: Erro inesperado ao processar item. Detalhes: {e_gen_item}")
                    self.error_count += 1

        except OSError as e:
            # Loga erro se não conseguir listar o diretório
            self.logger.error(
                f"{folder_path} - Motivo: Erro ao acessar ou listar pasta. Detalhes: {e}")
            self.error_count += 1
        except Exception as e:
            # Loga erro genérico ao processar a pasta
            self.logger.error(
                f"{folder_path} - Motivo: Erro inesperado ao processar pasta. Detalhes: {e}")
            self.error_count += 1

    # process_file adaptado para contar erros

    def process_file(self, file_path):
        try:
            if file_path.lower().endswith(".eml"):
                self.process_eml_file(file_path)
            else:
                self.process_other_file(file_path)
        except Exception as e:
            self.logger.error(
                f"{file_path} - Motivo: Erro inesperado durante o processamento inicial. Detalhes: {e}")
            self.error_count += 1

    # process_eml_file adaptado com _parse_date, logging de erro refinado e contagem de erros

    def process_eml_file(self, eml_path):
        msg = None
        try:
            with open(eml_path, 'r', encoding='utf-8') as f:
                msg = email.message_from_file(f)
        except UnicodeDecodeError:
            try:
                with open(eml_path, 'r', encoding='latin-1') as f:
                    msg = email.message_from_file(f)
            except Exception as e:
                self.logger.error(
                    f"{eml_path} - Motivo: Falha ao ler o arquivo (tentativas UTF-8 e Latin-1). Detalhes: {e}")
                self.error_count += 1
                return
        except FileNotFoundError:
            self.logger.error(
                f"{eml_path} - Motivo: Arquivo não encontrado (pode ter sido movido/excluído).")
            self.error_count += 1
            return
        except OSError as e:
            self.logger.error(
                f"{eml_path} - Motivo: Erro de sistema ao ler o arquivo. Detalhes: {e}")
            self.error_count += 1
            return
        except Exception as e:
            self.logger.error(
                f"{eml_path} - Motivo: Falha genérica ao ler o arquivo. Detalhes: {e}")
            self.error_count += 1
            return

        if not msg:
            self.logger.error(
                f"{eml_path} - Motivo: Não foi possível interpretar o conteúdo do e-mail após leitura.")
            self.error_count += 1
            return

        date_str = msg.get("Date")
        # Pass path for potential logging inside
        date_obj = self._parse_date(date_str, eml_path)

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        try:
            # Verifica se o arquivo JÁ ESTÁ na pasta de destino correta
            current_folder_abs = os.path.normpath(
                os.path.abspath(os.path.dirname(eml_path)))
            target_folder_abs = os.path.normpath(
                os.path.abspath(archive_folder))

            if current_folder_abs == target_folder_abs:
                return  # Silently ignore if already in the correct place

            # Chama move_file_to_archive
            self.move_file_to_archive(eml_path, archive_folder)

        except Exception as e:
            # Catch potential errors during path comparison or before move call
            self.logger.error(
                f"{eml_path} - Motivo: Erro ao determinar pasta de destino ou iniciar movimentação. Detalhes: {e}")
            self.error_count += 1

    # _parse_date adaptado para logar erro se falhar

    def _parse_date(self, date_str, file_path_for_log):
        """Tenta analisar a string de data. Retorna datetime.now() e loga erro em caso de falha."""
        if not date_str:
            # Log warning instead of error? Or just proceed with now()? Let's log warning.
            # self.logger.warning(f"{file_path_for_log} - Motivo: Cabeçalho 'Date' ausente ou vazio. Usando data/hora atual.")
            return datetime.now()  # Don't count this as a critical error

        formats_to_try = [
            "%a, %d %b %Y %H:%M:%S %z",    # Standard RFC 5322 format with timezone offset
            "%a, %d %b %Y %H:%M:%S %Z",    # Format with timezone name
            "%d %b %Y %H:%M:%S %z",        # Format without weekday
            "%d %b %Y %H:%M:%S %Z",        # Format without weekday, with timezone name
            # Add other common non-standard formats if needed
            "%Y-%m-%d %H:%M:%S",           # ISO-like without T or Z
        ]

        # 1. Try email.utils first (handles complex timezone offsets well)
        try:
            # Remove timezone name in parentheses like (UTC), (PDT) etc. parsedate_to_datetime handles offsets better
            cleaned_date_str_util = re.sub(
                r'\s*\([^)]*\)\s*$', '', date_str).strip()
            parsed_dt = email.utils.parsedate_to_datetime(
                cleaned_date_str_util)
            if parsed_dt:
                # If timezone is naive, make it aware using local timezone (or UTC)
                # This might not be perfectly accurate if the original email had a specific offset
                # but it's better than assuming UTC for everything.
                # Commenting out for now, as naive might be acceptable if consistent.
                # if parsed_dt.tzinfo is None or parsed_dt.tzinfo.utcoffset(parsed_dt) is None:
                #     parsed_dt = parsed_dt.astimezone() # Convert to local timezone aware
                return parsed_dt
        except Exception:
            pass  # Ignore parsing errors here, try strptime next

        # 2. Try strptime with various formats
        for fmt in formats_to_try:
            try:
                # Clean timezone name in parentheses for strptime as well
                cleaned_date_str_strptime = re.sub(
                    r'\s*\([^)]*\)\s*$', '', date_str).strip()
                # For formats with %Z, timezone name parsing can be tricky/OS-dependent.
                # For formats with %z, Python < 3.7 might need external libraries like python-dateutil
                # Let's assume Python 3.7+ for %z support.
                return datetime.strptime(cleaned_date_str_strptime, fmt)
            except ValueError:
                continue  # Try the next format

        # 3. If all parsing fails
        self.logger.error(
            f"{file_path_for_log} - Motivo: Falha ao interpretar data '{date_str}'. Usando data/hora atual.")
        self.error_count += 1  # Count this as an error as we couldn't parse the date
        return datetime.now()

    # process_other_file adaptado com tratamento de erro e contagem de erros

    def process_other_file(self, file_path):
        try:
            modification_time = os.path.getmtime(file_path)
            date_obj = datetime.fromtimestamp(modification_time)
        except FileNotFoundError:
            self.logger.error(
                f"{file_path} - Motivo: Arquivo não encontrado ao obter data de modificação.")
            self.error_count += 1
            return
        except OSError as e:
            self.logger.error(
                f"{file_path} - Motivo: Falha ao obter data de modificação. Detalhes: {e}")
            self.error_count += 1
            return  # Impede a movimentação

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        try:
            # Verifica se o arquivo JÁ ESTÁ na pasta de destino correta
            current_folder_abs = os.path.normpath(
                os.path.abspath(os.path.dirname(file_path)))
            target_folder_abs = os.path.normpath(
                os.path.abspath(archive_folder))

            if current_folder_abs == target_folder_abs:
                return  # Silently ignore

            # Chama move_file_to_archive
            self.move_file_to_archive(file_path, archive_folder)

        except Exception as e:
            # Catch potential errors during path comparison or before move call
            self.logger.error(
                f"{file_path} - Motivo: Erro ao determinar pasta de destino ou iniciar movimentação. Detalhes: {e}")
            self.error_count += 1

    # _sanitize_filename (igual ao dos outros scripts)

    def _sanitize_filename(self, filename):
        """Remove ou substitui caracteres inválidos e o prefixo 'msg '."""
        # 1. Remove o prefixo "msg " (case-insensitive) do início
        #    O padrão ^ indica o início da string
        #    re.IGNORECASE faz a busca ignorar maiúsculas/minúsculas
        # Adicionado \s+ para remover o espaço seguinte também
        sanitized = re.sub(r'^msg\s+', '', filename, flags=re.IGNORECASE)

        # 2. Remove caracteres inválidos: < > : " / \ | ? *
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)

        # 3. Remove caracteres de controle (ASCII 0-31)
        sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)

        # 4. Remove espaços em branco no início ou fim (após remover prefixo e inválidos)
        sanitized = sanitized.strip()

        # 5. Normaliza números no início do nome para remover zeros à esquerda
        # Procura por um número no início do nome do arquivo
        match = re.match(r'^(\d+)(.*)', sanitized)
        if match:
            number_str, rest_of_name = match.groups()
            # Converte para inteiro para remover zeros à esquerda
            number = int(number_str)
            # Reconstrói o nome com o número sem zeros à esquerda
            sanitized = str(number) + rest_of_name

        # 6. Garante que o nome não seja vazio após a limpeza
        if not sanitized:
            # Se o nome original era apenas "msg " ou algo similar que foi removido
            sanitized = "arquivo_renomeado"  # Ou gerar um nome único com timestamp
        # Não loga mais a sanitização
        return sanitized

    # _truncate_filename (igual ao dos outros scripts, com contagem de erro)

    def _truncate_filename(self, folder_path, filename, max_len):
        """Trunca o nome do arquivo se o caminho completo exceder max_len."""
        base, ext = os.path.splitext(filename)
        # Ensure extension is not overly long (rare, but possible)
        if len(ext) > 20:  # Arbitrary limit for sanity
            ext = ext[:20]

        full_path = os.path.join(folder_path, filename)
        # Use bytes length for more accuracy
        full_path_len = len(full_path.encode('utf-8'))

        if full_path_len <= max_len:
            return filename

        # Calculate available space for the base name in bytes
        folder_path_len = len(folder_path.encode('utf-8'))
        sep_len = len(os.sep.encode('utf-8'))
        ext_len = len(ext.encode('utf-8'))
        available_len_for_base = max_len - \
            (folder_path_len + sep_len + ext_len)

        if available_len_for_base <= 0:
            # Log error if truncation is impossible (folder path itself is too long)
            self.logger.error(
                f"Não é possível criar um nome de arquivo válido para '{filename}' na pasta '{folder_path}' devido ao limite de comprimento ({max_len}). O caminho da pasta é muito longo.")
            self.error_count += 1
            return filename  # Return original, let the move/rename fail and log that specific error

        # Truncate the base name based on available byte length
        # This requires encoding/decoding to handle multi-byte characters correctly
        encoded_base = base.encode('utf-8')
        truncated_encoded_base = encoded_base[:available_len_for_base]
        # Decode back, ignoring errors in case we cut a multi-byte char
        truncated_base = truncated_encoded_base.decode(
            'utf-8', errors='ignore')

        # Ensure the truncated base doesn't end with problematic chars like space or dot
        truncated_base = truncated_base.strip(' .')

        # Reassemble the filename
        truncated_filename = f"{truncated_base}{ext}"

        # Log a warning that truncation occurred (optional, could be INFO level)
        # self.logger.warning(f"Nome do arquivo truncado devido ao limite de comprimento: '{filename}' -> '{truncated_filename}' em '{folder_path}'")

        return truncated_filename

    # move_file_to_archive substituído pela versão mais robusta com contagem

    def move_file_to_archive(self, file_path, archive_folder):
        """Move o arquivo para a pasta de destino, tratando sanitização, truncamento e duplicados."""
        archive_year_folder = os.path.dirname(archive_folder)
        try:
            # Cria pastas (sem alterações na lógica, mas erros são logados e contados)
            if not os.path.exists(archive_year_folder):
                os.makedirs(archive_year_folder)
                self.created_folders_count += 1
            if not os.path.exists(archive_folder):
                os.makedirs(archive_folder)
                self.created_folders_count += 1
        except OSError as e:
            self.logger.error(
                f"{file_path} - Motivo: Erro ao criar pasta de destino '{archive_folder}'. Detalhes: {e}")
            self.error_count += 1
            return  # Cannot proceed if destination folder cannot be created

        original_filename = os.path.basename(file_path)
        sanitized_filename = self._sanitize_filename(original_filename)

        # 1. Truncar o nome sanitizado SE necessário
        max_allowed_path = MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN
        final_filename = self._truncate_filename(
            archive_folder, sanitized_filename, max_allowed_path)

        destination_path = os.path.join(archive_folder, final_filename)

        # 2. Verificar duplicidade e renomear se necessário
        counter = 1
        base, ext = os.path.splitext(final_filename)
        # Guarda o nome antes do loop de duplicados
        temp_final_filename = final_filename

        while os.path.exists(destination_path):
            # Tenta adicionar um contador (_1, _2, ...)
            new_filename_base = f"{base}_{counter}"
            potential_new_filename = f"{new_filename_base}{ext}"

            # Trunca o nome com contador *antes* de verificar o comprimento total
            truncated_with_counter = self._truncate_filename(
                archive_folder, potential_new_filename, max_allowed_path)
            potential_full_path = os.path.join(
                archive_folder, truncated_with_counter)

            # Verifica se o nome truncado com contador já existe
            if not os.path.exists(potential_full_path):
                final_filename = truncated_with_counter
                destination_path = potential_full_path
                # Log warning about duplicate rename (optional)
                # self.logger.warning(f"Arquivo duplicado '{temp_final_filename}' em '{archive_folder}'. Renomeando para '{final_filename}' (Origem: {file_path})")
                break  # Sai do while loop, nome único encontrado
            else:
                # Se o nome com contador (mesmo truncado) ainda existe, tenta timestamp
                # Use a base original (antes de adicionar _counter) para o timestamp
                base_original_sem_contador, ext_original = os.path.splitext(
                    temp_final_filename)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                nome_com_timestamp = f"{base_original_sem_contador}_{timestamp}{ext_original}"

                # Trunca o nome com timestamp
                final_filename = self._truncate_filename(
                    archive_folder, nome_com_timestamp, max_allowed_path)
                destination_path = os.path.join(archive_folder, final_filename)

                # Verifica se o nome truncado com timestamp já existe (muito raro)
                if os.path.exists(destination_path):
                    self.logger.error(
                        f"{file_path} - Motivo: Conflito de nome irresolúvel em '{archive_folder}' após tentar adicionar contador e timestamp (arquivo duplicado: {original_filename}).")
                    self.error_count += 1
                    return  # Aborta a movimentação deste arquivo
                else:
                    # Log warning about duplicate rename with timestamp (optional)
                    # self.logger.warning(f"Arquivo duplicado '{temp_final_filename}' em '{archive_folder}'. Renomeando para '{final_filename}' com timestamp (Origem: {file_path})")
                    break  # Sai do while loop, nome único encontrado

            counter += 1
            if counter > 100:  # Safety break to prevent infinite loops
                self.logger.error(
                    f"{file_path} - Motivo: Loop infinito detectado ao tentar renomear arquivo duplicado '{temp_final_filename}' em '{archive_folder}'.")
                self.error_count += 1
                return  # Aborta

        # 3. Mover o arquivo
        try:
            # Double check source exists before moving
            if not os.path.exists(file_path):
                self.logger.error(
                    f"{file_path} - Motivo: Arquivo de origem desapareceu antes da movimentação para '{destination_path}'.")
                self.error_count += 1
                return

            shutil.move(file_path, destination_path)
            self.moved_files_count += 1  # Incrementa contador de sucesso
            # print(f"Arquivo {os.path.basename(destination_path)} arquivado em {archive_folder}") # Removido print
        except Exception as e:
            self.logger.error(
                f"{file_path} - Motivo: Falha ao mover para '{destination_path}'. Detalhes: {e}")
            self.error_count += 1
            # Try to restore original name if rename happened due to duplication check? Maybe too complex.


# select_folder permanece o mesmo
def select_folder():
    """Abre uma janela para o usuário selecionar uma pasta."""
    root = tk.Tk()
    root.withdraw()  # Oculta a janela principal do Tkinter
    folder_selected = filedialog.askdirectory(
        title="Selecione a Pasta para Arquivar")
    root.destroy()  # Fecha a instância do Tkinter
    return folder_selected

# --- Função show_auto_close_message copiada de arquiva_raiz.py ---


def show_auto_close_message(message, timeout):
    """
    Exibe uma mensagem que se fecha automaticamente após o tempo especificado.

    Args:
        message: Texto da mensagem
        timeout: Tempo em milissegundos antes do fechamento automático
    """
    # Criar janela
    root = tk.Tk()
    root.title("Processamento Concluído")

    # Centralizar na tela
    window_width = 500
    # Adjust height based on message length? Or use a scrollbar? Keep fixed for now.
    window_height = 350  # Reduced height slightly
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_coordinate = int((screen_width - window_width) / 2)
    y_coordinate = int((screen_height - window_height) / 2)
    root.geometry(
        f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")
    root.resizable(False, False)  # Prevent resizing

    # Adicionar texto
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    # Adicionar contador regressivo
    countdown_var = tk.StringVar()
    countdown_var.set(f"Esta mensagem se fechará em {timeout//1000} segundos")

    # Título
    title_label = tk.Label(
        frame, text="Processamento Concluído", font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))

    # Mensagem principal com scrollbar if needed (using Text widget)
    msg_frame = tk.Frame(frame)
    msg_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(msg_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    msg_text = tk.Text(
        msg_frame,
        wrap=tk.WORD,
        yscrollcommand=scrollbar.set,
        padx=5,
        pady=5,
        height=10,  # Adjust height as needed
        borderwidth=0,
        highlightthickness=0,  # Remove border
        bg=root.cget('bg')  # Match background color
    )
    msg_text.insert(tk.END, message)
    msg_text.config(state=tk.DISABLED)  # Make it read-only
    msg_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar.config(command=msg_text.yview)

    # Contador
    countdown_label = tk.Label(frame, textvariable=countdown_var, fg="gray")
    countdown_label.pack(pady=(10, 0))

    # Botão para fechar manualmente
    close_button = tk.Button(frame, text="Fechar Agora",
                             command=root.destroy, width=15)
    close_button.pack(pady=10)

    # Função para atualizar o contador e fechar a janela
    def update_countdown(remaining):
        if remaining < 0:  # Check if already closed manually
            if root.winfo_exists():
                root.destroy()
            return
        if remaining == 0:
            if root.winfo_exists():
                root.destroy()
            return
        countdown_var.set(f"Esta mensagem se fechará em {remaining} segundos")
        # Check if window still exists before scheduling next update
        if root.winfo_exists():
            root.after(1000, update_countdown, remaining - 1)

    # Iniciar o contador
    if root.winfo_exists():
        root.after(0, update_countdown, timeout // 1000)

    # Iniciar o temporizador para fechar a janela (redundant with countdown?)
    # Let countdown handle the closing
    # root.after(timeout, root.destroy)

    # Iniciar loop principal
    root.mainloop()
# --- Fim da função show_auto_close_message ---


# main adaptado para usar a pasta selecionada como watch e archive root, e mostrar mensagem final
def main():
    # Use Tkinter temporarily for the initial message box
    temp_root = tk.Tk()
    temp_root.withdraw()
    messagebox.showinfo("Seleção de Pasta",
                        "Selecione a pasta onde os arquivos (.eml e outros) serão organizados em subpastas de Ano/Mês.")
    temp_root.destroy()  # Close the temporary root

    watch_folder = select_folder()
    if not watch_folder:
        # Use messagebox for cancellation info
        temp_root = tk.Tk()
        temp_root.withdraw()
        messagebox.showinfo("Operação Cancelada",
                            "Nenhuma pasta selecionada. Encerrando.")
        temp_root.destroy()
        return

    # Define archive_root como a mesma pasta selecionada
    archive_root = watch_folder
    # Logs inside the main folder
    log_folder = os.path.join(archive_root, "ERROS")

    # Show info before starting processing
    temp_root = tk.Tk()
    temp_root.withdraw()
    info_message = f"Pasta selecionada: {watch_folder}\n"
    info_message += f"Os arquivos serão movidos para subpastas Ano/Mês dentro dela.\n"
    info_message += f"Logs de erros serão salvos em: {log_folder}\n\n"
    info_message += "Iniciando o processo de arquivamento..."
    messagebox.showinfo("Processo Iniciado", info_message)
    temp_root.destroy()

    archiver = FileArchiver(watch_folder, archive_root, log_folder)
    archiver.process_files()  # Processa e gera a mensagem de resumo interna

    # --- Preparar e Mostrar Mensagem Final ---
    # Get the summary generated by process_files
    final_message = archiver.summary_message

    # Adiciona verificação e mensagem sobre logs de falha
    log_files = []
    if os.path.exists(log_folder):
        try:
            log_files = [f for f in os.listdir(log_folder) if f.startswith(
                "archive_failures_") and f.endswith(".log")]
        except OSError:
            final_message += f"\nAviso: Não foi possível verificar a pasta de logs '{log_folder}'."

    if log_files:
        final_message += f"\nVerifique o(s) arquivo(s) de log em '{log_folder}' para detalhes sobre erros:"
        # List only the most recent few logs if there are many? Or just the latest?
        # Let's list the latest one found.
        latest_log = sorted(log_files, reverse=True)[0]
        final_message += f"\n- {latest_log}"
        if len(log_files) > 1:
            final_message += f" (e {len(log_files) - 1} outro(s))"
    elif archiver.error_count > 0:
        # If errors were counted but no log file found (e.g., logger setup failed)
        final_message += f"\nForam encontrados {archiver.error_count} erros, mas o arquivo de log pode não ter sido criado corretamente em '{log_folder}'."
    # No need for an "else" here, the summary already covers the "no errors" case.

    # Mostrar a mensagem final na janela auto-close
    show_auto_close_message(final_message, 5000)  # 15 segundos
    # --- Fim Preparar e Mostrar Mensagem Final ---


if __name__ == "__main__":
    main()

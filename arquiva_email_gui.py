import os
import shutil
import email
import logging
import re  # Importar re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# Definir constantes do arquiva_email.py
MAX_PATH_LENGTH = 255
SAFE_FILENAME_MARGIN = 10

class FileArchiver:
    # __init__ permanece o mesmo, mas remove self.last_processed_type
    def __init__(self, watch_folder, archive_root, log_folder):
        self.watch_folder = watch_folder
        self.archive_root = archive_root
        self.log_folder = log_folder
        self.setup_logger()
        # self.last_processed_type = None # Removido

    # setup_logger substituído pelo do arquiva_email.py
    def setup_logger(self):
        """Configura o logger para registrar apenas erros."""
        try:
            if not os.path.exists(self.log_folder):
                os.makedirs(self.log_folder)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            log_file = os.path.join(
                self.log_folder, f"archive_failures_{timestamp}.log") # Nome do arquivo alterado

            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.ERROR) # Nível de log definido para ERROR

            if self.logger.hasHandlers():
                self.logger.handlers.clear()

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.ERROR) # Nível do handler também definido para ERROR

            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - Arquivo: %(message)s", # Formato ajustado
                datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            # BlankLineHandler removido

        except Exception as e:
            print(f"ERRO CRÍTICO: Não foi possível configurar o logger em {self.log_folder}. Erro: {e}")
            self.logger = logging.getLogger('null')
            self.logger.addHandler(logging.NullHandler())

    # process_files adaptado para remover logging INFO e BlankLineHandler
    def process_files(self):
        if not os.path.exists(self.watch_folder):
            # Log de erro mantido
            self.logger.error(f"{self.watch_folder} - Motivo: Pasta de monitoramento não encontrada.")
            print(f"ERRO: Pasta de monitoramento não encontrada: {self.watch_folder}")
            return

        # Itera apenas pelos arquivos
        for filename in os.listdir(self.watch_folder):
            file_path = os.path.join(self.watch_folder, filename)
            if os.path.isfile(file_path):
                # Ignora .ffs_db silenciosamente
                if file_path.lower().endswith(".ffs_db"):
                    continue
                # Remove chamadas ao BlankLineHandler e last_processed_type
                self.process_file(file_path)

    # process_file adaptado para remover logging INFO
    def process_file(self, file_path):
        try:
            # Remove logger.info
            if file_path.lower().endswith(".eml"):
                self.process_eml_file(file_path)
            else:
                self.process_other_file(file_path)
        except Exception as e:
            # Log de erro mantido e adaptado
            self.logger.error(f"{file_path} - Motivo: Erro inesperado durante o processamento inicial. Detalhes: {e}")

    # process_eml_file adaptado com _parse_date e logging de erro refinado
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
                # Log de erro mantido e adaptado
                self.logger.error(f"{eml_path} - Motivo: Falha ao ler o arquivo (tentativas UTF-8 e Latin-1). Detalhes: {e}")
                return
        except Exception as e:
            # Log de erro mantido e adaptado
            self.logger.error(f"{eml_path} - Motivo: Falha ao ler o arquivo. Detalhes: {e}")
            return

        if not msg:
             # Log de erro adicionado
             self.logger.error(f"{eml_path} - Motivo: Não foi possível interpretar o conteúdo do e-mail após leitura.")
             return

        date_str = msg.get("Date")
        # Usa _parse_date (não loga mais erro aqui se falhar)
        date_obj = self._parse_date(date_str, eml_path)

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        # Chama move_file_to_archive sem 'year'
        self.move_file_to_archive(eml_path, archive_folder)

    # Adicionado _parse_date do arquiva_email.py
    def _parse_date(self, date_str, file_path_for_log):
        """Tenta analisar a string de data. Retorna datetime.now() em caso de falha."""
        if not date_str:
            return datetime.now()

        formats_to_try = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %Z",
        ]

        try:
            parsed_dt = email.utils.parsedate_to_datetime(date_str)
            if parsed_dt:
                return parsed_dt
        except Exception:
            pass

        for fmt in formats_to_try:
            try:
                cleaned_date_str = re.sub(r'\s*\([^)]*\)\s*$', '', date_str).strip()
                return datetime.strptime(cleaned_date_str, fmt)
            except ValueError:
                continue

        return datetime.now()

    # process_other_file adaptado com tratamento de erro para getmtime
    def process_other_file(self, file_path):
        try:
            modification_time = os.path.getmtime(file_path)
            date_obj = datetime.fromtimestamp(modification_time)
        except OSError as e:
             # Log de erro adicionado
             self.logger.error(f"{file_path} - Motivo: Falha ao obter data de modificação. Detalhes: {e}")
             return # Impede a movimentação

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        # Chama move_file_to_archive sem 'year'
        self.move_file_to_archive(file_path, archive_folder)

    # Adicionado _sanitize_filename do arquiva_email.py
    def _sanitize_filename(self, filename):
        """Remove ou substitui caracteres inválidos e o prefixo 'msg '."""
        sanitized = re.sub(r'^msg\s+', '', filename, flags=re.IGNORECASE)
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)
        sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)
        sanitized = sanitized.strip()
        if not sanitized:
            sanitized = "arquivo_renomeado"
        return sanitized

    # Adicionado _truncate_filename do arquiva_email.py
    def _truncate_filename(self, folder_path, filename, max_len):
        """Trunca o nome do arquivo se o caminho completo exceder max_len."""
        base, ext = os.path.splitext(filename)
        full_path = os.path.join(folder_path, filename)
        full_path_len = len(full_path)

        if full_path_len <= max_len:
            return filename

        available_len_for_base = max_len - (len(folder_path) + len(os.sep) + len(ext))

        if available_len_for_base <= 0:
             return filename # Deixa o erro ocorrer no move

        truncated_base = base[:available_len_for_base]
        truncated_filename = f"{truncated_base}{ext}"
        return truncated_filename

    # move_file_to_archive substituído pelo do arquiva_email.py
    def move_file_to_archive(self, file_path, archive_folder):
        """Move o arquivo para a pasta de destino, tratando sanitização, truncamento e duplicados."""
        archive_year_folder = os.path.dirname(archive_folder)
        try:
            if not os.path.exists(archive_year_folder):
                os.makedirs(archive_year_folder)
                print(f"Pasta {archive_year_folder} criada.")
            if not os.path.exists(archive_folder):
                os.makedirs(archive_folder)
                print(f"Pasta {archive_folder} criada.")
        except OSError as e:
            self.logger.error(f"{file_path} - Motivo: Erro ao criar pasta de destino '{archive_folder}'. Detalhes: {e}")
            return

        original_filename = os.path.basename(file_path)
        sanitized_filename = self._sanitize_filename(original_filename)
        final_filename = self._truncate_filename(archive_folder, sanitized_filename, MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN)
        destination_path = os.path.join(archive_folder, final_filename)

        counter = 1
        base, ext = os.path.splitext(final_filename)
        temp_final_filename = final_filename
        while os.path.exists(destination_path):
            new_filename_base = f"{base}_{counter}"
            potential_new_filename = f"{new_filename_base}{ext}"

            if len(os.path.join(archive_folder, potential_new_filename)) <= MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN:
                 final_filename = potential_new_filename
            else:
                 timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                 base_original_sem_contador, ext_original = os.path.splitext(temp_final_filename)
                 nome_com_timestamp = f"{base_original_sem_contador}_{timestamp}{ext_original}"
                 final_filename = self._truncate_filename(archive_folder, nome_com_timestamp, MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN)

                 if os.path.exists(os.path.join(archive_folder, final_filename)):
                     self.logger.error(f"{file_path} - Motivo: Conflito de nome irresolúvel em '{archive_folder}' após tentar adicionar contador e timestamp (arquivo duplicado: {original_filename}).")
                     return

            destination_path = os.path.join(archive_folder, final_filename)
            counter += 1

        try:
            shutil.move(file_path, destination_path)
            print(f"Arquivo {os.path.basename(destination_path)} arquivado em {archive_folder}")
        except Exception as e:
            self.logger.error(f"{file_path} - Motivo: Falha ao mover para '{destination_path}'. Detalhes: {e}")


# Classe BlankLineHandler removida

# select_folder permanece o mesmo
def select_folder():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    folder_selected = filedialog.askdirectory()
    return folder_selected

# main adaptado para remover criação desnecessária e adicionar verificação de log
def main():
    watch_folder = select_folder()
    if not watch_folder:
        print("Nenhuma pasta selecionada. Encerrando.")
        return

    archive_root = watch_folder
    log_folder = os.path.join(archive_root, "ERROS")

    # Não precisa mais criar archive_root explicitamente aqui
    # if not os.path.exists(archive_root):
    #     os.makedirs(archive_root)
    #     print(f"Pasta {archive_root} criada.")

    archiver = FileArchiver(watch_folder, archive_root, log_folder)
    archiver.process_files()
    print("\nProcessamento concluído.")

    # Adiciona verificação e mensagem sobre logs de falha
    log_files = [f for f in os.listdir(log_folder) if f.startswith("archive_failures_") and f.endswith(".log")] if os.path.exists(log_folder) else []
    if log_files:
        print(f"Verifique o arquivo de log em '{log_folder}' para detalhes sobre arquivos que não foram movidos:")
        for log_f in sorted(log_files, reverse=True):
            print(f"- {log_f}")
    elif os.path.exists(log_folder):
         print(f"Nenhum erro registrado durante a execução (verificado em '{log_folder}').")


if __name__ == "__main__":
    main()

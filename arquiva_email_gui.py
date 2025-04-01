import os
import shutil
import email
import logging
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

class FileArchiver:
    def __init__(self, watch_folder, archive_root, log_folder):
        self.watch_folder = watch_folder
        self.archive_root = archive_root
        self.log_folder = log_folder
        self.setup_logger()

    def setup_logger(self):
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)

        log_file = os.path.join(self.log_folder, "archive_errors.log")
        logging.basicConfig(
            filename=log_file,
            level=logging.ERROR,
            format="%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.logger = logging.getLogger(__name__)

    def process_files(self):
        if not os.path.exists(self.watch_folder):
            self.logger.error(f"Pasta de monitoramento não encontrada: {self.watch_folder}")
            return
        
        if not os.path.exists(self.archive_root):
            self.logger.error(f"Pasta de arquivamento não encontrada: {self.archive_root}")
            return
        
        # Iterate only through files in the watch_folder, not subfolders
        for filename in os.listdir(self.watch_folder):
            file_path = os.path.join(self.watch_folder, filename)
            if os.path.isfile(file_path):
                self.process_file(file_path)

        # Remove the call to check_and_correct_subfolders, as we're not processing subfolders
        # self.check_and_correct_subfolders(self.archive_root)

    # Removed process_folder method, as it's no longer needed

    def process_file(self, file_path):
        try:
            if file_path.lower().endswith(".eml"):
                self.process_eml_file(file_path)
            else:
                self.process_other_file(file_path)
        except Exception as e:
            self.logger.error(f"Erro ao processar o arquivo {file_path}: {e}")

    def process_eml_file(self, eml_path):
        try:
            with open(eml_path, 'r', encoding='utf-8') as f:
                msg = email.message_from_file(f)
        except UnicodeDecodeError:
            try:
                with open(eml_path, 'r', encoding='latin-1') as f:
                    msg = email.message_from_file(f)
            except Exception as e:
                self.logger.error(f"Erro ao ler o arquivo {eml_path}: {e}")
                return
        except Exception as e:
            self.logger.error(f"Erro ao ler o arquivo {eml_path}: {e}")
            return

        date_str = msg.get("Date")
        if date_str:
            try:
                # Tenta converter a data para diferentes formatos comuns
                date_obj = email.utils.parsedate_to_datetime(date_str)
                if date_obj is None:
                    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            except ValueError:
                try:
                    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %Z")
                except ValueError:
                    try:
                        date_obj = datetime.strptime(date_str, "%d %b %Y %H:%M:%S %z")
                    except ValueError:
                        try:
                            date_obj = datetime.strptime(date_str, "%d %b %Y %H:%M:%S %Z")
                        except ValueError:
                            self.logger.error(f"Não foi possível converter a data do e-mail: {date_str} no arquivo {eml_path}. Usando a data atual.")
                            date_obj = datetime.now()
        else:
            self.logger.error(f"Data não encontrada no e-mail {eml_path}. Usando a data atual.")
            date_obj = datetime.now()

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        self.move_file_to_archive(eml_path, archive_folder, year)

    def process_other_file(self, file_path):
        modification_time = os.path.getmtime(file_path)
        date_obj = datetime.fromtimestamp(modification_time)
        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        self.move_file_to_archive(file_path, archive_folder, year)

    def move_file_to_archive(self, file_path, archive_folder, year):
        archive_year_folder = os.path.dirname(archive_folder)
        if not os.path.exists(archive_year_folder):
            os.makedirs(archive_year_folder)
            print(f"Pasta {archive_year_folder} criada.")

        if not os.path.exists(archive_folder):
            os.makedirs(archive_folder)
            print(f"Pasta {archive_folder} criada.")

        filename = os.path.basename(file_path)
        destination_path = os.path.join(archive_folder, filename)

        if os.path.exists(destination_path):
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_filename = f"{os.path.splitext(filename)[0]}_{timestamp}{os.path.splitext(filename)[1]}"
            destination_path = os.path.join(archive_folder, new_filename)
            self.logger.warning(f"Arquivo {filename} já existe em {archive_folder}. Renomeando para {new_filename}")

        try:
            shutil.move(file_path, destination_path)
            print(f"Arquivo {os.path.basename(destination_path)} arquivado em {archive_folder}")
        except Exception as e:
            self.logger.error(f"Erro ao mover o arquivo {filename}: {e}")

    # Removed check_and_correct_subfolders, is_valid_year_month_folder, is_valid_year_folder, check_and_move_folder and check_and_move_file methods, as they are no longer needed

def select_folder():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    folder_selected = filedialog.askdirectory()
    return folder_selected

def main():
    watch_folder = select_folder()
    if not watch_folder:
        print("Nenhuma pasta selecionada. Encerrando.")
        return

    # Define the archive_root as the same folder of watch_folder
    archive_root = watch_folder

    log_folder = os.path.join(archive_root, "ERROS")  # Pasta para logs de erro

    if not os.path.exists(archive_root):
        os.makedirs(archive_root)
        print(f"Pasta {archive_root} criada.")

    archiver = FileArchiver(watch_folder, archive_root, log_folder)
    archiver.process_files()


if __name__ == "__main__":
    main()

import os
import shutil
import logging
from datetime import datetime
import tkinter as tk
from tkinter import filedialog


class FileMover:
    def __init__(self, root_folder, log_folder):
        self.root_folder = root_folder
        self.log_folder = log_folder
        self.setup_logger()
        self.excluded_folders = ["erros", "anos anteriores"]

    def setup_logger(self):
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_file = os.path.join(
            self.log_folder, f"move_files_log_{timestamp}.log")

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def move_files(self):
        if not os.path.exists(self.root_folder):
            self.logger.error(
                f"Pasta raiz não encontrada: {self.root_folder}")
            return

        self.logger.info(
            f"Iniciando movimentação de arquivos na pasta: {self.root_folder}")
        for root, dirs, files in os.walk(self.root_folder):
            # Exclude specific folders from processing
            dirs[:] = [d for d in dirs if d.lower() not in self.excluded_folders]

            if root == self.root_folder:
                continue  # Skip the root folder itself

            for file in files:
                source_path = os.path.join(root, file)
                destination_path = os.path.join(self.root_folder, file)

                if os.path.exists(destination_path):
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    base, ext = os.path.splitext(file)
                    new_filename = f"{base}_{timestamp}{ext}"
                    destination_path = os.path.join(
                        self.root_folder, new_filename)
                    self.logger.warning(
                        f"Arquivo duplicado: {file}. Renomeando para {new_filename}")

                try:
                    shutil.move(source_path, destination_path)
                    self.logger.info(
                        f"Arquivo movido de {source_path} para {destination_path}")
                except Exception as e:
                    self.logger.error(
                        f"Erro ao mover o arquivo {source_path}: {e}")

        self.logger.info(
            f"Finalizado a movimentação de arquivos na pasta: {self.root_folder}")
        self.remove_empty_folders()

    def remove_empty_folders(self):
        for root, dirs, _ in os.walk(self.root_folder, topdown=False):
            # Exclude specific folders from processing
            dirs[:] = [d for d in dirs if d.lower() not in self.excluded_folders]
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        self.logger.info(f"Pasta vazia removida: {dir_path}")
                except OSError as e:
                    self.logger.error(
                        f"Erro ao remover a pasta {dir_path}: {e}")


def select_folder():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    return folder_selected


def main():
    root_folder = select_folder()
    if not root_folder:
        print("Nenhuma pasta selecionada. Encerrando.")
        return

    log_folder = os.path.join(root_folder, "ERROS")

    if not os.path.exists(root_folder):
        print(f"Pasta {root_folder} não existe.")
        return

    mover = FileMover(root_folder, log_folder)
    mover.move_files()
    print("Processo concluído.")


if __name__ == "__main__":
    main()

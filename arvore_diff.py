import os
import logging
from datetime import datetime
import filecmp
import tkinter as tk
from tkinter import filedialog


class DirectoryComparator:
    def __init__(self, dir1, dir2, log_folder):
        self.dir1 = dir1
        self.dir2 = dir2
        self.log_folder = log_folder
        self.setup_logger()

    def setup_logger(self):
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_file = os.path.join(
            self.log_folder, f"directory_comparison_{timestamp}.log")

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def compare_directories(self):
        self.logger.info(f"Iniciando comparação entre: {self.dir1} e {self.dir2}")
        self._compare_recursive(self.dir1, self.dir2)
        self.logger.info(f"Comparação concluída.")

    def _compare_recursive(self, dir1, dir2):
        # Get the relative paths for logging
        relative_dir1 = os.path.relpath(dir1, self.dir1) if dir1 != self.dir1 else "."
        relative_dir2 = os.path.relpath(dir2, self.dir2) if dir2 != self.dir2 else "."

        # List items in each directory
        items1 = set(os.listdir(dir1))
        items2 = set(os.listdir(dir2))

        # Find items unique to each directory
        only_in_dir1 = items1 - items2
        only_in_dir2 = items2 - items1

        # Log unique items
        for item in only_in_dir1:
            item_path = os.path.join(relative_dir1, item)
            self.logger.warning(f"Apenas em {self.dir1}: {item_path}")
        for item in only_in_dir2:
            item_path = os.path.join(relative_dir2, item)
            self.logger.warning(f"Apenas em {self.dir2}: {item_path}")

        # Find common items
        common_items = items1 & items2

        # Compare common items
        for item in common_items:
            path1 = os.path.join(dir1, item)
            path2 = os.path.join(dir2, item)

            if os.path.isdir(path1) and os.path.isdir(path2):
                # Recurse into subdirectories
                self._compare_recursive(path1, path2)
            elif os.path.isfile(path1) and os.path.isfile(path2):
                # Compare files
                if not filecmp.cmp(path1, path2, shallow=False):
                    self.logger.warning(f"Arquivos diferentes: {os.path.join(relative_dir1, item)} e {os.path.join(relative_dir2, item)}")
            elif os.path.isdir(path1) and os.path.isfile(path2):
                self.logger.warning(f"Tipo diferente: {os.path.join(relative_dir1, item)} é pasta e {os.path.join(relative_dir2, item)} é arquivo")
            elif os.path.isfile(path1) and os.path.isdir(path2):
                self.logger.warning(f"Tipo diferente: {os.path.join(relative_dir1, item)} é arquivo e {os.path.join(relative_dir2, item)} é pasta")

def select_folder():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    folder_selected = filedialog.askdirectory()
    return folder_selected

def main():
    print("Selecione a primeira pasta para comparação:")
    dir1 = select_folder()
    if not dir1:
        print("Nenhuma pasta selecionada para a primeira comparação. Encerrando.")
        return

    print("Selecione a segunda pasta para comparação:")
    dir2 = select_folder()
    if not dir2:
        print("Nenhuma pasta selecionada para a segunda comparação. Encerrando.")
        return
    
    print("Selecione a pasta para salvar os logs:")
    log_folder = select_folder()
    if not log_folder:
        print("Nenhuma pasta selecionada para salvar os logs. Encerrando.")
        return

    if not os.path.exists(dir1):
        print(f"Pasta {dir1} não existe.")
        return
    
    if not os.path.exists(dir2):
        print(f"Pasta {dir2} não existe.")
        return

    comparator = DirectoryComparator(dir1, dir2, log_folder)
    comparator.compare_directories()
    print("Processo concluído.")

if __name__ == "__main__":
    main()

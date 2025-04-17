import os
import tkinter as tk
from tkinter import filedialog, messagebox
import logging
from datetime import datetime

class FolderComparer:
    def __init__(self):
        self.folder1 = None
        self.folder2 = None
        self.setup_logger()
        
    def setup_logger(self):
        """Configura o sistema de logging para registrar erros."""
        self.log_folder = None  # Será definido após selecionar a primeira pasta
        self.logger = logging.getLogger("folder_comparer")
        self.logger.setLevel(logging.ERROR)
        # Handler será adicionado após definir a pasta de log
        
    def configure_log_folder(self):
        """Configura a pasta de log após a seleção da primeira pasta."""
        if not self.folder1:
            return
            
        self.log_folder = os.path.join(self.folder1, "ERROS")
        if not os.path.exists(self.log_folder):
            try:
                os.makedirs(self.log_folder)
            except Exception as e:
                print(f"ERRO: Não foi possível criar a pasta de log: {e}")
                return
                
        # Evita duplicação de handlers
        if self.logger.handlers:
            self.logger.handlers.clear()
            
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_file = os.path.join(self.log_folder, f"comparison_failures_{timestamp}.log")
        
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"ERRO: Não foi possível configurar o logger: {e}")
            # Adiciona um handler nulo para evitar erros
            self.logger.addHandler(logging.NullHandler())
    
    def select_folders(self):
        """Solicita ao usuário selecionar duas pastas via interface gráfica."""
        root = tk.Tk()
        root.withdraw()  # Oculta a janela principal
        
        # Seleciona a primeira pasta
        self.folder1 = filedialog.askdirectory(title="Selecione a primeira pasta")
        if not self.folder1:
            messagebox.showinfo("Operação cancelada", "Seleção da primeira pasta cancelada pelo usuário.")
            return False
            
        # Configura o logger após selecionar a primeira pasta
        self.configure_log_folder()
        
        # Seleciona a segunda pasta
        self.folder2 = filedialog.askdirectory(title="Selecione a segunda pasta")
        if not self.folder2:
            messagebox.showinfo("Operação cancelada", "Seleção da segunda pasta cancelada pelo usuário.")
            return False
            
        return True
    
    def get_files_in_folder(self, folder_path):
        """Obtém a lista de arquivos em uma pasta e suas subpastas."""
        files = []
        try:
            for root, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    # Ignora arquivos de sistema como .ffs_db
                    if filename.lower() == ".ffs_db":
                        continue
                    # Caminho relativo à pasta raiz para comparação justa
                    rel_path = os.path.relpath(os.path.join(root, filename), folder_path)
                    files.append(rel_path)
        except Exception as e:
            self.logger.error(f"Erro ao listar arquivos em {folder_path}: {e}")
        
        return files
    
    def compare_folders(self):
        """Compara os arquivos entre as duas pastas e gera um relatório."""
        if not self.folder1 or not self.folder2:
            return "Erro: Pastas não selecionadas."
            
        print(f"Comparando pastas:\n1: {self.folder1}\n2: {self.folder2}")
        
        try:
            # Obtém listas de arquivos (caminhos relativos)
            files1 = set(self.get_files_in_folder(self.folder1))
            files2 = set(self.get_files_in_folder(self.folder2))
            
            # Identifica arquivos exclusivos de cada pasta
            only_in_folder1 = files1 - files2
            only_in_folder2 = files2 - files1
            
            # Gera o relatório
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report = [
                f"RELATÓRIO DE COMPARAÇÃO DE PASTAS - {timestamp}",
                f"\nPasta 1: {self.folder1}",
                f"Pasta 2: {self.folder2}",
                f"\nTotal de arquivos na Pasta 1: {len(files1)}",
                f"Total de arquivos na Pasta 2: {len(files2)}",
                f"\n{'=' * 80}",
                f"\nARQUIVOS EXCLUSIVOS DA PASTA 1 ({len(only_in_folder1)} arquivos):",
                f"{'=' * 80}"
            ]
            
            if only_in_folder1:
                for file in sorted(only_in_folder1):
                    report.append(file)
            else:
                report.append("Nenhum arquivo exclusivo encontrado.")
                
            report.extend([
                f"\n{'=' * 80}",
                f"\nARQUIVOS EXCLUSIVOS DA PASTA 2 ({len(only_in_folder2)} arquivos):",
                f"{'=' * 80}"
            ])
            
            if only_in_folder2:
                for file in sorted(only_in_folder2):
                    report.append(file)
            else:
                report.append("Nenhum arquivo exclusivo encontrado.")
                
            report.extend([
                f"\n{'=' * 80}",
                f"\nRESUMO:",
                f"Arquivos em comum: {len(files1.intersection(files2))}",
                f"Arquivos exclusivos da Pasta 1: {len(only_in_folder1)}",
                f"Arquivos exclusivos da Pasta 2: {len(only_in_folder2)}",
                f"{'=' * 80}"
            ])
            
            return "\n".join(report)
            
        except Exception as e:
            error_msg = f"Erro durante a comparação: {e}"
            self.logger.error(error_msg)
            return f"ERRO NA COMPARAÇÃO: {error_msg}"
    
    def save_report(self, report_content):
        """Salva o relatório em um arquivo de texto na primeira pasta."""
        if not self.folder1:
            return False
            
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        report_filename = os.path.join(self.folder1, f"comparacao_pastas_{timestamp}.txt")
        
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"Relatório salvo em: {report_filename}")
            return report_filename
        except Exception as e:
            error_msg = f"Erro ao salvar o relatório: {e}"
            self.logger.error(error_msg)
            print(f"ERRO: {error_msg}")
            return False
    
    def run(self):
        """Executa o fluxo completo de comparação de pastas."""
        print("Iniciando comparação de pastas...")
        
        # Solicita as pastas
        if not self.select_folders():
            return
            
        # Realiza a comparação
        report = self.compare_folders()
        
        # Salva o relatório
        report_path = self.save_report(report)
        
        if report_path:
            messagebox.showinfo("Comparação concluída", 
                               f"Relatório de comparação salvo em:\n{report_path}")
        else:
            messagebox.showerror("Erro", 
                                "Não foi possível salvar o relatório. Verifique o log de erros.")

if __name__ == "__main__":
    comparer = FolderComparer()
    comparer.run()

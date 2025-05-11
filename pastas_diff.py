import os
import tkinter as tk_module # Alias para evitar conflitos
from tkinter import filedialog, messagebox
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, List

# --- Constantes ---
LOG_FOLDER_NAME = "ERROS"
LOG_FILENAME_PREFIX = "comparison_failures_"
# --- Fim Constantes ---

class FolderComparer:
    """
    Compara o conteúdo de duas pastas (incluindo subpastas) e gera um relatório
    listando os arquivos exclusivos de cada uma.
    """
    def __init__(self):
        self.folder1: Optional[Path] = None
        self.folder2: Optional[Path] = None
        self.log_file_path: Optional[Path] = None # Caminho completo do arquivo de log
        self.logger: logging.Logger = self._setup_initial_logger()

    def _setup_initial_logger(self) -> logging.Logger:
        """Configura o logger inicialmente sem um file handler."""
        logger = logging.getLogger(f"{__name__}.FolderComparer.{id(self)}")
        logger.setLevel(logging.ERROR)
        logger.propagate = False # Evita logs duplicados se um root logger estiver configurado
        if not logger.hasHandlers(): # Adiciona NullHandler para evitar warnings "No handlers found"
            logger.addHandler(logging.NullHandler())
        return logger

    def _configure_file_logging(self) -> None:
        """
        Configura o file handler para o logger.
        Este método deve ser chamado após self.folder1 ser definido.
        """
        if not self.folder1:
            print("ERRO INTERNO: Tentativa de configurar log de arquivo sem a primeira pasta definida.")
            return

        log_dir = self.folder1 / LOG_FOLDER_NAME
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"AVISO: Não foi possível criar a pasta de log '{log_dir}': {e}. Logs de erro não serão salvos em arquivo.")
            return # Não configura o file handler se a pasta não puder ser criada

        # Remove handlers anteriores (especialmente o NullHandler)
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            if hasattr(handler, 'close'): # Fecha o handler se possível
                handler.close()

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.log_file_path = log_dir / f"{LOG_FILENAME_PREFIX}{timestamp}.log"

        try:
            file_handler = logging.FileHandler(str(self.log_file_path), encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        except Exception as e: # Captura qualquer exceção durante a configuração do handler
            print(f"AVISO: Não foi possível configurar o logger para o arquivo '{self.log_file_path}': {e}. "
                  "Logs de erro podem não ser salvos.")
            # Se a configuração do FileHandler falhar, readiciona o NullHandler
            if not self.logger.hasHandlers():
                self.logger.addHandler(logging.NullHandler())

    def select_folders(self) -> bool:
        """Solicita ao usuário selecionar duas pastas via interface gráfica."""
        root = tk_module.Tk()
        root.withdraw()

        folder1_str = filedialog.askdirectory(title="Selecione a Primeira Pasta (Base para Logs e Relatório)")
        if not folder1_str:
            messagebox.showinfo("Operação Cancelada", "Seleção da primeira pasta cancelada.")
            root.destroy()
            return False
        self.folder1 = Path(folder1_str)

        # Configura o logging de arquivo agora que folder1 é conhecido
        self._configure_file_logging()

        folder2_str = filedialog.askdirectory(title="Selecione a Segunda Pasta")
        if not folder2_str:
            messagebox.showinfo("Operação Cancelada", "Seleção da segunda pasta cancelada.")
            root.destroy()
            return False
        self.folder2 = Path(folder2_str)

        root.destroy()
        return True

    def _get_files_in_folder(self, folder_path: Path) -> Set[str]:
        """Obtém um conjunto de caminhos de arquivo relativos em uma pasta e suas subpastas."""
        relative_files: Set[str] = set()
        if not folder_path.is_dir(): # Verifica se o caminho é um diretório válido
            self.logger.error(f"A pasta fornecida não existe ou não é um diretório: {folder_path}")
            return relative_files

        try:
            # os.walk é mantido pela sua robustez e conveniência com os.path.relpath
            for root, _, filenames in os.walk(str(folder_path)):
                for filename in filenames:
                    if filename.lower() == ".ffs_db": # Exclusão específica
                        continue
                    
                    full_path_str = os.path.join(root, filename)
                    try:
                        # os.path.relpath para obter o caminho relativo
                        rel_path_str = os.path.relpath(full_path_str, str(folder_path))
                        # Normaliza separadores para consistência entre OS
                        relative_files.add(rel_path_str.replace(os.sep, '/'))
                    except ValueError as e_relpath: # Caso raro, mas possível
                        self.logger.error(f"Erro ao calcular caminho relativo para {full_path_str} a partir de {folder_path}: {e_relpath}")
        except Exception as e_walk: # Captura erros durante o próprio os.walk
            self.logger.error(f"Erro ao listar arquivos em {folder_path}: {e_walk}")
        
        return relative_files

    def compare_folders(self) -> str:
        """Compara os arquivos entre as duas pastas e gera uma string de relatório."""
        if not self.folder1 or not self.folder2:
            # Esta verificação deve ser feita pelo método chamador (run)
            return "ERRO: As duas pastas não foram selecionadas."
            
        print(f"Comparando pastas:\nPasta 1: {self.folder1}\nPasta 2: {self.folder2}")
        
        try:
            files1 = self._get_files_in_folder(self.folder1)
            files2 = self._get_files_in_folder(self.folder2)
            
            only_in_folder1 = sorted(list(files1 - files2)) # Ordena para saída consistente
            only_in_folder2 = sorted(list(files2 - files1)) # Ordena
            common_files = files1.intersection(files2)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_lines: List[str] = [
                f"RELATÓRIO DE COMPARAÇÃO DE PASTAS - {timestamp}",
                f"\nPasta 1: {self.folder1}",
                f"Pasta 2: {self.folder2}",
                f"\nTotal de arquivos na Pasta 1 (considerados): {len(files1)}",
                f"Total de arquivos na Pasta 2 (considerados): {len(files2)}",
                f"\n{'=' * 80}",
                f"\nARQUIVOS EXCLUSIVOS DA PASTA 1 ({len(only_in_folder1)} arquivos):",
                f"{'=' * 80}"
            ]
            
            if only_in_folder1:
                report_lines.extend(only_in_folder1)
            else:
                report_lines.append("Nenhum arquivo exclusivo encontrado.")
                
            report_lines.extend([
                f"\n{'=' * 80}",
                f"\nARQUIVOS EXCLUSIVOS DA PASTA 2 ({len(only_in_folder2)} arquivos):",
                f"{'=' * 80}"
            ])
            
            if only_in_folder2:
                report_lines.extend(only_in_folder2)
            else:
                report_lines.append("Nenhum arquivo exclusivo encontrado.")
                
            report_lines.extend([
                f"\n{'=' * 80}",
                f"\nRESUMO:",
                f"Arquivos em comum: {len(common_files)}",
                f"Arquivos exclusivos da Pasta 1: {len(only_in_folder1)}",
                f"Arquivos exclusivos da Pasta 2: {len(only_in_folder2)}",
                f"{'=' * 80}"
            ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            error_msg = f"Erro durante a comparação: {e}"
            self.logger.error(error_msg)
            print(f"ERRO DURANTE COMPARAÇÃO: {error_msg}") # Feedback imediato
            return f"ERRO NA COMPARAÇÃO: {error_msg}. Verifique o console ou o arquivo de log (se configurado)."

    def save_report(self, report_content: str) -> Optional[Path]:
        """Salva o relatório em um arquivo de texto na primeira pasta selecionada."""
        if not self.folder1:
            print("ERRO: A primeira pasta não foi selecionada, não é possível salvar o relatório.")
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # O relatório é salvo diretamente na folder1, não na subpasta de logs
        report_file_path = self.folder1 / f"comparacao_pastas_{timestamp}.txt"
        
        try:
            with report_file_path.open('w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"Relatório salvo em: {report_file_path}")
            return report_file_path
        except (IOError, OSError) as e: # Captura exceções de I/O
            error_msg = f"Erro ao salvar o relatório em '{report_file_path}': {e}"
            self.logger.error(error_msg)
            print(f"ERRO: {error_msg}") # Feedback imediato
            return None

    def run(self) -> None:
        """Executa o fluxo completo de seleção de pastas, comparação e salvamento do relatório."""
        print("Iniciando comparação de pastas...")
        
        if not self.select_folders():
            print("Seleção de pastas não concluída ou cancelada. Encerrando.")
            return
            
        # self.folder1 e self.folder2 devem estar definidos se select_folders retornou True
        if not self.folder1 or not self.folder2: # Verificação de segurança adicional
            messagebox.showerror("Erro", "Ambas as pastas devem ser selecionadas para comparação.")
            return

        report_content = self.compare_folders()
        
        if report_content.startswith("ERRO NA COMPARAÇÃO:"):
            messagebox.showerror("Erro na Comparação", report_content)
            if self.log_file_path:
                 messagebox.showinfo("Log de Erros", f"Detalhes adicionais podem estar no arquivo de log: {self.log_file_path}")
            return

        saved_report_path = self.save_report(report_content)
        
        if saved_report_path:
            messagebox.showinfo("Comparação Concluída", 
                               f"Relatório de comparação salvo em:\n{saved_report_path}")
        else:
            messagebox.showerror("Erro ao Salvar Relatório", 
                                "Não foi possível salvar o relatório. Verifique o console para erros.")
            if self.log_file_path: # Informa sobre o log de erros se o salvamento do relatório falhou
                 messagebox.showinfo("Log de Erros", f"Detalhes do erro de salvamento podem estar no arquivo de log: {self.log_file_path}")

if __name__ == "__main__":
    comparer = FolderComparer()
    comparer.run()

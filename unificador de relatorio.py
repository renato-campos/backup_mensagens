import tkinter as tk_module  # Alias to avoid conflict
from tkinter import filedialog
import markdown  # Importa a biblioteca markdown
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# --- Constantes ---
LOG_FOLDER_NAME = "LOGS_UNIFICADOR"
LOG_FILENAME_PREFIX = "unificador_report_log_"
HTML_STYLE = """
<style>
  body { font-family: sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: auto; }
  h2 { border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-top: 30px; }
  pre { background-color: #f4f4f4; padding: 15px; border: 1px solid #ddd; border-radius: 4px; overflow-x: auto; }
  code { font-family: monospace; }
  hr { border: 0; height: 1px; background: #ddd; margin: 20px 0; }
</style>
"""
# --- Fim Constantes ---


class ReportCombiner:
    """
    Combina arquivos .txt de uma pasta em um único arquivo HTML,
    tratando o conteúdo dos .txt como Markdown.
    """

    def __init__(self, folder_path_str: str):
        self.folder_path: Path = Path(folder_path_str).resolve()
        self.log_folder_path: Path = self.folder_path / LOG_FOLDER_NAME
        self.logger: logging.Logger = self._setup_logger()
        self.output_html_path: Optional[Path] = None

    def _setup_logger(self) -> logging.Logger:
        """Configura o logger para o processo de combinação."""
        try:
            self.log_folder_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Se não puder criar a pasta de log, imprime no console e continua sem log de arquivo
            print(f"AVISO: Não foi possível criar a pasta de log '{self.log_folder_path}': {e}. "
                  "Logs não serão salvos em arquivo.")
            # Configura um logger que só imprime no console em caso de erro
            logger = logging.getLogger(
                f"{__name__}.ReportCombiner.NoFile.{id(self)}")
            logger.setLevel(logging.INFO)
            if not logger.hasHandlers():  # Evita adicionar handlers múltiplos
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s'))
                logger.addHandler(console_handler)
            return logger

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_file = self.log_folder_path / \
            f"{LOG_FILENAME_PREFIX}{timestamp}.log"

        logger = logging.getLogger(f"{__name__}.ReportCombiner.{id(self)}")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if logger.hasHandlers():
            logger.handlers.clear()

        try:
            file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(
                f"ERRO CRÍTICO: Não foi possível configurar o logger para o arquivo {log_file}. Erro: {e}")
            if not logger.hasHandlers():
                # Evita falhas se o logger for usado
                logger.addHandler(logging.NullHandler())
        return logger

    def combine_txt_to_html_content(self) -> Tuple[Optional[str], List[str]]:
        """
        Lê arquivos .txt, combina seu conteúdo como Markdown.

        Returns:
            Uma tupla contendo a string Markdown combinada (ou None em caso de falha grave)
            e uma lista dos nomes dos arquivos .txt encontrados.
        """
        txt_files_found: List[str] = []
        combined_markdown_content = ""

        self.logger.info(
            f"Procurando por arquivos .txt em: {self.folder_path}")

        # Coleta e ordena os arquivos para processamento consistente
        try:
            # Filtra e ordena os arquivos .txt
            files_to_process = sorted(
                [item for item in self.folder_path.iterdir() if item.is_file()
                 and item.suffix.lower() == ".txt"]
            )
        except OSError as e:
            self.logger.error(
                f"Erro ao listar arquivos na pasta '{self.folder_path}': {e}")
            return None, txt_files_found

        for file_path in files_to_process:
            txt_files_found.append(file_path.name)
            self.logger.info(f"Processando: {file_path.name}")

            # Título Markdown
            combined_markdown_content += f"## {file_path.name}\n\n"

            try:
                encodings_to_try = ['utf-8', 'latin-1', 'cp1252']
                file_content = None
                last_exception: Optional[Exception] = None

                for enc in encodings_to_try:
                    try:
                        with file_path.open('r', encoding=enc) as f:
                            file_content = f.read()
                        self.logger.info(
                            f"Lido '{file_path.name}' com sucesso usando {enc}.")
                        break
                    except UnicodeDecodeError as e:
                        last_exception = e
                        continue
                    except Exception as read_err:  # Outros erros de leitura
                        last_exception = read_err
                        self.logger.warning(
                            f"Erro ao ler '{file_path.name}' com {enc}: {read_err}")
                        break  # Interrompe tentativas para este arquivo se um erro não-Unicode ocorrer

                if file_content is not None:
                    combined_markdown_content += file_content + \
                        "\n\n---\n\n"  # Conteúdo e separador
                else:
                    error_msg = f"*Não foi possível ler o conteúdo de {file_path.name}. Último erro: {last_exception}*"
                    self.logger.error(
                        f"Falha ao ler '{file_path.name}' após todas as tentativas. Último erro: {last_exception}")
                    combined_markdown_content += f"{error_msg}\n\n---\n\n"

            except Exception as e:  # Erros inesperados durante o processamento do arquivo
                error_msg = f"*Erro inesperado ao processar {file_path.name}: {e}*"
                self.logger.error(
                    f"Erro inesperado ao processar '{file_path.name}': {e}")
                combined_markdown_content += f"{error_msg}\n\n---\n\n"

        return combined_markdown_content, txt_files_found

    def generate_html_report(self, markdown_content: str) -> str:
        """Converte conteúdo Markdown para HTML e o envolve em uma estrutura HTML completa."""
        self.logger.info("Convertendo conteúdo Markdown para HTML...")
        try:
            # Usa extensões como 'fenced_code' para blocos de código e 'tables' para tabelas
            html_body_content = markdown.markdown(markdown_content, extensions=[
                                                  'fenced_code', 'tables', 'nl2br'])
        except Exception as md_err:
            self.logger.error(
                f"Erro durante a conversão de Markdown para HTML: {md_err}")
            # Retorna um corpo HTML de erro se a conversão falhar
            html_body_content = f"<p><strong>Erro ao renderizar o conteúdo Markdown:</strong> {md_err}</p>"

        full_html_content = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de {self.folder_path.name}</title>
    {HTML_STYLE}
</head>
<body>
{html_body_content}
</body>
</html>
"""
        return full_html_content

    def save_html_report(self, html_content: str) -> bool:
        """Salva o conteúdo HTML em um arquivo."""
        output_filename = f"Relatório de {self.folder_path.name}.html"
        self.output_html_path = self.folder_path / output_filename

        self.logger.info(
            f"Escrevendo o arquivo HTML combinado em: {self.output_html_path}")
        try:
            with self.output_html_path.open('w', encoding='utf-8') as outfile:
                outfile.write(html_content)
            self.logger.info(
                f"Arquivo HTML combinado salvo com sucesso: {self.output_html_path}")
            return True
        except (IOError, OSError) as e:
            self.logger.error(
                f"Erro ao salvar o arquivo HTML '{self.output_html_path}': {e}")
            return False

    def run(self) -> None:
        """Executa o fluxo completo de combinação e geração de relatório HTML."""
        self.logger.info(
            f"Iniciando combinação de relatórios para a pasta: {self.folder_path}")

        if not self.folder_path.is_dir():
            self.logger.error(
                f"O caminho fornecido não é uma pasta válida: {self.folder_path}")
            messagebox.showerror(
                "Erro de Pasta", f"A pasta selecionada não existe ou não é acessível:\n{self.folder_path}")
            return

        try:
            combined_markdown, txt_files = self.combine_txt_to_html_content()

            if combined_markdown is None:  # Falha grave ao listar arquivos
                messagebox.showerror(
                    "Erro de Processamento", f"Não foi possível processar os arquivos na pasta '{self.folder_path}'. Verifique os logs.")
                return

            if not txt_files:
                self.logger.info(
                    "Nenhum arquivo .txt encontrado na pasta selecionada.")
                messagebox.showinfo(
                    "Nenhum Arquivo", "Nenhum arquivo .txt encontrado na pasta selecionada.")
                return

            full_html = self.generate_html_report(combined_markdown)

            if self.save_html_report(full_html) and self.output_html_path:
                success_msg = f"Arquivos .txt combinados e salvos como HTML com sucesso!\n\nO arquivo de saída é:\n{self.output_html_path}"
                self.logger.info(success_msg)
                messagebox.showinfo("Concluído", success_msg)
            else:
                error_msg = f"Falha ao salvar o relatório HTML. Verifique os logs em '{self.log_folder_path}'."
                self.logger.error(error_msg)
                messagebox.showerror("Erro ao Salvar", error_msg)

        except ImportError:
            error_msg = "Erro: A biblioteca 'markdown' não está instalada.\nPor favor, instale-a executando: pip install markdown"
            self.logger.critical(error_msg)  # Erro crítico
            print(error_msg)  # Também no console para visibilidade imediata
            messagebox.showerror("Dependência Faltando", error_msg)
        except Exception as e:
            error_msg = f"Ocorreu um erro inesperado durante a execução: {e}"
            self.logger.exception(error_msg)  # Loga a exceção com stack trace
            messagebox.showerror("Erro Inesperado", error_msg)


def main_gui_flow():
    """Controla o fluxo da GUI para seleção de pasta e execução do combinador."""
    root = tk_module.Tk()
    root.withdraw()

    print("Por favor, selecione a pasta contendo os arquivos .txt para unificar:")
    folder_path_str = filedialog.askdirectory(
        title="Selecione a pasta com os arquivos .txt")

    if not folder_path_str:
        print("Nenhuma pasta selecionada. Saindo...")
        messagebox.showinfo("Cancelado", "Nenhuma pasta selecionada.")
        root.destroy()
        return

    print(f"Pasta selecionada: {folder_path_str}")
    root.destroy()  # Destruir a janela raiz do Tkinter após a seleção

    combiner = ReportCombiner(folder_path_str)
    combiner.run()


if __name__ == "__main__":
    main_gui_flow()

import re
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Tuple, List, Set
import logging
from datetime import datetime
import markdown  # Necessário para ReportCombiner

# --- Constantes ---
ICON_PATH = 'imagens/msg.ico'
REPORT_FILENAME_TEMPLATE = "relatorio_verificacao_{}.txt"

# --- Constantes para ReportCombiner ---
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


def selecionar_pasta() -> None:
    """Abre um diálogo para selecionar uma pasta e atualiza o campo de entrada."""
    pasta_selecionada = filedialog.askdirectory(title="Selecione a pasta")
    if pasta_selecionada:
        entry_pasta.delete(0, tk.END)
        entry_pasta.insert(0, pasta_selecionada)

# --- Classe ReportCombiner (integrada de unificador_de_relatorio.py) ---


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
        logger_name = f"{__name__}.ReportCombiner.{id(self)}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        if logger.hasHandlers():
            logger.handlers.clear()

        log_file_configured = False
        try:
            self.log_folder_path.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            log_file = self.log_folder_path / \
                f"{LOG_FILENAME_PREFIX}{timestamp}.log"

            try:
                file_handler = logging.FileHandler(
                    str(log_file), encoding='utf-8')
                formatter = logging.Formatter(
                    '%(asctime)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                log_file_configured = True
            except Exception as e_fh:
                print(f"ERRO: Não foi possível configurar o logger para o arquivo '{log_file}': {e_fh}. "
                      "Logs de arquivo não estarão disponíveis.")
        except OSError as e_dir:
            print(f"AVISO: Não foi possível criar a pasta de log '{self.log_folder_path}': {e_dir}. "
                  "Logs de arquivo não estarão disponíveis.")

        if not log_file_configured and not logger.hasHandlers():
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(console_handler)
            # print(f"INFO: Logger '{logger_name}' configurado para saída no console pois o log em arquivo falhou.")

        return logger

    def combine_txt_to_html_content(self) -> tuple[Optional[str], List[str]]:
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

        try:
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
                    except Exception as read_err:
                        last_exception = read_err
                        self.logger.warning(
                            f"Erro ao ler '{file_path.name}' com {enc}: {read_err}")
                        break
                if file_content is not None:
                    combined_markdown_content += file_content + "\n\n---\n\n"
                else:
                    error_msg = f"*Não foi possível ler o conteúdo de {file_path.name}. Último erro: {last_exception}*"
                    self.logger.error(
                        f"Falha ao ler '{file_path.name}' após todas as tentativas. Último erro: {last_exception}")
                    combined_markdown_content += f"{error_msg}\n\n---\n\n"
            except Exception as e:
                error_msg = f"*Erro inesperado ao processar {file_path.name}: {e}*"
                self.logger.error(
                    f"Erro inesperado ao processar '{file_path.name}': {e}")
                combined_markdown_content += f"{error_msg}\n\n---\n\n"
        return combined_markdown_content, txt_files_found

    def generate_html_report(self, markdown_content: str) -> str:
        """Converte conteúdo Markdown para HTML e o envolve em uma estrutura HTML completa."""
        self.logger.info("Convertendo conteúdo Markdown para HTML...")
        try:
            html_body_content = markdown.markdown(markdown_content, extensions=[
                                                  'fenced_code', 'tables', 'nl2br'])
        except Exception as md_err:
            self.logger.error(
                f"Erro durante a conversão de Markdown para HTML: {md_err}")
            html_body_content = f"<p><strong>Erro ao renderizar o conteúdo Markdown:</strong> {md_err}</p>"
        full_html_content = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Consolidado de {self.folder_path.name}</title>
    {HTML_STYLE}
</head>
<body>
{html_body_content}
</body>
</html>"""
        return full_html_content

    def save_html_report(self, html_content: str) -> bool:
        """Salva o conteúdo HTML em um arquivo."""
        output_filename = f"Relatorio_{self.folder_path.name}.html"
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
            if combined_markdown is None:
                messagebox.showerror(
                    "Erro de Processamento", f"Não foi possível processar os arquivos na pasta '{self.folder_path}'. Verifique os logs.")
                return
            if not txt_files:
                self.logger.info(
                    "Nenhum arquivo .txt encontrado na pasta selecionada para unificação.")
                messagebox.showinfo(
                    "Unificação: Nenhum Arquivo", "Nenhum arquivo .txt encontrado na pasta para unificação.")
                return
            full_html = self.generate_html_report(combined_markdown)
            if self.save_html_report(full_html) and self.output_html_path:
                # Excluir os arquivos .txt originais
                deleted_files_count = 0
                deletion_errors = []
                for txt_filename in txt_files:
                    try:
                        file_to_delete = self.folder_path / txt_filename
                        file_to_delete.unlink()
                        self.logger.info(
                            f"Arquivo .txt original excluído: {file_to_delete}")
                        deleted_files_count += 1
                    except OSError as e_del:
                        self.logger.error(
                            f"Erro ao excluir o arquivo .txt original '{txt_filename}': {e_del}")
                        deletion_errors.append(txt_filename)

                success_msg = f"Relatórios .txt unificados e salvos como HTML com sucesso!\n\nO arquivo de saída é:\n{self.output_html_path}\n\n{deleted_files_count} arquivo(s) .txt original(is) foi(ram) excluído(s)."
                if deletion_errors:
                    success_msg += f"\n\nFalha ao excluir os seguintes arquivos .txt: {', '.join(deletion_errors)}. Verifique os logs."
                self.logger.info(success_msg)
                messagebox.showinfo("Unificação Concluída", success_msg)
            else:
                error_msg = f"Falha ao salvar o relatório HTML unificado. Verifique os logs em '{self.log_folder_path}'."
                self.logger.error(error_msg)
                messagebox.showerror("Unificação: Erro ao Salvar", error_msg)
        except ImportError:
            error_msg = "Erro: A biblioteca 'markdown' não está instalada.\nPor favor, instale-a executando: pip install markdown"
            self.logger.critical(error_msg)
            print(error_msg)
            messagebox.showerror("Unificação: Dependência Faltando", error_msg)
        except Exception as e:
            error_msg = f"Ocorreu um erro inesperado durante a unificação: {e}"
            self.logger.exception(error_msg)
            messagebox.showerror("Unificação: Erro Inesperado", error_msg)

# --- Funções do contador_mensagens ---


def _validar_entradas(pasta_str: str, inicio_str: str, fim_str: str) -> Tuple[Optional[Path], Optional[int], Optional[int], Optional[str]]:
    """Valida as entradas do usuário para pasta, número inicial e final."""
    if not pasta_str:
        return None, None, None, "O caminho da pasta não pode estar vazio."

    pasta_path = Path(pasta_str)
    if not pasta_path.is_dir():
        return None, None, None, f"A pasta selecionada não existe: {pasta_str}"

    try:
        inicio = int(inicio_str)
        fim = int(fim_str)
    except ValueError:
        return None, None, None, "Os valores inicial e final devem ser números inteiros."

    if inicio > fim:
        return None, None, None, "O número inicial deve ser menor ou igual ao número final."

    return pasta_path, inicio, fim, None


def _extrair_numero_inicial(nome_arquivo: str) -> Optional[int]:
    """Extrai um número do início do nome do arquivo usando regex."""
    match = re.match(r'^(\d+)', nome_arquivo)
    if match:
        return int(match.group(1))
    return None


def _processar_arquivos_da_pasta(pasta: Path, inicio: int, fim: int) -> Tuple[Set[int], List[str], List[int]]:
    """Processa os arquivos na pasta para encontrar números e categorizá-los."""
    numeros_encontrados: Set[int] = set()
    arquivos_sem_numero: List[str] = []
    numeros_fora_intervalo: List[int] = []

    for item_path in pasta.iterdir():
        if item_path.is_file():
            nome_arquivo = item_path.name
            numero = _extrair_numero_inicial(nome_arquivo)

            if numero is not None:
                numeros_encontrados.add(numero)
                if not (inicio <= numero <= fim):
                    numeros_fora_intervalo.append(numero)
            else:
                arquivos_sem_numero.append(nome_arquivo)

    return numeros_encontrados, arquivos_sem_numero, sorted(numeros_fora_intervalo)


def _identificar_numeros_faltantes(inicio: int, fim: int, numeros_encontrados: Set[int]) -> List[int]:
    """Identifica os números faltantes no intervalo especificado."""
    return [num for num in range(inicio, fim + 1) if num not in numeros_encontrados]


def _formatar_lista_para_relatorio(titulo: str, itens: List, mensagem_vazio: str) -> List[str]:
    """Formata uma lista de itens para inclusão no relatório."""
    linhas_relatorio = [f"\n{titulo}:"]
    if itens:
        if isinstance(itens[0], int):  # Para listas de números
            linhas_relatorio.append(", ".join(map(str, itens)))
        else:  # Para listas de nomes de arquivos
            linhas_relatorio.extend(itens)
    else:
        linhas_relatorio.append(mensagem_vazio)
    return linhas_relatorio


def _gerar_conteudo_relatorio(
    pasta: Path,
    inicio: int,
    fim: int,
    numeros_faltantes: List[int],
    numeros_fora_intervalo: List[int],
    arquivos_sem_numero: List[str]
) -> str:
    """Gera o conteúdo textual do relatório."""
    relatorio = [
        "=== RELATÓRIO DE VERIFICAÇÃO ===",
        f"Pasta analisada: {pasta}",
        f"Intervalo verificado: {inicio} a {fim}",
    ]

    relatorio.extend(_formatar_lista_para_relatorio(
        "Números faltantes no intervalo",
        numeros_faltantes,
        "Nenhum número faltante encontrado."
    ))
    relatorio.extend(_formatar_lista_para_relatorio(
        "Números encontrados fora do intervalo",
        numeros_fora_intervalo,
        "Nenhum número encontrado fora do intervalo."
    ))
    relatorio.extend(_formatar_lista_para_relatorio(
        "Arquivos que não começam com números",
        arquivos_sem_numero,
        "Nenhum arquivo encontrado sem número no início."
    ))

    return "\n".join(relatorio)


def _salvar_relatorio(pasta_base: Path, nome_pasta_analisada: str, conteudo_relatorio: str) -> Optional[Path]:
    """Salva o relatório em um arquivo .txt na pasta analisada."""
    try:
        nome_arquivo_relatorio = REPORT_FILENAME_TEMPLATE.format(
            nome_pasta_analisada)  # Mantém o nome da pasta analisada no nome do arquivo
        caminho_relatorio = pasta_base.parent / \
            nome_arquivo_relatorio  # Salva na pasta pai
        with open(caminho_relatorio, 'w', encoding='utf-8') as f:
            f.write(conteudo_relatorio)
        return caminho_relatorio
    except IOError as e:
        messagebox.showerror(
            "Erro ao Salvar", f"Não foi possível salvar o relatório:\n{e}")
        return None


def verificar_arquivos() -> None:
    """Função principal para verificar arquivos, chamada pelo botão da GUI."""
    pasta_str = entry_pasta.get()
    inicio_str = entry_inicio.get()
    fim_str = entry_fim.get()

    pasta, inicio, fim, erro_validacao = _validar_entradas(
        pasta_str, inicio_str, fim_str)

    if erro_validacao:
        messagebox.showerror("Erro de Entrada", erro_validacao)
        return

    # Assegura que pasta, inicio e fim não são None neste ponto (devido à validação)
    assert pasta is not None
    assert inicio is not None
    assert fim is not None

    numeros_encontrados, arquivos_sem_numero, numeros_fora_intervalo = _processar_arquivos_da_pasta(
        pasta, inicio, fim)
    numeros_faltantes = _identificar_numeros_faltantes(
        inicio, fim, numeros_encontrados)

    conteudo_relatorio = _gerar_conteudo_relatorio(
        pasta, inicio, fim, numeros_faltantes, numeros_fora_intervalo, arquivos_sem_numero
    )

    caminho_relatorio_salvo = _salvar_relatorio(
        pasta, pasta.name, conteudo_relatorio)

    if caminho_relatorio_salvo:
        messagebox.showinfo(
            "Concluído", f"Verificação finalizada. Relatório salvo em:\n{caminho_relatorio_salvo}")

        if var_unificar_relatorios.get():  # Verifica o estado do checkbutton
            pasta_para_unificar = caminho_relatorio_salvo.parent
            print(
                f"INFO: Iniciando unificação de relatórios na pasta: {pasta_para_unificar}")
            # Não é necessário um messagebox aqui, pois o ReportCombiner.run() já informa o usuário.
            try:
                combiner = ReportCombiner(str(pasta_para_unificar))
                combiner.run()  # Este método já lida com seus próprios pop-ups e logging
            except Exception as e:
                # Captura erros na instanciação de ReportCombiner ou outros não tratados por run()
                messagebox.showerror("Erro na Unificação",
                                     f"Ocorreu um erro inesperado ao iniciar o processo de unificação:\n{e}")
                if hasattr(combiner, 'logger'):  # Se o logger foi inicializado
                    combiner.logger.exception(
                        "Erro crítico ao tentar unificar relatórios.")


# Configuração da janela principal
root = tk.Tk()
try:
    root.iconbitmap(ICON_PATH)
except tk.TclError:
    print(f"Aviso: Ícone '{ICON_PATH}' não encontrado ou formato inválido.")
root.title("Verificador de Mensagens")

# Frame principal
frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

# Widgets
tk.Label(frame, text="Pasta:").grid(row=0, column=0, sticky="w")
entry_pasta = tk.Entry(frame, width=50)
entry_pasta.grid(row=0, column=1, padx=5)
tk.Button(frame, text="Selecionar",
          command=selecionar_pasta).grid(row=0, column=2)

tk.Label(frame, text="Número Inicial:").grid(row=1, column=0, sticky="w")
entry_inicio = tk.Entry(frame, width=10)
entry_inicio.grid(row=1, column=1, sticky="w", padx=5)

tk.Label(frame, text="Número Final:").grid(row=2, column=0, sticky="w")
entry_fim = tk.Entry(frame, width=10)
entry_fim.grid(row=2, column=1, sticky="w", padx=5)

# Checkbutton para unificar relatórios
var_unificar_relatorios = tk.BooleanVar()
check_unificar = tk.Checkbutton(frame, text="Unificar relatórios da pasta pai após verificação",
                                variable=var_unificar_relatorios)
check_unificar.grid(row=3, column=0, columnspan=3, sticky="w", pady=(5, 0))

tk.Button(frame, text="Verificar Arquivos", command=verificar_arquivos).grid(
    row=4, column=0, columnspan=3, pady=10)

root.mainloop()

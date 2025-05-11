import tkinter as tk_module # Alias para evitar conflitos
from tkinter import filedialog, messagebox
import email
from email import policy
from email.header import decode_header, make_header
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone # Import datetime from datetime
import re
import shutil
import logging
from pathlib import Path
from typing import Optional, Tuple

# --- Constantes ---
DUPLICATES_SUBFOLDER = "Duplicatas"
PROBLEMS_SUBFOLDER = "Problemas" # Nova pasta para erros de leitura
LOG_FOLDER_NAME = "LOGS_RENOMEAR_EML" # Pasta para logs específicos deste script
LOG_FILENAME_PREFIX = "renomear_eml_log_"
# Caracteres inválidos para nomes de arquivo no Windows/Unix
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
MAX_FILENAME_PART_LEN = 60 # Limite para partes do nome (assunto/remetente) para evitar nomes muito longos
FALLBACK_PART_NAME = "Desconhecido"
FALLBACK_INVALID_PART_NAME = "Invalido"
FALLBACK_HEADER_DECODE_ERROR = "Cabecalho_Indecifravel"
# --- Fim Constantes ---

class EmlRenamer:
    """
    Processa arquivos .eml em uma pasta, renomeando-os com base em seus cabeçalhos
    (data, assunto, remetente) e movendo duplicatas ou arquivos problemáticos
    para subpastas designadas.
    """

    def __init__(self, base_folder_path: str):
        self.base_folder: Path = Path(base_folder_path).resolve()
        self.duplicates_path: Path = self.base_folder / DUPLICATES_SUBFOLDER
        self.problems_path: Path = self.base_folder / PROBLEMS_SUBFOLDER
        self.log_folder_path: Path = self.base_folder / LOG_FOLDER_NAME
        
        self.logger: logging.Logger = self._setup_logger()

        # Contadores
        self.renamed_count: int = 0
        self.moved_to_duplicates_count: int = 0
        self.moved_to_problems_count: int = 0
        self.error_count: int = 0 # Erros gerais durante o processamento
        self.skipped_count: int = 0 # Arquivos não .eml ou pastas especiais

    def _setup_logger(self) -> logging.Logger:
        """Configura o logger para este script."""
        self.log_folder_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_file = self.log_folder_path / f"{LOG_FILENAME_PREFIX}{timestamp}.log"

        logger = logging.getLogger(f"{__name__}.EmlRenamer.{id(self)}")
        logger.setLevel(logging.INFO) # Captura INFO, WARNING, ERROR
        logger.propagate = False

        if logger.hasHandlers():
            logger.handlers.clear()

        try:
            file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"ERRO CRÍTICO: Não foi possível configurar o logger em {log_file}. Erro: {e}")
            # Adiciona um NullHandler para evitar que o programa falhe se o logger for usado
            logger.addHandler(logging.NullHandler())
        return logger

    def _sanitize_filename_part(self, text: Optional[str]) -> str:
        """Limpa uma string para ser usada em nomes de arquivo."""
        if not text:
            return FALLBACK_PART_NAME
        
        sanitized = re.sub(INVALID_FILENAME_CHARS, '_', text)
        sanitized = re.sub(r'[\s_]+', '_', sanitized) # Múltiplos espaços/underscores para um único underscore
        sanitized = sanitized.strip('_') # Remove underscores no início/fim
        
        if len(sanitized) > MAX_FILENAME_PART_LEN:
            base_part = sanitized[:MAX_FILENAME_PART_LEN]
            # Tenta cortar em um underscore antes do limite para manter palavras
            if '_' in base_part:
                 sanitized = base_part.rsplit('_', 1)[0]
            else: # Se não houver underscore, corta diretamente
                 sanitized = base_part
        
        if not sanitized: # Se tudo foi removido
            return FALLBACK_INVALID_PART_NAME
        return sanitized

    def _decode_email_header(self, header_string: Optional[str]) -> str:
        """Decodifica um cabeçalho de e-mail (Subject, From, To)."""
        if header_string is None:
            return ""
        try:
            decoded_parts = decode_header(header_string)
            header = make_header(decoded_parts)
            return str(header)
        except Exception as e:
            self.logger.warning(f"Falha ao decodificar cabeçalho: '{header_string}'. Erro: {e}")
            # Tenta uma decodificação forçada como fallback
            try:
                if isinstance(header_string, bytes):
                    try:
                        return header_string.decode('utf-8', 'ignore')
                    except UnicodeDecodeError:
                        return header_string.decode('latin-1', 'ignore')
                # Se já for string, pode ter caracteres problemáticos
                return header_string.encode('latin-1', 'replace').decode('utf-8', 'replace')
            except Exception:
                return FALLBACK_HEADER_DECODE_ERROR

    def _get_formatted_date(self, date_header_string: Optional[str], fallback_file_path: Optional[Path] = None) -> Optional[str]:
        """Analisa o cabeçalho Date e retorna 'YYYY MM DD HHMMSS'. Usa data de modificação como fallback."""
        dt_object: Optional[datetime] = None
        if date_header_string:
            try:
                dt_object = parsedate_to_datetime(date_header_string)
                if dt_object.tzinfo:
                    try:
                        # Tenta converter para o timezone local do sistema
                        dt_object = dt_object.astimezone(datetime.now().astimezone().tzinfo)
                    except (ValueError, OSError):
                         self.logger.warning(f"Falha ao converter timezone para local para data '{date_header_string}'. Usando UTC.")
                         dt_object = dt_object.astimezone(timezone.utc)
            except Exception as e:
                self.logger.warning(f"Não foi possível analisar a data do cabeçalho '{date_header_string}': {e}")
                dt_object = None # Garante que o fallback seja usado

        if not dt_object and fallback_file_path and fallback_file_path.exists():
            self.logger.info(f"Usando data de modificação do arquivo '{fallback_file_path.name}' como fallback para data principal.")
            try:
                 mod_time = fallback_file_path.stat().st_mtime
                 dt_object = datetime.fromtimestamp(mod_time)
            except OSError as ts_err:
                 self.logger.error(f"Não foi possível obter data de modificação para '{fallback_file_path.name}': {ts_err}. Usando data atual.")
                 self.error_count += 1
                 dt_object = datetime.now()
        
        if not dt_object: # Se ainda não há data (nem do header, nem do fallback)
            self.logger.error(f"Não foi possível determinar uma data para o arquivo (cabeçalho e fallback falharam). Usando data atual.")
            self.error_count += 1
            dt_object = datetime.now()
            
        return dt_object.strftime("%Y %m %d %H%M%S")

    def _handle_problematic_file(self, original_path: Path, error_info: str) -> None:
        """Move um arquivo que causou erro para a pasta de problemas."""
        self.logger.error(f"Erro ao ler/processar cabeçalhos de '{original_path.name}': {error_info}. Movendo para '{PROBLEMS_SUBFOLDER}'.")
        self.error_count += 1

        if not original_path.exists():
            self.logger.warning(f"Arquivo original '{original_path.name}' (com erro) desapareceu antes de ser movido para Problemas.")
            return

        try:
            self.problems_path.mkdir(parents=True, exist_ok=True)
            
            # Usa timestamp de modificação (ou criação se modificação falhar) para o nome do arquivo problemático
            try:
                mod_time = original_path.stat().st_mtime
            except OSError:
                mod_time = original_path.stat().st_ctime # Fallback para tempo de criação

            fallback_date_obj = datetime.fromtimestamp(mod_time)
            formatted_fallback_date = fallback_date_obj.strftime("%Y %m %d %H%M%S")

            original_base_sanitized = self._sanitize_filename_part(original_path.stem)
            problem_base_name = f"{formatted_fallback_date} - ERRO_LEITURA - {original_base_sanitized}"
            
            problem_target_path = self.problems_path / f"{problem_base_name}{original_path.suffix}"
            counter = 1
            while problem_target_path.exists():
                self.logger.warning(f"Nome '{problem_target_path.name}' também existe em '{PROBLEMS_SUBFOLDER}'. Tentando sufixo.")
                problem_target_path = self.problems_path / f"{problem_base_name}_{counter}{original_path.suffix}"
                counter += 1
                if counter > 100:
                    self.logger.error(f"Muitas tentativas de sufixo para '{original_path.name}' em {PROBLEMS_SUBFOLDER}. Abortando movimentação.")
                    return

            shutil.move(str(original_path), str(problem_target_path))
            self.logger.info(f"Movido '{original_path.name}' (com erro) para '{problem_target_path.relative_to(self.base_folder)}'")
            self.moved_to_problems_count += 1
        except Exception as move_err:
            self.logger.error(f"ERRO CRÍTICO ao tentar mover '{original_path.name}' para '{PROBLEMS_SUBFOLDER}': {move_err}")
            self.error_count +=1 # Erro adicional na tentativa de mover

    def _handle_duplicate_file(self, original_path: Path, new_base_name_for_duplicate: str) -> None:
        """Move um arquivo para a pasta de duplicatas, resolvendo conflitos de nome lá dentro."""
        self.logger.warning(f"Nome '{new_base_name_for_duplicate}{original_path.suffix}' já existe na pasta principal. Movendo '{original_path.name}' para '{DUPLICATES_SUBFOLDER}'.")
        
        if not original_path.exists():
            self.logger.warning(f"Arquivo original '{original_path.name}' desapareceu antes de ser movido para Duplicatas.")
            return

        try:
            self.duplicates_path.mkdir(parents=True, exist_ok=True)

            move_target_path = self.duplicates_path / f"{new_base_name_for_duplicate}{original_path.suffix}"
            counter = 1
            while move_target_path.exists():
                self.logger.warning(f"Nome '{move_target_path.name}' também existe em '{DUPLICATES_SUBFOLDER}'. Tentando sufixo.")
                move_target_path = self.duplicates_path / f"{new_base_name_for_duplicate}_{counter}{original_path.suffix}"
                counter += 1
                if counter > 100:
                    self.logger.error(f"Muitas tentativas de sufixo para '{original_path.name}' em Duplicatas. Abortando movimentação.")
                    return

            shutil.move(str(original_path), str(move_target_path))
            self.logger.info(f"Movido '{original_path.name}' para '{move_target_path.relative_to(self.base_folder)}'")
            self.moved_to_duplicates_count += 1
        except Exception as move_err:
            self.logger.error(f"Erro ao mover '{original_path.name}' para Duplicatas: {move_err}")
            self.error_count += 1

    def _process_single_eml(self, original_path: Path) -> None:
        """Processa um único arquivo .eml."""
        # self.logger.info(f"Processando: {original_path.name}") # Log removido conforme solicitado
        try:
            msg = None
            try:
                with original_path.open('rb') as f:
                    msg = email.message_from_binary_file(f, policy=policy.default)
            except Exception as bin_read_err: # Captura erros mais amplos na leitura binária
                self.logger.warning(f"Falha ao ler '{original_path.name}' como binário com policy default ({bin_read_err}), tentando leitura manual...")
                try:
                    with original_path.open('r', encoding='utf-8', errors='ignore') as f:
                        msg = email.message_from_file(f, policy=policy.default)
                except UnicodeDecodeError:
                    try:
                        with original_path.open('r', encoding='latin-1', errors='ignore') as f:
                            msg = email.message_from_file(f, policy=policy.default)
                    except Exception as fallback_read_err:
                        raise fallback_read_err # Re-levanta para o except externo

            if not msg:
                raise ValueError("Não foi possível interpretar o arquivo EML após tentativas de leitura.")

            date_str = msg.get("Date")
            subject_str = self._decode_email_header(msg.get("Subject"))
            from_str = self._decode_email_header(msg.get("From"))

            formatted_date = self._get_formatted_date(date_str, fallback_file_path=original_path)
            # formatted_date agora sempre retorna uma string ou None, mas _get_formatted_date foi ajustado para sempre retornar uma data válida
            if not formatted_date: # Segurança, embora _get_formatted_date deva sempre retornar algo
                self.logger.error(f"Data não pôde ser determinada para {original_path.name}, usando data atual para nome.")
                formatted_date = datetime.now().strftime("%Y %m %d %H%M%S")

            sanitized_subject = self._sanitize_filename_part(subject_str)
            sanitized_sender = self._sanitize_filename_part(from_str)

            new_base_name = f"{formatted_date} - {sanitized_subject} - {sanitized_sender}"
            new_filename_with_ext = f"{new_base_name}{original_path.suffix}" # Mantém extensão original
            potential_target_path = self.base_folder / new_filename_with_ext

            if potential_target_path.exists():
                if original_path.resolve() == potential_target_path.resolve():
                    # Log removido conforme solicitado:
                    # self.logger.info(f"Nome '{original_path.name}' já está correto. Ignorando renomeação.")
                    pass # Nenhuma ação ou log se o nome já está correto
                else: # Arquivo diferente com o mesmo nome de destino
                    self._handle_duplicate_file(original_path, new_base_name)
            else:
                try:
                    if not original_path.exists(): # Re-check
                        self.logger.warning(f"Arquivo original '{original_path.name}' desapareceu antes de ser renomeado.")
                        return
                    original_path.rename(potential_target_path)
                    self.logger.info(f"Renomeado '{original_path.name}' para '{potential_target_path.name}'")
                    self.renamed_count += 1
                except Exception as rename_err:
                    self.logger.error(f"Erro ao renomear '{original_path.name}': {rename_err}")
                    self.error_count += 1
        except Exception as e:
            self._handle_problematic_file(original_path, str(e))

    def run(self) -> str:
        """Processa todos os arquivos .eml na pasta base."""
        self.logger.info(f"Iniciando processamento da pasta: {self.base_folder}")
        
        if not self.base_folder.is_dir():
            error_msg = f"O caminho selecionado não é uma pasta válida: {self.base_folder}"
            self.logger.error(error_msg)
            messagebox.showerror("Erro de Pasta", error_msg)
            return f"ERRO: {error_msg}"

        for item_path in self.base_folder.iterdir():
            # Pula subpastas (incluindo as especiais) e arquivos que não são .eml
            if item_path.is_dir():
                if item_path.name not in [DUPLICATES_SUBFOLDER, PROBLEMS_SUBFOLDER, LOG_FOLDER_NAME]:
                    self.skipped_count += 1
                continue # Pula todas as pastas
            
            if not item_path.name.lower().endswith(".eml"):
                self.skipped_count += 1
                continue

            self._process_single_eml(item_path)

        summary = self._generate_summary()
        self.logger.info(f"Processamento concluído para {self.base_folder}.\n{summary}")
        return summary

    def _generate_summary(self) -> str:
        """Gera a mensagem de resumo do processamento."""
        summary_lines = [
            f"Processamento concluído em: {self.base_folder}\n",
            f"Arquivos .eml renomeados na pasta principal: {self.renamed_count}",
            f"Arquivos movidos para '{DUPLICATES_SUBFOLDER}' (nomes duplicados): {self.moved_to_duplicates_count}",
            f"Arquivos movidos para '{PROBLEMS_SUBFOLDER}' (erro leitura/processamento): {self.moved_to_problems_count}",
            f"Arquivos/Pastas ignorados (não .eml ou pastas especiais): {self.skipped_count}",
            f"Erros totais encontrados (leitura/renomeação/movimentação): {self.error_count}"
        ]
        return "\n".join(summary_lines)

def main_gui_flow():
    """Controla o fluxo da GUI para seleção de pasta e exibição de resultados."""
    root = tk_module.Tk()
    root.withdraw()

    folder_path_str = filedialog.askdirectory(title="Selecione a pasta com os arquivos .eml")

    if not folder_path_str:
        messagebox.showinfo("Cancelado", "Nenhuma pasta selecionada.")
        root.destroy()
        return

    renamer = EmlRenamer(folder_path_str)
    summary_message = renamer.run()
    
    print("-" * 30) # Separador no console
    print(summary_message) # Imprime resumo no console também
    messagebox.showinfo("Concluído", summary_message)
    root.destroy()

if __name__ == "__main__":
    main_gui_flow()

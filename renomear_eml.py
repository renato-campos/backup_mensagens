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
PROBLEMS_SUBFOLDER = "Problemas" # Nova pasta para erros de leitura
LOG_FOLDER_NAME = "LOGS_RENOMEAR_EML" # Pasta para logs específicos deste script
LOG_FILENAME_PREFIX = "renomear_eml_log_"
# Caracteres inválidos para nomes de arquivo no Windows/Unix
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f\r\n]' # Adicionado \r\n
MAX_SUBJECT_LEN = 149       # Limite para o assunto (ajustado para caber em MAX_ALLOWED_FILENAME_BASE_LEN)
MAX_SENDER_LEN = 30         # Limite para o remetente
DEFAULT_MAX_PART_LEN = 60   # Limite padrão para outras partes do nome
FALLBACK_PART_NAME = "Desconhecido"
MAX_ALLOWED_FILENAME_BASE_LEN = 200 # Limite para o nome base do arquivo (sem extensão)
FALLBACK_INVALID_PART_NAME = "Invalido"
FALLBACK_HEADER_DECODE_ERROR = "Cabecalho_Indecifravel"
# Para sufixos de duplicatas: "" (sem sufixo), "a"-"z" (26), "aa"-"zz" (26*26=676). Total = 1+26+676 = 703 tentativas.
MAX_SUFFIX_ATTEMPTS = 1 + 26 + (26 * 26)
# --- Fim Constantes ---

class EmlRenamer:
    """
    Processa arquivos .eml em uma pasta, renomeando-os com base em seus cabeçalhos
    (data, assunto, remetente) e movendo duplicatas ou arquivos problemáticos
    para subpastas designadas.
    """

    def __init__(self, base_folder_path: str):
        self.base_folder: Path = Path(base_folder_path).resolve()
        self.problems_path: Path = self.base_folder / PROBLEMS_SUBFOLDER
        self.log_folder_path: Path = self.base_folder / LOG_FOLDER_NAME
        
        self.logger: logging.Logger = self._setup_logger()

        # Contadores
        self.renamed_count: int = 0
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

    def _sanitize_filename_part(self, text: Optional[str], max_len: int) -> str:
        """Limpa uma string para ser usada em nomes de arquivo."""
        if not text:
            return FALLBACK_PART_NAME
        
        sanitized = re.sub(INVALID_FILENAME_CHARS, '_', text)
        sanitized = re.sub(r'[\s_.-]+', '_', sanitized) # Múltiplos espaços/underscores/pontos/hífens para um único underscore
        sanitized = sanitized.strip('_') # Remove underscores no início/fim
        
        if len(sanitized) > max_len:
            base_part = sanitized[:max_len]
            # Tenta cortar em um underscore antes do limite para manter palavras
            if '_' in base_part:
                # Garante que não corte para uma string vazia se o primeiro underscore for o último char permitido
                cut_part = base_part.rsplit('_', 1)[0]
                sanitized = cut_part if cut_part else base_part
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

    def _get_email_body_content(self, msg: email.message.Message) -> str:
        """Extrai o conteúdo de texto simples do corpo do e-mail."""
        body_parts = []
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", "")).lower()

                if content_type == "text/plain" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset()
                        decoded_payload_str = None
                        if charset:
                            try:
                                decoded_payload_str = payload.decode(charset, errors='replace')
                            except (UnicodeDecodeError, LookupError):
                                self.logger.debug(f"Falha ao decodificar payload com charset '{charset}', tentando fallbacks.")
                        # Se charset falhou, não foi especificado, ou payload ainda é None
                        if decoded_payload_str is None:
                            try:
                                decoded_payload_str = payload.decode('utf-8', errors='replace')
                            except UnicodeDecodeError:
                                try:
                                    decoded_payload_str = payload.decode('latin-1', errors='replace')
                                except UnicodeDecodeError:
                                    self.logger.warning(f"Não foi possível decodificar parte do corpo (text/plain) com utf-8 nem latin-1.")
                                    decoded_payload_str = "" # Evita adicionar None
                        if decoded_payload_str: # Adiciona apenas se houver conteúdo
                            body_parts.append(decoded_payload_str)
        else: # Não é multipart
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8' # Default para utf-8
                decoded_payload_str = None
                try:
                    decoded_payload_str = payload.decode(charset, errors='replace')
                except (UnicodeDecodeError, LookupError):
                    self.logger.debug(f"Falha ao decodificar payload (não multipart) com charset '{charset}', tentando latin-1.")
                    try:
                        decoded_payload_str = payload.decode('latin-1', errors='replace')
                    except UnicodeDecodeError:
                        self.logger.warning(f"Não foi possível decodificar payload (não multipart) com charset '{charset}' nem latin-1.")
                if decoded_payload_str:
                    body_parts.append(decoded_payload_str)
        
        return "\n".join(filter(None, body_parts))

    def _extract_date_time_from_body(self, body_content: str) -> Optional[datetime]:
        """
        Procura por 'Mensagem=' no corpo e tenta extrair data (ddmmyy) e hora (hh:mm)
        da linha seguinte. Retorna um objeto datetime se bem-sucedido.
        """
        if not body_content:
            return None

        lines = body_content.splitlines()
        found_marker_line_index = -1
        for i, line_content in enumerate(lines):
            if "Mensagem=" in line_content:
                found_marker_line_index = i
                break
        
        if found_marker_line_index == -1 or found_marker_line_index + 1 >= len(lines):
            return None
        
        data_hora_line_str = lines[found_marker_line_index + 1]
        match_data_hora = re.search(r"(\d{2})(\d{2})(\d{2}).*?(\d{2}):(\d{2})", data_hora_line_str)

        if match_data_hora:
            dd, mm_date, yy, hh, min_time = match_data_hora.groups()
            try:
                year = int("20" + yy) # Assume século 21
                dt_obj = datetime(year, int(mm_date), int(dd), int(hh), int(min_time))
                self.logger.info(f"Data/hora extraída do corpo do e-mail (após 'Mensagem='): {dt_obj.strftime('%Y-%m-%d %H:%M')}")
                return dt_obj
            except ValueError as ve:
                self.logger.warning(f"Valor de data/hora inválido ('{data_hora_line_str}') extraído do corpo: {ve}")
        return None

    def _get_formatted_date(self, msg: email.message.Message, date_header_string: Optional[str], fallback_file_path: Optional[Path] = None) -> str:
        """
        Analisa o cabeçalho Date, tenta extrair do corpo do e-mail, ou usa data de modificação
        do arquivo como fallback. Retorna 'YYYY MM DD HHMM'.
        """
        dt_object: Optional[datetime] = None

        # 1. Tenta pelo cabeçalho 'Date'
        if date_header_string:
            try:
                dt_object = parsedate_to_datetime(date_header_string)
                if dt_object: # parsedate_to_datetime pode retornar None
                    if dt_object.tzinfo:
                        try:
                            dt_object = dt_object.astimezone(datetime.now().astimezone().tzinfo)
                        except (ValueError, OSError):
                             self.logger.warning(f"Falha ao converter timezone para local para data do cabeçalho '{date_header_string}'. Usando UTC.")
                             dt_object = dt_object.astimezone(timezone.utc)
                    # else: datetime é naive, deixa como está
            except Exception as e:
                self.logger.warning(f"Não foi possível analisar a data do cabeçalho '{date_header_string}': {e}")
                dt_object = None

        # 2. Se não conseguiu pelo cabeçalho, tenta extrair do corpo do e-mail
        if not dt_object:
            file_id_for_log = fallback_file_path.name if fallback_file_path else "arquivo desconhecido"
            self.logger.info(f"Data não encontrada/parseada no cabeçalho. Tentando extrair do corpo para '{file_id_for_log}'.")
            email_body = self._get_email_body_content(msg)
            if email_body:
                dt_object_from_body = self._extract_date_time_from_body(email_body)
                if dt_object_from_body:
                    dt_object = dt_object_from_body
                else:
                    self.logger.info(f"Não foi possível extrair data/hora do corpo do e-mail para '{file_id_for_log}'.")
            else:
                self.logger.info(f"Corpo do e-mail vazio ou não extraído para '{file_id_for_log}'. Não foi possível tentar extrair data do corpo.")

        # 3. Se ainda não há data, usa data de modificação do arquivo como fallback
        if not dt_object and fallback_file_path and fallback_file_path.exists(): # type: ignore
            self.logger.info(f"Usando data de modificação do arquivo '{fallback_file_path.name}' como fallback para data principal.")
            try:
                 mod_time = fallback_file_path.stat().st_mtime
                 dt_object = datetime.fromtimestamp(mod_time)
            except OSError as ts_err:
                 self.logger.error(f"Não foi possível obter data de modificação para '{fallback_file_path.name}': {ts_err}. Usando data atual.")
                 self.error_count += 1
                 dt_object = datetime.now() # Define aqui para garantir que não seja None
        
        # 4. Se ainda não há data (nem do header, nem do corpo, nem do fallback do arquivo)
        if not dt_object:
            file_id_for_log = fallback_file_path.name if fallback_file_path else "arquivo desconhecido"
            self.logger.error(f"Não foi possível determinar uma data para '{file_id_for_log}' (cabeçalho, corpo e fallback de arquivo falharam). Usando data atual.")
            self.error_count += 1
            dt_object = datetime.now()
            
        return dt_object.strftime("%Y %m %d %H%M")

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
            formatted_fallback_date = fallback_date_obj.strftime("%Y %m %d %H%M") # Ajustado para novo formato

            original_base_sanitized = self._sanitize_filename_part(original_path.stem, DEFAULT_MAX_PART_LEN)
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

    def _get_alphabetic_suffix(self, attempt_number: int) -> str:
        """
        Gera um sufixo alfabético com base no número da tentativa.
        0 -> ""
        1-26 -> "a" - "z"
        27-702 -> "aa" - "zz" (26 + 26*26 = 702)
        """
        if attempt_number == 0:
            return ""
        elif 1 <= attempt_number <= 26:
            # Sufixo de uma letra (a-z)
            return chr(ord('a') + attempt_number - 1)
        elif 27 <= attempt_number < MAX_SUFFIX_ATTEMPTS: # 27 até 702
            # Sufixo de duas letras (aa-zz)
            # Ajusta o número para o intervalo de duas letras (1 a 26*26 = 676)
            adjusted_attempt = attempt_number - 26
            
            first_char_index = (adjusted_attempt - 1) // 26 # 0-25
            second_char_index = (adjusted_attempt - 1) % 26  # 0-25
            
            return chr(ord('a') + first_char_index) + chr(ord('a') + second_char_index)
        return f"_err_suffix_{attempt_number}" # Fallback se exceder zz, não deve acontecer com MAX_SUFFIX_ATTEMPTS

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
            # message_id_str = msg.get("Message-ID") # Não é mais usado no nome do arquivo

            formatted_date = self._get_formatted_date(msg, date_str, fallback_file_path=original_path)
            
            sanitized_subject = self._sanitize_filename_part(subject_str, MAX_SUBJECT_LEN)
            sanitized_sender = self._sanitize_filename_part(from_str, MAX_SENDER_LEN)
            # sanitized_message_id não é mais necessário para o nome do arquivo

            current_attempt_number = 0
            while True:
                if current_attempt_number >= MAX_SUFFIX_ATTEMPTS:
                    self.logger.error(f"Excedido o número máximo de tentativas de sufixo ({MAX_SUFFIX_ATTEMPTS-1}, até 'zz') para '{original_path.name}'. Movendo para '{PROBLEMS_SUBFOLDER}'.")
                    self._handle_problematic_file(original_path, f"Excesso de duplicatas (limite de sufixo '{self._get_alphabetic_suffix(MAX_SUFFIX_ATTEMPTS-1)}' atingido)")
                    return  # Aborta para este arquivo

                suffix_letter = self._get_alphabetic_suffix(current_attempt_number)
                # Construir o nome base candidato
                # Formato: YYYY MM DD HHMM{sufixo_opcional} - Subject - From
                base_name_candidate = f"{formatted_date}{suffix_letter} - {sanitized_subject} - {sanitized_sender}"

                # Truncar o nome base candidato se exceder o limite global
                if len(base_name_candidate) > MAX_ALLOWED_FILENAME_BASE_LEN:
                    original_candidate_for_log = base_name_candidate
                    base_name_candidate = base_name_candidate[:MAX_ALLOWED_FILENAME_BASE_LEN]
                    self.logger.warning(f"Nome base truncado de '{original_candidate_for_log}' para '{base_name_candidate}' para o arquivo '{original_path.name}' devido ao limite de {MAX_ALLOWED_FILENAME_BASE_LEN} caracteres.")

                new_filename_with_ext = f"{base_name_candidate}{original_path.suffix}"
                potential_target_path = self.base_folder / new_filename_with_ext

                if not potential_target_path.exists():
                    # Nome disponível, renomear
                    try:
                        if not original_path.exists(): # Re-check
                            self.logger.warning(f"Arquivo original '{original_path.name}' desapareceu antes de ser renomeado.")
                            return
                        original_path.rename(potential_target_path)
                        self.logger.info(f"Renomeado '{original_path.name}' para '{potential_target_path.name}'")
                        self.renamed_count += 1
                    except Exception as rename_err:
                        self.logger.error(f"Erro ao renomear '{original_path.name}' para '{potential_target_path.name}': {rename_err}")
                        self.error_count += 1
                    break # Sucesso, sai do loop while
                else:
                    # Nome já existe. Verificar se é o próprio arquivo.
                    if original_path.resolve() == potential_target_path.resolve():
                        # O arquivo já tem o nome correto (com ou sem sufixo). Nenhuma ação.
                        # self.logger.info(f"Nome '{original_path.name}' já está correto. Ignorando renomeação.")
                        break # Sai do loop while
                    else:
                        # É um arquivo diferente com o mesmo nome de destino.
                        # Prepara para tentar o próximo sufixo.
                        self.logger.info(f"Nome '{potential_target_path.name}' (sufixo '{suffix_letter}') já existe. Tentando próximo sufixo para '{original_path.name}'.")
                        current_attempt_number += 1
                        # O loop continuará

        except Exception as e:
            # Se qualquer outra exceção ocorrer durante o processamento do arquivo (incluindo falhas de leitura não tratadas antes)
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
                if item_path.name not in [PROBLEMS_SUBFOLDER, LOG_FOLDER_NAME]: # DUPLICATES_SUBFOLDER removido
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

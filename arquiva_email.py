import shutil
import email
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# --- Constantes ---
# Limite prático para caminhos no Windows (MAX_PATH (260) - 1 para nulo)
EFFECTIVE_MAX_PATH = 259
SAFE_PATH_MARGIN = 10     # Margem de segurança para evitar atingir o limite exato
LOG_FOLDER_NAME = "ERROS"  # Nome da pasta de logs
FALLBACK_SANITIZED_FILENAME = "arquivo_renomeado"
# Máximo de tentativas para resolver nomes duplicados
MAX_DUPLICATE_RESOLUTION_ATTEMPTS = 10
LOG_FILENAME_PREFIX = "archive_failures_"

# Pasta de monitoramento. Ajuste conforme necessário ou considere torná-la um parâmetro.
# Original do Desktop de mensagens
WATCH_FOLDER_PATH_STR = r"C:\backup_mensagens"
# Pasta teste
# WATCH_FOLDER_PATH_STR = r"C:\Users\renat\OneDrive\Área de Trabalho\Mensagens"
# --- Fim Constantes ---


class FileArchiver:
    """Arquiva arquivos de uma pasta de monitoramento para uma estrutura de pastas baseada em data."""

    def __init__(self, watch_folder_str: str, archive_root_str: str, log_folder_name: str = LOG_FOLDER_NAME):
        self.watch_folder: Path = Path(watch_folder_str).resolve()
        self.archive_root: Path = Path(archive_root_str).resolve()
        self.log_folder: Path = self.archive_root / log_folder_name
        self.setup_logger()

    def setup_logger(self) -> None:
        """Configura o logger para registrar apenas erros."""
        try:
            self.log_folder.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            log_file = self.log_folder / \
                f"{LOG_FILENAME_PREFIX}{timestamp}.log"

            # Configura o logger principal
            self.logger = logging.getLogger(
                f"{__name__}.{id(self)}")  # Nome único
            # Nível de log definido para ERROR
            self.logger.setLevel(logging.ERROR)

            # Remove handlers existentes para evitar duplicação se chamado novamente
            if self.logger.hasHandlers():
                self.logger.handlers.clear()

            # Cria o file handler
            file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
            # Nível do handler também definido para ERROR
            file_handler.setLevel(logging.ERROR)

            # Cria o formatter
            formatter = logging.Formatter(
                # Formato ajustado
                "%(asctime)s - %(levelname)s - Arquivo: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)

            # Adiciona o handler ao logger
            self.logger.addHandler(file_handler)

        except Exception as e:
            # Se houver erro ao configurar o log, imprime no console
            print(
                f"ERRO CRÍTICO: Não foi possível configurar o logger em {self.log_folder}. Erro: {e}")
            # Define um logger nulo para evitar falhas posteriores
            self.logger = logging.getLogger(
                'null_logger_due_to_error')  # Nome mais específico
            self.logger.addHandler(logging.NullHandler())

    def process_files(self) -> None:
        """Processa todos os arquivos na pasta de monitoramento."""
        if not self.watch_folder.exists() or not self.watch_folder.is_dir():
            # Loga o erro se a pasta de origem não existe
            self.logger.error(
                f"{self.watch_folder} - Motivo: Pasta de monitoramento não encontrada ou não é um diretório.")
            return

        # Itera apenas pelos arquivos na pasta WATCH_FOLDER
        for item_path in self.watch_folder.iterdir():
            if item_path.is_file():
                # Ignora arquivos .ffs_db silenciosamente
                if item_path.name.lower().endswith(".ffs_db") or item_path.name.lower().endswith(".ffs_lock"):
                    continue
                self.process_file(item_path)

    def process_file(self, file_path: Path) -> None:
        """Processa um único arquivo, chamando a função apropriada."""
        try:
            if file_path.suffix.lower() == ".eml":
                self.process_eml_file(file_path)
            else:
                self.process_other_file(file_path)
        except Exception as e:
            # Loga erro genérico no processamento do arquivo que impede a movimentação
            self.logger.error(
                f"{file_path.name} (em {file_path.parent}) - Motivo: Erro inesperado durante o processamento inicial. Detalhes: {e}")

    def process_eml_file(self, eml_path: Path) -> None:
        """Processa arquivos .eml para extrair data e mover."""
        msg: Optional[email.message.Message] = None
        try:
            # Tenta ler com UTF-8
            with eml_path.open('r', encoding='utf-8') as f:
                msg = email.message_from_file(f)
        except UnicodeDecodeError:
            try:
                # Se falhar, tenta com Latin-1
                with eml_path.open('r', encoding='latin-1') as f:
                    msg = email.message_from_file(f)
            except Exception as e:
                # Loga erro se a leitura falhar com ambos encodings
                self.logger.error(
                    f"{eml_path.name} - Motivo: Falha ao ler o arquivo (tentativas UTF-8 e Latin-1). Detalhes: {e}")
                return  # Impede a movimentação
        except Exception as e:
            # Loga erro genérico de leitura
            self.logger.error(
                f"{eml_path.name} - Motivo: Falha ao ler o arquivo. Detalhes: {e}")
            return  # Impede a movimentação

        # Se msg não foi lido com sucesso (caso raro, mas possível)
        if not msg:
            self.logger.error(
                f"{eml_path.name} - Motivo: Não foi possível interpretar o conteúdo do e-mail após leitura.")
            return  # Impede a movimentação

        date_str = msg.get("Date")
        # A falha na análise da data agora usa a data atual, não impede a movimentação,
        # então não logamos mais como erro aqui.
        # Passa o path para logs internos se necessário
        date_obj = self._parse_date(date_str, eml_path)

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_folder = self.archive_root / year / year_month

        self.move_file_to_archive(eml_path, archive_folder)

    def _parse_date(self, date_str: Optional[str], file_path_for_log: Path) -> datetime:
        """Tenta analisar a string de data. Retorna datetime.now() em caso de falha."""
        if not date_str:
            # Não loga mais aviso/erro, apenas retorna data atual
            return datetime.now()

        formats_to_try = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %Z",
        ]

        try:
            # Tenta com email.utils primeiro (mais robusto para fusos horários)
            parsed_dt = email.utils.parsedate_to_datetime(date_str)
            if parsed_dt:
                return parsed_dt
        except Exception:
            pass  # Continua para strptime

        for fmt in formats_to_try:
            try:
                cleaned_date_str = re.sub(
                    r'\s*\([^)]*\)\s*$', '', date_str).strip()
                return datetime.strptime(cleaned_date_str, fmt)
            except ValueError:
                continue

        # Se todos os formatos falharem, não loga erro, apenas retorna data atual
        # print(f"Debug: Falha ao parsear data '{date_str}' para {file_path_for_log}. Usando data atual.") # Debug opcional
        return datetime.now()

    def process_other_file(self, file_path: Path) -> None:
        """Processa outros tipos de arquivo usando data de modificação."""
        try:
            modification_time = file_path.stat().st_mtime
            date_obj = datetime.fromtimestamp(modification_time)
        except OSError as e:
            # Loga erro se não conseguir obter data de modificação
            self.logger.error(
                f"{file_path.name} - Motivo: Falha ao obter data de modificação. Detalhes: {e}")
            # Poderia optar por usar data atual ou retornar para não mover
            # Vamos retornar para garantir que só mova se tiver data válida
            return  # Impede a movimentação

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_folder = self.archive_root / year / year_month

        self.move_file_to_archive(file_path, archive_folder)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Remove ou substitui caracteres inválidos, o prefixo 'msg ',
        espaços extras e normaliza números no início do nome.
        """
        sanitized = re.sub(r'^msg\s+', '', filename, flags=re.IGNORECASE)
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)
        sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)
        sanitized = sanitized.strip()

        match = re.match(r'^(\d+)(.*)', sanitized)
        if match:
            number_str, rest_of_name = match.groups()
            try:
                number = int(number_str)
                sanitized = str(number) + rest_of_name
            except ValueError:  # Para números muito grandes
                if len(number_str) > 1 and number_str.startswith('0'):
                    sanitized = number_str.lstrip('0') + rest_of_name
                else:
                    sanitized = number_str + rest_of_name

        if not sanitized:
            self.logger.error(  # Erro, pois um nome de arquivo vazio é problemático
                f"Nome do arquivo '{filename}' resultou em vazio após sanitização. Usando fallback '{FALLBACK_SANITIZED_FILENAME}'.")
            sanitized = FALLBACK_SANITIZED_FILENAME
        return sanitized

    def _truncate_filename(self, target_folder: Path, filename: str, max_full_path_len: int) -> str:
        """
        Trunca o nome do arquivo (preservando a extensão) se o caminho completo
        (target_folder / filename) exceder max_full_path_len.
        """
        file_path_obj = Path(filename)
        base, ext = file_path_obj.stem, file_path_obj.suffix
        potential_full_path = target_folder / filename

        if len(str(potential_full_path)) <= max_full_path_len:
            return filename

        len_of_folder_path_str = len(str(target_folder))
        len_of_separator = 1  # Para o '/' ou '\'
        len_of_extension = len(ext)

        available_len_for_base = max_full_path_len - \
            (len_of_folder_path_str + len_of_separator + len_of_extension)

        if available_len_for_base <= 0:
            self.logger.error(
                f"Não é possível criar nome para '{filename}' em '{target_folder}' (limite: {max_full_path_len}). "
                f"Caminho da pasta base muito longo. Disponível para base: {available_len_for_base}")
            # Tenta retornar um nome mínimo se possível
            if len(ext) < max_full_path_len - (len_of_folder_path_str + len_of_separator):
                minimal_base_len = max_full_path_len - \
                    (len_of_folder_path_str + len_of_separator + len_of_extension)
                if minimal_base_len < 1 and len(base) > 0:
                    return f"_{ext}" if ext else "_"
                if minimal_base_len < 1 and len(base) == 0:
                    return "_"
            return filename  # Fallback

        if available_len_for_base < len(base):
            # Log apenas se o truncamento for realmente necessário e ocorrer
            # self.logger.warning( # Opcional: logar truncamento se desejado
            # f"Nome truncado: '{filename}' -> '{base[:available_len_for_base]}{ext}' em '{target_folder}'")
            return f"{base[:available_len_for_base]}{ext}"

        return filename  # Não precisou truncar a base

    def move_file_to_archive(self, file_path: Path, archive_folder: Path) -> None:
        """Move o arquivo para a pasta de destino, tratando sanitização, truncamento e duplicados."""
        try:
            archive_folder.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(
                f"{file_path.name} - Motivo: Erro ao criar pasta de destino '{archive_folder}'. Detalhes: {e}")
            return  # Impede a movimentação

        original_filename = file_path.name
        sanitized_filename = self._sanitize_filename(original_filename)

        current_final_filename = self._truncate_filename(
            archive_folder, sanitized_filename, EFFECTIVE_MAX_PATH - SAFE_PATH_MARGIN)

        destination_path = archive_folder / current_final_filename
        num_attempts = 0
        original_conflicting_filename_part = current_final_filename

        while destination_path.exists() and num_attempts < MAX_DUPLICATE_RESOLUTION_ATTEMPTS:
            num_attempts += 1
            if num_attempts == 1:  # Loga apenas na primeira tentativa de renomeação por duplicidade
                self.logger.error(  # Log como erro, pois é um conflito que precisa de ação
                    f"{file_path.name} - Motivo: Conflito de nome em '{archive_folder}' para '{original_conflicting_filename_part}'. Tentando renomear.")

            base_name_orig, ext_orig = Path(original_conflicting_filename_part).stem, Path(
                original_conflicting_filename_part).suffix
            if not base_name_orig:  # Caso o nome original seja apenas uma extensão ou vazio após sanitização/truncamento
                base_name_orig = FALLBACK_SANITIZED_FILENAME.split(
                    '.')[0]  # Use o fallback sem extensão

            if num_attempts <= MAX_DUPLICATE_RESOLUTION_ATTEMPTS / 2:  # Tenta com contador primeiro
                name_with_counter = f"{base_name_orig}_{num_attempts}{ext_orig}"
                current_final_filename = self._truncate_filename(
                    archive_folder, name_with_counter, EFFECTIVE_MAX_PATH - SAFE_PATH_MARGIN)
            else:  # Depois tenta com timestamp
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                name_with_timestamp = f"{base_name_orig}_{timestamp}{ext_orig}"
                current_final_filename = self._truncate_filename(
                    archive_folder, name_with_timestamp, EFFECTIVE_MAX_PATH - SAFE_PATH_MARGIN)

            destination_path = archive_folder / current_final_filename

        if destination_path.exists():
            self.logger.error(
                f"{file_path.name} - Motivo: Conflito de nome irresolúvel em '{archive_folder}' para '{original_conflicting_filename_part}' "
                f"após {num_attempts} tentativas. Arquivo não movido.")
            return

        try:
            shutil.move(str(file_path), str(destination_path))
        except Exception as e:
            self.logger.error(
                f"{file_path.name} - Motivo: Falha ao mover para '{destination_path}'. Detalhes: {e}")


def main() -> None:
    """Função principal para configurar e executar o arquivador de arquivos."""
    watch_folder = Path(WATCH_FOLDER_PATH_STR)
    archive_root = watch_folder  # Arquiva dentro da pasta de monitoramento, em subpastas

    # Cria a pasta de monitoramento se não existir (para testes)
    if not watch_folder.exists():
        try:
            watch_folder.mkdir(parents=True, exist_ok=True)
            print(f"Pasta de monitoramento {watch_folder} criada para teste.")
            # Crie alguns arquivos .eml ou outros para teste dentro dela
            with (watch_folder / "msg teste1.eml").open("w", encoding='utf-8') as f:
                f.write(
                    "Date: Mon, 1 Jan 2024 10:00:00 +0000\nSubject: Teste\n\nCorpo do email.")
            with (watch_folder / "MSG Arquivo com espaço.txt").open("w", encoding='utf-8') as f:
                f.write("Conteúdo.")
            long_name = "msg " + "a" * 240 + ".txt"
            with (watch_folder / long_name).open("w", encoding='utf-8') as f:
                f.write("Longo.")
            with (watch_folder / "arquivo sem prefixo.txt").open("w", encoding='utf-8') as f:
                f.write("Normal.")
        except OSError as e:
            print(f"Erro ao criar pasta de monitoramento {watch_folder}: {e}")
            return  # Não continuar se a pasta de teste não puder ser criada

    # Passa strings como esperado pelo __init__
    archiver = FileArchiver(str(watch_folder), str(archive_root))
    archiver.process_files()
    print("\nProcessamento concluído.")

    # Informa onde verificar os logs de falha
    log_files_found: List[Path] = []
    if archiver.log_folder.exists():
        log_files_found = sorted(
            [f for f in archiver.log_folder.iterdir() if f.is_file() and f.name.startswith(
                LOG_FILENAME_PREFIX) and f.name.endswith(".log")],
            reverse=True
        )

    # Preparar mensagem para a caixa de diálogo
    message = "Processamento concluído."
    if log_files_found:
        message += f"\n\nVerifique o(s) arquivo(s) de log em '{archiver.log_folder}' para detalhes sobre arquivos que não foram movidos:\n"
        for log_p in log_files_found:
            message += f"- {log_p.name}\n"
    elif archiver.log_folder.exists():  # Pasta de log existe, mas sem arquivos de erro
        message += f"\n\nNenhum erro registrado durante a execução (verificado em '{archiver.log_folder}')."
    # Pasta de log nem foi criada (pode acontecer se o logger falhar criticamente)
    else:
        message += f"\n\nA pasta de log '{archiver.log_folder}' não foi encontrada."

    # Criar janela de mensagem com fechamento automático
    show_auto_close_message(message, 5000)  # 5000 ms = 5 segundos


def show_auto_close_message(message: str, timeout: int) -> None:
    """
    Exibe uma mensagem que se fecha automaticamente após o tempo especificado.

    Args:
        message: Texto da mensagem
        timeout: Tempo em milissegundos antes do fechamento automático
    """
    # Importar tkinter aqui para não afetar o resto do código
    import tkinter as tk_module  # Evitar conflito com possível variável tk

    # Criar janela
    root = tk_module.Tk()
    root.title("Status do Arquivamento")

    # Centralizar na tela
    window_width = 500
    window_height = 300
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_coordinate = int((screen_width - window_width) / 2)
    y_coordinate = int((screen_height - window_height) / 2)
    root.geometry(
        f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

    # Adicionar texto
    frame = tk_module.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk_module.BOTH, expand=True)

    # Adicionar contador regressivo
    countdown_var = tk_module.StringVar()
    countdown_var.set(f"Esta mensagem se fechará em {timeout//1000} segundos")

    # Título
    title_label = tk_module.Label(
        frame, text="Arquivamento Concluído", font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))

    # Mensagem principal
    msg_label = tk_module.Label(
        frame, text=message, justify=tk_module.LEFT, wraplength=450)
    msg_label.pack(pady=10)

    # Contador
    countdown_label = tk_module.Label(
        frame, textvariable=countdown_var, fg="gray")
    countdown_label.pack(pady=(10, 0))

    # Botão para fechar manualmente
    close_button = tk_module.Button(frame, text="Fechar", command=root.destroy)
    close_button.pack(pady=10)

    # Função para atualizar o contador e fechar a janela
    def update_countdown(remaining):
        if remaining <= 0:
            root.destroy()
            return
        countdown_var.set(f"Esta mensagem se fechará em {remaining} segundos")
        root.after(1000, update_countdown, remaining - 1)

    # Iniciar o contador
    root.after(0, update_countdown, timeout // 1000)

    # Iniciar o temporizador para fechar a janela
    root.after(timeout, root.destroy)

    # Iniciar loop principal
    root.mainloop()


if __name__ == "__main__":
    main()

import os
import shutil
import email
import logging
import re
from datetime import datetime
import tkinter as tk
# Added messagebox for potential future use, though not strictly needed now
from tkinter import filedialog, messagebox

# Definir constantes do arquiva_email.py (ou arquiva_raiz.py)
MAX_PATH_LENGTH = 255
SAFE_FILENAME_MARGIN = 10


class FileArchiver:
    def __init__(self, watch_folder, archive_root, log_folder):
        self.watch_folder = watch_folder
        self.archive_root = archive_root
        self.log_folder = log_folder
        self.setup_logger()
        # --- Adicionado contadores ---
        self.processed_files_count = 0
        self.error_count = 0
        # Para evitar prints repetidos de criação de pasta (agora removidos)
        self.created_folders = set()
        # --- Fim Adicionado contadores ---

    def setup_logger(self):
        """Configura o logger para registrar apenas erros."""
        try:
            if not os.path.exists(self.log_folder):
                # Não incrementa error_count aqui, pois é uma configuração inicial
                os.makedirs(self.log_folder)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            log_file = os.path.join(
                self.log_folder, f"archive_failures_{timestamp}.log")

            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.ERROR)

            if self.logger.hasHandlers():
                self.logger.handlers.clear()

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.ERROR)

            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - Arquivo: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

        except Exception as e:
            # Erro crítico na configuração do log, imprime no console e usa NullHandler
            print(
                f"ERRO CRÍTICO: Não foi possível configurar o logger em {self.log_folder}. Erro: {e}")
            self.logger = logging.getLogger('null')
            self.logger.addHandler(logging.NullHandler())
            # Consideramos isso um erro na operação geral
            self.error_count += 1

    def process_files(self):
        if not os.path.exists(self.watch_folder):
            self.logger.error(
                f"{self.watch_folder} - Motivo: Pasta de monitoramento não encontrada.")
            # Incrementa erro e retorna, pois não pode processar
            self.error_count += 1
            # Mantém o print para erro crítico inicial
            print(
                f"ERRO: Pasta de monitoramento não encontrada: {self.watch_folder}")
            return

        files_to_process = [f for f in os.listdir(self.watch_folder)
                            if os.path.isfile(os.path.join(self.watch_folder, f))
                            and not f.lower().endswith(".ffs_db")]  # Ignora .ffs_db

        if not files_to_process:
            # Se não há arquivos, não há o que processar (não é um erro)
            return  # Sai mais cedo

        for filename in files_to_process:
            file_path = os.path.join(self.watch_folder, filename)
            self.process_file(file_path)

    def process_file(self, file_path):
        try:
            if file_path.lower().endswith(".eml"):
                self.process_eml_file(file_path)
            else:
                self.process_other_file(file_path)
        except Exception as e:
            self.logger.error(
                f"{file_path} - Motivo: Erro inesperado durante o processamento inicial. Detalhes: {e}")
            # Incrementa erro
            self.error_count += 1

    def process_eml_file(self, eml_path):
        msg = None
        try:
            with open(eml_path, 'r', encoding='utf-8') as f:
                msg = email.message_from_file(f)
        except UnicodeDecodeError:
            try:
                with open(eml_path, 'r', encoding='latin-1') as f:
                    msg = email.message_from_file(f)
            except Exception as e:
                self.logger.error(
                    f"{eml_path} - Motivo: Falha ao ler o arquivo (tentativas UTF-8 e Latin-1). Detalhes: {e}")
                # Incrementa erro
                self.error_count += 1
                return
        except Exception as e:
            self.logger.error(
                f"{eml_path} - Motivo: Falha ao ler o arquivo. Detalhes: {e}")
            # Incrementa erro
            self.error_count += 1
            return

        if not msg:
            self.logger.error(
                f"{eml_path} - Motivo: Não foi possível interpretar o conteúdo do e-mail após leitura.")
            # Incrementa erro
            self.error_count += 1
            return

        date_str = msg.get("Date")
        # _parse_date lida com data inválida internamente
        date_obj = self._parse_date(date_str, eml_path)

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        self.move_file_to_archive(eml_path, archive_folder)

    def _parse_date(self, date_str, file_path_for_log):
        """Tenta analisar a string de data. Retorna datetime.now() em caso de falha."""
        if not date_str:
            # Não loga como erro, apenas usa data atual como fallback
            # print(f"Aviso: Data não encontrada em '{file_path_for_log}', usando data atual.") # Removido print
            return datetime.now()

        # Tenta parse com email.utils primeiro (mais robusto)
        try:
            parsed_dt = email.utils.parsedate_to_datetime(date_str)
            if parsed_dt:
                # Ajusta para timezone local se for timezone-aware
                if parsed_dt.tzinfo:
                    parsed_dt = parsed_dt.astimezone(
                        datetime.now().astimezone().tzinfo)
                return parsed_dt.replace(tzinfo=None)  # Retorna naive datetime
        except Exception:
            # print(f"Debug: email.utils falhou para '{date_str}'") # Removido print
            pass  # Tenta formatos manuais

        # Formatos manuais (alguns podem precisar de ajuste de timezone manualmente se %z não funcionar)
        formats_to_try = [
            "%a, %d %b %Y %H:%M:%S %z",       # Common RFC 5322 format with timezone offset
            # Format with timezone name (less reliable)
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",          # Variation without weekday
            "%d %b %Y %H:%M:%S %Z",          # Variation without weekday
            "%Y-%m-%d %H:%M:%S",             # ISO-like format
            # Adicione outros formatos comuns se necessário
        ]

        # Limpa timezone em parênteses (ex: " (UTC)") que strptime não entende
        cleaned_date_str = re.sub(r'\s*\([^)]*\)\s*$', '', date_str).strip()
        # Tenta remover explicitamente " UTC" ou " GMT" se %Z falhar
        cleaned_date_str_no_tz_name = re.sub(
            r'\s+(UTC|GMT)$', '', cleaned_date_str, flags=re.IGNORECASE).strip()

        for fmt in formats_to_try:
            try:
                # Tenta com a string limpa
                dt = datetime.strptime(cleaned_date_str, fmt)
                # Se o formato inclui %z, o objeto datetime será timezone-aware
                if dt.tzinfo:
                    dt = dt.astimezone(datetime.now().astimezone().tzinfo)
                return dt.replace(tzinfo=None)  # Retorna naive
            except ValueError:
                try:
                    # Tenta sem o nome do timezone no final
                    dt = datetime.strptime(
                        cleaned_date_str_no_tz_name, fmt.replace("%Z", "").strip())
                    # Assume local time se o timezone foi removido
                    return dt  # Já é naive
                except ValueError:
                    continue  # Tenta o próximo formato

        # Se todos os formatos falharem, loga e usa data/hora atual
        # Não logamos mais erro aqui, apenas usamos fallback
        # print(f"Aviso: Não foi possível parsear a data '{date_str}' de '{file_path_for_log}', usando data atual.") # Removido print
        return datetime.now()

    def process_other_file(self, file_path):
        try:
            modification_time = os.path.getmtime(file_path)
            date_obj = datetime.fromtimestamp(modification_time)
        except OSError as e:
            self.logger.error(
                f"{file_path} - Motivo: Falha ao obter data de modificação. Detalhes: {e}")
            # Incrementa erro
            self.error_count += 1
            return

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        self.move_file_to_archive(file_path, archive_folder)

    def _sanitize_filename(self, filename):
        """Remove ou substitui caracteres inválidos e o prefixo 'msg '."""
        # 1. Remove o prefixo "msg " (case-insensitive) do início
        #    O padrão ^ indica o início da string
        #    re.IGNORECASE faz a busca ignorar maiúsculas/minúsculas
        # Adicionado \s+ para remover o espaço seguinte também
        sanitized = re.sub(r'^msg\s+', '', filename, flags=re.IGNORECASE)

        # 2. Remove caracteres inválidos: < > : " / \ | ? *
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)

        # 3. Remove caracteres de controle (ASCII 0-31)
        sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)

        # 4. Remove espaços em branco no início ou fim (após remover prefixo e inválidos)
        sanitized = sanitized.strip()

        # 5. Normaliza números no início do nome para remover zeros à esquerda
        # Procura por um número no início do nome do arquivo
        match = re.match(r'^(\d+)(.*)', sanitized)
        if match:
            number_str, rest_of_name = match.groups()
            # Converte para inteiro para remover zeros à esquerda
            number = int(number_str)
            # Reconstrói o nome com o número sem zeros à esquerda
            sanitized = str(number) + rest_of_name

        # 6. Garante que o nome não seja vazio após a limpeza
        if not sanitized:
            # Se o nome original era apenas "msg " ou algo similar que foi removido
            sanitized = "arquivo_renomeado"  # Ou gerar um nome único com timestamp
        # Não loga mais a sanitização
        return sanitized


    def _truncate_filename(self, folder_path, filename, max_len):
        """Trunca o nome do arquivo se o caminho completo exceder max_len."""
        base, ext = os.path.splitext(filename)
        full_path = os.path.join(folder_path, filename)
        # Use bytes for more accurate length check
        full_path_len = len(full_path.encode('utf-8'))

        if full_path_len <= max_len:
            return filename

        # Calcula o espaço disponível para a base do nome do arquivo em bytes
        folder_path_len = len(folder_path.encode('utf-8'))
        sep_len = len(os.sep.encode('utf-8'))
        ext_len = len(ext.encode('utf-8'))
        available_len_for_base = max_len - \
            (folder_path_len + sep_len + ext_len)

        if available_len_for_base <= 0:
            # Não é possível truncar, o erro ocorrerá no move/rename.
            # Logar isso pode ser útil, mas faremos no erro do move.
            # self.logger.warning(f"Não é possível truncar '{filename}' em '{folder_path}', caminho base muito longo.")
            return filename

        # Trunca a base do nome garantindo que não quebre caracteres multibyte
        encoded_base = base.encode('utf-8')
        truncated_encoded_base = encoded_base[:available_len_for_base]
        # Decodifica de volta, ignorando erros se cortar no meio de um char
        truncated_base = truncated_encoded_base.decode(
            'utf-8', errors='ignore')

        # Remonta o nome do arquivo truncado
        truncated_filename = f"{truncated_base}{ext}"

        # Log é útil aqui, mas vamos manter o log apenas para erros fatais
        # self.logger.warning(f"Nome truncado: '{filename}' -> '{truncated_filename}' em '{folder_path}'")
        return truncated_filename

    def move_file_to_archive(self, file_path, archive_folder):
        """Move o arquivo para a pasta de destino, tratando sanitização, truncamento e duplicados."""
        archive_year_folder = os.path.dirname(archive_folder)
        try:
            # Cria pastas se não existirem (makedirs cria pais também)
            if not os.path.exists(archive_folder):
                # exist_ok=True evita erro se existir
                os.makedirs(archive_folder, exist_ok=True)
                # Removido print de criação de pasta
                # if archive_folder not in self.created_folders:
                #      print(f"Pasta {archive_folder} criada.")
                #      self.created_folders.add(archive_folder)
                #      # Adiciona pasta pai também para evitar print duplo
                #      if archive_year_folder not in self.created_folders and archive_year_folder != self.archive_root:
                #           self.created_folders.add(archive_year_folder)

        except OSError as e:
            self.logger.error(
                f"{file_path} - Motivo: Erro ao criar pasta de destino '{archive_folder}'. Detalhes: {e}")
            # Incrementa erro
            self.error_count += 1
            return

        original_filename = os.path.basename(file_path)
        # 1. Sanitizar
        sanitized_filename = self._sanitize_filename(original_filename)
        # 2. Truncar (considerando a pasta de destino)
        max_allowed_path = MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN
        final_filename = self._truncate_filename(
            archive_folder, sanitized_filename, max_allowed_path)
        destination_path = os.path.join(archive_folder, final_filename)

        # 3. Lidar com duplicados
        counter = 1
        base, ext = os.path.splitext(final_filename)
        temp_final_filename = final_filename  # Guarda o nome antes de adicionar sufixos

        while os.path.exists(destination_path):
            # Tenta adicionar _contador
            new_filename_base = f"{base}_{counter}"
            potential_new_filename = f"{new_filename_base}{ext}"
            potential_new_path = os.path.join(
                archive_folder, potential_new_filename)

            # Verifica se o nome com contador ainda cabe no limite de path
            if len(potential_new_path.encode('utf-8')) <= max_allowed_path:
                final_filename = potential_new_filename
            else:
                # Se não couber, tenta truncar a base original e adicionar timestamp
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                # Usa a base do nome *antes* de adicionar o contador para truncar
                base_original_sem_contador, ext_original = os.path.splitext(
                    temp_final_filename)
                nome_com_timestamp = f"{base_original_sem_contador}_{timestamp}{ext_original}"

                # Trunca o nome com timestamp
                final_filename = self._truncate_filename(
                    archive_folder, nome_com_timestamp, max_allowed_path)
                potential_new_path_ts = os.path.join(
                    archive_folder, final_filename)

                # Verifica colisão *novamente* após truncar com timestamp (raro, mas possível)
                if os.path.exists(potential_new_path_ts):
                    self.logger.error(
                        f"{file_path} - Motivo: Conflito de nome irresolúvel em '{archive_folder}' após tentar adicionar contador e timestamp (arquivo duplicado: {original_filename}).")
                    # Incrementa erro
                    self.error_count += 1
                    return  # Não pode mover
                else:
                    # Nome com timestamp truncado funcionou, sai do loop while
                    destination_path = potential_new_path_ts
                    break  # Sai do while

            # Atualiza destination_path para a próxima iteração do while (caso contador funcione)
            destination_path = os.path.join(archive_folder, final_filename)
            counter += 1
            # Adiciona um limite para evitar loops infinitos em casos extremos
            if counter > 100:
                self.logger.error(
                    f"{file_path} - Motivo: Loop infinito detectado ao tentar resolver nome duplicado para '{original_filename}' em '{archive_folder}'.")
                self.error_count += 1
                return  # Não pode mover

        # 4. Mover o arquivo
        try:
            shutil.move(file_path, destination_path)
            # Incrementa contador de sucesso
            self.processed_files_count += 1
            # Removido print de sucesso individual
            # print(f"Arquivo {os.path.basename(destination_path)} arquivado em {archive_folder}")
        except Exception as e:
            self.logger.error(
                f"{file_path} - Motivo: Falha ao mover para '{destination_path}'. Detalhes: {e}")
            # Incrementa erro
            self.error_count += 1


# select_folder permanece o mesmo
def select_folder():
    """Abre uma janela para o usuário selecionar uma pasta."""
    root = tk.Tk()
    root.withdraw()  # Oculta a janela principal do Tkinter
    folder_selected = filedialog.askdirectory(
        title="Selecione a Pasta a ser Processada")
    root.destroy()  # Fecha a instância do Tkinter temporária
    return folder_selected

# --- Copiado de arquiva_raiz.py ---


def show_auto_close_message(message, timeout):
    """
    Exibe uma mensagem que se fecha automaticamente após o tempo especificado.

    Args:
        message: Texto da mensagem
        timeout: Tempo em milissegundos antes do fechamento automático
    """
    # Criar janela
    root = tk.Tk()
    root.title("Processamento Concluído")

    # Centralizar na tela
    window_width = 500
    window_height = 350  # Ajuste a altura conforme necessário
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_coordinate = int((screen_width - window_width) / 2)
    y_coordinate = int((screen_height - window_height) / 2)
    root.geometry(
        f"{window_width}x{window_height}+{x_coordinate}+{y_coordinate}")

    # Adicionar texto
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    # Adicionar contador regressivo
    countdown_var = tk.StringVar()
    countdown_var.set(f"Esta mensagem se fechará em {timeout//1000} segundos")

    # Título
    title_label = tk.Label(
        frame, text="Processamento Concluído", font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))

    # Mensagem principal
    # Use um Text widget para permitir rolagem se a mensagem for longa
    msg_text = tk.Text(frame, wrap=tk.WORD, height=10,
                       width=60, relief=tk.FLAT, bg=root.cget('bg'))
    msg_text.insert(tk.END, message)
    msg_text.config(state=tk.DISABLED)  # Torna o texto somente leitura
    msg_text.pack(pady=10, fill=tk.BOTH, expand=True)

    # Contador
    countdown_label = tk.Label(frame, textvariable=countdown_var, fg="gray")
    countdown_label.pack(pady=(10, 0))

    # Botão para fechar manualmente
    close_button = tk.Button(frame, text="Fechar", command=root.destroy)
    close_button.pack(pady=10)

    # Função para atualizar o contador e fechar a janela
    def update_countdown(remaining):
        if remaining <= 0:
            try:
                # Verifica se a janela ainda existe antes de destruir
                if root.winfo_exists():
                    root.destroy()
            except tk.TclError:
                pass  # Ignora erro se a janela já foi fechada manualmente
            return
        countdown_var.set(f"Esta mensagem se fechará em {remaining} segundos")
        # Agenda a próxima atualização apenas se a janela ainda existir
        if root.winfo_exists():
            root.after(1000, update_countdown, remaining - 1)

    # Iniciar o contador
    # Usar root.after garante que a janela principal seja exibida primeiro
    root.after(100, lambda: update_countdown(timeout // 1000))

    # Iniciar o temporizador para fechar a janela (redundante com o contador, mas seguro)
    # root.after(timeout, root.destroy) # Removido, o contador já faz isso

    # Iniciar loop principal
    root.mainloop()
# --- Fim Copiado de arquiva_raiz.py ---


def main():
    # Usa Tkinter para seleção inicial, mas oculta a janela root principal
    root_temp = tk.Tk()
    root_temp.withdraw()
    messagebox.showinfo("Seleção de Pasta",
                        "Selecione a pasta contendo os arquivos .eml (ou outros) a serem arquivados.")
    root_temp.destroy()  # Fecha a janela temporária do messagebox

    watch_folder = select_folder()
    if not watch_folder:
        # Usa messagebox para cancelamento também
        root_temp = tk.Tk()
        root_temp.withdraw()
        messagebox.showwarning("Operação Cancelada",
                               "Nenhuma pasta selecionada. Encerrando.")
        root_temp.destroy()
        return

    # Define a pasta de arquivamento como a própria pasta selecionada
    # e a pasta de logs como 'ERROS' dentro dela.
    archive_root = watch_folder
    log_folder = os.path.join(archive_root, "ERROS")

    # --- Mensagem inicial informativa ---
    root_temp = tk.Tk()
    root_temp.withdraw()
    info_message = f"Pasta selecionada: {watch_folder}\n"
    info_message += f"Os arquivos serão arquivados em subpastas Ano/Ano-Mês dentro dela.\n"
    info_message += f"Os logs de erros serão salvos em: {log_folder}\n\n"
    info_message += "Iniciando o processo..."
    messagebox.showinfo("Processo Iniciado", info_message)
    root_temp.destroy()
    # --- Fim Mensagem inicial ---

    archiver = FileArchiver(watch_folder, archive_root, log_folder)
    archiver.process_files()

    # --- Construção da Mensagem Final ---
    summary_message = "-" * 30 + "\n"
    if archiver.processed_files_count > 0:
        summary_message += f"Processamento concluído:\n"
        summary_message += f"- {archiver.processed_files_count} arquivos arquivados com sucesso.\n"
    else:
        # Verifica se houve erros para diferenciar de "nenhum arquivo encontrado"
        if archiver.error_count == 0:
            # Verifica se a pasta de monitoramento realmente tinha arquivos (exceto .ffs_db)
            has_files = any(os.path.isfile(os.path.join(watch_folder, f)) and not f.lower().endswith(".ffs_db")
                            for f in os.listdir(watch_folder)) if os.path.exists(watch_folder) else False
            if has_files:
                summary_message += "Nenhum arquivo foi arquivado (possivelmente devido a erros ou já estavam organizados).\n"
            else:
                summary_message += "Nenhum arquivo encontrado para processar na pasta selecionada.\n"

        else:
            summary_message += "Nenhum arquivo foi arquivado com sucesso.\n"

    if archiver.error_count > 0:
        summary_message += f"\nAtenção: Ocorreram {archiver.error_count} erros durante a operação.\n"
        summary_message += f"Verifique o arquivo de log em '{log_folder}' para detalhes sobre os arquivos que não puderam ser movidos."
    else:
        # Verifica se a pasta de log foi criada (mesmo sem erros, pode indicar problemas de setup)
        if os.path.exists(log_folder):
            # Verifica se realmente existe um arquivo de log de *erros*
            log_files = [f for f in os.listdir(log_folder) if f.startswith(
                "archive_failures_") and f.endswith(".log")]
            if log_files:
                # Isso não deveria acontecer se error_count é 0, mas por segurança
                summary_message += f"\nAtenção: {len(log_files)} arquivo(s) de log encontrado(s) em '{log_folder}', embora nenhum erro tenha sido contado internamente. Verifique os logs."
            else:
                summary_message += f"\nOperação concluída sem erros registrados."
        else:
            summary_message += f"\nOperação concluída sem erros registrados (pasta de log não criada)."

    summary_message += "\n" + "-" * 30
    # --- Fim Construção da Mensagem Final ---

    # --- Exibe a mensagem final usando a janela auto-close ---
    # Não precisa mais dos prints finais no console
    # print("\nProcessamento concluído.")
    # log_files = [f for f in os.listdir(log_folder) if f.startswith("archive_failures_") and f.endswith(".log")] if os.path.exists(log_folder) else []
    # if log_files:
    #     print(f"Verifique o arquivo de log em '{log_folder}' para detalhes sobre arquivos que não foram movidos:")
    #     for log_f in sorted(log_files, reverse=True):
    #         print(f"- {log_f}")
    # elif os.path.exists(log_folder) and archiver.error_count == 0 : # Só diz que não há erros se a pasta existe e o contador é 0
    #      print(f"Nenhum erro registrado durante a execução (verificado em '{log_folder}').")

    show_auto_close_message(summary_message, 5000)  # Exibe por 15 segundos


if __name__ == "__main__":
    main()

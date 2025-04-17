import os
import shutil
import email
import logging
import re
from datetime import datetime

# Definir um comprimento máximo seguro para o caminho completo
MAX_PATH_LENGTH = 255
SAFE_FILENAME_MARGIN = 10  # Margem para evitar problemas exatos no limite
# Definir a pasta de monitoramento e a pasta de arquivamento
# Ajuste conforme necessário
WATCH_FOLDER = r"C:\Users\CEPOL\Documents\Arquivos do Outlook\Backup MSG"


class FileArchiver:
    def __init__(self, WATCH_FOLDER, archive_root, log_folder):
        self.watch_folder = WATCH_FOLDER
        self.archive_root = archive_root
        self.log_folder = log_folder
        self.setup_logger()

    def setup_logger(self):
        """Configura o logger para registrar apenas erros."""
        try:
            if not os.path.exists(self.log_folder):
                os.makedirs(self.log_folder)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            log_file = os.path.join(
                # Nome do arquivo alterado para clareza
                self.log_folder, f"archive_failures_{timestamp}.log")

            # Configura o logger principal
            self.logger = logging.getLogger(__name__)
            # Nível de log definido para ERROR
            self.logger.setLevel(logging.ERROR)

            # Remove handlers existentes para evitar duplicação se chamado novamente
            if self.logger.hasHandlers():
                self.logger.handlers.clear()

            # Cria o file handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
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

            # Não precisamos mais do BlankLineHandler
            # self.blank_line_handler = BlankLineHandler(self.logger)

        except Exception as e:
            # Se houver erro ao configurar o log, imprime no console
            print(
                f"ERRO CRÍTICO: Não foi possível configurar o logger em {self.log_folder}. Erro: {e}")
            # Define um logger nulo para evitar falhas posteriores
            self.logger = logging.getLogger('null')
            self.logger.addHandler(logging.NullHandler())

    def process_files(self):
        if not os.path.exists(self.watch_folder):
            # Loga o erro se a pasta de origem não existe
            self.logger.error(
                f"{self.watch_folder} - Motivo: Pasta de monitoramento não encontrada.")
            # print(f"ERRO: Pasta de monitoramento não encontrada: {self.watch_folder}")
            return

        # Itera apenas pelos arquivos na pasta WATCH_FOLDER
        for filename in os.listdir(self.watch_folder):
            file_path = os.path.join(self.watch_folder, filename)
            if os.path.isfile(file_path):
                # Ignora arquivos .ffs_db silenciosamente
                if file_path.lower().endswith(".ffs_db"):
                    continue
                # Não adiciona mais linhas em branco ou loga início de processamento
                self.process_file(file_path)
                # Não rastreia mais o último tipo processado

    def process_file(self, file_path):
        """Processa um único arquivo, chamando a função apropriada."""
        try:
            # Não loga mais o início do processamento
            if file_path.lower().endswith(".eml"):
                self.process_eml_file(file_path)
            else:
                self.process_other_file(file_path)
        except Exception as e:
            # Loga erro genérico no processamento do arquivo que impede a movimentação
            self.logger.error(
                f"{file_path} - Motivo: Erro inesperado durante o processamento inicial. Detalhes: {e}")

    def process_eml_file(self, eml_path):
        """Processa arquivos .eml para extrair data e mover."""
        msg = None
        try:
            # Tenta ler com UTF-8
            with open(eml_path, 'r', encoding='utf-8') as f:
                msg = email.message_from_file(f)
        except UnicodeDecodeError:
            try:
                # Se falhar, tenta com Latin-1
                with open(eml_path, 'r', encoding='latin-1') as f:
                    msg = email.message_from_file(f)
            except Exception as e:
                # Loga erro se a leitura falhar com ambos encodings
                self.logger.error(
                    f"{eml_path} - Motivo: Falha ao ler o arquivo (tentativas UTF-8 e Latin-1). Detalhes: {e}")
                return  # Impede a movimentação
        except Exception as e:
            # Loga erro genérico de leitura
            self.logger.error(
                f"{eml_path} - Motivo: Falha ao ler o arquivo. Detalhes: {e}")
            return  # Impede a movimentação

        # Se msg não foi lido com sucesso (caso raro, mas possível)
        if not msg:
            self.logger.error(
                f"{eml_path} - Motivo: Não foi possível interpretar o conteúdo do e-mail após leitura.")
            return  # Impede a movimentação

        date_str = msg.get("Date")
        # A falha na análise da data agora usa a data atual, não impede a movimentação,
        # então não logamos mais como erro aqui.
        # Passa o path para logs internos se necessário
        date_obj = self._parse_date(date_str, eml_path)

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        # Não precisa mais passar 'year'
        self.move_file_to_archive(eml_path, archive_folder)

    def _parse_date(self, date_str, file_path_for_log):
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

    def process_other_file(self, file_path):
        """Processa outros tipos de arquivo usando data de modificação."""
        try:
            modification_time = os.path.getmtime(file_path)
            date_obj = datetime.fromtimestamp(modification_time)
        except OSError as e:
            # Loga erro se não conseguir obter data de modificação
            self.logger.error(
                f"{file_path} - Motivo: Falha ao obter data de modificação. Detalhes: {e}")
            # Poderia optar por usar data atual ou retornar para não mover
            # Vamos retornar para garantir que só mova se tiver data válida
            return  # Impede a movimentação
            # date_obj = datetime.now() # Alternativa: usar data atual

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        # Não precisa mais passar 'year'
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

        # 5. Garante que o nome não seja vazio após a limpeza
        if not sanitized:
            # Se o nome original era apenas "msg " ou algo similar que foi removido
            sanitized = "arquivo_renomeado"  # Ou gerar um nome único com timestamp
        # Não loga mais a sanitização
        return sanitized

    def _truncate_filename(self, folder_path, filename, max_len):
        """Trunca o nome do arquivo se o caminho completo exceder max_len."""
        base, ext = os.path.splitext(filename)
        full_path = os.path.join(folder_path, filename)
        full_path_len = len(full_path)

        if full_path_len <= max_len:
            return filename  # Não precisa truncar

        available_len_for_base = max_len - \
            (len(folder_path) + len(os.sep) + len(ext))

        if available_len_for_base <= 0:
            # Loga erro se não houver espaço nem para a base truncada
            # A mensagem de erro será logada na chamada de shutil.move se falhar,
            # mas podemos logar aqui também para mais detalhes.
            # self.logger.error(f"{full_path} - Motivo: Caminho do destino excede o limite ({max_len}) e não é possível truncar o nome do arquivo.")
            # Retornar o nome original pode causar erro em shutil.move, que será logado.
            # Ou retornar um nome muito curto para tentar evitar falha total?
            # Vamos retornar o nome original e deixar o erro ocorrer em shutil.move.
            # return f"trunc_{datetime.now().strftime('%f')}{ext}" # Opção alternativa
            return filename  # Deixa o erro ocorrer no move

        truncated_base = base[:available_len_for_base]
        truncated_filename = f"{truncated_base}{ext}"
        # Não loga mais o aviso de truncamento
        return truncated_filename

    def move_file_to_archive(self, file_path, archive_folder):
        """Move o arquivo para a pasta de destino, tratando sanitização, truncamento e duplicados."""
        # Cria as pastas de destino se não existirem
        archive_year_folder = os.path.dirname(archive_folder)
        try:
            # Cria a pasta do ano
            if not os.path.exists(archive_year_folder):
                os.makedirs(archive_year_folder)
                # print(f"Pasta {archive_year_folder} criada.")
            # Cria a pasta do mês
            if not os.path.exists(archive_folder):
                os.makedirs(archive_folder)
                # print(f"Pasta {archive_folder} criada.")
        except OSError as e:
            # Loga erro se não conseguir criar as pastas
            self.logger.error(
                f"{file_path} - Motivo: Erro ao criar pasta de destino '{archive_folder}'. Detalhes: {e}")
            return  # Impede a movimentação

        original_filename = os.path.basename(file_path)
        # 1. Sanitizar (agora remove 'msg ' também)
        sanitized_filename = self._sanitize_filename(original_filename)
        # Não loga mais a sanitização

        # 2. Truncar (considerando a pasta de destino)
        final_filename = self._truncate_filename(
            archive_folder, sanitized_filename, MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN)

        destination_path = os.path.join(archive_folder, final_filename)

        # 3. Verificar duplicidade e renomear se necessário
        counter = 1
        base, ext = os.path.splitext(final_filename)
        # Guarda o nome antes do loop de duplicados
        temp_final_filename = final_filename
        while os.path.exists(destination_path):
            # Tenta adicionar um contador
            new_filename_base = f"{base}_{counter}"
            potential_new_filename = f"{new_filename_base}{ext}"

            # Verifica se o nome com contador ainda cabe
            if len(os.path.join(archive_folder, potential_new_filename)) <= MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN:
                final_filename = potential_new_filename
            else:
                # Se o contador não cabe, tenta truncar a base original + timestamp
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                # Usa a base do nome *antes* de adicionar contadores para truncar
                base_original_sem_contador, ext_original = os.path.splitext(
                    temp_final_filename)
                nome_com_timestamp = f"{base_original_sem_contador}_{timestamp}{ext_original}"
                final_filename = self._truncate_filename(
                    archive_folder, nome_com_timestamp, MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN)

                # Verifica se o nome truncado com timestamp já existe (muito raro)
                if os.path.exists(os.path.join(archive_folder, final_filename)):
                    # Loga erro se não conseguir gerar nome único
                    self.logger.error(
                        f"{file_path} - Motivo: Conflito de nome irresolúvel em '{archive_folder}' após tentar adicionar contador e timestamp (arquivo duplicado: {original_filename}).")
                    return  # Impede a movimentação

            destination_path = os.path.join(archive_folder, final_filename)
            # Não loga mais o aviso de duplicado/renomeação
            counter += 1

        # 4. Mover o arquivo
        try:
            shutil.move(file_path, destination_path)
            # Não loga mais a movimentação bem-sucedida
            # print(f"Arquivo {os.path.basename(destination_path)} arquivado em {archive_folder}")
        except Exception as e:
            # Loga erro se a movimentação falhar
            self.logger.error(
                f"{file_path} - Motivo: Falha ao mover para '{destination_path}'. Detalhes: {e}")


def main():
    # Mantenha ou ajuste as pastas conforme necessário
    archive_root = WATCH_FOLDER
    log_folder = os.path.join(archive_root, "ERROS")

    # Cria a pasta WATCH_FOLDER se não existir (para testes)
    if not os.path.exists(WATCH_FOLDER):
        try:
            os.makedirs(WATCH_FOLDER)
            print(f"Pasta de monitoramento {WATCH_FOLDER} criada para teste.")
            # Crie alguns arquivos .eml ou outros para teste dentro dela
            with open(os.path.join(WATCH_FOLDER, "msg teste1.eml"), "w", encoding='utf-8') as f:
                f.write(
                    "Date: Mon, 1 Jan 2024 10:00:00 +0000\nSubject: Teste\n\nCorpo do email.")
            with open(os.path.join(WATCH_FOLDER, "MSG Arquivo com espaço.txt"), "w", encoding='utf-8') as f:
                f.write("Conteúdo.")
            long_name = "msg " + "a" * 240 + ".txt"
            with open(os.path.join(WATCH_FOLDER, long_name), "w", encoding='utf-8') as f:
                f.write("Longo.")
            with open(os.path.join(WATCH_FOLDER, "arquivo sem prefixo.txt"), "w", encoding='utf-8') as f:
                f.write("Normal.")
        except OSError as e:
            print(f"Erro ao criar pasta de monitoramento {WATCH_FOLDER}: {e}")

    archiver = FileArchiver(WATCH_FOLDER, archive_root, log_folder)
    archiver.process_files()
    print("\nProcessamento concluído.")

    # Informa onde verificar os logs de falha
    log_files = [f for f in os.listdir(log_folder) if f.startswith(
        "archive_failures_") and f.endswith(".log")] if os.path.exists(log_folder) else []

    # Preparar mensagem para a caixa de diálogo
    message = "Processamento concluído."
    if log_files:
        message += f"\n\nVerifique o arquivo de log em '{log_folder}' para detalhes sobre arquivos que não foram movidos:\n"
        for log_f in sorted(log_files, reverse=True):
            message += f"- {log_f}\n"
    elif os.path.exists(log_folder):
        message += f"\n\nNenhum erro registrado durante a execução (verificado em '{log_folder}')."

    # Criar janela de mensagem com fechamento automático
    show_auto_close_message(message, 5000)  # 5000 ms = 5 segundos


def show_auto_close_message(message, timeout):
    """
    Exibe uma mensagem que se fecha automaticamente após o tempo especificado.

    Args:
        message: Texto da mensagem
        timeout: Tempo em milissegundos antes do fechamento automático
    """
    # Importar tkinter aqui para não afetar o resto do código
    import tkinter as tk

    # Criar janela
    root = tk.Tk()
    root.title("Arquivamento Concluído")

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
    frame = tk.Frame(root, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    # Adicionar contador regressivo
    countdown_var = tk.StringVar()
    countdown_var.set(f"Esta mensagem se fechará em {timeout//1000} segundos")

    # Título
    title_label = tk.Label(
        frame, text="Arquivamento Concluído", font=("Arial", 14, "bold"))
    title_label.pack(pady=(0, 10))

    # Mensagem principal
    msg_label = tk.Label(frame, text=message, justify=tk.LEFT, wraplength=450)
    msg_label.pack(pady=10)

    # Contador
    countdown_label = tk.Label(frame, textvariable=countdown_var, fg="gray")
    countdown_label.pack(pady=(10, 0))

    # Botão para fechar manualmente
    close_button = tk.Button(frame, text="Fechar", command=root.destroy)
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

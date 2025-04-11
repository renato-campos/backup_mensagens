import os
import shutil
import email
import logging
import re  # Importar re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# Definir constantes
MAX_PATH_LENGTH = 255
SAFE_FILENAME_MARGIN = 10

class FileArchiver:
    def __init__(self, watch_folder, archive_root, log_folder):
        self.watch_folder = watch_folder
        # No arquiva_subpastas, archive_root é geralmente o mesmo que watch_folder
        self.archive_root = archive_root
        self.log_folder = log_folder
        self.setup_logger()
        # Pastas a serem ignoradas durante o processamento recursivo
        self.excluded_folders = ["anos anteriores", "erros"]

    # setup_logger substituído pela versão focada em erros
    def setup_logger(self):
        """Configura o logger para registrar apenas erros."""
        try:
            if not os.path.exists(self.log_folder):
                os.makedirs(self.log_folder)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            log_file = os.path.join(
                self.log_folder, f"archive_failures_{timestamp}.log") # Nome do arquivo alterado

            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.ERROR) # Nível de log definido para ERROR

            if self.logger.hasHandlers():
                self.logger.handlers.clear()

            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.ERROR) # Nível do handler também definido para ERROR

            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - Arquivo: %(message)s", # Formato ajustado
                datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)
            # BlankLineHandler removido

        except Exception as e:
            print(f"ERRO CRÍTICO: Não foi possível configurar o logger em {self.log_folder}. Erro: {e}")
            self.logger = logging.getLogger('null')
            self.logger.addHandler(logging.NullHandler())

    # process_files adaptado para chamar process_folder e remover logging INFO
    def process_files(self):
        if not os.path.exists(self.watch_folder):
            # Log de erro mantido
            self.logger.error(f"{self.watch_folder} - Motivo: Pasta de monitoramento não encontrada.")
            print(f"ERRO: Pasta de monitoramento não encontrada: {self.watch_folder}")
            return

        # archive_root geralmente é o mesmo que watch_folder neste script
        if not os.path.exists(self.archive_root):
             # Log de erro se a pasta raiz (destino) não existir
             self.logger.error(f"{self.archive_root} - Motivo: Pasta raiz de arquivamento não encontrada.")
             print(f"ERRO: Pasta raiz de arquivamento não encontrada: {self.archive_root}")
             return

        # Inicia o processo recursivo a partir da pasta raiz/monitorada
        self.process_folder(self.watch_folder)

    # process_folder adaptado para remover logging INFO e BlankLineHandler
    def process_folder(self, folder_path):
        # Remove logger.info sobre processar pasta
        try:
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    # Exclui pastas especificadas (case-insensitive)
                    if item.lower() not in self.excluded_folders:
                        # Chamada recursiva para subpastas
                        self.process_folder(item_path)
                elif os.path.isfile(item_path):
                    # Ignora .ffs_db silenciosamente
                    if item_path.lower().endswith(".ffs_db"):
                        continue
                    self.process_file(item_path)
        except OSError as e:
             # Loga erro se não conseguir listar o diretório
             self.logger.error(f"{folder_path} - Motivo: Erro ao acessar ou listar pasta. Detalhes: {e}")
        except Exception as e:
             # Loga erro genérico ao processar a pasta
             self.logger.error(f"{folder_path} - Motivo: Erro inesperado ao processar pasta. Detalhes: {e}")
        # Remove chamada ao BlankLineHandler

    # process_file adaptado para remover logging INFO
    def process_file(self, file_path):
        try:
            # Remove logger.info sobre processar arquivo
            if file_path.lower().endswith(".eml"):
                self.process_eml_file(file_path)
            else:
                self.process_other_file(file_path)
        except Exception as e:
            # Log de erro mantido e adaptado
            self.logger.error(f"{file_path} - Motivo: Erro inesperado durante o processamento inicial. Detalhes: {e}")

    # process_eml_file adaptado com _parse_date, logging de erro refinado e verificação de pasta
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
                # Log de erro mantido e adaptado
                self.logger.error(f"{eml_path} - Motivo: Falha ao ler o arquivo (tentativas UTF-8 e Latin-1). Detalhes: {e}")
                return
        except Exception as e:
            # Log de erro mantido e adaptado
            self.logger.error(f"{eml_path} - Motivo: Falha ao ler o arquivo. Detalhes: {e}")
            return

        if not msg:
             # Log de erro adicionado
             self.logger.error(f"{eml_path} - Motivo: Não foi possível interpretar o conteúdo do e-mail após leitura.")
             return

        date_str = msg.get("Date")
        # Usa _parse_date (não loga mais erro aqui se falhar)
        date_obj = self._parse_date(date_str, eml_path)

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        # archive_root é a pasta base onde as pastas de ano/mês serão criadas
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        # Verifica se o arquivo JÁ ESTÁ na pasta de destino correta
        # Compara os caminhos absolutos normalizados para evitar problemas com case/separadores
        current_folder_abs = os.path.normpath(os.path.abspath(os.path.dirname(eml_path)))
        target_folder_abs = os.path.normpath(os.path.abspath(archive_folder))

        if current_folder_abs == target_folder_abs:
            # Remove logger.info, apenas ignora silenciosamente
            return

        # Chama move_file_to_archive sem 'year'
        self.move_file_to_archive(eml_path, archive_folder)

    # Adicionado _parse_date (igual ao dos outros scripts)
    def _parse_date(self, date_str, file_path_for_log):
        """Tenta analisar a string de data. Retorna datetime.now() em caso de falha."""
        if not date_str:
            return datetime.now()

        formats_to_try = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%d %b %Y %H:%M:%S %z",
            "%d %b %Y %H:%M:%S %Z",
        ]

        try:
            parsed_dt = email.utils.parsedate_to_datetime(date_str)
            if parsed_dt:
                return parsed_dt
        except Exception:
            pass

        for fmt in formats_to_try:
            try:
                cleaned_date_str = re.sub(r'\s*\([^)]*\)\s*$', '', date_str).strip()
                return datetime.strptime(cleaned_date_str, fmt)
            except ValueError:
                continue

        return datetime.now()

    # process_other_file adaptado com tratamento de erro e verificação de pasta
    def process_other_file(self, file_path):
        try:
            modification_time = os.path.getmtime(file_path)
            date_obj = datetime.fromtimestamp(modification_time)
        except OSError as e:
             # Log de erro adicionado
             self.logger.error(f"{file_path} - Motivo: Falha ao obter data de modificação. Detalhes: {e}")
             return # Impede a movimentação

        year = date_obj.strftime("%Y")
        year_month = date_obj.strftime("%Y-%m")
        archive_year_folder = os.path.join(self.archive_root, year)
        archive_folder = os.path.join(archive_year_folder, year_month)

        # Verifica se o arquivo JÁ ESTÁ na pasta de destino correta
        current_folder_abs = os.path.normpath(os.path.abspath(os.path.dirname(file_path)))
        target_folder_abs = os.path.normpath(os.path.abspath(archive_folder))

        if current_folder_abs == target_folder_abs:
            # Remove logger.info, apenas ignora silenciosamente
            return

        # Chama move_file_to_archive sem 'year'
        self.move_file_to_archive(file_path, archive_folder)

    # Adicionado _sanitize_filename (igual ao dos outros scripts)
    def _sanitize_filename(self, filename):
        """Remove ou substitui caracteres inválidos e o prefixo 'msg '."""
        sanitized = re.sub(r'^msg\s+', '', filename, flags=re.IGNORECASE)
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)
        sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)
        sanitized = sanitized.strip()
        if not sanitized:
            sanitized = "arquivo_renomeado"
        return sanitized

    # Adicionado _truncate_filename (igual ao dos outros scripts)
    def _truncate_filename(self, folder_path, filename, max_len):
        """Trunca o nome do arquivo se o caminho completo exceder max_len."""
        base, ext = os.path.splitext(filename)
        full_path = os.path.join(folder_path, filename)
        full_path_len = len(full_path)

        if full_path_len <= max_len:
            return filename

        available_len_for_base = max_len - (len(folder_path) + len(os.sep) + len(ext))

        if available_len_for_base <= 0:
             self.logger.error(f"Não é possível criar um nome de arquivo válido para '{filename}' na pasta '{folder_path}' devido ao limite de comprimento ({max_len}).")
             return filename # Deixa o erro ocorrer no move

        truncated_base = base[:available_len_for_base]
        truncated_filename = f"{truncated_base}{ext}"
        return truncated_filename

    # move_file_to_archive substituído pela versão mais robusta
    def move_file_to_archive(self, file_path, archive_folder):
        """Move o arquivo para a pasta de destino, tratando sanitização, truncamento e duplicados."""
        archive_year_folder = os.path.dirname(archive_folder)
        try:
            # Cria pastas (sem alterações na lógica, mas erros são logados)
            if not os.path.exists(archive_year_folder):
                os.makedirs(archive_year_folder)
                print(f"Pasta {archive_year_folder} criada.")
            if not os.path.exists(archive_folder):
                os.makedirs(archive_folder)
                print(f"Pasta {archive_folder} criada.")
        except OSError as e:
            self.logger.error(f"{file_path} - Motivo: Erro ao criar pasta de destino '{archive_folder}'. Detalhes: {e}")
            return

        original_filename = os.path.basename(file_path)
        sanitized_filename = self._sanitize_filename(original_filename)

        # 1. Truncar o nome sanitizado SE necessário
        max_allowed_path = MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN
        final_filename = self._truncate_filename(archive_folder, sanitized_filename, max_allowed_path)

        destination_path = os.path.join(archive_folder, final_filename)

        # 2. Verificar duplicidade e renomear se necessário
        counter = 1
        base, ext = os.path.splitext(final_filename)
        temp_final_filename = final_filename # Guarda o nome antes do loop

        while os.path.exists(destination_path):
            # Tenta adicionar um contador
            new_filename_base = f"{base}_{counter}"
            potential_new_filename = f"{new_filename_base}{ext}"
            potential_full_path = os.path.join(archive_folder, potential_new_filename)

            # Verifica se o nome com contador ainda cabe
            if len(potential_full_path) <= max_allowed_path:
                 final_filename = potential_new_filename
                 # destination_path será atualizado antes da próxima verificação ou do move
            else:
                 # Se o contador não cabe, tenta truncar a base original + timestamp
                 timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                 base_original_sem_contador, ext_original = os.path.splitext(temp_final_filename)
                 nome_com_timestamp = f"{base_original_sem_contador}_{timestamp}{ext_original}"
                 # Trunca *agora* se o nome com timestamp for muito longo
                 final_filename = self._truncate_filename(archive_folder, nome_com_timestamp, max_allowed_path)
                 # destination_path será atualizado antes da próxima verificação ou do move

                 # Verifica se o nome truncado com timestamp já existe (muito raro)
                 # Recalcula o path com o nome final (truncado com timestamp)
                 temp_destination_path = os.path.join(archive_folder, final_filename)
                 if os.path.exists(temp_destination_path):
                     self.logger.error(f"{file_path} - Motivo: Conflito de nome irresolúvel em '{archive_folder}' após tentar adicionar contador e timestamp (arquivo duplicado: {original_filename}).")
                     return
                 else:
                     # Achou nome único com timestamp, atualiza destination_path e sai do loop
                     destination_path = temp_destination_path
                     break # Sai do while loop

            # Atualiza destination_path para a próxima verificação no while ou para o move final
            destination_path = os.path.join(archive_folder, final_filename)
            counter += 1


        # 3. Mover o arquivo
        try:
            shutil.move(file_path, destination_path)
            # Remove logger.info sobre mover
            print(f"Arquivo {os.path.basename(destination_path)} arquivado em {archive_folder}")
        except Exception as e:
            # Log de erro mantido e adaptado
            self.logger.error(f"{file_path} - Motivo: Falha ao mover para '{destination_path}'. Detalhes: {e}")


# Classe BlankLineHandler removida

# select_folder permanece o mesmo
def select_folder():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    return folder_selected

# main adaptado para usar a pasta selecionada como watch e archive root
def main():
    watch_folder = select_folder()
    if not watch_folder:
        print("Nenhuma pasta selecionada. Encerrando.")
        return

    # Define archive_root como a mesma pasta selecionada
    archive_root = watch_folder

    log_folder = os.path.join(archive_root, "ERROS")

    # Não precisa criar archive_root, pois é a pasta selecionada
    # if not os.path.exists(archive_root):
    #     os.makedirs(archive_root)
    #     print(f"Pasta {archive_root} criada.")

    archiver = FileArchiver(watch_folder, archive_root, log_folder)
    archiver.process_files()
    print("\nProcessamento concluído.")

    # Adiciona verificação e mensagem sobre logs de falha
    log_files = [f for f in os.listdir(log_folder) if f.startswith("archive_failures_") and f.endswith(".log")] if os.path.exists(log_folder) else []
    if log_files:
        print(f"Verifique o arquivo de log em '{log_folder}' para detalhes sobre arquivos que não foram movidos:")
        for log_f in sorted(log_files, reverse=True):
            print(f"- {log_f}")
    elif os.path.exists(log_folder):
         print(f"Nenhum erro registrado durante a execução (verificado em '{log_folder}').")


if __name__ == "__main__":
    main()

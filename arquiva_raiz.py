import os
import shutil
import logging
import re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

# --- Constantes ---
MAX_PATH_LENGTH = 255  # Limite máximo de caracteres para um caminho no Windows
SAFE_FILENAME_MARGIN = 10  # Margem de segurança para evitar atingir o limite exato
# --- Fim Constantes ---


class FileMover:
    def __init__(self, root_folder, log_folder):
        # Pasta principal onde os arquivos serão centralizados
        self.root_folder = root_folder
        # Pasta para salvar os logs (geralmente 'ERROS' dentro da root_folder)
        self.log_folder = log_folder
        self.setup_logger()
        # Pastas a serem ignoradas durante o processamento
        self.excluded_folders = ["erros", "anos anteriores"]

    def setup_logger(self):
        """Configura o logger para registrar eventos importantes."""
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # Define o nome do arquivo de log com timestamp
        log_file = os.path.join(
            self.log_folder, f"process_root_log_{timestamp}.log")

        self.logger = logging.getLogger(__name__)
        if not self.logger.hasHandlers():
            # Configura o nível mínimo de log a ser capturado (INFO pega sanitização, WARNING pega truncamento/duplicados, ERROR pega falhas)
            self.logger.setLevel(logging.INFO)
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            # Handler processa logs a partir deste nível
            file_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _sanitize_filename(self, filename):
        """Remove ou substitui caracteres inválidos e o prefixo 'msg '."""
        sanitized = re.sub(r'^msg\s+', '', filename, flags=re.IGNORECASE)
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', sanitized)
        sanitized = re.sub(r'[\x00-\x1f]', '', sanitized)
        sanitized = sanitized.strip()
        if not sanitized:
            # Gera um nome único se o nome ficar vazio após a limpeza
            sanitized = f"arquivo_renomeado_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        return sanitized

    def _truncate_filename(self, folder_path, filename, max_len):
        """Trunca o nome do arquivo se o caminho completo exceder max_len."""
        base, ext = os.path.splitext(filename)
        full_path = os.path.join(folder_path, filename)
        full_path_len = len(full_path)

        if full_path_len <= max_len:
            return filename  # Não precisa truncar

        # Calcula o espaço disponível para a base do nome do arquivo
        available_len_for_base = max_len - \
            (len(folder_path) + len(os.sep) + len(ext))

        if available_len_for_base <= 0:
            # Loga erro se não for possível truncar (caminho da pasta já é muito longo)
            self.logger.error(
                f"Não é possível criar um nome de arquivo válido para '{filename}' na pasta '{folder_path}' devido ao limite de comprimento ({max_len}). O caminho da pasta é muito longo.")
            return filename  # Retorna original, o erro ocorrerá no move/rename

        # Guarda o nome original para registrar no log de aviso
        original_filename_for_log = filename
        truncated_base = base[:available_len_for_base]
        truncated_filename = f"{truncated_base}{ext}"
        # Loga um aviso informando que o nome foi truncado
        self.logger.warning(
            f"Nome do arquivo truncado devido ao limite de comprimento do caminho: '{original_filename_for_log}' -> '{truncated_filename}' em '{folder_path}'")
        return truncated_filename

    def process_files_in_root(self):
        """Processa arquivos: move de subpastas para a raiz e renomeia (sanitiza/trunca) arquivos na raiz e os movidos."""
        if not os.path.exists(self.root_folder):
            self.logger.error(
                f"Pasta raiz não encontrada: {self.root_folder}")
            print(f"ERRO: Pasta raiz não encontrada: {self.root_folder}")
            return

        processed_files_count = 0
        renamed_files_count = 0
        moved_files_count = 0
        error_count = 0

        # Itera por todas as pastas, incluindo a raiz (`topdown=True` permite modificar `dirs`)
        for root, dirs, files in os.walk(self.root_folder, topdown=True):
            # Remove pastas excluídas da lista `dirs` para não entrar nelas
            dirs[:] = [d for d in dirs if d.lower(
            ) not in self.excluded_folders and os.path.join(root, d) != self.log_folder]

            for original_filename in files:
                source_path = os.path.join(root, original_filename)

                # Ignora arquivos dentro da pasta de log
                if os.path.dirname(source_path) == self.log_folder:
                    continue

                # 1. Aplica sanitização ao nome do arquivo
                sanitized_filename = self._sanitize_filename(original_filename)
                sanitization_occurred = (
                    original_filename != sanitized_filename)
                if sanitization_occurred:
                    # Loga apenas se o nome foi realmente alterado pela sanitização
                    self.logger.info(
                        f"Sanitizando nome: '{original_filename}' -> '{sanitized_filename}' (Origem: '{root}')")

                # 2. Aplica truncamento ao nome sanitizado, considerando o destino (root_folder)
                max_allowed_path = MAX_PATH_LENGTH - SAFE_FILENAME_MARGIN
                target_base_filename = self._truncate_filename(
                    self.root_folder, sanitized_filename, max_allowed_path)
                # Nome após sanitização e truncamento inicial
                final_filename = target_base_filename

                potential_destination_path = os.path.join(
                    self.root_folder, final_filename)

                # 3. Pula se o arquivo já está na raiz e o nome final é o mesmo (nenhuma ação necessária)
                if root == self.root_folder and source_path == potential_destination_path:
                    continue

                # 4. Verifica se já existe um arquivo com o nome final no destino (root_folder)
                destination_path = potential_destination_path
                counter = 1
                temp_base_filename_for_duplicates = final_filename
                renamed_due_to_duplicate = False

                while os.path.exists(destination_path):
                    renamed_due_to_duplicate = True  # Indica que precisou renomear por duplicidade
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                    base_original_dup, ext_original_dup = os.path.splitext(
                        temp_base_filename_for_duplicates)
                    # Gera um novo nome com timestamp
                    nome_com_timestamp = f"{base_original_dup}_{timestamp}{ext_original_dup}"

                    # Trunca o nome com timestamp novamente, se necessário
                    final_filename = self._truncate_filename(
                        self.root_folder, nome_com_timestamp, max_allowed_path)
                    destination_path = os.path.join(
                        self.root_folder, final_filename)

                    # Verifica se o nome com timestamp ainda colide (raro)
                    if os.path.exists(destination_path):
                        self.logger.error(
                            f"Erro ao tentar renomear arquivo duplicado '{temp_base_filename_for_duplicates}' após adicionar timestamp. Conflito irresolúvel ou caminho muito longo. Pulando '{source_path}'.")
                        error_count += 1
                        final_filename = None  # Marca para pular este arquivo
                        break  # Sai do loop de renomeação
                    else:
                        # Loga aviso sobre a renomeação por duplicidade
                        self.logger.warning(
                            f"Arquivo duplicado ou conflito de nome em '{self.root_folder}' para '{temp_base_filename_for_duplicates}'. Renomeando para '{final_filename}' (Origem: '{source_path}')")
                        break  # Sai do loop, nome único encontrado

                    counter += 1
                    # Limite de segurança para evitar loops infinitos
                    if counter > 5:
                        self.logger.error(
                            f"Loop inesperado ao tentar renomear '{temp_base_filename_for_duplicates}'. Pulando '{source_path}'.")
                        error_count += 1
                        final_filename = None
                        break

                # Pula para o próximo arquivo se houve erro irresolúvel na renomeação
                if final_filename is None:
                    continue

                # Atualiza o caminho de destino com o nome final definitivo
                destination_path = os.path.join(
                    self.root_folder, final_filename)

                # 5. Executa a ação: Mover (se veio de subpasta) ou Renomear (se já estava na raiz)
                try:
                    if root == self.root_folder:
                        # Renomeia o arquivo dentro da pasta raiz, se o nome mudou
                        if source_path != destination_path:
                            os.rename(source_path, destination_path)
                            renamed_files_count += 1
                            processed_files_count += 1
                    else:
                        # Move o arquivo da subpasta para a raiz
                        shutil.move(source_path, destination_path)
                        moved_files_count += 1
                        processed_files_count += 1

                except Exception as e:
                    # Loga erro se a movimentação ou renomeação falhar
                    action_verb = "renomear" if root == self.root_folder else "mover"
                    self.logger.error(
                        f"Erro ao {action_verb} o arquivo '{source_path}' para '{destination_path}': {e}")
                    error_count += 1

        # Exibe um resumo da operação para o usuário
        print("-" * 30)
        if processed_files_count > 0:
            print(f"Processamento concluído:")
            if renamed_files_count > 0:
                print(
                    f"- {renamed_files_count} arquivos renomeados na pasta raiz.")
            if moved_files_count > 0:
                print(
                    f"- {moved_files_count} arquivos movidos das subpastas para a raiz.")
        else:
            print("Nenhum arquivo precisou ser movido ou renomeado.")

        if error_count > 0:
            print(
                f"\nAtenção: Ocorreram {error_count} erros durante a operação. Verifique o log em '{self.log_folder}'.")
        else:
            # Verifica se algum log foi gerado (mesmo sem erros fatais)
            log_file_exists = any(fname.startswith("process_root_log_") for fname in os.listdir(
                self.log_folder)) if os.path.exists(self.log_folder) else False
            if log_file_exists:
                print(
                    f"\nOperação concluída. Logs de sanitização, truncamento ou renomeação por duplicidade podem ter sido gerados em '{self.log_folder}'.")
            else:
                print(
                    "\nOperação concluída sem erros ou necessidade de alterações nos nomes dos arquivos.")

        # Remove pastas vazias somente se arquivos foram movidos
        if moved_files_count > 0:
            self.remove_empty_folders()
        else:
            print("Nenhuma pasta vazia para remover (nenhum arquivo foi movido).")

    def remove_empty_folders(self):
        """Remove pastas vazias APENAS das subpastas de onde os arquivos foram movidos."""
        print("Verificando pastas vazias para remoção...")
        removed_count = 0
        error_remove_count = 0
        # Itera de baixo para cima (`topdown=False`) para remover subpastas antes das pastas pai
        for root, dirs, _ in os.walk(self.root_folder, topdown=False):
            # Garante que não tentaremos remover pastas excluídas ou a pasta de log
            dirs[:] = [d for d in dirs if d.lower(
            ) not in self.excluded_folders and os.path.join(root, d) != self.log_folder]

            # Não remove a pasta raiz principal nem a pasta de log
            if root == self.root_folder or root == self.log_folder:
                continue

            current_folder_name = os.path.basename(root)
            # Verifica novamente se a pasta atual não está na lista de exclusão
            if current_folder_name.lower() not in self.excluded_folders:
                try:
                    # Tenta remover a pasta se estiver vazia
                    if not os.listdir(root):
                        os.rmdir(root)
                        removed_count += 1
                except OSError as e:
                    # Loga erro se não conseguir verificar ou remover a pasta
                    self.logger.error(
                        f"Erro ao verificar ou remover a pasta '{root}': {e}")
                    error_remove_count += 1

        if removed_count > 0:
            print(
                f"Remoção de pastas vazias concluída. {removed_count} pastas removidas.")
        else:
            print("Nenhuma pasta vazia encontrada para remover.")

        if error_remove_count > 0:
            print(
                f"Atenção: Ocorreram {error_remove_count} erros durante a remoção de pastas vazias. Verifique o log.")


def select_folder():
    """Abre uma janela para o usuário selecionar uma pasta."""
    root = tk.Tk()
    root.withdraw()  # Oculta a janela principal do Tkinter
    folder_selected = filedialog.askdirectory(title="Selecione a Pasta Raiz")
    root.destroy()  # Fecha a instância do Tkinter
    return folder_selected


def main():
    print("Selecionando a pasta raiz para centralizar e sanitizar os arquivos...")
    root_folder = select_folder()
    if not root_folder:
        print("Nenhuma pasta selecionada. Encerrando.")
        return

    # Define a pasta de logs como 'ERROS' dentro da pasta raiz selecionada
    log_folder = os.path.join(root_folder, "ERROS")

    if not os.path.exists(root_folder):
        # Verificação adicional caso a pasta seja removida entre a seleção e o uso
        print(f"ERRO: A pasta selecionada {root_folder} não foi encontrada.")
        return

    print(f"Pasta raiz selecionada: {root_folder}")
    print(f"Os logs de erros e alterações serão salvos em: {log_folder}")
    print("Iniciando o processo...")

    mover = FileMover(root_folder, log_folder)
    mover.process_files_in_root()  # Chama o método principal da classe

    print("\nProcesso concluído.")
    print(
        f"Verifique o arquivo de log em '{log_folder}' para detalhes sobre erros ou alterações realizadas nos nomes dos arquivos.")


if __name__ == "__main__":
    main()

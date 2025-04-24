import os
import shutil
import logging
import re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

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

    # Métodos públicos (API da classe)
    def process_files_in_root(self):
        """Processa arquivos: move de subpastas para a raiz e renomeia (sanitiza/trunca) arquivos na raiz e os movidos."""
        if not os.path.exists(self.root_folder):
            self.logger.error(
                f"Pasta raiz não encontrada: {self.root_folder}")
            # print(f"ERRO: Pasta raiz não encontrada: {self.root_folder}")
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
        summary_message = "-" * 30 + "\n"
        if processed_files_count > 0:
            summary_message += f"Processamento concluído:\n"
            if renamed_files_count > 0:
                summary_message += f"- {renamed_files_count} arquivos renomeados na pasta raiz.\n"
            if moved_files_count > 0:
                summary_message += f"- {moved_files_count} arquivos movidos das subpastas para a raiz.\n"
        else:
            summary_message += "Nenhum arquivo precisou ser movido ou renomeado.\n"

        if error_count > 0:
            summary_message += f"\nAtenção: Ocorreram {error_count} erros durante a operação. Verifique o log em '{self.log_folder}'.\n"
        else:
            # Verifica se algum log foi gerado (mesmo sem erros fatais)
            log_file_exists = any(fname.startswith("process_root_log_") for fname in os.listdir(
                self.log_folder)) if os.path.exists(self.log_folder) else False
            if log_file_exists:
                summary_message += f"\nOperação concluída. Logs de sanitização, truncamento ou renomeação por duplicidade podem ter sido gerados em '{self.log_folder}'.\n"
            else:
                summary_message += "\nOperação concluída sem erros ou necessidade de alterações nos nomes dos arquivos.\n"

        # Armazene a mensagem para uso posterior
        self.summary_message = summary_message

        # Remove pastas vazias somente se arquivos foram movidos
        if moved_files_count > 0:
            empty_folders_message = self.remove_empty_folders()
            self.summary_message += "\n" + empty_folders_message
        else:
            self.summary_message += "\nNenhuma pasta vazia para remover (nenhum arquivo foi movido)."

    def remove_empty_folders(self):
        """Remove pastas vazias APENAS das subpastas de onde os arquivos foram movidos."""
        message = "Verificando pastas vazias para remoção...\n"
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
            message += f"Remoção de pastas vazias concluída. {removed_count} pastas removidas.\n"
        else:
            message += "Nenhuma pasta vazia encontrada para remover.\n"

        if error_remove_count > 0:
            message += f"Atenção: Ocorreram {error_remove_count} erros durante a remoção de pastas vazias. Verifique o log.\n"

        return message

    # Métodos privados auxiliares
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


def select_folder():
    """Abre uma janela para o usuário selecionar uma pasta."""
    root = tk.Tk()
    root.withdraw()  # Oculta a janela principal do Tkinter
    folder_selected = filedialog.askdirectory(title="Selecione a Pasta Raiz")
    root.destroy()  # Fecha a instância do Tkinter
    return folder_selected


def main():
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Seleção de Pasta",
                        "Selecionando a pasta raiz para centralizar e sanitizar os arquivos...")

    root_folder = select_folder()
    if not root_folder:
        messagebox.showinfo("Operação Cancelada",
                            "Nenhuma pasta selecionada. Encerrando.")
        root.destroy()
        return

    # Define a pasta de logs como 'ERROS' dentro da pasta raiz selecionada
    log_folder = os.path.join(root_folder, "ERROS")

    if not os.path.exists(root_folder):
        # Verificação adicional caso a pasta seja removida entre a seleção e o uso
        messagebox.showerror("Erro",
                             f"ERRO: A pasta selecionada {root_folder} não foi encontrada.")
        root.destroy()
        return

    info_message = f"Pasta raiz selecionada: {root_folder}\n"
    info_message += f"Os logs de erros e alterações serão salvos em: {log_folder}\n"
    info_message += "Iniciando o processo..."

    messagebox.showinfo("Processo Iniciado", info_message)

    mover = FileMover(root_folder, log_folder)
    mover.process_files_in_root()  # Chama o método principal da classe

    # Verificar se existem logs para informar ao usuário
    log_files = [f for f in os.listdir(log_folder) if f.startswith(
        "process_root_log_") and f.endswith(".log")] if os.path.exists(log_folder) else []

    final_message = mover.summary_message + "\n\n"
    if log_files:
        final_message += f"Verifique o arquivo de log em '{log_folder}' para detalhes sobre erros ou alterações realizadas nos nomes dos arquivos."
    else:
        final_message += "Nenhum erro ou alteração significativa foi registrada durante o processo."

    # Substituir messagebox.showinfo por show_auto_close_message
    root.destroy()  # Destruir a janela root antes de criar a nova
    show_auto_close_message(final_message, 10000)  # 10 segundos


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
    window_height = 500
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

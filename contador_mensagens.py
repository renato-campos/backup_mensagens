import re
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Tuple, List, Set

# --- Constantes ---
ICON_PATH = 'imagens/msg.ico'
REPORT_FILENAME_TEMPLATE = "relatorio_verificacao_{}.txt"


def selecionar_pasta() -> None:
    """Abre um diálogo para selecionar uma pasta e atualiza o campo de entrada."""
    pasta_selecionada = filedialog.askdirectory(title="Selecione a pasta")
    if pasta_selecionada:
        entry_pasta.delete(0, tk.END)
        entry_pasta.insert(0, pasta_selecionada)


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
            nome_pasta_analisada)
        caminho_relatorio = pasta_base / nome_arquivo_relatorio
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

tk.Button(frame, text="Verificar Arquivos", command=verificar_arquivos).grid(
    row=3, column=0, columnspan=3, pady=10)

root.mainloop()

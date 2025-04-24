import os
import tkinter as tk
from tkinter import filedialog, messagebox

def selecionar_pasta():
    pasta = filedialog.askdirectory(title="Selecione a pasta")
    if pasta:
        entry_pasta.delete(0, tk.END)
        entry_pasta.insert(0, pasta)

def verificar_arquivos():
    pasta = entry_pasta.get()
    try:
        inicio = int(entry_inicio.get())
        fim = int(entry_fim.get())
    except ValueError:
        messagebox.showerror("Erro", "Os valores inicial e final devem ser números inteiros.")
        return
    
    if inicio > fim:
        messagebox.showerror("Erro", "O número inicial deve ser menor ou igual ao número final.")
        return
    
    if not os.path.isdir(pasta):
        messagebox.showerror("Erro", "A pasta selecionada não existe.")
        return
    
    arquivos = os.listdir(pasta)
    numeros_encontrados = set()
    arquivos_sem_numero = []
    
    for arquivo in arquivos:
        # Extrai os números no início do nome do arquivo (considerando até 4 dígitos)
        numero_str = ''
        for char in arquivo:
            if char.isdigit():
                numero_str += char
            else:
                break
        
        if numero_str:
            numero = int(numero_str)
            numeros_encontrados.add(numero)
        else:
            arquivos_sem_numero.append(arquivo)
    
    # Verifica os números faltantes no intervalo
    numeros_faltantes = []
    for num in range(inicio, fim + 1):
        if num not in numeros_encontrados:
            numeros_faltantes.append(num)
    
    # Gera o relatório
    relatorio = []
    relatorio.append("=== RELATÓRIO DE VERIFICAÇÃO ===")
    relatorio.append(f"Pasta analisada: {pasta}")
    relatorio.append(f"Intervalo verificado: {inicio} a {fim}")
    relatorio.append("\nNúmeros faltantes no intervalo:")
    
    if numeros_faltantes:
        relatorio.append(", ".join(map(str, numeros_faltantes)))
    else:
        relatorio.append("Nenhum número faltante encontrado.")
    
    relatorio.append("\nArquivos que não começam com números:")
    if arquivos_sem_numero:
        relatorio.extend(arquivos_sem_numero)
    else:
        relatorio.append("Nenhum arquivo encontrado sem número no início.")
    
    # Obtém o nome da pasta para incluir no nome do relatório
    nome_pasta = os.path.basename(pasta)
    caminho_relatorio = os.path.join(pasta, f"relatorio_verificacao_{nome_pasta}.txt")
    
    # Salva o relatório em um arquivo .txt na mesma pasta
    with open(caminho_relatorio, 'w', encoding='utf-8') as f:
        f.write("\n".join(relatorio))
    
    messagebox.showinfo("Concluído", f"Verificação finalizada. Relatório salvo em:\n{caminho_relatorio}")

# Configuração da janela principal
root = tk.Tk()
root.title("Verificador de Arquivos Numéricos")

# Frame principal
frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

# Widgets
tk.Label(frame, text="Pasta:").grid(row=0, column=0, sticky="w")
entry_pasta = tk.Entry(frame, width=50)
entry_pasta.grid(row=0, column=1, padx=5)
tk.Button(frame, text="Selecionar", command=selecionar_pasta).grid(row=0, column=2)

tk.Label(frame, text="Número Inicial:").grid(row=1, column=0, sticky="w")
entry_inicio = tk.Entry(frame, width=10)
entry_inicio.grid(row=1, column=1, sticky="w", padx=5)

tk.Label(frame, text="Número Final:").grid(row=2, column=0, sticky="w")
entry_fim = tk.Entry(frame, width=10)
entry_fim.grid(row=2, column=1, sticky="w", padx=5)

tk.Button(frame, text="Verificar Arquivos", command=verificar_arquivos).grid(row=3, column=0, columnspan=3, pady=10)

root.mainloop()
# Unificador de Relatórios TXT para HTML (`unificador de relatorio.py`)

## 1. Objetivo

Este script Python tem como objetivo principal combinar o conteúdo de múltiplos arquivos de texto (`.txt`) localizados dentro de uma pasta selecionada pelo usuário em um único arquivo HTML. O script assume que o conteúdo dos arquivos `.txt` está formatado em Markdown e utiliza a biblioteca `markdown` para renderizá-lo corretamente no HTML final, incluindo formatação básica e estilização CSS para melhor legibilidade.

## 2. Funcionalidades Principais

*   **Interface Gráfica para Seleção:** Utiliza Tkinter para permitir ao usuário selecionar facilmente a pasta que contém os arquivos `.txt` a serem unificados.
*   **Leitura de Arquivos `.txt`:** Varre a pasta selecionada e processa todos os arquivos com a extensão `.txt` (case-insensitive).
*   **Tratamento de Codificação:** Tenta ler cada arquivo `.txt` com múltiplas codificações comuns (`utf-8`, `latin-1`, `cp1252`) para maximizar a compatibilidade.
*   **Combinação de Conteúdo:** Agrega o conteúdo de todos os arquivos `.txt` lidos com sucesso em uma única estrutura.
*   **Formatação Markdown:**
    *   Insere o nome de cada arquivo `.txt` original como um título de nível 2 (`<h2>`) no documento final.
    *   Insere uma linha horizontal (`<hr>`) como separador visual entre o conteúdo de cada arquivo.
*   **Conversão Markdown para HTML:** Utiliza a biblioteca externa `markdown` para converter o conteúdo combinado (incluindo títulos e separadores) de Markdown para HTML.
    *   Suporta extensões comuns como `fenced_code` (blocos de código), `tables` (tabelas) e `nl2br` (quebras de linha automáticas).
*   **Estilização CSS:** Incorpora um CSS básico diretamente no arquivo HTML gerado para melhorar a aparência (fonte, espaçamento, estilo de títulos e blocos de código).
*   **Geração de Arquivo HTML:** Salva o resultado final como um arquivo `.html` na **mesma pasta** que foi selecionada pelo usuário.
*   **Nomeação Dinâmica do Arquivo:** O nome do arquivo HTML gerado é baseado no nome da pasta selecionada (ex: `Relatório de MinhaPasta.html`).
*   **Feedback e Tratamento de Erros:**
    *   Imprime mensagens de progresso e erros no console durante a execução.
    *   Inclui mensagens de erro diretamente no HTML gerado caso um arquivo `.txt` não possa ser lido.
    *   Informa o usuário se a biblioteca `markdown` não estiver instalada.
    *   Informa o caminho do arquivo HTML gerado ao final do processo.

## 3. Modo de Usar

1.  **Instale a Dependência:** Este script requer a biblioteca `markdown`. Se você ainda não a tem, abra seu terminal ou prompt de comando e execute:
    ```bash
    pip install markdown
    ```
2.  **Execute o Script:** Certifique-se de ter o Python 3 instalado. Execute o script `unificador de relatorio.py` (por exemplo, clicando duas vezes nele ou rodando `python "unificador de relatorio.py"` no terminal).
3.  **Selecione a Pasta:** Uma janela de diálogo do sistema operacional será aberta. Navegue até a pasta que contém os arquivos `.txt` que você deseja combinar e clique em "Selecionar pasta" (ou o botão equivalente).
4.  **Aguarde o Processamento:** O script lerá os arquivos `.txt`, combinará o conteúdo, converterá para HTML e salvará o resultado. O progresso será exibido no console.
5.  **Consulte o Relatório HTML:** Após a conclusão (indicada no console), navegue até a pasta que você selecionou. Você encontrará um novo arquivo `.html` com um nome baseado no nome da pasta (ex: `Relatório de SuaPasta.html`). Abra este arquivo em qualquer navegador web para visualizar o relatório combinado e formatado.

## 4. Especificações Técnicas

*   **Linguagem:** Python 3.x
*   **Interface Gráfica (GUI):** Tkinter (módulo padrão) para seleção de pasta (`filedialog`).
*   **Dependências:**
    *   Módulos padrão: `os`, `tkinter`, `sys`.
    *   **Externa:** `markdown` (requer instalação via `pip install markdown`).
*   **Escopo:** Processa apenas arquivos `.txt` (case-insensitive) localizados **diretamente** na pasta selecionada. Não processa subpastas.
*   **Entrada:** Arquivos `.txt` contendo texto formatado em Markdown.
*   **Saída:** Um único arquivo `.html` na mesma pasta selecionada, codificado em UTF-8.
*   **Codificação de Leitura (TXT):** Tenta `utf-8`, `latin-1`, `cp1252`.
*   **Conversão Markdown:** Utiliza a biblioteca `markdown` com as extensões `fenced_code`, `tables`, `nl2br`.
*   **Estilo:** CSS básico embutido no HTML.
*   **Logging:** Não utiliza a biblioteca `logging`. Mensagens são impressas no console (`stdout`/`stderr`).

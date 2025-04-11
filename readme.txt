# Descrição dos Scripts Python de Arquivamento e Comparação de Pastas

Este arquivo descreve a funcionalidade de 5 scripts Python desenvolvidos para arquivar arquivos, mover arquivos e comparar diretórios.

## Visão Geral

Este conjunto de scripts Python foi desenvolvido para automatizar tarefas de organização e comparação de arquivos e pastas, principalmente focados em arquivos de e-mail (.eml) e outros tipos de arquivos. Os scripts lidam com o arquivamento de arquivos em uma estrutura de pastas organizada por ano e mês, a movimentação de arquivos de subpastas para a raiz e a comparação de duas árvores de diretórios para identificar diferenças.

## Descrição dos Scripts

Abaixo estão as descrições detalhadas de cada script:

### 1. arquiva_email.py

*   **Funcionalidade:** Este script monitora uma pasta específica em busca de arquivos, incluindo arquivos de e-mail (.eml) e outros tipos de arquivos. Ele arquiva os arquivos encontrados em subpastas organizadas por ano e mês, com base na data do e-mail (para arquivos .eml) ou na data de modificação do arquivo (para outros tipos de arquivos). O script também lida com arquivos duplicados, renomeando-os com um timestamp para evitar sobrescritas.
*   **Entrada:** O script espera que uma pasta seja definida como `watch_folder` no código, que é a pasta a ser monitorada. Também espera que a pasta `ERROS` esteja no mesmo nível da pasta monitorada.
*   **Saída:** O script move os arquivos encontrados na pasta `watch_folder` para subpastas dentro da mesma pasta, organizadas por ano e mês (ex: `watch_folder/2023/2023-10/arquivo.eml`). Ele também cria um arquivo de log na pasta `ERROS` que registra erros e avisos encontrados durante o processo. Imprime no console os arquivos que foram movidos e as pastas que foram criadas.
*   **Exemplo de Uso:** `python arquiva_email.py` (após configurar a variável `watch_folder` no código).
Pasta padrão do programa e que só pode ser alterada diretamente no código: "C:\Users\CEPOL\Documents\Arquivos do Outlook\Backup MSG"


### 2. arquiva_email_gui.py

*   **Funcionalidade:** Este script é uma versão aprimorada do `arquiva_email.py`, que adiciona uma interface gráfica (GUI) para selecionar a pasta a ser monitorada. Ele mantém a mesma funcionalidade de arquivamento de arquivos por ano e mês, tratamento de arquivos duplicados e geração de logs de erro.
*   **Entrada:** O script solicita ao usuário que selecione uma pasta através de uma janela de diálogo (file dialog).
*   **Saída:** Similar ao `arquiva_email.py`, o script move os arquivos encontrados na pasta selecionada para subpastas organizadas por ano e mês. Ele também cria um arquivo de log na pasta `ERROS` (dentro da pasta selecionada) que registra erros e avisos. Imprime no console os arquivos que foram movidos e as pastas que foram criadas.
*   **Exemplo de Uso:** `python arquiva_email_gui.py` (uma janela de seleção de pasta será aberta).

### 3. arquiva_subpastas.py

*   **Funcionalidade:** Este script é semelhante ao `arquiva_email_gui.py`, mas ele processa também as subpastas dentro da pasta selecionada. Ele percorre recursivamente as subpastas, arquivando os arquivos encontrados em subpastas organizadas por ano e mês, com base na data do e-mail ou na data de modificação do arquivo. Ele também ignora as pastas "Anos Anteriores" e "ERROS".
*   **Entrada:** O script solicita ao usuário que selecione uma pasta através de uma janela de diálogo.
*   **Saída:** O script move os arquivos encontrados na pasta selecionada e em suas subpastas para subpastas organizadas por ano e mês. Ele também cria um arquivo de log na pasta `ERROS` (dentro da pasta selecionada) que registra erros e avisos. Imprime no console os arquivos que foram movidos e as pastas que foram criadas.
*   **Exemplo de Uso:** `python arquiva_subpastas.py` (uma janela de seleção de pasta será aberta).

### 4. arquiva_raiz.py

*   **Funcionalidade:** Este script move todos os arquivos encontrados em subpastas dentro de uma pasta raiz para a própria pasta raiz. Após mover os arquivos, ele remove as subpastas vazias. Ele também exclui as pastas "erros" e "anos anteriores" do processo.
*   **Entrada:** O script solicita ao usuário que selecione uma pasta raiz através de uma janela de diálogo.
*   **Saída:** O script move todos os arquivos das subpastas para a pasta raiz. Cria um arquivo de log na pasta `ERROS` (dentro da pasta raiz) que registra os arquivos movidos, erros e avisos. Imprime no console que o processo foi concluído.
*   **Exemplo de Uso:** `python arquiva_raiz.py` (uma janela de seleção de pasta será aberta).

### 5. arvore_diff.py

*   **Funcionalidade:** Este script compara duas árvores de diretórios (duas pastas e suas subpastas) e identifica as diferenças entre elas. Ele verifica arquivos e pastas que existem apenas em uma das árvores, arquivos com o mesmo nome mas conteúdos diferentes e itens com o mesmo nome mas que são de tipos diferentes (um é arquivo e o outro é pasta).
*   **Entrada:** O script solicita ao usuário que selecione duas pastas para comparação e uma terceira pasta para salvar os logs.
*   **Saída:** O script cria um arquivo de log na pasta selecionada que registra as diferenças encontradas entre as duas árvores de diretórios. Imprime no console que o processo foi concluído.
*   **Exemplo de Uso:** `python arvore_diff.py` (três janelas de seleção de pasta serão abertas).

## Diferenças entre os Scripts

*   `arquiva_email.py` e `arquiva_email_gui.py` são focados em arquivar arquivos em uma estrutura de pastas organizada por data, mas o `arquiva_email_gui.py` possui uma interface gráfica para seleção de pasta. O `arquiva_email.py` tem a pasta fixa no código.
*   `arquiva_subpastas.py` é uma extensão dos scripts anteriores, pois também processa subpastas recursivamente.
*   `arquiva_raiz.py` tem um propósito diferente: mover arquivos de subpastas para a raiz e remover as subpastas vazias.
*   `arvore_diff.py` é o único script que não move ou arquiva arquivos, mas sim compara duas árvores de diretórios e identifica diferenças.
* Os scripts `arquiva_email_gui.py`, `arquiva_subpastas.py`, `arquiva_raiz.py` e `arvore_diff.py` utilizam interface gráfica para seleção de pastas, enquanto o `arquiva_email.py` tem a pasta fixa no código.
* Os scripts `arquiva_email.py`, `arquiva_email_gui.py` e `arquiva_subpastas.py` trabalham com arquivos .eml, enquanto o `arquiva_raiz.py` e `arvore_diff.py` não tem essa restrição.
* Os scripts `arquiva_email.py`, `arquiva_email_gui.py` e `arquiva_subpastas.py` criam pastas de ano e mês, enquanto o `arquiva_raiz.py` move os arquivos para a raiz e o `arvore_diff.py` não cria nenhuma pasta.

## Requisitos

*   Python 3.x
*   Bibliotecas padrão do Python: `os`, `shutil`, `email`, `logging`, `datetime`, `filecmp`, `tkinter`
*   Não há necessidade de instalar bibliotecas externas.

## Considerações Finais

*   Os scripts foram desenvolvidos para automatizar tarefas de organização e comparação de arquivos e pastas.
*   Os scripts de arquivamento lidam com arquivos duplicados, renomeando-os para evitar sobrescritas.
*   Todos os scripts geram arquivos de log na pasta `ERROS` para registrar erros e avisos.
*   Os scripts podem ser modificados e adaptados para outras necessidades.
*   Os scripts `arquiva_email.py`, `arquiva_email_gui.py` e `arquiva_subpastas.py` ignoram arquivos com a extensão `.ffs_db`.
* O script `arquiva_subpastas.py` e `arquiva_raiz.py` ignoram as pastas "erros" e "anos anteriores".
* O script `arquiva_raiz.py` remove as pastas vazias.
* O script `arvore_diff.py` compara pastas e subpastas recursivamente.

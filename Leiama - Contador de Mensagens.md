# Verificador de Sequência Numérica de Arquivos (`contador_mensagens.py`)

## 1. Objetivo

Este script Python, com interface gráfica (GUI), tem como objetivo principal analisar os nomes dos arquivos dentro de uma pasta selecionada pelo usuário para:

*   Verificar a integridade de uma sequência numérica esperada (ex: 1, 2, 3, ..., 100).
*   Identificar quais números estão faltando dentro dessa sequência.
*   Listar arquivos cujos nomes começam com números que estão *fora* do intervalo esperado.
*   Listar arquivos cujos nomes não começam com um número.

É particularmente útil para gerenciar arquivos que deveriam seguir uma numeração sequencial, como documentos digitalizados, logs, backups ou mensagens de e-mail exportadas.

## 2. Funcionalidades Principais

*   **Interface Gráfica Simples:** Utiliza Tkinter para fornecer uma interface amigável onde o usuário pode:
    *   Selecionar a pasta a ser analisada.
    *   Definir o número inicial e final da sequência numérica esperada.
    *   Iniciar o processo de verificação.
*   **Seleção de Pasta:** Permite ao usuário navegar e escolher facilmente a pasta alvo através de um diálogo padrão do sistema.
*   **Definição de Intervalo:** O usuário especifica o intervalo numérico (início e fim) que os nomes dos arquivos deveriam seguir.
*   **Extração de Números:** Identifica e extrai o número inicial de cada nome de arquivo na pasta selecionada. Ignora zeros à esquerda (ex: `001.txt` é tratado como `1`).
*   **Verificação de Sequência:** Compara os números extraídos com o intervalo definido pelo usuário e identifica:
    *   **Números Faltantes:** Quais números dentro do intervalo esperado não foram encontrados em nenhum nome de arquivo.
    *   **Números Fora do Intervalo:** Quais arquivos começam com números menores que o inicial ou maiores que o final definido. *(Opcional: Se a modificação no código for aplicada, lista também os nomes dos arquivos)*.
    *   **Arquivos Sem Número Inicial:** Quais arquivos na pasta não possuem um número no início do nome.
*   **Geração de Relatório:** Cria um arquivo de texto (`.txt`) detalhado na própria pasta analisada, contendo:
    *   A pasta analisada e o intervalo verificado.
    *   A lista de números faltantes.
    *   A lista de números (e opcionalmente arquivos) encontrados fora do intervalo.
    *   A lista de nomes de arquivos que não começam com números.
*   **Feedback ao Usuário:** Exibe mensagens de erro se a pasta for inválida ou se os números do intervalo não forem válidos. Exibe uma mensagem de confirmação ao final, indicando onde o relatório foi salvo.

## 3. Modo de Usar

1.  **Execute o Script:** Certifique-se de ter o Python 3 instalado. Execute o script `contador_mensagens.py` (por exemplo, clicando duas vezes nele ou rodando `python contador_mensagens.py` no terminal).
2.  **Selecione a Pasta:** Na janela do programa, clique no botão "Selecionar". Navegue até a pasta que contém os arquivos que você deseja verificar e clique em "Selecionar pasta" (ou o botão equivalente). O caminho da pasta aparecerá no campo "Pasta:".
3.  **Defina o Intervalo:**
    *   No campo "Número Inicial:", digite o primeiro número da sequência que você espera encontrar (ex: `1`).
    *   No campo "Número Final:", digite o último número da sequência (ex: `100`).
4.  **Inicie a Verificação:** Clique no botão "Verificar Arquivos".
5.  **Aguarde:** O script analisará os arquivos na pasta selecionada. Para um grande número de arquivos, isso pode levar alguns instantes.
6.  **Verifique o Resultado:** Uma janela de mensagem aparecerá informando que a verificação foi concluída e indicando o nome e localização do arquivo de relatório (que será salvo dentro da pasta que você analisou).
7.  **Consulte o Relatório:** Navegue até a pasta analisada e abra o arquivo `.txt` gerado (ex: `relatorio_verificacao_MinhaPasta.txt`) para ver os detalhes dos números faltantes, arquivos fora do intervalo e arquivos sem numeração inicial.

## 4. Especificações Técnicas

*   **Linguagem:** Python 3.x
*   **Interface Gráfica (GUI):** Tkinter (módulo padrão do Python)
*   **Dependências:** Utiliza apenas módulos padrão do Python:
    *   `os`: Para listar arquivos e interagir com o sistema de arquivos.
    *   `tkinter`: Para a criação da interface gráfica (janela, botões, campos de entrada, diálogos de seleção de pasta e mensagens).
*   **Escopo da Análise:** O script analisa **apenas** os arquivos localizados diretamente na pasta selecionada. Ele **não** verifica arquivos em subpastas.
*   **Extração de Números:** Considera apenas dígitos (`0-9`) que aparecem no **início** do nome do arquivo. A extração para ao encontrar o primeiro caractere não numérico. Zeros à esquerda são ignorados na conversão para número inteiro (ex: `007` é tratado como `7`).
*   **Arquivo de Saída:** O relatório é salvo como um arquivo `.txt` na mesma pasta que foi analisada, com o nome no formato `relatorio_verificacao_[nome_da_pasta].txt`, codificado em UTF-8.


# Verificador de Sequência Numérica e Unificador de Relatórios (`relatorio_mensagens.py`)

## 1. Objetivo

Este script Python, com interface gráfica (GUI), tem como objetivos principais:

1.  **Analisar nomes de arquivos** dentro de uma pasta selecionada para:
    *   Verificar a integridade de uma sequência numérica esperada (ex: 1, 2, 3, ..., 100).
    *   Identificar quais números estão faltando dentro dessa sequência.
    *   Listar arquivos cujos nomes começam com números que estão *fora* do intervalo esperado.
    *   Listar arquivos cujos nomes não começam com um número.
2.  **Unificar relatórios de verificação** (arquivos `.txt`) de uma pasta em um único relatório consolidado em formato HTML.

É particularmente útil para gerenciar arquivos que deveriam seguir uma numeração sequencial e para consolidar os resultados de múltiplas verificações.

## 2. Funcionalidades Principais

*   **Interface Gráfica Simples:** Utiliza Tkinter para fornecer uma interface amigável onde o usuário pode:
    *   Selecionar a pasta a ser analisada.
    *   Definir o número inicial e final da sequência numérica esperada.
    *   Optar por unificar relatórios `.txt` existentes na pasta pai da pasta analisada.
    *   Iniciar o processo de verificação (e opcionalmente, unificação).
*   **Seleção de Pasta:** Permite ao usuário navegar e escolher facilmente a pasta alvo para análise através de um diálogo padrão do sistema.
*   **Definição de Intervalo:** O usuário especifica o intervalo numérico (início e fim) que os nomes dos arquivos deveriam seguir.
*   **Extração de Números:** Identifica e extrai o número inicial de cada nome de arquivo na pasta selecionada. Ignora zeros à esquerda (ex: `001.txt` é tratado como `1`).
*   **Verificação de Sequência:** Compara os números extraídos com o intervalo definido pelo usuário e identifica:
    *   **Números Faltantes:** Quais números dentro do intervalo esperado não foram encontrados em nenhum nome de arquivo.
    *   **Números Fora do Intervalo:** Quais arquivos começam com números menores que o inicial ou maiores que o final definido.
    *   **Arquivos Sem Número Inicial:** Quais arquivos na pasta não possuem um número no início do nome.
*   **Geração de Relatório Individual (`.txt`):** Após a verificação de uma pasta, cria um arquivo de texto (`.txt`) detalhado.
    *   Este relatório é salvo na **pasta mãe** da pasta que foi analisada.
    *   Contém: a pasta analisada, o intervalo verificado, a lista de números faltantes, a lista de números fora do intervalo e a lista de arquivos sem numeração inicial.
*   **Unificação Opcional de Relatórios (`.html`):**
    *   Se a opção "Unificar relatórios..." for marcada, após a verificação e salvamento do relatório `.txt` individual, o script tentará unificar **todos** os arquivos `.txt` (que se presume serem relatórios de verificação anteriores) localizados na **pasta mãe** da pasta analisada.
    *   Gera um único arquivo HTML consolidado, também salvo na **pasta mãe**.
    *   Após a unificação bem-sucedida, os arquivos `.txt` originais que foram unificados são **excluídos**.
    *   Logs detalhados do processo de unificação são salvos em uma subpasta `LOGS_UNIFICADOR` dentro da pasta mãe.
*   **Feedback ao Usuário:** Exibe mensagens de erro (ex: pasta inválida, intervalo inválido, falha na unificação) e mensagens de confirmação (ex: relatório `.txt` salvo, relatório HTML unificado salvo, arquivos `.txt` excluídos).

## 3. Modo de Usar

1.  **Execute o Script:** Certifique-se de ter o Python 3 instalado e a biblioteca `markdown` (`pip install markdown`). Execute o script `relatorio_mensagens.py` (por exemplo, clicando duas vezes nele ou rodando `python relatorio_mensagens.py` no terminal).
2.  **Selecione a Pasta:** Na janela do programa, clique no botão "Selecionar". Navegue até a pasta que contém os arquivos que você deseja verificar e clique em "Selecionar pasta" (ou o botão equivalente). O caminho da pasta aparecerá no campo "Pasta:".
3.  **Defina o Intervalo:**
    *   No campo "Número Inicial:", digite o primeiro número da sequência que você espera encontrar (ex: `1`).
    *   No campo "Número Final:", digite o último número da sequência (ex: `100`).
4.  **(Opcional) Unificar Relatórios:** Se desejar que, após a verificação, o script tente unificar todos os relatórios `.txt` existentes na **pasta mãe** da pasta selecionada em um único arquivo HTML, marque a caixa de seleção "Unificar relatórios da pasta pai após verificação".
5.  **Inicie a Verificação:** Clique no botão "Verificar Arquivos".
6.  **Aguarde:** O script analisará os arquivos na pasta selecionada e, se aplicável, realizará a unificação. Isso pode levar alguns instantes.
7.  **Verifique o Resultado:**
    *   Uma janela de mensagem aparecerá informando que a verificação foi concluída e indicando o nome e localização do arquivo de relatório `.txt` individual (que será salvo na **pasta mãe** da que você analisou, ex: `relatorio_verificacao_MinhaPastaAnalisada.txt`).
    *   Se a unificação foi selecionada e bem-sucedida, outra mensagem informará sobre a criação do arquivo HTML unificado (ex: `Relatorio_Unificado_PastaMae.html`, também na pasta mãe) e sobre a exclusão dos arquivos `.txt` originais.
8.  **Consulte os Relatórios:**
    *   Navegue até a **pasta mãe** da pasta analisada para encontrar o relatório `.txt` individual.
    *   Se a unificação foi realizada, você também encontrará o relatório HTML consolidado e uma pasta `LOGS_UNIFICADOR` com os logs do processo de unificação.

## 4. Especificações Técnicas

*   **Linguagem:** Python 3.x
*   **Interface Gráfica (GUI):** Tkinter (módulo padrão do Python)
*   **Dependências:**
    *   Módulos padrão do Python: `re`, `tkinter`, `pathlib`, `logging`, `datetime`.
    *   Biblioteca externa: `markdown` (necessária para a unificação de relatórios em HTML). Instale com `pip install markdown`.
*   **Escopo da Análise de Sequência:** A verificação de sequência numérica analisa **apenas** os arquivos localizados diretamente na pasta selecionada. Ela **não** verifica arquivos em subpastas.
*   **Escopo da Unificação de Relatórios:** A unificação processa todos os arquivos `.txt` encontrados diretamente na **pasta mãe** da pasta selecionada para análise de sequência.
*   **Extração de Números:** Considera apenas dígitos (`0-9`) que aparecem no **início** do nome do arquivo. A extração para ao encontrar o primeiro caractere não numérico. Zeros à esquerda são ignorados na conversão para número inteiro (ex: `007` é tratado como `7`).
*   **Arquivos de Saída:**
    *   **Relatório de Verificação Individual:** Salvo como um arquivo `.txt` na **pasta mãe** da pasta analisada, com o nome no formato `relatorio_verificacao_[nome_da_pasta_analisada].txt`, codificado em UTF-8.
    *   **Relatório Unificado (Opcional):** Salvo como um arquivo `.html` na **pasta mãe** da pasta analisada, com o nome no formato `Relatorio_Unificado_[nome_da_pasta_mae].html`, codificado em UTF-8.
    *   **Logs da Unificação (Opcional):** Arquivos `.log` salvos na subpasta `LOGS_UNIFICADOR` dentro da pasta mãe, caso a unificação seja executada.
*   **Exclusão de Arquivos:** Se a unificação de relatórios for bem-sucedida, os arquivos `.txt` originais que foram combinados no relatório HTML são excluídos da pasta mãe.


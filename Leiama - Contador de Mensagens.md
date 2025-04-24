# Contador de Mensagens

## Descrição

O **Contador de Mensagens** é uma ferramenta gráfica que verifica a sequência numérica de arquivos em uma pasta. Ele foi desenvolvido para identificar números faltantes em uma sequência de arquivos que começam com números, como mensagens ou documentos numerados sequencialmente.

## Funcionalidades

- **Verificação de Sequência**: Identifica números faltantes em uma sequência definida pelo usuário
- **Detecção de Arquivos sem Numeração**: Lista arquivos que não começam com números
- **Geração de Relatório**: Cria um relatório detalhado com os resultados da verificação
- **Interface Gráfica**: Oferece uma interface simples e intuitiva para o usuário

## Como Usar

1. **Iniciar o Programa**: Execute o arquivo `contador_mensagens.py`
2. **Selecionar Pasta**: Clique no botão "Selecionar" para escolher a pasta que contém os arquivos a serem verificados
3. **Definir Intervalo**: 
   - Digite o número inicial da sequência no campo "Número Inicial"
   - Digite o número final da sequência no campo "Número Final"
4. **Iniciar Verificação**: Clique no botão "Verificar Arquivos"
5. **Visualizar Resultados**: Após a conclusão, um relatório será salvo na pasta analisada e uma mensagem de confirmação será exibida

## Relatório Gerado

O relatório gerado inclui:
- Nome da pasta analisada
- Intervalo verificado
- Lista de números faltantes na sequência
- Lista de arquivos que não começam com números

## Exemplo de Uso

Este programa é útil para verificar se há mensagens ou documentos faltantes em uma sequência. Por exemplo, se você tem uma pasta com arquivos de mensagens numeradas de 1 a 100, o programa pode identificar quais números estão faltando.

## Requisitos

- Python 3.x
- Tkinter (geralmente incluído nas instalações padrão do Python)

## Observações

- O programa considera apenas números no início do nome do arquivo
- Zeros à esquerda são ignorados (por exemplo, "001.txt" e "1.txt" são considerados o mesmo número)
- O relatório é salvo na pasta analisada com o nome "relatorio_verificacao_[nome_da_pasta].txt"

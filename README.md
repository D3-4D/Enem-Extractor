# Enem Extractor

Script para baixar provas e gabaritos do ENEM diretamente do site oficial do INEP.

Este script foi desenvolvido como parte de um sistema maior em construção, voltado para ferramentas educacionais e automação de coleta de material didático. Ele funciona como um módulo independente, mas sua função principal é integrar-se a esse ecossistema, fornecendo uma camada confiável de download, filtragem e recuperação de provas e gabaritos a partir do banco público do INEP.

A ferramenta coleta todos os arquivos disponíveis, tratando arquivos mal formatados ou adaptados, com algumas exceções.

### Arquivos ignorados
- **Arquivos adaptados 2022–2023**: versões adaptadas das provas originais, com formatação diferente. Foram ignorados por causa do formato incomum e por não fazerem parte do conjunto de arquivos que o script foi projetado para baixar.
- **Arquivos redundantes (temas de redação 2023)**: PDFs que contêm o tema da redação, já presente em todas as provas. Também são ignorados, pois não fazem parte do conjunto de arquivos que o script foi projetado para baixar.

### Provas antigas
- Provas de 1998-2008 não possuem formatação adequada; suas pastas são nomeadas como `"Undefined"`.

## Funcionalidades

- Preserva arquivos mal formatados.
- Estrutura organizada por ano, aba e título.
- Suporta filtragem por ano, título, aba ou link.

# Usos

## Básico
python downloader.py

## Com Filtros
python downloader.py --Type 1 --Year 2017 --Title Azul

## Retomada 
python downloader.py --Retry ErrorLogs.json

### Opções de filtro:

- --Type
  - 0: Nenhum
  - 1: Inclusivo
  - 2: Exclusivo

- --Mode
  - 0: Apenas prova
  - 1: Apenas gabarito
  - 2: Ambos
  - 3: Ambos, estrito (somente baixa se houver prova e gabarito)

- --Year  
  Baixar anos específicos
  
- --Title  
  Baixar apenas provas/gabaritos que contenham palavras específicas

- --Tab  
  Baixar apenas provas/gabaritos categorizados com palavras específicas

- --Link  
  Baixar apenas provas/gabaritos com links que contenham palavras específicas

- **--Replace**  
  Substituir arquivos existentes

- **--Retry**  
  Retomar downloads falhados a partir de um arquivo JSON de erros gerado anteriormente

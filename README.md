Aqui está a versão atualizada do seu README, mantendo a estrutura e o idioma (português) do original, mas complementado e corrigido para refletir exatamente o que o seu novo código faz (como os novos argumentos do CLI, uso de threads, sistema de retry resiliente e as correções internas).

---

# Enem Extractor

Script multi-threaded de alta performance para baixar provas e gabaritos do ENEM diretamente do site oficial do INEP.

Este script foi desenvolvido como parte de um sistema maior voltado para ferramentas educacionais e automação de coleta de material didático. Ele funciona como um módulo independente, fornecendo uma camada confiável de download, filtragem avançada e recuperação de provas e gabaritos a partir do banco público do INEP, utilizando processamento paralelo e conexões resilientes.

A ferramenta coleta os arquivos disponíveis tratando automaticamente links mal formatados ou variações na estrutura das páginas do INEP.

### Tratamento de Arquivos e Exceções

* **Correções de URL nativas:** O script corrige automaticamente links quebrados do próprio servidor do INEP (como os erros de protocolo `http//` encontrados nas páginas de 2017).
* **Suporte a layouts antigos (1998–2008):** Provas antigas que não possuem uma formatação de tags consistente têm suas abas categorizadas automaticamente como `"Undefined"` para garantir que o download não seja interrompido.
* **Layouts modernos (2022–2023):** O parser adapta-se dinamicamente às mudanças de contêineres HTML (`div.list-download__row` e `id="parent-fieldname-text"`) usadas nos anos mais recentes.

---

## Funcionalidades

* **Multi-threading duplo:** Divide tanto a etapa de extração de endpoints (leitura das páginas) quanto a etapa de downloads em múltiplas threads paralelas para máxima velocidade.
* **Download Adaptativo e Resiliente:** Se uma conexão cair no meio de um arquivo, o script tenta retomar o download via pacotes de bytes específicos (`Range`), reduzindo o tamanho do chunk dinamicamente se houver instabilidade.
* **Conexão Otimizada:** Ignora checagens pesadas de SSL (overhead de certificação do INEP) e monta adaptadores HTTP com políticas de retry automáticas para erros de servidor (500, 502, 503, 504).
* **Estrutura Organizada:** Salva os arquivos criando automaticamente uma árvore de pastas no formato: `[Diretório Selecionado] / [Ano] / [Aba] / [Título] / exam.pdf` (ou `answers.pdf`).

---

## Instalação

Certifique-se de instalar as dependências necessárias antes de rodar o script:

### Funcional
```bash
pip install requests beautifulsoup4
```
### Completo
```bash
pip install requests beautifulsoup4 tqdm colorama
```

*(Nota: O script possui fallbacks visuais. Caso o terminal não suporte Colorama/TQDM ou a interface gráfica do Tkinter não esteja disponível, ele rodará em modo texto puro de forma segura).*

---

# Usos

## Básico

Executa o script abrindo uma janela de seleção de pasta (ou input no terminal) e baixa todos arquivos disponíveis:

```bash
python downloader.py

```

## Com Filtros Avançados

Baixa apenas as provas (sem gabarito) dos anos de 2017 e 2022 que contenham a palavra "Azul" no título:

```bash
python downloader.py --Type 0 --Mode 0 --Year 2017 2022 --Title Azul

```

## Retomada de Falhas (Retry)

Se houver falhas críticas de rede, o script gera um arquivo de recuperação `ErrorLogs.json`. Você pode retomar de onde parou sem executar o mesmo comando de extração novamente:

```bash
python downloader.py --Retry ErrorLogs.json

```

---

## Referência de Argumentos (CLI)

### Configurações Gerais

* `--Debug (int)`: Nível de detalhes no terminal. `0`: Desativado, `1`: Mínimo, `2`: Básico, `3`: Detalhado/Verboso (Padrão: `3`).
* `--Retry (str)`: Caminho para um arquivo JSON de erros (ex: `ErrorLogs.json`). Ignora a raspagem padrão e foca apenas em baixar o que falhou.

### Parâmetros de Extração e Filtragem

* `--Mode (int)`: Modo de operação do download.
* `0`: Apenas Provas (`exam.pdf`)
* `1`: Apenas Gabaritos (`answers.pdf`)
* `2`: Ambos (Padrão)
* `3`: Ambos (Estrito - Só baixa se o par prova e gabarito existirem na página)


* `--Type (int)`: Tipo de lógica dos filtros (`--Link`, `--Tab`, `--Title`, `--Year`).
* `0`: Inclusivo (Padrão - Baixa apenas o que coincidir com os filtros)
* `1`: Exclusivo (Ignora o que coincidir com os filtros)


* `--Year (int [lista])`: Filtra anos específicos (Ex: `--Year 2020 2021 2024`).
* `--Title (str [lista])`: Filtra palavras-chave nos títulos das provas (Ex: `--Title Azul Rosa Amarela`).
* `--Tab (str [lista])`: Filtra palavras-chave nas abas/categorias do site (Ex: `--Tab Aplicação Regular Segunda`).
* `--Link (str [lista])`: Filtra sub-strings diretamente na URL do arquivo.
* `--LooseEx (bool)`: Se `True` (Padrão), o script ignora anos que derem erro de página vazia e continua a execução.
* `--ThreadedEx (bool)`: Se `True` (Padrão), processa e raspa as páginas do INEP em paralelo usando pool de threads.

### Comportamento do Download

* `--ThreadedDw (bool)`: Se `True` (Padrão), baixa múltiplos PDFs simultaneamente.
* `--Replace (bool)`: Se `True` (Padrão), substitui arquivos locais que já tenham sido baixados anteriormente.

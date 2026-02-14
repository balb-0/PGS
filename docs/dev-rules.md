<Table>
  <tr>
    <td><a href= "https://www.sankhya.com.br/software-de-gestao-erp/erp-para-gestao-empresarial/produtos/asis/"><img src="img/asis.png" alt="Asis" border="0"></td>
    <td>
      <a href= "https://www.inteli.edu.br/"><img src="img/logo-Inteli.png" alt="Inteli - Instituto de Tecnologia e Liderança" border="0"></a>
    </td>
  </tr>
</table>

# Nome do Projeto: P.G.S (Projeto do Grupo Seis)

## Nome do Grupo: O.G.S (O Grupo Seis)

## Integrantes:

- <a href="https://www.linkedin.com/in/arthur-bretas/">Arthur Bretas Oliveira</a>
- <a href="https://www.linkedin.com/in/daviversan/">Davi D'avila Versan</a>
- <a href="https://www.linkedin.com/in/gabriel-nascimento3/">Gabriel Santos do Nascimento</a>
- <a href="https://www.linkedin.com/in/nicolasramons/">Nicolas Ramon da Silva</a>
- <a href="https://www.linkedin.com/in/otavio-vasc/">Otavio de Carvalho Vasconcelos</a>
- <a href="https://www.linkedin.com/in/vitor-balbo/">Vitor Margarido Balbo</a>
- <a href="https://www.linkedin.com/in/viniciussavian/">Vinicius dos Reis Savian</a>

# Sumário

- [1. Introdução](#1-introdução)
  - [1.1 Objetivo do Documento](#11-objetivo-do-documento)
- [2. Padrões de Codificação (Python)](#2-padrões-de-codificação-python)
  - [2.1 Convenções de Nomenclatura](#21-convenções-de-nomenclatura)
  - [2.2 Formatação e Estilo](#22-formatação-e-estilo)
  - [2.3 Importações e Organização de Módulos](#23-importações-e-organização-de-módulos)
  - [2.4 Tratamento de Erros e Contratos](#24-tratamento-de-erros-e-contratos)
  - [2.5 Boas práticas FastAPI](#25-boas-práticas-fastapi)
- [3. Padrões de Projeto e Estrutura do Repositório](#3-padrões-de-projeto-e-estrutura-do-repositório)
  - [3.1 Estrutura em `src/`](#31-estrutura-em-src)
  - [3.2 Princípios adotados](#32-princípios-adotados)
- [4. Práticas de Desenvolvimento](#4-práticas-de-desenvolvimento)
  - [4.1 Testes Automatizados (pytest)](#41-testes-automatizados-pytest)
  - [4.2 Qualidade e Revisão](#42-qualidade-e-revisão)
  - [4.3 Execução local (Makefile)](#43-execução-local-makefile)
- [5. Ferramentas e Tecnologias](#5-ferramentas-e-tecnologias)
  - [5.1 Ferramentas](#51-ferramentas)
  - [5.2 Tecnologias e Bibliotecas](#52-tecnologias-e-bibliotecas)

# 1. Introdução
Este documento consolida padrões de codificação e práticas de desenvolvimento para manter **consistência**, **qualidade** e **reprodutibilidade** no projeto.

O repositório é centrado em uma **API FastAPI** (em `src/core/mock_api.py`) e em **testes automatizados com pytest** organizados por contexto (Blue Team e Red Team) em `src/tests/`.

## 1.1 Objetivo do Documento

Definir regras claras para:

- reduzir divergências de estilo entre autores;
- facilitar leitura, revisão e manutenção;
- manter a API e a suíte de testes alinhadas aos Direcionadores de Negócio (BD/DN);
- garantir execução reproduzível localmente e em esteira (quando aplicável).

# 2. Padrões de Codificação (Python)

As regras abaixo refletem o padrão adotado no código de `src/` (FastAPI + pytest).

## 2.1 Convenções de Nomenclatura

- **Variáveis e funções**: `snake_case`
  - Ex.: `processar_auditoria`, `processar_auditoria_resiliente`, `reset_availability_state`
- **Classes**: `PascalCase`
  - Ex.: `TestDN2IntegrityValidation`, `TestDN3RedTeam`
- **Constantes**: `UPPER_CASE`
  - Ex.: `HEADERS_VALIDOS`, `HEADERS`
- **Arquivos e módulos**: `snake_case.py`
  - Ex.: `mock_api.py`, `availability.py`, `non_repudiation.py`
- **Rotas e versões**: manter padrão `/api/v1/...` e nomes semânticos (ex.: `/auditar`, `/auditar/resilient`, `/health`)

## 2.2 Formatação e Estilo

- **Indentação**: 4 espaços (PEP 8).
- **Comprimento de linha**: preferencialmente até 100 caracteres (quebrar linhas longas quando necessário).
- **Strings e JSON**: preferir aspas duplas (`"`) ao montar exemplos de payload/response para manter consistência visual com JSON.
- **Tipagem**: quando útil, usar type hints (`Dict[str, Any]`, `Optional[str]`, etc.) e manter assinaturas legíveis.
- **Docstrings**: manter docstrings concisas para módulos, classes e endpoints, descrevendo objetivo e regras de negócio aplicadas.

## 2.3 Importações e Organização de Módulos

- **Agrupamento de imports** (nesta ordem):
  - standard library (ex.: `uuid`, `asyncio`, `random`)
  - terceiros (ex.: `fastapi`, `pytest`)
  - internos (ex.: `from core.availability import ...`)
- **Imports internos**: manter referências a `core.*` para módulos em `src/core/`.
- **Evitar circularidade**: regras de disponibilidade e não-repúdio ficam em módulos dedicados e são importadas pela `mock_api.py`.

## 2.4 Tratamento de Erros e Contratos

- **HTTP status codes coerentes com a regra**:
  - `400` para payload inválido (DN2)
  - `404` para recurso não encontrado (ex.: consulta por posição inexistente no log)
  - `429` para rate limiting (DN3)
  - `503` para indisponibilidade por proteção (circuit breaker / degradação graciosa)
- **Sem efeitos colaterais em erro**: validações devem ocorrer antes de gerar `tracking_id` e antes de iniciar processamento assíncrono.
- **Mensagens claras**: o campo `detail` deve indicar o motivo de falha de forma objetiva.

## 2.5 Boas práticas FastAPI

- **Rotas versionadas**: manter o padrão `/api/v1/...`.
- **Headers obrigatórios**: declarar via `Header(...)` (ex.: `account_key`, `app_key`) e manter consistência nos testes.
  - Observação: o FastAPI converte `_` em `-` nos nomes de headers HTTP; por isso os testes usam `account-key`, `app-key` e `idempotency-key`.
- **Documentação automática**: manter título/versão no `FastAPI(...)` e docstrings nos endpoints. A documentação OpenAPI é exposta em `/docs` e `/openapi.json` (padrão FastAPI).

# 3. Padrões de Projeto e Estrutura do Repositório

## 3.1 Estrutura em `src/`

- `src/core/`: implementação da API mock e módulos de suporte.
  - `mock_api.py`: aplicação FastAPI e endpoints principais.
  - `availability.py`: componentes de disponibilidade/resiliência (rate limiter, circuit breaker, health checker, idempotência, degradação graciosa).
  - `non_repudiation.py`: funções e estruturas para não-repúdio (assinatura, recibo, log encadeado).
- `src/tests/blue_team/`: testes voltados a critérios de aceite e conformidade.
- `src/tests/red_team/`: testes adversariais para explorar limites e lacunas.

## 3.2 Princípios adotados

- **Separação de responsabilidades**: regras de disponibilidade e não-repúdio ficam em módulos dedicados (evita acoplamento desnecessário).
- **Coesão por DN**: organização de código e testes segue Direcionadores de Negócio (DN2, DN3, DN4).
- **Reprodutibilidade**: quando houver aleatoriedade/sleep na API mock, testes podem usar `monkeypatch` para controlar tempo e garantir consistência (como no Red Team).

# 4. Práticas de Desenvolvimento
As práticas abaixo orientam como evoluímos `src/` com segurança e consistência.

## 4.1 Testes Automatizados (pytest)

- **Framework**: `pytest` + `fastapi.testclient.TestClient` (padrão do repositório).
- **Blue Team (`src/tests/blue_team/`)**: valida critérios de aceite e regras de negócio (ex.: DN2 e DN4).
- **Red Team (`src/tests/red_team/`)**: simula comportamento adversarial para tensionar resiliência e contratos (ex.: DN3).
- **Regras**:
  - cada teste deve validar um comportamento observável (status code + invariantes de resposta);
  - evitar flakiness: controlar delays/aleatoriedade quando necessário (ex.: monkeypatch do `random.uniform`).

## 4.2 Qualidade e Revisão

- Toda mudança deve ser revisável e explicável:
  - docstrings e comentários devem focar no **porquê**;
  - commits pequenos e objetivos (ver `docs/gestao-configuração.md`).
- Antes de abrir um MR, rodar localmente as suítes relevantes para a mudança.

## 4.3 Execução local (Makefile)

O repositório oferece atalhos no `Makefile` para reduzir variação entre ambientes:

- `make run`: sobe a API (`uvicorn src.core.mock_api:app --reload`)
- `make test-dn2`: roda testes de integridade (DN2)
- `make test-nr`: roda testes de não-repúdio (DN4)
- `make test-all`: roda as suítes principais (DN2 + DN4)
- `make stress`: executa teste de carga/latência (DN1)

# 5. Ferramentas e Tecnologias

## 5.1 Ferramentas

- **Editor/IDE**: VS Code ou Cursor (recomendado: extensão Python).
- **Git**: versionamento e colaboração via branches + Merge Requests (GitLab).
- **Makefile**: atalhos padronizados para execução e testes (`make run`, `make test-all`, etc.).

Ferramentas opcionais (não obrigatórias no estado atual do repositório):

- **GitLens**: apoio à revisão/histórico dentro do editor.
- **Formatador/Linter Python** (ex.: Black/Ruff): automatiza consistência de estilo quando/ se o time decidir adotar.

## 5.2 Tecnologias e Bibliotecas

- **Python**
- **FastAPI** (API mock e OpenAPI)
- **Uvicorn** (servidor ASGI local)
- **Pytest** (testes automatizados)
- **HTTPX** e **Requests** (clientes HTTP usados em testes/scripts, conforme necessidade)

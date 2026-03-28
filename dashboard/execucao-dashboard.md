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

# Como Executar o Dashboard

Este documento consolida todas as instruções necessárias para executar a stack completa do projeto: API ASIS (FastAPI), stack de observabilidade (Prometheus + Grafana + Alertmanager) e frontend executivo (Next.js).

---

# Sumário

- [1. Pré-requisitos](#1-pré-requisitos)
- [2. Configuração do Ambiente Python](#2-configuração-do-ambiente-python)
  - [2.1 Virtual Environment](#21-virtual-environment)
  - [2.2 Variáveis de Ambiente (Backend)](#22-variáveis-de-ambiente-backend)
- [3. Subir a Stack de Observabilidade](#3-subir-a-stack-de-observabilidade)
  - [3.1 Docker Compose](#31-docker-compose)
  - [3.2 Serviços e Portas](#32-serviços-e-portas)
- [4. Iniciar a API ASIS](#4-iniciar-a-api-asis)
- [5. Pytest Metrics Exporter (Opcional)](#5-pytest-metrics-exporter-opcional)
- [6. Iniciar o Frontend Next.js](#6-iniciar-o-frontend-nextjs)
  - [6.1 Instalação e Execução](#61-instalação-e-execução)
  - [6.2 Variáveis de Ambiente (Frontend)](#62-variáveis-de-ambiente-frontend)
  - [6.3 Rotas do Frontend](#63-rotas-do-frontend)
- [7. Gerar Tráfego e Popular os Dashboards](#7-gerar-tráfego-e-popular-os-dashboards)
- [8. Verificação e Troubleshooting](#8-verificação-e-troubleshooting)
  - [8.1 Validação da Stack](#81-validação-da-stack)
  - [8.2 Problemas Comuns](#82-problemas-comuns)
- [9. Parar os Serviços](#9-parar-os-serviços)

---

# 1. Pré-requisitos

| Dependência | Versão Mínima | Verificação |
|-------------|---------------|-------------|
| **Python** | 3.12+ | `python --version` |
| **pip** | 23+ | `pip --version` |
| **Node.js** | 18+ | `node --version` |
| **npm** | 9+ | `npm --version` |
| **Docker** | 24+ | `docker --version` |
| **Docker Compose** | 2.20+ | `docker compose version` |
| **Git** | 2.40+ | `git --version` |

```bash
git clone https://git.inteli.edu.br/graduacao/2026-1a/t13/g06
cd g06
```

---

# 2. Configuração do Ambiente Python

## 2.1 Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate    # macOS / Linux
# .venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

Todas as chamadas Python, uvicorn e pytest devem usar o `.venv` do repositório.

## 2.2 Variáveis de Ambiente (Backend)

Crie um arquivo `.env` na raiz do projeto. O `python-dotenv` carrega automaticamente em cada módulo.

| Variável | Uso | Exemplo |
|----------|-----|---------|
| `ASIS_APP_KEY` | Autenticação API (DN4/RNF2) | `D68C6D...` |
| `ASIS_ACCOUNT_KEY` | Rate limiting / tenant isolation | `94426c...` |
| `CLERK_SECRET_KEY` | Autenticação híbrida (INT3) | `sk_test_...` |
| `CLERK_PUBLISHABLE_KEY` | Autenticação híbrida (INT3) | `pk_test_...` |
| `CLERK_JWKS_URL` | Validação JWT Clerk | `https://.../.well-known/jwks.json` |
| `RED_TEAM_API_URL` | URL alvo dos testes red team | `http://127.0.0.1:8000` |
| `GITLAB_PRIVATE_TOKEN` | API GitLab (INT4) — opcional | `glpat-xxx` |

Nenhuma variável precisa ser exportada manualmente — basta ter o `.env` na raiz.

---

# 3. Subir a Stack de Observabilidade

## 3.1 Docker Compose

```bash
docker-compose up -d
```

O comando sobe três containers com provisionamento automático de datasources e dashboards no Grafana.

## 3.2 Serviços e Portas

| Serviço | Container | Porta | URL | Credenciais |
|---------|-----------|-------|-----|-------------|
| **Prometheus** | `asis-prometheus` | 9090 | http://localhost:9090/targets | — |
| **Grafana** | `asis-grafana` | 3000 | http://localhost:3000 | `admin` / `admin` |
| **Alertmanager** | `asis-alertmanager` | 9093 | http://localhost:9093 | — |

O Grafana inicia com o datasource Prometheus conectado e 4 dashboards pré-carregados:

| Dashboard | UID | Foco |
|-----------|-----|------|
| Dashboard da Qualidade | `asis-quality-dashboard` | 25 painéis técnicos (DN1-DN4, RF, Testes, Alertas) |
| Dashboard de Negócio | `asis-business-dashboard` | Leitura executiva de SLA, throughput e impacto |
| Dashboard de Saúde do Sistema | `asis-system-health-dashboard` | Saúde operacional, incidentes, circuit breaker |
| Dashboard de Testes Restantes | `asis-testing-gap-dashboard` | Cobertura e gaps de teste |

---

# 4. Iniciar a API ASIS

Em um terminal separado (com o `.venv` ativado):

```bash
python -m uvicorn src.core.api:app --host 0.0.0.0 --port 8000
```

A API expõe:
- `GET /metrics` — métricas Prometheus (DN1-DN4, RF1, RNF1)
- `GET /api/v1/dashboard/business` — dados agregados de negócio
- `GET /api/v1/dashboard/system-health` — dados de saúde do sistema
- `GET /api/v1/dashboard/testing-gap` — dados de cobertura de testes
- `GET /api/v1/dashboard/metadata` — metadados dos dashboards

Para verificar que a API está expondo métricas:

```bash
curl -s http://localhost:8000/metrics | head -20
```

---

# 5. Pytest Metrics Exporter (Opcional)

O exporter coleta métricas de testes pytest e as expõe para o Prometheus na porta 9092.

Em um terminal separado (com o `.venv` ativado):

```bash
python src/scripts/pytest_metrics_exporter.py --port 9092 --interval 300
```

| Parâmetro | CLI | Variável de Ambiente | Padrão |
|-----------|-----|---------------------|--------|
| Porta HTTP | `--port` | `PYTEST_EXPORTER_PORT` | 9092 |
| Intervalo entre execuções | `--interval` | `PYTEST_EXPORTER_INTERVAL` | 300s (5min) |

O Prometheus faz scrape de `host.docker.internal:9092/metrics` a cada 60s. Os painéis da seção "Massa de Testes" no dashboard da Qualidade dependem deste exporter.

---

# 6. Iniciar o Frontend Next.js

## 6.1 Instalação e Execução

```bash
cd dashboard/frontend
npm install
npm run dev
```

A aplicação roda em **http://localhost:3100**.

## 6.2 Variáveis de Ambiente (Frontend)

Crie o arquivo `dashboard/frontend/.env.local` (use `.env.example` como base):

```bash
cp dashboard/frontend/.env.example dashboard/frontend/.env.local
```

| Variável | Descrição | Valor Padrão |
|----------|-----------|--------------|
| `DASHBOARD_API_BASE_URL` | URL do backend FastAPI | `http://localhost:8000` |
| `DASHBOARD_ACCOUNT_KEY` | Chave da conta para autenticação | `conta-teste-123` |
| `DASHBOARD_APP_KEY` | Chave da aplicação | `app-teste-456` |
| `NEXT_PUBLIC_GRAFANA_URL` | URL do Grafana (usada nos iframes) | `http://localhost:3000` |
| `NEXT_PUBLIC_GRAFANA_THEME` | Tema dos embeds Grafana | `dark` |
| `OPENAI_API_KEY` | Chave OpenAI para busca IA (opcional) | — |
| `OPENAI_MODEL` | Modelo OpenAI | `gpt-4.1-mini` |
| `MAX_RESULTS` | Máximo de resultados na busca IA | `5` |

As credenciais de API ficam apenas no backend do Next.js. As variáveis `NEXT_PUBLIC_*` controlam a origem e o tema dos iframes Grafana no browser.

Sem `OPENAI_API_KEY`, a busca inteligente entra automaticamente em fallback local por tags.

## 6.3 Rotas do Frontend

| Rota | Descrição | Público-alvo |
|------|-----------|--------------|
| `/` | Landing page com navegação para os dashboards | Todos |
| `/business` | Dashboard de Negócio (KPIs, SLA, throughput) | Liderança, gestores |
| `/system-health` | Dashboard de Saúde do Sistema (incidentes, resiliência) | Engenharia, SRE, operação |
| `/ai-search` | Busca inteligente de painéis por linguagem natural | Qualquer usuário |

---

# 7. Gerar Tráfego e Popular os Dashboards

Os dashboards Grafana precisam de dados para exibir painéis. Para popular:

**Executar a suíte de testes (gera métricas na API):**

```bash
python -m pytest src/tests/ -q
```

Testes GitLab (blue/red) são skipados automaticamente se `GITLAB_PRIVATE_TOKEN` não estiver no `.env`.

**Gerar carga contínua com Locust:**

```bash
python -m locust -f src/locust_tests.py --headless -u 10 -r 2 --host http://localhost:8000
```

Após gerar tráfego, aguarde 15-60 segundos para o Prometheus coletar as métricas e os dashboards Grafana serem atualizados.

---

# 8. Verificação e Troubleshooting

## 8.1 Validação da Stack

```bash
# Verificar que a API está expondo métricas
curl -s http://localhost:8000/metrics | head -20

# Verificar targets no Prometheus (ambos devem estar UP)
curl -s http://localhost:9090/api/v1/targets | python -m json.tool | head -30

# Verificar que Grafana carregou o datasource
curl -s http://admin:admin@localhost:3000/api/datasources | python -m json.tool

# Verificar que os dashboards foram provisionados
curl -s http://admin:admin@localhost:3000/api/dashboards/uid/asis-quality-dashboard | python -m json.tool | head -10

# Verificar que o frontend responde
curl -s http://localhost:3100 | head -5
```

## 8.2 Problemas Comuns

| Problema | Causa Provável | Solução |
|----------|---------------|---------|
| Grafana sem dados nos painéis | API não está rodando ou Prometheus não consegue alcançar `host.docker.internal:8000` | Verificar se a API está rodando na porta 8000 e se o target está UP em `http://localhost:9090/targets` |
| Frontend mostra erro de conexão | Backend FastAPI não está acessível | Confirmar que a API está rodando e que `DASHBOARD_API_BASE_URL` no `.env.local` aponta para `http://localhost:8000` |
| Painéis de "Massa de Testes" vazios | Pytest exporter não está rodando | Iniciar o exporter conforme seção 5 |
| Busca IA retorna "Fallback local" | `OPENAI_API_KEY` não configurada | Adicionar a chave no `.env.local` ou usar normalmente (fallback funciona por tags) |
| Porta 3000 ocupada | Outro serviço usando a porta | Parar o serviço conflitante ou alterar a porta no `docker-compose.yml` |
| Porta 3100 ocupada | Outra instância do frontend | Parar o processo ou alterar a porta no `next.config.mjs` |

---

# 9. Parar os Serviços

```bash
# Parar a stack Docker (Prometheus + Grafana + Alertmanager)
docker-compose down

# Parar a API ASIS e o exporter: Ctrl+C nos terminais respectivos
# Parar o frontend Next.js: Ctrl+C no terminal do npm run dev
```

Para remover volumes Docker criados:

```bash
docker-compose down -v
```

---

# Resumo dos Serviços

| Serviço | Porta | Comando de Início |
|---------|-------|-------------------|
| **API ASIS** | 8000 | `python -m uvicorn src.core.api:app --host 0.0.0.0 --port 8000` |
| **Prometheus** | 9090 | `docker-compose up -d` |
| **Grafana** | 3000 | `docker-compose up -d` |
| **Alertmanager** | 9093 | `docker-compose up -d` |
| **Pytest Exporter** | 9092 | `python src/scripts/pytest_metrics_exporter.py` |
| **Frontend Next.js** | 3100 | `cd dashboard/frontend && npm run dev` |

Para operação completa, a ordem recomendada de inicialização é:

1. Ativar `.venv` e configurar `.env`
2. `docker-compose up -d` (Prometheus, Grafana, Alertmanager)
3. Iniciar API ASIS (porta 8000)
4. (Opcional) Iniciar Pytest Exporter (porta 9092)
5. Configurar `.env.local` e iniciar frontend Next.js (porta 3100)
6. Gerar tráfego com pytest ou Locust

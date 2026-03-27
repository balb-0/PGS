# Dashboard da Qualidade como Ativo de Software

## Prometheus vs Grafana

**Prometheus** é o sistema de coleta e armazenamento de métricas. Ele "scrape" (raspa) o endpoint `/metrics` da API ASIS a cada 15s e armazena as séries temporais. Os alertas (`rules.yml`) são avaliados pelo Prometheus.

**Grafana** é **apenas** a camada de visualização. Ele conecta ao Prometheus como datasource e executa queries PromQL para renderizar os gráficos do dashboard. Sem Prometheus rodando, o Grafana não tem dados.

```
API (:8000)  ──scrape──▶  Prometheus (:9090)  ──query──▶  Grafana (:3000)
Pytest (:9092) ──scrape──▶       │                      (painéis, filtros)
                                 │
                           Alertmanager (:9093)
```

## Truth Definitions

| # | Definição | Referência |
|---|-----------|------------|
| D1 | O dashboard consome métricas Prometheus coletadas via scrape do endpoint `/metrics` da API ASIS em `localhost:8000`. | `prometheus.docker.standalone.yml`, `src/core/api.py:1534` |
| D2 | A latência P90 (DN1) deve ser <= 500ms; acima de 650ms dispara alerta de warning. O painel exibe P50/P90/P99 ao longo do tempo. | `rules.yml:8`, `src/core/metrics.py:25` |
| D3 | Erros de validação (DN2) são contabilizados por tipo (`validation_type`) e campo (`field`) via `asis_validation_errors_total`. | `src/core/metrics.py:42` |
| D4 | A disponibilidade (DN3) é monitorada por: taxa de erro (limiar 30%), estado do circuit breaker (CLOSED/OPEN/HALF_OPEN), rate limit restante e uptime. | `rules.yml:27-52`, `src/core/metrics.py:52-82` |
| D5 | O não-repúdio (DN4) é verificado via contadores de entradas no audit log, tamanho do log e alertas por tipo (`asis_nr_alerts_total`). | `rules.yml:54-63`, `src/core/metrics.py:88-102` |
| D6 | O tamanho do ProcessStore e IdempotencyStore (RF1/DN3) são expostos como gauges para rastrear volume de dados. | `src/core/metrics.py:108-116` |
| D7 | Métricas de massa de testes (`pytest_tests_total`, `pytest_tests_passed`) são coletadas pelo exporter em `localhost:9092` com scrape a cada 60s. | `src/scripts/pytest_metrics_exporter.py`, `prometheus.docker.standalone.yml:25-29` |
| D8 | O dashboard possui filtros (variáveis template) para `endpoint`, `method`, `status`, `source`, `account` e `interval` de agregação. | `grafana/dashboards/asis-quality-dashboard.json` (seção templating) |
| D9 | Alertas Prometheus são exibidos na tabela de "Alertas Ativos" quando estão no estado `firing`, com severidade e DN mapeados. | `rules.yml` (7 regras), dashboard painel ID 25 |
| D10 | Grafana é provisionado automaticamente via Docker Compose com datasource Prometheus e o dashboard pré-carregado. | `grafana/provisioning/`, `docker-compose.yml` |
| D11 | As queries PromQL do dashboard seguem o padrão definido em `docs/plano_integracao_prometheus.md` seção 5.2. | `plano_integracao_prometheus.md` |
| D12 | O módulo `src/scripts/verifica_versao_gitlab.py` expõe `verificar_protocolo_gitlab()`, `get_ultimo_commit()` e `verificar_sincronismo()` que chamam a API v4 do GitLab. Testes gitlab são skipados automaticamente se `GITLAB_PRIVATE_TOKEN` não estiver configurado no `.env`. | `src/scripts/verifica_versao_gitlab.py` |

---

## Arquitetura do Dashboard

```
┌─────────────┐    scrape /metrics     ┌───────────┐
│  API ASIS   │ ◄────────────────────  │ Prometheus│
│  :8000      │                        │  :9090    │
└─────────────┘                        └─────┬─────┘
                                             │ query
┌─────────────┐    scrape /metrics     ┌─────┴─────┐
│  Pytest     │ ◄────────────────────  │  Grafana  │
│  Exporter   │                        │  :3000    │
│  :9092      │                        └───────────┘
└─────────────┘
```

## Painéis do Dashboard

| Seção | Painéis | Métricas Utilizadas |
|-------|---------|---------------------|
| **DN1 — Latência** | Gauge P90, Gauge P95, Taxa de req/s, Latência P50/P90/P99, Requisições por status/fonte | `asis_request_duration_seconds`, `asis_requests_total` |
| **DN2 — Integridade** | Erros por tipo (timeseries), Erros por campo (tabela) | `asis_validation_errors_total` |
| **DN3 — Disponibilidade** | Gauge taxa de erro, Stat uptime, Stat circuit breaker, Rate limit restante, Taxa de erro timeline | `asis_health_error_rate_percent`, `asis_health_uptime_seconds`, `asis_circuit_breaker_state`, `asis_rate_limit_remaining` |
| **DN4 — Não-Repúdio** | Stat entradas audit log, Stat tamanho log, Alertas NR por tipo, Crescimento log, Detecção violações | `asis_audit_log_entries_total`, `asis_audit_log_size`, `asis_nr_alerts_total` |
| **RF1/RF2 — Registros** | ProcessStore/IdempotencyStore, Requisições concorrentes, Health requests vs errors | `asis_process_store_size`, `asis_idempotency_store_size`, `asis_concurrent_requests`, `asis_health_total_requests`, `asis_health_total_errors` |
| **Massa de Testes** | Gauge pass rate %, Stat total, Stat passed, Stat failed | `pytest_tests_total`, `pytest_tests_passed` |
| **Alertas** | Tabela de alertas firing | `ALERTS{alertstate="firing"}` |

## Como Executar

### Dashboards Grafana (Executivo e Tecnico)

O fluxo oficial do projeto passa a ser **Grafana-first**, com 3 dashboards separados (equivalentes a abas de decisão):

- `ASIS TaxTech - Dashboard de Negocio`
- `ASIS TaxTech - Dashboard de Saude do Sistema`
- `ASIS TaxTech - Dashboard de Testes Restantes`

Arquivos provisionados:

- `grafana/dashboards/asis-business-dashboard.json`
- `grafana/dashboards/asis-system-health-dashboard.json`
- `grafana/dashboards/asis-testing-gap-dashboard.json`

Cada dashboard possui no minimo 8 paineis com foco em tomada de decisao, incluindo KPIs, tendencias, breakdown por causa, pressao operacional e risco.

Endpoints backend de agregacao permanecem disponiveis para evolucoes e consumo externo:

- `GET /api/v1/dashboard/business`
- `GET /api/v1/dashboard/system-health`
- `GET /api/v1/dashboard/testing-gap`
- `GET /api/v1/dashboard/metadata`

### Pré-requisitos
- Docker e Docker Compose instalados
- `.venv` criado e dependências instaladas (`pip install -r requirements.txt`)
- Arquivo `.env` presente na raiz (contém `ASIS_APP_KEY`, `ASIS_ACCOUNT_KEY`, chaves Clerk, etc.)

### Passo a Passo

Todas as chamadas Python/uvicorn/pytest devem usar o `.venv` do repositório.
O arquivo `.env` é carregado automaticamente pelo `python-dotenv` (já no `requirements.txt`).

```bash
# Definir atalho para o venv (todos os terminais)
VENV=.venv/bin/python

# 1. Iniciar a API ASIS (terminal 1)
$VENV -m uvicorn src.core.api:app --host 0.0.0.0 --port 8000

# 2. (Opcional) Iniciar o exporter de métricas pytest (terminal 2)
$VENV src/scripts/pytest_metrics_exporter.py --port 9092 --interval 300

# 3. Subir Prometheus + Alertmanager + Grafana (terminal 3)
docker-compose up -d

# 4. Acessar o dashboard
#    Grafana:     http://localhost:3000  (login: admin / admin)
#    Prometheus:  http://localhost:9090/targets
#    Alertmanager: http://localhost:9093

# 5. Gerar tráfego para popular o dashboard
#    Executar testes (gera métricas na API):
$VENV -m pytest src/tests/ -q

#    Nota: testes gitlab (blue/red) sao skipados automaticamente
#    se GITLAB_PRIVATE_TOKEN nao estiver no .env
#    Para roda-los: adicione GITLAB_PRIVATE_TOKEN=glpat-xxx ao .env

#    Ou usar Locust:
$VENV -m locust -f src/locust_tests.py --headless -u 10 -r 2 --host http://localhost:8000
```

### Variáveis de Ambiente

O `.env` é carregado automaticamente por `python-dotenv` em cada módulo. As variáveis necessárias:

| Variável | Uso | Exemplo |
|----------|-----|---------|
| `ASIS_APP_KEY` | Autenticação API (DN4/RNF2) | `D68C6D...` |
| `ASIS_ACCOUNT_KEY` | Rate limiting / tenant isolation | `94426c...` |
| `CLERK_SECRET_KEY` | Híbrido auth (INT3) | `sk_test_...` |
| `CLERK_PUBLISHABLE_KEY` | Híbrido auth (INT3) | `pk_test_...` |
| `CLERK_JWKS_URL` | Validação JWT Clerk | `https://.../.well-known/jwks.json` |
| `RED_TEAM_API_URL` | URL alvo dos testes red team | `http://127.0.0.1:8000` |

Nenhuma variável precisa ser exportada manualmente — basta ter o `.env` na raiz do projeto.

### Validar que Tudo Funciona

```bash
# Verificar que a API está expondo métricas
curl -s http://localhost:8000/metrics | head -20

# Verificar targets no Prometheus
curl -s http://localhost:9090/api/v1/targets | .venv/bin/python -m json.tool | head -30

# Verificar que Grafana carregou o datasource
curl -s http://admin:admin@localhost:3000/api/datasources | .venv/bin/python -m json.tool
```

### Parar Tudo

```bash
docker-compose down
```

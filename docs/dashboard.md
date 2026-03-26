# Dashboard da Qualidade como Ativo de Software

O **Dashboard da Qualidade ASIS TaxTech** consolida, em tempo real, todas as métricas de qualidade da API de auditoria fiscal. Ele cobre os quatro Direcionadores de Negócio (DN1-DN4), Requisitos Funcionais (RF1/RF2), Requisito Não Funcional de capacidade (RNF1), massa de testes automatizados e alertas operacionais.

A visualização é feita pelo **Grafana** (porta 3000), alimentado pelo **Prometheus** (porta 9090), que coleta métricas da API ASIS (porta 8000) e do exporter de testes pytest (porta 9092). O provisionamento é totalmente automático via Docker Compose.

| Item | Valor |
|------|-------|
| **UID** | `asis-quality-dashboard` |
| **Título** | ASIS TaxTech — Dashboard da Qualidade |
| **Refresh** | 15s (auto) |
| **Janela padrão** | Última 1 hora |
| **Tags** | `asis`, `qualidade`, `prometheus`, `dn1`, `dn2`, `dn3`, `dn4` |
| **Schema** | Grafana v39 |
| **JSON** | `grafana/dashboards/asis-quality-dashboard.json` |

---

## 1. Arquitetura da Stack de Observabilidade

```
┌──────────────────┐    scrape /metrics (15s)    ┌────────────────┐
│   API ASIS       │ ◄──────────────────────────  │   Prometheus   │
│   :8000          │                              │   :9090        │
│   (FastAPI)      │                              │                │
└──────────────────┘                              └───────┬────────┘
                                                          │
┌──────────────────┐    scrape /metrics (60s)              │  query (PromQL)
│  Pytest Exporter │ ◄──────────────────────────           │
│  :9092           │                              ┌───────┴────────┐
│  (prometheus_    │                              │    Grafana     │
│   client)        │                              │    :3000       │
└──────────────────┘                              │  (Dashboard)   │
                                                  └────────────────┘
                         alertas (firing)
                    ┌────────────────────────┐
                    │     Alertmanager       │
                    │     :9093              │
                    └────────────────────────┘
```

**Componentes e responsabilidades:**

| Componente | Porta | Função |
|------------|-------|--------|
| **API ASIS** (FastAPI) | 8000 | Expõe `GET /metrics` com métricas DN1-DN4, RF1, RNF1. Atualiza gauges com estado atual antes de cada scrape. |
| **Pytest Exporter** | 9092 | Servidor HTTP independente que roda pytest periodicamente e expõe `pytest_tests_total` / `pytest_tests_passed`. |
| **Prometheus** | 9090 | Coleta (scrape) métricas de ambas as fontes, armazena séries temporais e avalia regras de alerta. |
| **Grafana** | 3000 | Renderiza o dashboard com queries PromQL. Provisionado automaticamente com datasource e JSON. |
| **Alertmanager** | 9093 | Recebe alertas do Prometheus, agrupa, deduplica e roteia por severidade. |

**Provisionamento automático (Docker Compose):**

O `docker-compose.yml` monta três volumes no container Grafana:

| Volume local | Destino no container | Função |
|-------------|----------------------|--------|
| `grafana/provisioning/datasources/prometheus.yml` | `/etc/grafana/provisioning/datasources/` | Configura Prometheus como datasource padrão (UID: `prometheus`) |
| `grafana/provisioning/dashboards/dashboards.yml` | `/etc/grafana/provisioning/dashboards/` | File provider que carrega dashboards de `/var/lib/grafana/dashboards` |
| `grafana/dashboards/` | `/var/lib/grafana/dashboards/` | Contém o JSON do dashboard |

O Grafana inicia já com o datasource conectado e o dashboard pré-carregado, sem configuração manual.

---

## 2. Métricas Prometheus Expostas

Todas as métricas são definidas em `src/core/metrics.py` e instrumentadas na API (`src/core/api.py`). O endpoint `GET /metrics` atualiza os gauges com o estado atual dos componentes antes de gerar a saída.

### 2.1 API ASIS (porta 8000)

| Categoria | Métrica | Tipo Prometheus | Labels | Descrição |
|-----------|---------|-----------------|--------|-----------|
| **DN1** | `asis_request_duration_seconds` | Histogram | `endpoint`, `method`, `status`, `source` | Duração das requisições. Buckets: 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0, 2.0, 5.0s |
| **DN1** | `asis_requests_total` | Counter | `endpoint`, `method`, `status`, `source` | Total de requisições processadas |
| **DN2** | `asis_validation_errors_total` | Counter | `validation_type`, `field` | Erros de validação HTTP 400 |
| **DN3** | `asis_health_uptime_seconds` | Gauge | — | Uptime da API em segundos |
| **DN3** | `asis_health_total_requests` | Gauge | — | Total de requisições registradas pelo HealthChecker |
| **DN3** | `asis_health_total_errors` | Gauge | — | Total de erros registrados pelo HealthChecker |
| **DN3** | `asis_health_error_rate_percent` | Gauge | — | Taxa de erro em % (limiar: 30%) |
| **DN3** | `asis_circuit_breaker_state` | Gauge | `state` | Estado do circuit breaker: 0=CLOSED, 1=OPEN, 2=HALF_OPEN |
| **DN3** | `asis_rate_limit_remaining` | Gauge | `account_key_hash` | Requisições restantes na janela por conta |
| **DN4** | `asis_audit_log_entries_total` | Counter | — | Total de entradas no log de auditoria |
| **DN4** | `asis_audit_log_size` | Gauge | — | Tamanho atual do log de auditoria (registros) |
| **DN4** | `asis_nr_alerts_total` | Counter | `alert_type` | Alertas de não-repúdio emitidos |
| **RF1** | `asis_process_store_size` | Gauge | — | Quantidade de processos no ProcessStore |
| **RF1** | `asis_idempotency_store_size` | Gauge | — | Quantidade de chaves no IdempotencyStore |
| **RNF1** | `asis_concurrent_requests` | Gauge | — | Requisições em processamento simultâneo |

### 2.2 Pytest Exporter (porta 9092)

| Métrica | Tipo Prometheus | Descrição |
|---------|-----------------|-----------|
| `pytest_tests_total` | Gauge | Total de testes na suíte (passados + falhados + skipped + error) |
| `pytest_tests_passed` | Gauge | Total de testes que passaram na última execução |

O exporter (`src/scripts/pytest_metrics_exporter.py`) executa `pytest src/tests/ -q --tb=no` periodicamente (padrão: 300s) e atualiza os gauges. O Prometheus faz scrape a cada 60s.

---

## 3. Variáveis Template (Filtros)

O dashboard disponibiliza 6 variáveis no topo da página para drill-down dinâmico:

| Variável | Tipo | Multi-select | Fonte (PromQL) | Uso |
|----------|------|:---:|--------|-----|
| `$endpoint` | query | Sim | `label_values(asis_requests_total, endpoint)` | Filtra painéis de latência e requisições por endpoint |
| `$method` | query | Sim | `label_values(asis_requests_total, method)` | Filtra por método HTTP (GET, POST, etc.) |
| `$status` | query | Sim | `label_values(asis_requests_total, status)` | Filtra por status da resposta (success, error, etc.) |
| `$source` | query | Sim | `label_values(asis_requests_total, source)` | Filtra por fonte (real, mock) |
| `$account` | query | Sim | `label_values(asis_rate_limit_remaining, account_key_hash)` | Filtra rate limit por hash da conta |
| `$interval` | custom | Não | Valores fixos: `15s`, `30s`, **`1m`** (padrão), `5m`, `15m` | Janela de agregação para `rate()` e `increase()` |

Todas as variáveis query incluem opção "All" e atualizam ao trocar o intervalo de tempo.

---

## 4. Painéis do Dashboard

O dashboard contém **25 painéis** organizados em **7 seções** (rows). Cada painel é documentado com seu tipo Grafana, query PromQL exata e thresholds quando aplicáveis.

---

### 4.1 DN1 — Latência de Ingestão (SLA P90 ≤ 500ms)

5 painéis que monitoram a latência do fluxo de auditoria fiscal e o volume de requisições.

#### Painel 1 — Latência P90 (SLA: 500ms / Alerta: 650ms)

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Gauge |
| **Unidade** | segundos (s) |
| **Cálculo** | Último valor não-nulo |

**Query PromQL:**

```promql
histogram_quantile(0.9, sum(rate(asis_request_duration_seconds_bucket{endpoint=~"$endpoint"}[$interval])) by (le))
```

**Thresholds:**

| Faixa | Cor | Significado |
|-------|-----|-------------|
| 0 – 0.4s | Verde | Dentro do ideal |
| 0.4 – 0.5s | Amarelo | Aproximando-se do SLA |
| 0.5 – 0.65s | Laranja | **SLA violado** (P90 > 500ms) |
| > 0.65s | Vermelho | **Alerta de latência** (P90 > 650ms) |

---

#### Painel 2 — Latência P95

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Gauge |
| **Unidade** | segundos (s) |
| **Cálculo** | Último valor não-nulo |

**Query PromQL:**

```promql
histogram_quantile(0.95, sum(rate(asis_request_duration_seconds_bucket{endpoint=~"$endpoint"}[$interval])) by (le))
```

Sem thresholds customizados. Complementar ao P90 para visibilidade da cauda de latência.

---

#### Painel 3 — Taxa de Requisições por Endpoint (req/s)

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Tabela, à direita |
| **Tooltip** | Multi-series |

**Query PromQL:**

```promql
sum(rate(asis_requests_total{endpoint=~"$endpoint", method=~"$method", status=~"$status", source=~"$source"}[$interval])) by (endpoint)
```

Legenda: `{{ endpoint }}`. Mostra o throughput (req/s) de cada endpoint ao longo do tempo, filtrado pelas variáveis template.

---

#### Painel 4 — Latência ao Longo do Tempo (P50 / P90 / P99)

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Tabela, embaixo |
| **Tooltip** | Multi-series |

**Queries PromQL (3 séries):**

```promql
# P50 (mediana)
histogram_quantile(0.5, sum(rate(asis_request_duration_seconds_bucket{endpoint=~"$endpoint"}[$interval])) by (le))

# P90 (SLA)
histogram_quantile(0.9, sum(rate(asis_request_duration_seconds_bucket{endpoint=~"$endpoint"}[$interval])) by (le))

# P99 (cauda)
histogram_quantile(0.99, sum(rate(asis_request_duration_seconds_bucket{endpoint=~"$endpoint"}[$interval])) by (le))
```

Legendas: `P50`, `P90`, `P99`. Permite observar a distribuição de latência e detectar degradação progressiva.

---

#### Painel 5 — Requisições por Status e Fonte (real/mock)

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Tabela, embaixo |
| **Tooltip** | Multi-series |

**Query PromQL:**

```promql
sum(increase(asis_requests_total{endpoint=~"$endpoint", method=~"$method", status=~"$status", source=~"$source"}[5m])) by (status, source)
```

Legenda: `{{ status }} / {{ source }}`. Discrimina requisições por resultado (success/error) e origem (real/mock) em janelas de 5 minutos.

---

### 4.2 DN2 — Integridade dos Dados Fiscais

2 painéis que monitoram erros de validação nos dados fiscais ingeridos.

#### Painel 6 — Erros de Validação por Tipo

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Tabela, embaixo |
| **Tooltip** | Multi-series |

**Query PromQL:**

```promql
sum(increase(asis_validation_errors_total[$interval])) by (validation_type)
```

Legenda: `{{ validation_type }}`. Exibe a evolução temporal de erros agrupados por tipo de validação (ex.: `missing_field`, `invalid_type`, `out_of_range`).

---

#### Painel 7 — Erros de Validação por Campo

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Table |
| **Modo** | Instant query (snapshot atual) |
| **Ordenação** | Coluna "Erros", decrescente |

**Query PromQL:**

```promql
sum(increase(asis_validation_errors_total[$interval])) by (validation_type, field)
```

**Transformações aplicadas (rename):**

| Label original | Nome exibido |
|----------------|-------------|
| `validation_type` | Tipo |
| `field` | Campo |
| `Value` | Erros |

Permite identificar rapidamente quais campos (`sessao_cliente`, `valor`, `destino`) concentram a maior parte dos erros de integridade.

---

### 4.3 DN3 — Disponibilidade e Resiliência

5 painéis que monitoram a saúde operacional da API, incluindo taxa de erro, uptime, circuit breaker e rate limiting.

#### Painel 8 — Taxa de Erro % (limiar 30%)

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Gauge |
| **Unidade** | percent (%) |
| **Cálculo** | Último valor não-nulo |

**Query PromQL:**

```promql
asis_health_error_rate_percent
```

**Thresholds:**

| Faixa | Cor | Significado |
|-------|-----|-------------|
| 0 – 15% | Verde | Operação normal |
| 15 – 30% | Amarelo | Degradação detectada |
| > 30% | Vermelho | **Alerta DN3** — taxa de erro acima do limiar |

---

#### Painel 9 — Uptime (segundos)

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Stat |
| **Unidade** | segundos (s) |
| **Visual** | Valor + sparkline (area) |

**Query PromQL:**

```promql
asis_health_uptime_seconds
```

Mostra o tempo total que a API está ativa desde o último reinício.

---

#### Painel 10 — Circuit Breaker

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Stat |
| **Visual** | Fundo colorido, sem sparkline |

**Query PromQL:**

```promql
asis_circuit_breaker_state{state="OPEN"}
```

**Value mappings:**

| Valor numérico | Texto exibido | Cor |
|:-:|---|---|
| 0 | CLOSED | Verde |
| 1 | OPEN | Vermelho |
| 2 | HALF_OPEN | Amarelo |

O fundo do painel muda de cor conforme o estado, dando visibilidade instantânea de problemas de resiliência.

---

#### Painel 11 — Rate Limit Restante por Conta

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Lista, embaixo |
| **Tooltip** | Multi-series |

**Query PromQL:**

```promql
asis_rate_limit_remaining{account_key_hash=~"$account"}
```

Legenda: `{{ account_key_hash }}`. Mostra quantas requisições restam na janela de rate limiting para cada conta, permitindo identificar contas que se aproximam do esgotamento.

---

#### Painel 12 — Taxa de Erro ao Longo do Tempo

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries (largura total — 24 colunas) |
| **Legenda** | Lista, embaixo |
| **Tooltip** | Multi-series |

**Query PromQL:**

```promql
asis_health_error_rate_percent
```

Legenda: `Error Rate %`. Visualização temporal da taxa de erro para identificar tendências de degradação ou picos.

---

### 4.4 DN4 — Não-Repúdio e Auditoria

5 painéis que monitoram o log de auditoria, a integridade da hash chain e alertas de violação.

#### Painel 13 — Total de Entradas no Audit Log

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Stat |
| **Visual** | Valor + sparkline (area) |
| **Cor** | Verde (crescimento esperado) |

**Query PromQL:**

```promql
asis_audit_log_entries_total
```

Legenda: `Entradas`. Contagem acumulada de todas as operações registradas no log de auditoria.

---

#### Painel 14 — Tamanho do Audit Log (registros)

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Stat |
| **Visual** | Valor + sparkline (area) |

**Query PromQL:**

```promql
asis_audit_log_size
```

Legenda: `Registros`. Tamanho atual do log (pode divergir do total de entradas se houver compactação ou limpeza).

---

#### Painel 15 — Alertas de Não-Repúdio por Tipo

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Tabela, embaixo |
| **Tooltip** | Multi-series |

**Query PromQL:**

```promql
sum(increase(asis_nr_alerts_total[$interval])) by (alert_type)
```

Legenda: `{{ alert_type }}`. Exibe a frequência de alertas por tipo (ex.: `chain`, `missing_field`) ao longo do tempo.

**Thresholds:** Verde por padrão; Vermelho acima de 1 alerta (qualquer alerta é sinal de violação).

---

#### Painel 16 — Audit Log — Crescimento ao Longo do Tempo

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Lista, embaixo |
| **Tooltip** | Multi-series |

**Queries PromQL (2 séries):**

```promql
# Tamanho atual do log
asis_audit_log_size

# Total acumulado de entradas
asis_audit_log_entries_total
```

Legendas: `Tamanho`, `Total Entradas`. Permite correlacionar o crescimento do log com o volume de operações e detectar anomalias (ex.: tamanho estagnado com entradas crescendo).

---

#### Painel 17 — Alertas NR — Detecção de Violações

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Lista, embaixo |
| **Tooltip** | Multi-series |

**Query PromQL:**

```promql
sum(asis_nr_alerts_total) by (alert_type)
```

Legenda: `{{ alert_type }}`. Exibe o total acumulado de alertas por tipo, complementando o painel 15 (que mostra a taxa de novos alertas).

---

### 4.5 RF1 / RF2 — Processos e Registros

3 painéis que monitoram o volume de dados nos stores internos e a capacidade de processamento.

#### Painel 18 — ProcessStore e IdempotencyStore

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Lista, embaixo |
| **Tooltip** | Multi-series |

**Queries PromQL (2 séries):**

```promql
asis_process_store_size

asis_idempotency_store_size
```

Legendas: `ProcessStore`, `IdempotencyStore`. Rastreia o volume de dados armazenados em memória. Crescimento ilimitado indica risco de consumo de RAM (cf. DN3.R8).

---

#### Painel 19 — Requisições Concorrentes (RNF1)

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Lista, embaixo |
| **Tooltip** | Multi-series |

**Query PromQL:**

```promql
asis_concurrent_requests
```

Legenda: `Concorrentes`. Mostra o número de requisições em processamento simultâneo. Útil para dimensionamento de capacidade e detecção de picos de carga.

---

#### Painel 20 — Health — Total de Requisições vs Erros

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Timeseries |
| **Legenda** | Lista, embaixo |
| **Tooltip** | Multi-series |

**Queries PromQL (2 séries):**

```promql
asis_health_total_requests

asis_health_total_errors
```

Legendas: `Total Requests`, `Total Errors`. Comparação direta entre volume total e erros para visualizar a proporção e tendências.

---

### 4.6 Massa de Testes (Pytest)

4 painéis que exibem o status da suíte de testes automatizados, alimentados pelo pytest exporter (porta 9092).

#### Painel 21 — Taxa de Sucesso dos Testes %

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Gauge |
| **Unidade** | percent (%) |
| **Cálculo** | Último valor não-nulo |

**Query PromQL:**

```promql
(pytest_tests_passed / pytest_tests_total) * 100
```

**Thresholds:**

| Faixa | Cor | Significado |
|-------|-----|-------------|
| 0 – 50% | Vermelho | Suíte com falhas críticas |
| 50 – 80% | Amarelo | Parcialmente passando |
| > 80% | Verde | Suíte saudável |

---

#### Painel 22 — Total de Testes

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Stat |
| **Visual** | Valor + sparkline (area) |

**Query PromQL:**

```promql
pytest_tests_total
```

Legenda: `Total`. Número total de testes descobertos na última execução do pytest (inclui passed + failed + skipped + error).

---

#### Painel 23 — Testes Passando

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Stat |
| **Cor** | Verde fixo |
| **Visual** | Valor + sparkline (area) |

**Query PromQL:**

```promql
pytest_tests_passed
```

Legenda: `Passed`. Número de testes que passaram na última execução.

---

#### Painel 24 — Testes Falhando

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Stat |
| **Cor** | Vermelho fixo |
| **Visual** | Valor + sparkline (area) |

**Query PromQL:**

```promql
pytest_tests_total - pytest_tests_passed
```

Legenda: `Failed`. Derivado por subtração (total - passed). Threshold: vermelho se >= 1 teste falhando.

---

### 4.7 Alertas Ativos

1 painel que consolida todos os alertas Prometheus em estado `firing`.

#### Painel 25 — Alertas Prometheus Ativos

| Propriedade | Valor |
|-------------|-------|
| **Tipo** | Table (largura total — 24 colunas) |
| **Modo** | Instant query (snapshot atual) |

**Query PromQL:**

```promql
ALERTS{alertstate="firing"}
```

**Transformações aplicadas:**

| Operação | Detalhe |
|----------|---------|
| Renomear `alertname` → `Alerta` | Nome do alerta |
| Renomear `severity` → `Severidade` | `warning` ou `critical` |
| Renomear `dn` → `DN` | Direcionador de negócio associado |
| Renomear `Value` → `Estado` | Valor do alerta |
| Ocultar | `Time`, `__name__`, `instance`, `job`, `alertstate` |

Este painel funciona como painel de controle operacional, exibindo apenas alertas ativamente disparados.

---

## 5. Regras de Alerta Prometheus

As regras são definidas em `rules.yml` e avaliadas pelo Prometheus a cada 15s. Quando uma condição é verdadeira pelo período `for`, o alerta entra em estado `firing`.

| Alerta | Grupo | Expressão | Duração (`for`) | Severidade | DN | Descrição |
|--------|-------|-----------|:---:|:---:|:---:|-----------|
| **HighLatency** | `asis_dn1_latency` | `histogram_quantile(0.9, sum(rate(asis_request_duration_seconds_bucket[5m])) by (le)) > 0.65` | 2m | warning | DN1 | Latência P90 acima de 650ms |
| **SLAViolation** | `asis_dn1_latency` | `histogram_quantile(0.9, sum(rate(asis_request_duration_seconds_bucket[5m])) by (le)) > 0.5` | 2m | critical | DN1 | Violação de SLA — P90 acima de 500ms |
| **HighErrorRate** | `asis_dn3_availability` | `asis_health_error_rate_percent > 30` | 2m | warning | DN3 | Taxa de erro acima de 30% |
| **CircuitBreakerOpen** | `asis_dn3_availability` | `asis_circuit_breaker_state{state="OPEN"} == 1` | 1m | critical | DN3 | Circuit breaker em estado aberto |
| **RateLimitLow** | `asis_dn3_availability` | `asis_rate_limit_remaining < 3` | 2m | warning | DN3 | Rate limit restante baixo (< 3 requisições) |
| **AuditChainAlert** | `asis_dn4_non_repudiation` | `increase(asis_nr_alerts_total{alert_type="chain"}[5m]) > 0` | 1m | critical | DN4 | Cadeia de auditoria comprometida |

---

## 6. Alertmanager

O Alertmanager (`alertmanager.yml`) recebe alertas do Prometheus, agrupa por `alertname` + `severity` e roteia para receivers:

| Severidade | Receiver | Alertas encaminhados | Timing |
|:---:|----------|----------------------|--------|
| `critical` | `critical` | SLAViolation, CircuitBreakerOpen, AuditChainAlert | `group_wait: 30s` |
| `warning` | `warning` | HighLatency, HighErrorRate, RateLimitLow | `group_interval: 5m` |
| Demais | `default` | Agrupamento sem notificação | `repeat_interval: 5m` |

Os receivers estão configurados sem canais de notificação externa. Para ativar:

```yaml
# Exemplo: adicionar webhook ao receiver critical
receivers:
  - name: critical
    webhook_configs:
      - url: 'http://localhost:5001/webhook'

# Exemplo: Slack para warnings
  - name: warning
    slack_configs:
      - channel: '#alertas-asis'
        api_url: 'https://hooks.slack.com/services/...'
```

Interface web: http://localhost:9093

---

## 7. Pytest Metrics Exporter

O script `src/scripts/pytest_metrics_exporter.py` implementa o modelo Pull do Prometheus para métricas de testes.

**Funcionamento:**

1. Inicia um servidor HTTP na porta 9092 (via `prometheus_client.start_http_server`)
2. Em uma thread daemon, executa `pytest src/tests/ -q --tb=no` periodicamente
3. Parseia a saída do pytest com regex para extrair contagens de passed, failed, skipped, error
4. Atualiza os gauges `pytest_tests_total` e `pytest_tests_passed`
5. O Prometheus faz scrape de `host.docker.internal:9092/metrics` a cada 60s

**Configuração:**

| Parâmetro | CLI | Variável de ambiente | Padrão |
|-----------|-----|---------------------|--------|
| Porta HTTP | `--port` | `PYTEST_EXPORTER_PORT` | 9092 |
| Intervalo entre execuções | `--interval` | `PYTEST_EXPORTER_INTERVAL` | 300s (5min) |
| Raiz do projeto | — | `PROJECT_ROOT` | Diretório do script `../../` |

**Relação com os painéis:** Os 4 painéis da seção "Massa de Testes" (painéis 21–24) consomem exclusivamente as métricas deste exporter.

---

## 8. Truth Definitions

Cada definição mapeia um aspecto do dashboard ao código-fonte, garantindo rastreabilidade.

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
| D9 | Alertas Prometheus são exibidos na tabela de "Alertas Ativos" quando estão no estado `firing`, com severidade e DN mapeados. | `rules.yml` (6 regras), dashboard painel ID 25 |
| D10 | Grafana é provisionado automaticamente via Docker Compose com datasource Prometheus e o dashboard pré-carregado. | `grafana/provisioning/`, `docker-compose.yml` |
| D11 | As queries PromQL do dashboard seguem o padrão definido em `docs/plano_integracao_prometheus.md` seção 5.2. | `plano_integracao_prometheus.md` |
| D12 | O módulo `src/scripts/verifica_versao_gitlab.py` expõe `verificar_protocolo_gitlab()`, `get_ultimo_commit()` e `verificar_sincronismo()` que chamam a API v4 do GitLab. Testes gitlab são skipados automaticamente se `GITLAB_PRIVATE_TOKEN` não estiver configurado no `.env`. | `src/scripts/verifica_versao_gitlab.py` |

---

## 9. Como Executar

### 9.1 Pré-requisitos

- Docker e Docker Compose instalados
- `.venv` criado e dependências instaladas (`pip install -r requirements.txt`)
- Arquivo `.env` presente na raiz (ver seção 9.4)

### 9.2 Passo a Passo

Todas as chamadas Python/uvicorn/pytest devem usar o `.venv` do repositório. O `.env` é carregado automaticamente pelo `python-dotenv`.

```bash
VENV=.venv/bin/python

# 1. Iniciar a API ASIS (terminal 1)
$VENV -m uvicorn src.core.api:app --host 0.0.0.0 --port 8000

# 2. (Opcional) Iniciar o exporter de métricas pytest (terminal 2)
$VENV src/scripts/pytest_metrics_exporter.py --port 9092 --interval 300

# 3. Subir Prometheus + Alertmanager + Grafana (terminal 3)
docker-compose up -d

# 4. Acessar o dashboard
#    Grafana:      http://localhost:3000  (login: admin / admin)
#    Prometheus:   http://localhost:9090/targets
#    Alertmanager: http://localhost:9093
```

### 9.3 Gerar Tráfego para Popular o Dashboard

```bash
# Executar testes (gera métricas na API)
$VENV -m pytest src/tests/ -q

# Testes gitlab (blue/red) são skipados automaticamente
# se GITLAB_PRIVATE_TOKEN não estiver no .env.
# Para rodá-los: adicione GITLAB_PRIVATE_TOKEN=glpat-xxx ao .env

# Ou usar Locust para carga contínua
$VENV -m locust -f src/locust_tests.py --headless -u 10 -r 2 --host http://localhost:8000
```

### 9.4 Variáveis de Ambiente

O `.env` é carregado automaticamente por `python-dotenv` em cada módulo.

| Variável | Uso | Exemplo |
|----------|-----|---------|
| `ASIS_APP_KEY` | Autenticação API (DN4/RNF2) | `D68C6D...` |
| `ASIS_ACCOUNT_KEY` | Rate limiting / tenant isolation | `94426c...` |
| `CLERK_SECRET_KEY` | Autenticação híbrida (INT3) | `sk_test_...` |
| `CLERK_PUBLISHABLE_KEY` | Autenticação híbrida (INT3) | `pk_test_...` |
| `CLERK_JWKS_URL` | Validação JWT Clerk | `https://.../.well-known/jwks.json` |
| `RED_TEAM_API_URL` | URL alvo dos testes red team | `http://127.0.0.1:8000` |
| `GITLAB_PRIVATE_TOKEN` | API GitLab (INT4) — opcional | `glpat-xxx` |

Nenhuma variável precisa ser exportada manualmente — basta ter o `.env` na raiz do projeto.

### 9.5 Validar que Tudo Funciona

```bash
# Verificar que a API está expondo métricas
curl -s http://localhost:8000/metrics | head -20

# Verificar targets no Prometheus (ambos UP)
curl -s http://localhost:9090/api/v1/targets | python -m json.tool | head -30

# Verificar que Grafana carregou o datasource
curl -s http://admin:admin@localhost:3000/api/datasources | python -m json.tool

# Verificar que o dashboard foi provisionado
curl -s http://admin:admin@localhost:3000/api/dashboards/uid/asis-quality-dashboard | python -m json.tool | head -10
```

### 9.6 Parar Tudo

```bash
docker-compose down
```

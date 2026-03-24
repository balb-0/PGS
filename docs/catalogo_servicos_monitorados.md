# Catálogo de Serviços e Componentes Monitorados por Códigos de Qualidade

Este documento mapeia os endpoints da API ASIS TaxTech aos Direcionadores de Negócio (DN), Requisitos Funcionais (RF), Requisitos Não Funcionais (RNF) e Integrações (INT), definindo as métricas Prometheus associadas para o Dashboard da Qualidade como ativo de software.

**Versão:** 1.0  
**Data:** 2026-03-19  
**Branch:** feat/prometheus

---

## 1. Visão Geral

| Componente | Descrição | BD/DN Relacionados |
|------------|-----------|---------------------|
| API ASIS Proxy/Mock | API unificada com proxy para ASIS real e fallback mock | DN1, DN2, DN3, DN4, RF1, RF2, RNF1, RNF2, INT3 |
| HealthChecker | Monitoramento de saúde (uptime, taxa de erro) | DN3 |
| RateLimiter | Controle de taxa por account-key | DN3 |
| CircuitBreaker | Proteção contra falhas em cascata | DN3 |
| ProcessStore | Rastreio de processos assíncronos | RF1 |
| AuditLog | Log de auditoria com hash chain | DN4 |
| IdempotencyStore | Armazenamento de respostas idempotentes | DN3 |
| TransactionHistoryStore | Histórico para análise de sazonalidade | RNF1 |

---

## 2. Mapeamento Endpoint → DN → Métrica

### 2.1 Endpoints de Auditoria Fiscal

| Endpoint | Método | DN/RF/RNF | Métricas Prometheus | Descrição |
|----------|--------|-----------|---------------------|-----------|
| `/api/v1/auditar` | POST | DN1, DN2, RF1, RF2 | `asis_request_duration_seconds{endpoint="/api/v1/auditar",source="real\|mock"}`, `asis_requests_total`, `asis_validation_errors_total` | Auditoria fiscal base. Valida payload (DN2), gera tracking_id. Fallback mock quando API real falha. |
| `/api/v1/auditar/resilient` | POST | DN1, DN2, DN3, RF1, RF2 | `asis_request_duration_seconds`, `asis_requests_total`, `asis_rate_limit_remaining`, `asis_circuit_breaker_state`, `asis_health_error_rate` | Auditoria com rate limit, circuit breaker, idempotência. |
| `/api/v1/auditar/nr` | POST | DN1, DN2, DN4, RF1, RF2 | `asis_request_duration_seconds`, `asis_requests_total`, `asis_audit_log_entries_total`, `asis_nr_alerts_total` | Auditoria com não-repúdio (HMAC, recibo, log). |
| `/api/v1/auditar/clerk` | POST | DN1, DN2, DN4, INT3, RF1, RF2 | `asis_request_duration_seconds`, `asis_requests_total`, `asis_audit_log_entries_total` | Auditoria com autenticação híbrida Clerk + API Keys. |

### 2.2 Endpoints de Upload (Proxy ASIS)

| Endpoint | Método | DN/RF/RNF | Métricas Prometheus | Descrição |
|----------|--------|-----------|---------------------|-----------|
| `/api/v1/upload` | POST | DN1 | `asis_request_duration_seconds`, `asis_requests_total`, `asis_upload_source{source="real\|mock"}` | Upload multipart. Proxy para ASIS real com fallback mock. |
| `/api/v1/upload/base64` | POST | DN1 | `asis_request_duration_seconds`, `asis_requests_total` | Upload base64. Proxy para ASIS real com fallback mock. |

### 2.3 Endpoints de Consulta de Processo

| Endpoint | Método | DN/RF/RNF | Métricas Prometheus | Descrição |
|----------|--------|-----------|---------------------|-----------|
| `/api/v1/processo/{process_id}` | GET | RF1 | `asis_request_duration_seconds`, `asis_requests_total` | Consulta status de processo ASIS (proxy). |
| `/api/v1/processo/{tracking_id}` | GET | RF1 | `asis_request_duration_seconds`, `asis_requests_total`, `asis_process_store_size` | Consulta status por tracking_id (store local). |
| `/api/v1/resultado/processo/{process_id}` | GET | RF1 | `asis_request_duration_seconds`, `asis_requests_total` | Extração de resultados (proxy). |
| `/api/v1/resultado/processo/{process_id}/auditoria/{auditoria_id}` | GET | RF1 | `asis_request_duration_seconds`, `asis_requests_total` | Relatório base da auditoria (proxy). |

### 2.4 Endpoints de Não-Repúdio e Disputa

| Endpoint | Método | DN/RF/RNF | Métricas Prometheus | Descrição |
|----------|--------|-----------|---------------------|-----------|
| `/api/v1/disputa/nr` | POST | RNF1 | `asis_request_duration_seconds`, `asis_requests_total`, `asis_nr_alerts_total{alert_type="dispute"}` | Verificação de não-repúdio a partir de reclamação (análise de sazonalidade). |
| `/api/v1/historico/{actor_hash}` | GET | RNF1 | `asis_request_duration_seconds`, `asis_requests_total` | Consulta histórico de transações do ator. |
| `/api/v1/audit-log` | GET | DN4 | `asis_request_duration_seconds`, `asis_requests_total`, `asis_audit_log_size`, `asis_nr_alerts_total{alert_type="chain"}` | Log completo de auditoria e integridade da cadeia. |
| `/api/v1/audit-log/{position}` | GET | DN4 | `asis_request_duration_seconds`, `asis_requests_total` | Entrada específica do log de auditoria. |

### 2.5 Endpoint de Saúde

| Endpoint | Método | DN/RF/RNF | Métricas Prometheus | Descrição |
|----------|--------|-----------|---------------------|-----------|
| `/api/v1/health` | GET | DN3 | `asis_health_status`, `asis_health_uptime_seconds`, `asis_health_error_rate`, `asis_circuit_breaker_state`, `asis_availability_alert` | Health check público. Não exige autenticação. |

---

## 3. Mapeamento DN → Métricas e SLAs

| DN | SLA/Limiar | Métricas | Alerta Prometheus |
|----|------------|----------|-------------------|
| **DN1** (Latência) | P90 ≤ 500ms, Alerta 650ms | `asis_request_duration_seconds` | HighLatency, SLAViolation |
| **DN2** (Integridade) | Rejeição HTTP 400 para payloads inválidos | `asis_validation_errors_total` | — |
| **DN3** (Disponibilidade) | Taxa erro < 30%, Rate 10 req/min, Circuit 5 falhas | `asis_health_error_rate`, `asis_rate_limit_remaining`, `asis_circuit_breaker_state` | HighErrorRate, CircuitBreakerOpen, RateLimitLow |
| **DN4** (Não-Repúdio) | 100% assinaturas, cadeia íntegra | `asis_audit_log_entries_total`, `asis_nr_alerts_total` | AuditChainAlert |

---

## 4. Componentes de Código Monitorados

| Componente | Arquivo | Métricas Expostas |
|------------|---------|-------------------|
| HealthChecker | `api.py` (linhas 362-393) | `asis_health_uptime_seconds`, `asis_health_total_requests`, `asis_health_total_errors`, `asis_health_error_rate_percent` |
| RateLimiter | `api.py` (linhas 236-282) | `asis_rate_limit_remaining` (por account_key_hash) |
| CircuitBreaker | `api.py` (linhas 294-356) | `asis_circuit_breaker_state` (CLOSED=0, OPEN=1, HALF_OPEN=2) |
| ProcessStore | `api.py` (linhas 175-232) | `asis_process_store_size` |
| AuditLog | `api.py` (linhas 670+) | `asis_audit_log_size` |
| IdempotencyStore | `api.py` (linhas 407+) | `asis_idempotency_store_size` (opcional) |

---

## 5. Labels Padrão para Métricas

| Label | Valores | Uso |
|-------|---------|-----|
| `endpoint` | `/api/v1/auditar`, `/api/v1/auditar/resilient`, `/api/v1/auditar/nr`, `/api/v1/health`, etc. | Identificação do endpoint |
| `method` | `GET`, `POST` | Método HTTP |
| `status` | `success`, `error`, `validation_error` | Resultado da requisição |
| `source` | `real`, `mock` | Origem do processamento (API ASIS real ou fallback) |
| `dn` | `DN1`, `DN2`, `DN3`, `DN4` | Direcionador de negócio rastreado |
| `account_key_hash` | SHA-256 truncado (16 chars) | Isolamento por tenant sem expor chave |

---

## 6. Rastreabilidade para o Dashboard da Qualidade

Este catálogo sustenta os critérios do artefato **Documento de Dashboard da Qualidade como ativo de Software**:

- **Catálogo de serviços e componentes monitorados por códigos de qualidade [5.0 pts]**: Seções 1-4 deste documento.
- **Quadro de dados estatísticos**: Métricas de execuções (`asis_requests_total`, `asis_request_duration_seconds`), erros (`asis_validation_errors_total`, `asis_health_error_rate`), alertas (`asis_nr_alerts_total`), registros (`asis_process_store_size`, `asis_audit_log_size`).


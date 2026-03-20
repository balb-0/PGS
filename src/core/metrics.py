"""
Módulo de métricas Prometheus para a API ASIS TaxTech.

Expõe métricas alinhadas aos Direcionadores de Negócio (DN1-DN4) e ao
Dashboard da Qualidade como ativo de software.

Referência: docs/catalogo_servicos_monitorados.md
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from typing import Dict, Any, Optional
import hashlib

# =============================================================================
# DN1 — Latência de Ingestão (SLA P90 ≤ 500ms, Alerta 650ms)
# =============================================================================

asis_request_duration_seconds = Histogram(
    "asis_request_duration_seconds",
    "Duração das requisições em segundos (DN1)",
    ["endpoint", "method", "status", "source"],
    buckets=(0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0, 2.0, 5.0),
)

asis_requests_total = Counter(
    "asis_requests_total",
    "Total de requisições processadas",
    ["endpoint", "method", "status", "source"],
)

# =============================================================================
# DN2 — Integridade dos Dados Fiscais
# =============================================================================

asis_validation_errors_total = Counter(
    "asis_validation_errors_total",
    "Total de erros de validação (HTTP 400)",
    ["validation_type", "field"],
)

# =============================================================================
# DN3 — Disponibilidade e Resiliência
# =============================================================================

asis_health_uptime_seconds = Gauge(
    "asis_health_uptime_seconds",
    "Uptime da API em segundos (DN3)",
)

asis_health_total_requests = Gauge(
    "asis_health_total_requests",
    "Total de requisições registradas pelo HealthChecker",
)

asis_health_total_errors = Gauge(
    "asis_health_total_errors",
    "Total de erros registrados pelo HealthChecker",
)

asis_health_error_rate_percent = Gauge(
    "asis_health_error_rate_percent",
    "Taxa de erro em percentual (DN3 - limiar 30%)",
)

asis_circuit_breaker_state = Gauge(
    "asis_circuit_breaker_state",
    "Estado do circuit breaker: 0=CLOSED, 1=OPEN, 2=HALF_OPEN (DN3)",
    ["state"],
)

asis_rate_limit_remaining = Gauge(
    "asis_rate_limit_remaining",
    "Requisições restantes na janela por account_key_hash (DN3)",
    ["account_key_hash"],
)

# =============================================================================
# DN4 — Não-Repúdio
# =============================================================================

asis_audit_log_entries_total = Counter(
    "asis_audit_log_entries_total",
    "Total de entradas no log de auditoria (DN4)",
)

asis_audit_log_size = Gauge(
    "asis_audit_log_size",
    "Tamanho atual do log de auditoria (registros)",
)

asis_nr_alerts_total = Counter(
    "asis_nr_alerts_total",
    "Total de alertas de não-repúdio emitidos (DN4)",
    ["alert_type"],
)

# =============================================================================
# RF1 / Dashboard — Registros Gerados
# =============================================================================

asis_process_store_size = Gauge(
    "asis_process_store_size",
    "Quantidade de processos no ProcessStore (RF1)",
)

asis_idempotency_store_size = Gauge(
    "asis_idempotency_store_size",
    "Quantidade de chaves no IdempotencyStore (DN3)",
)

# =============================================================================
# RNF1 — Capacidade (requisições concorrentes)
# =============================================================================

asis_concurrent_requests = Gauge(
    "asis_concurrent_requests",
    "Requisições em processamento simultâneo (RNF1)",
)

# =============================================================================
# Funções de Instrumentação
# =============================================================================


def record_request(
    endpoint: str,
    method: str,
    duration_seconds: float,
    status: str = "success",
    source: str = "mock",
) -> None:
    """Registra uma requisição para métricas DN1."""
    asis_request_duration_seconds.labels(
        endpoint=endpoint, method=method, status=status, source=source
    ).observe(duration_seconds)
    asis_requests_total.labels(
        endpoint=endpoint, method=method, status=status, source=source
    ).inc()


def record_validation_error(validation_type: str, field: str = "") -> None:
    """Registra erro de validação DN2."""
    asis_validation_errors_total.labels(
        validation_type=validation_type, field=field
    ).inc()


def record_nr_alert(alert_type: str) -> None:
    """Registra alerta de não-repúdio DN4."""
    asis_nr_alerts_total.labels(alert_type=alert_type).inc()


def record_audit_log_entry() -> None:
    """Incrementa contador de entradas no log de auditoria DN4."""
    asis_audit_log_entries_total.inc()


def hash_account_key(account_key: str, length: int = 16) -> str:
    """Retorna hash truncado da account_key para uso como label (privacidade)."""
    return hashlib.sha256(account_key.encode()).hexdigest()[:length]


def update_gauges_from_state(
    health_status: Dict[str, Any],
    circuit_state: str,
    rate_limit_remaining_by_account: Dict[str, int],
    process_store_size: int,
    audit_log_size: int,
    idempotency_store_size: int = 0,
) -> None:
    """
    Atualiza os gauges com o estado atual dos componentes.
    Chamado pelo endpoint /metrics antes de expor os dados.
    """
    # DN3 — Health
    asis_health_uptime_seconds.set(health_status.get("uptime_seconds", 0))
    asis_health_total_requests.set(health_status.get("total_requests", 0))
    asis_health_total_errors.set(health_status.get("total_errors", 0))
    asis_health_error_rate_percent.set(health_status.get("error_rate_percent", 0))

    # DN3 — Circuit Breaker (1 = estado atual, 0 = demais)
    for s in ("CLOSED", "OPEN", "HALF_OPEN"):
        asis_circuit_breaker_state.labels(state=s).set(1 if s == circuit_state else 0)

    # DN3 — Rate Limit (uma série por account_key_hash)
    for key_hash, remaining in rate_limit_remaining_by_account.items():
        asis_rate_limit_remaining.labels(account_key_hash=key_hash).set(remaining)

    # RF1 / DN4 — Stores
    asis_process_store_size.set(process_store_size)
    asis_audit_log_size.set(audit_log_size)
    asis_idempotency_store_size.set(idempotency_store_size)


def get_metrics_output() -> bytes:
    """Retorna a saída no formato Prometheus (texto)."""
    return generate_latest(REGISTRY)


def get_content_type() -> str:
    """Retorna o Content-Type para a resposta /metrics."""
    return CONTENT_TYPE_LATEST

"""
Módulo de Disponibilidade e Resiliência — DN3
Projeto ASIS TaxTech - Grupo 06

Mecanismos implementados:
- DN3.1: Rate Limiting (janela deslizante por account-key)
- DN3.2: Circuit Breaker (proteção contra falhas em cascata)
- DN3.3: Health Check (monitoramento de saúde da API)
- DN3.4: Idempotência (chave de idempotência para reprocessamento seguro)
- DN3.5: Degradação Graciosa (fallback quando serviços auxiliares falham)
- DN3.6: Alerta de Disponibilidade (limiar 30%, padrão DN1)
"""

import time
import threading
import hashlib
import json
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


# ───────────────────────────────────────────────────────────────────────────
# Configurações
# ───────────────────────────────────────────────────────────────────────────

RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60.0

CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_RECOVERY_SECONDS = 30.0

ALERT_THRESHOLD_PERCENT = 0.30


# ───────────────────────────────────────────────────────────────────────────
# DN3.1 — Rate Limiter (janela deslizante)
# ───────────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Controle de taxa por account-key usando janela deslizante."""

    def __init__(
        self,
        max_requests: int = RATE_LIMIT_MAX_REQUESTS,
        window_seconds: float = RATE_LIMIT_WINDOW_SECONDS,
    ):
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, account_key: str) -> bool:
        now = time.time()
        with self._lock:
            timestamps = self._requests.setdefault(account_key, [])
            cutoff = now - self._window
            timestamps[:] = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= self._max_requests:
                return False
            timestamps.append(now)
            return True

    def remaining(self, account_key: str) -> int:
        now = time.time()
        with self._lock:
            timestamps = self._requests.get(account_key, [])
            cutoff = now - self._window
            active = [t for t in timestamps if t > cutoff]
            return max(0, self._max_requests - len(active))

    def reset(self, account_key: Optional[str] = None):
        with self._lock:
            if account_key:
                self._requests.pop(account_key, None)
            else:
                self._requests.clear()

    @property
    def max_requests(self) -> int:
        return self._max_requests

    @property
    def window_seconds(self) -> float:
        return self._window


# ───────────────────────────────────────────────────────────────────────────
# DN3.2 — Circuit Breaker
# ───────────────────────────────────────────────────────────────────────────

class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Proteção contra falhas em cascata.

    CLOSED  → funcionamento normal; conta falhas.
    OPEN    → bloqueia requisições por recovery_seconds.
    HALF_OPEN → permite 1 requisição de teste.
    """

    def __init__(
        self,
        threshold: int = CIRCUIT_BREAKER_THRESHOLD,
        recovery_seconds: float = CIRCUIT_BREAKER_RECOVERY_SECONDS,
    ):
        self._threshold = threshold
        self._recovery = recovery_seconds
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (
                    self._last_failure_time
                    and time.time() - self._last_failure_time >= self._recovery
                ):
                    self._state = CircuitState.HALF_OPEN
            return self._state

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failure_count

    def allow_request(self) -> bool:
        current = self.state
        return current in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._failure_count >= self._threshold:
                self._state = CircuitState.OPEN

    def reset(self):
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED
            self._last_failure_time = None

    @property
    def threshold(self) -> int:
        return self._threshold


# ───────────────────────────────────────────────────────────────────────────
# DN3.3 — Health Check
# ───────────────────────────────────────────────────────────────────────────

class HealthChecker:
    """Monitoramento de saúde da API e seus componentes."""

    def __init__(self):
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
        self._lock = threading.Lock()

    def record_request(self, success: bool = True):
        with self._lock:
            self._request_count += 1
            if not success:
                self._error_count += 1

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self._start_time
            error_rate = (
                (self._error_count / self._request_count * 100)
                if self._request_count > 0
                else 0.0
            )
            healthy = error_rate < (ALERT_THRESHOLD_PERCENT * 100)
            return {
                "status": "healthy" if healthy else "degraded",
                "uptime_seconds": round(uptime, 2),
                "total_requests": self._request_count,
                "total_errors": self._error_count,
                "error_rate_percent": round(error_rate, 2),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.1.0",
            }

    def reset(self):
        with self._lock:
            self._start_time = time.time()
            self._request_count = 0
            self._error_count = 0


# ───────────────────────────────────────────────────────────────────────────
# DN3.4 — Idempotência
# ───────────────────────────────────────────────────────────────────────────

class IdempotencyStore:
    """
    Armazena resultados de requisições por chave de idempotência.
    Garante que requisições duplicadas retornem o mesmo resultado.
    """

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def generate_key(self, account_key: str, payload: Dict[str, Any]) -> str:
        raw = account_key + "|" + json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._store.get(key)
            if entry:
                return entry["response"]
            return None

    def store(self, key: str, response: Dict[str, Any]):
        with self._lock:
            self._store[key] = {
                "response": response,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

    def exists(self, key: str) -> bool:
        with self._lock:
            return key in self._store

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self):
        with self._lock:
            self._store.clear()


# ───────────────────────────────────────────────────────────────────────────
# DN3.5 — Degradação Graciosa
# ───────────────────────────────────────────────────────────────────────────

def build_degraded_response(
    payload: Dict[str, Any],
    reason: str,
) -> Dict[str, Any]:
    """
    Constrói resposta de fallback quando o serviço opera em modo degradado.
    Retorna os dados básicos sem processamento completo.
    """
    return {
        "status": 207,
        "diagnostico": "Degradado",
        "motivo": reason,
        "detalhes": {
            "cliente": payload.get("sessao_cliente", "N/A"),
            "volume_processado": payload.get("valor", 0),
            "modulo": payload.get("destino", "N/A"),
        },
        "retry_after_seconds": int(CIRCUIT_BREAKER_RECOVERY_SECONDS),
    }


# ───────────────────────────────────────────────────────────────────────────
# DN3.6 — Alertas de Disponibilidade
# ───────────────────────────────────────────────────────────────────────────

def check_availability_alert(health: HealthChecker) -> Optional[str]:
    """Emite alerta quando taxa de erro ultrapassa limiar de 30%."""
    status = health.get_status()
    if status["error_rate_percent"] > ALERT_THRESHOLD_PERCENT * 100:
        return (
            f"ALERTA DISPONIBILIDADE: Taxa de erro em "
            f"{status['error_rate_percent']:.1f}% — acima do limiar de "
            f"{ALERT_THRESHOLD_PERCENT * 100:.0f}%"
        )
    return None


def check_circuit_alert(cb: CircuitBreaker) -> Optional[str]:
    """Emite alerta quando o circuit breaker está aberto."""
    if cb.state == CircuitState.OPEN:
        return (
            "ALERTA DISPONIBILIDADE: Circuit breaker ABERTO — "
            f"serviço indisponível após {cb.failure_count} falhas consecutivas"
        )
    return None


def check_rate_limit_alert(
    rl: RateLimiter, account_key: str
) -> Optional[str]:
    """Emite alerta quando restam menos de 30% das requisições."""
    remaining = rl.remaining(account_key)
    threshold = int(rl.max_requests * ALERT_THRESHOLD_PERCENT)
    if remaining <= threshold:
        return (
            f"ALERTA DISPONIBILIDADE: Apenas {remaining}/{rl.max_requests} "
            f"requisições restantes para a conta na janela de {rl.window_seconds}s"
        )
    return None


# ───────────────────────────────────────────────────────────────────────────
# Instâncias globais (singleton para o ciclo de vida da API)
# ───────────────────────────────────────────────────────────────────────────

rate_limiter = RateLimiter()
circuit_breaker = CircuitBreaker()
health_checker = HealthChecker()
idempotency_store = IdempotencyStore()

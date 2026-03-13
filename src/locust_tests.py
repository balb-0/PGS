"""
INT2 — Locust Stress Test Suite for ASIS TaxTech API

Covers 5 internal test scenarios (CEN-1 to CEN-5) targeting DN1 (Latency)
and DN3 (Availability/Resilience) business drivers.

Usage (run from g06/src/):
    # Start the API first
    python -m uvicorn core.api:app --host 127.0.0.1 --port 8000

    # Run Locust (web UI at http://localhost:8089)
    python -m locust -f locust_tests.py --host http://127.0.0.1:8000

    # Headless mode (CI/CD)
    python -m locust -f locust_tests.py --host http://127.0.0.1:8000 ^
        --headless -u 50 -r 10 --run-time 60s --csv results/locust
"""

import time
import uuid
import logging
import json
import numpy as np
from typing import Any

from locust import HttpUser, TaskSet, task, between, events, tag

# ---------------------------------------------------------------------------
# Protocol Version Definitions (CEN-1 to CEN-5)
# Each integration point has an expected response contract. If the contract
# changes, the verification function logs a protocol mismatch.
# ---------------------------------------------------------------------------

PROTOCOL_VERSIONS = {
    "CEN-1": {
        "version": "1.0.0",
        "endpoint": "POST /api/v1/auditar",
        "expected_fields": {"id", "status", "tracking_id", "arquivold", "diagnostico", "detalhes"},
        "expected_detail_fields": {"cliente", "volume_processado", "modulo"},
        "expected_status": 201,
    },
    "CEN-2": {
        "version": "1.2.0",
        "endpoint": "POST /api/v1/auditar/resilient",
        "expected_fields": {"id", "status", "tracking_id", "arquivold", "diagnostico", "detalhes", "availability"},
        "expected_availability_fields": {"circuit_state", "rate_limit_remaining", "idempotent_replay", "alert"},
        "expected_status": 201,
    },
    "CEN-3": {
        "version": "1.1.0",
        "endpoint": "GET /api/v1/health",
        "expected_fields": {"status", "uptime_seconds", "total_requests", "total_errors", "error_rate_percent", "timestamp", "version"},
        "expected_status": 200,
    },
    "CEN-4": {
        "version": "1.0.0",
        "endpoint": "Authentication Protocol",
        "expected_401_on_missing_headers": True,
        "expected_403_on_invalid_credentials": True,
    },
    "CEN-5": {
        "version": "1.0.0",
        "endpoint": "POST /api/v1/auditar/nr",
        "expected_fields": {"id", "status", "tracking_id", "arquivold", "diagnostico", "detalhes", "non_repudiation"},
        "expected_nr_fields": {"signature", "timestamp", "actor", "receipt", "log_position", "log_entry_hash", "alert", "chain_alert"},
        "expected_status": 201,
    },
}

logger = logging.getLogger("int2-locust")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Protocol Verification Functions
# ---------------------------------------------------------------------------

def verify_protocol_cen1(response_json: dict) -> bool:
    """CEN-1: Validate /api/v1/auditar response contract."""
    spec = PROTOCOL_VERSIONS["CEN-1"]
    missing = spec["expected_fields"] - set(response_json.keys())
    if missing:
        logger.warning("CEN-1 protocol mismatch (v%s): missing fields %s", spec["version"], missing)
        return False
    detalhes = response_json.get("detalhes", {})
    missing_detail = spec["expected_detail_fields"] - set(detalhes.keys())
    if missing_detail:
        logger.warning("CEN-1 protocol mismatch (v%s): missing detail fields %s", spec["version"], missing_detail)
        return False
    return True


def verify_protocol_cen2(response_json: dict) -> bool:
    """CEN-2: Validate /api/v1/auditar/resilient response contract."""
    spec = PROTOCOL_VERSIONS["CEN-2"]
    missing = spec["expected_fields"] - set(response_json.keys())
    if missing:
        logger.warning("CEN-2 protocol mismatch (v%s): missing fields %s", spec["version"], missing)
        return False
    availability = response_json.get("availability", {})
    missing_avail = spec["expected_availability_fields"] - set(availability.keys())
    if missing_avail:
        logger.warning("CEN-2 protocol mismatch (v%s): missing availability fields %s", spec["version"], missing_avail)
        return False
    return True


def verify_protocol_cen3(response_json: dict) -> bool:
    """CEN-3: Validate /api/v1/health response contract."""
    spec = PROTOCOL_VERSIONS["CEN-3"]
    missing = spec["expected_fields"] - set(response_json.keys())
    if missing:
        logger.warning("CEN-3 protocol mismatch (v%s): missing fields %s", spec["version"], missing)
        return False
    return True


def verify_protocol_cen5(response_json: dict) -> bool:
    """CEN-5: Validate /api/v1/auditar/nr response contract."""
    spec = PROTOCOL_VERSIONS["CEN-5"]
    missing = spec["expected_fields"] - set(response_json.keys())
    if missing:
        logger.warning("CEN-5 protocol mismatch (v%s): missing fields %s", spec["version"], missing)
        return False
    nr = response_json.get("non_repudiation", {})
    missing_nr = spec["expected_nr_fields"] - set(nr.keys())
    if missing_nr:
        logger.warning("CEN-5 protocol mismatch (v%s): missing NR fields %s", spec["version"], missing_nr)
        return False
    return True


# ---------------------------------------------------------------------------
# Shared Constants — Real ASIS TaxTech Credentials
# ---------------------------------------------------------------------------

ASIS_ACCOUNT_KEY = "94426c03635f18fcfb5060ee2f38f5e01c26a6c6c13f1978b732e65cbc0bfb0c"
ASIS_APP_KEY = "D68C6DA8D520CDF6FBE48D36FB2634691B926F981FC5B755D09F8E8623EE37F2"

AUTH_HEADERS_DN1 = {
    "account-key": ASIS_ACCOUNT_KEY,
    "app-key": ASIS_APP_KEY,
    "Content-Type": "application/json",
}

AUTH_HEADERS_DN3 = {
    "account-key": ASIS_ACCOUNT_KEY,
    "app-key": ASIS_APP_KEY,
    "Content-Type": "application/json",
}

AUTH_HEADERS_NR = {
    "account-key": ASIS_ACCOUNT_KEY,
    "app-key": ASIS_APP_KEY,
    "Content-Type": "application/json",
}

SLA_LATENCY_MS = 500
ALERT_LATENCY_MS = 650

VALID_PAYLOAD = {
    "sessao_cliente": "LOCUST_STRESS_SESSION",
    "valor": 3200.00,
    "destino": "EFD_ICMS_IPI",
}

ALT_PAYLOAD = {
    "sessao_cliente": "LOCUST_STRESS_ALT",
    "valor": 8100.75,
    "destino": "NCM_AUDIT",
}


# ---------------------------------------------------------------------------
# Metrics Collector (aggregates across all users for final report)
# ---------------------------------------------------------------------------

class MetricsCollector:
    """Collects per-scenario latency data for DN1/DN3 SLA analysis."""

    def __init__(self):
        self._data: dict[str, list[float]] = {}

    def record(self, scenario: str, latency_ms: float):
        self._data.setdefault(scenario, []).append(latency_ms)

    def report(self) -> dict[str, Any]:
        result = {}
        for scenario, latencies in self._data.items():
            arr = np.array(latencies)
            total = len(arr)
            within_sla = int(np.sum(arr <= SLA_LATENCY_MS))
            within_alert = int(np.sum(arr <= ALERT_LATENCY_MS))
            result[scenario] = {
                "count": total,
                "min_ms": round(float(np.min(arr)), 2),
                "max_ms": round(float(np.max(arr)), 2),
                "mean_ms": round(float(np.mean(arr)), 2),
                "p50_ms": round(float(np.percentile(arr, 50)), 2),
                "p90_ms": round(float(np.percentile(arr, 90)), 2),
                "p99_ms": round(float(np.percentile(arr, 99)), 2),
                "sla_conformity_pct": round(within_sla / total * 100, 2) if total else 0,
                "alert_conformity_pct": round(within_alert / total * 100, 2) if total else 0,
            }
        return result


metrics = MetricsCollector()


# ---------------------------------------------------------------------------
# CEN-1: DN1 Latency User — POST /api/v1/auditar
# ---------------------------------------------------------------------------

class DN1LatencyTasks(TaskSet):
    """
    CEN-1: Stress tests targeting the fiscal audit ingestion endpoint.
    Validates SLA compliance (P90 <= 500ms) under concurrent load.
    """

    @tag("CEN-1", "DN1", "latency")
    @task(10)
    def auditar_valid_payload(self):
        """Standard audit request with valid EFD_ICMS_IPI payload."""
        start = time.perf_counter()
        with self.client.post(
            "/api/v1/auditar",
            json=VALID_PAYLOAD,
            headers=AUTH_HEADERS_DN1,
            catch_response=True,
        ) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            metrics.record("CEN-1:auditar", elapsed_ms)
            if resp.status_code != 201:
                resp.failure(f"Expected 201, got {resp.status_code}")
            else:
                data = resp.json()
                if not verify_protocol_cen1(data):
                    resp.failure("CEN-1 protocol mismatch")
                elif elapsed_ms > ALERT_LATENCY_MS:
                    resp.failure(f"Latency {elapsed_ms:.0f}ms > alert threshold {ALERT_LATENCY_MS}ms")
                else:
                    resp.success()

    @tag("CEN-1", "DN1", "latency")
    @task(5)
    def auditar_alt_payload(self):
        """Audit request with alternate NCM_AUDIT payload."""
        start = time.perf_counter()
        with self.client.post(
            "/api/v1/auditar",
            json=ALT_PAYLOAD,
            headers=AUTH_HEADERS_DN1,
            catch_response=True,
        ) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            metrics.record("CEN-1:auditar_alt", elapsed_ms)
            if resp.status_code != 201:
                resp.failure(f"Expected 201, got {resp.status_code}")
            else:
                data = resp.json()
                if not verify_protocol_cen1(data):
                    resp.failure("CEN-1 protocol mismatch")
                else:
                    resp.success()

    @tag("CEN-1", "DN1", "latency", "heavy")
    @task(1)
    def auditar_large_volume(self):
        """Audit request with high document volume to stress processing."""
        payload = {
            "sessao_cliente": "LOCUST_HEAVY_SESSION",
            "valor": 999999.99,
            "destino": "SPED_FISCAL",
        }
        start = time.perf_counter()
        with self.client.post(
            "/api/v1/auditar",
            json=payload,
            headers=AUTH_HEADERS_DN1,
            catch_response=True,
        ) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            metrics.record("CEN-1:auditar_heavy", elapsed_ms)
            if resp.status_code != 201:
                resp.failure(f"Expected 201, got {resp.status_code}")
            else:
                resp.success()


class DN1LatencyUser(HttpUser):
    """
    CEN-1 / DN1: Simulates concurrent users submitting fiscal audit documents.
    Aggressive wait_time to generate high throughput for latency measurement.
    """
    tasks = [DN1LatencyTasks]
    wait_time = between(0.5, 2)
    weight = 5

    def on_start(self):
        logger.info("DN1LatencyUser started — verifying CEN-1 protocol")
        with self.client.post(
            "/api/v1/auditar",
            json=VALID_PAYLOAD,
            headers=AUTH_HEADERS_DN1,
            catch_response=True,
            name="CEN-1:protocol_check",
        ) as resp:
            if resp.status_code == 201:
                verify_protocol_cen1(resp.json())
            resp.success()


# ---------------------------------------------------------------------------
# CEN-2 / CEN-3: DN3 Resilience User — /api/v1/auditar/resilient + /health
# ---------------------------------------------------------------------------

class DN3ResilienceTasks(TaskSet):
    """
    CEN-2 & CEN-3: Stress tests targeting resilience mechanisms.
    Exercises rate limiting, circuit breaker, idempotency, health check,
    and graceful degradation under concurrent load.
    """

    @tag("CEN-2", "DN3", "resilience")
    @task(8)
    def auditar_resilient_valid(self):
        """Standard resilient audit — expects 201 or 429 (rate limited)."""
        start = time.perf_counter()
        with self.client.post(
            "/api/v1/auditar/resilient",
            json=VALID_PAYLOAD,
            headers=AUTH_HEADERS_DN3,
            catch_response=True,
        ) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            metrics.record("CEN-2:resilient", elapsed_ms)
            if resp.status_code == 201:
                data = resp.json()
                if not verify_protocol_cen2(data):
                    resp.failure("CEN-2 protocol mismatch")
                else:
                    resp.success()
            elif resp.status_code == 429:
                resp.success()
            elif resp.status_code == 503:
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @tag("CEN-2", "DN3", "idempotency")
    @task(3)
    def auditar_resilient_idempotent(self):
        """Send duplicate requests with same idempotency-key."""
        idemp_key = f"locust-idemp-{uuid.uuid4().hex[:8]}"
        headers = {**AUTH_HEADERS_DN3, "idempotency-key": idemp_key}

        with self.client.post(
            "/api/v1/auditar/resilient",
            json=VALID_PAYLOAD,
            headers=headers,
            catch_response=True,
            name="/api/v1/auditar/resilient [idempotent-1st]",
        ) as resp1:
            if resp1.status_code in (201, 429, 503):
                resp1.success()
            else:
                resp1.failure(f"Unexpected status {resp1.status_code}")

        with self.client.post(
            "/api/v1/auditar/resilient",
            json=VALID_PAYLOAD,
            headers=headers,
            catch_response=True,
            name="/api/v1/auditar/resilient [idempotent-replay]",
        ) as resp2:
            if resp2.status_code in (201, 429, 503):
                resp2.success()
            else:
                resp2.failure(f"Unexpected status {resp2.status_code}")

    @tag("CEN-2", "DN3", "rate-limit")
    @task(2)
    def auditar_resilient_rate_limit_burst(self):
        """
        Rapid-fire requests from a single account to trigger rate limiting.
        Expects 429 after 10 requests in 60s window.
        """
        burst_headers = {
            "account-key": f"locust-burst-{uuid.uuid4().hex[:6]}",
            "app-key": ASIS_APP_KEY,
            "Content-Type": "application/json",
        }
        accepted = 0
        rate_limited = 0
        for i in range(15):
            with self.client.post(
                "/api/v1/auditar/resilient",
                json=VALID_PAYLOAD,
                headers=burst_headers,
                catch_response=True,
                name="/api/v1/auditar/resilient [rate-burst]",
            ) as resp:
                if resp.status_code == 201:
                    accepted += 1
                    resp.success()
                elif resp.status_code == 429:
                    rate_limited += 1
                    resp.success()
                elif resp.status_code in (400, 403, 503):
                    resp.success()
                else:
                    resp.failure(f"Unexpected status {resp.status_code}")

    @tag("CEN-3", "DN3", "health")
    @task(5)
    def health_check(self):
        """CEN-3: Health check endpoint — no authentication required."""
        start = time.perf_counter()
        with self.client.get(
            "/api/v1/health",
            catch_response=True,
        ) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            metrics.record("CEN-3:health", elapsed_ms)
            if resp.status_code != 200:
                resp.failure(f"Health check returned {resp.status_code}")
            else:
                data = resp.json()
                if not verify_protocol_cen3(data):
                    resp.failure("CEN-3 protocol mismatch")
                elif data.get("status") not in ("healthy", "degraded"):
                    resp.failure(f"Unexpected health status: {data.get('status')}")
                else:
                    resp.success()

    @tag("CEN-2", "DN3", "degradation")
    @task(1)
    def trigger_circuit_breaker(self):
        """
        Send invalid payloads to accumulate failures and potentially
        trigger the circuit breaker (OPEN state after 5 consecutive failures).
        """
        invalid_payload = {"sessao_cliente": "LOCUST_INVALID", "valor": -1, "destino": "EFD_ICMS_IPI"}
        with self.client.post(
            "/api/v1/auditar/resilient",
            json=invalid_payload,
            headers=AUTH_HEADERS_DN3,
            catch_response=True,
            name="/api/v1/auditar/resilient [invalid-trigger]",
        ) as resp:
            if resp.status_code in (400, 429, 503):
                resp.success()
            elif resp.status_code == 201:
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")


class DN3ResilienceUser(HttpUser):
    """
    CEN-2 & CEN-3 / DN3: Simulates users interacting with resilience layer.
    Tests rate limiting, circuit breaker, idempotency, and health check
    under concurrent load conditions.
    """
    tasks = [DN3ResilienceTasks]
    wait_time = between(0.5, 3)
    weight = 3

    def on_start(self):
        logger.info("DN3ResilienceUser started — verifying CEN-2 & CEN-3 protocols")
        with self.client.get(
            "/api/v1/health",
            catch_response=True,
            name="CEN-3:protocol_check",
        ) as resp:
            if resp.status_code == 200:
                verify_protocol_cen3(resp.json())
            resp.success()


# ---------------------------------------------------------------------------
# CEN-4: Authentication Validation User
# ---------------------------------------------------------------------------

class AuthValidationTasks(TaskSet):
    """
    CEN-4: Validates authentication protocol under load.
    Ensures 401 on missing headers and 403 on invalid credentials.
    """

    @tag("CEN-4", "auth")
    @task(5)
    def missing_headers(self):
        """Request without authentication headers — expects 401."""
        with self.client.post(
            "/api/v1/auditar",
            json=VALID_PAYLOAD,
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="/api/v1/auditar [no-auth]",
        ) as resp:
            if resp.status_code == 401:
                resp.success()
            else:
                resp.failure(f"Expected 401, got {resp.status_code}")

    @tag("CEN-4", "auth")
    @task(3)
    def invalid_credentials(self):
        """Request with invalid credentials — expects 403."""
        headers = {
            "account-key": "invalid-account-xyz",
            "app-key": "invalid-app-xyz",
            "Content-Type": "application/json",
        }
        with self.client.post(
            "/api/v1/auditar",
            json=VALID_PAYLOAD,
            headers=headers,
            catch_response=True,
            name="/api/v1/auditar [invalid-auth]",
        ) as resp:
            if resp.status_code == 403:
                resp.success()
            else:
                resp.failure(f"Expected 403, got {resp.status_code}")

    @tag("CEN-4", "auth")
    @task(3)
    def partial_headers(self):
        """Request with only account-key, missing app-key — expects 401."""
        headers = {
            "account-key": ASIS_ACCOUNT_KEY,
            "Content-Type": "application/json",
        }
        with self.client.post(
            "/api/v1/auditar",
            json=VALID_PAYLOAD,
            headers=headers,
            catch_response=True,
            name="/api/v1/auditar [partial-auth]",
        ) as resp:
            if resp.status_code == 401:
                resp.success()
            else:
                resp.failure(f"Expected 401, got {resp.status_code}")

    @tag("CEN-4", "auth")
    @task(2)
    def valid_auth_resilient(self):
        """Valid auth on resilient endpoint — expects 201/429/503."""
        with self.client.post(
            "/api/v1/auditar/resilient",
            json=VALID_PAYLOAD,
            headers=AUTH_HEADERS_DN3,
            catch_response=True,
            name="/api/v1/auditar/resilient [valid-auth]",
        ) as resp:
            if resp.status_code in (201, 429, 503):
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    @tag("CEN-4", "auth")
    @task(2)
    def no_auth_health(self):
        """Health endpoint requires no auth — expects 200."""
        with self.client.get(
            "/api/v1/health",
            catch_response=True,
            name="/api/v1/health [no-auth-expected-ok]",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Expected 200, got {resp.status_code}")


class AuthValidationUser(HttpUser):
    """
    CEN-4: Simulates authentication edge cases under concurrent load.
    Validates that the auth protocol rejects correctly in all scenarios.
    """
    tasks = [AuthValidationTasks]
    wait_time = between(1, 4)
    weight = 1


# ---------------------------------------------------------------------------
# CEN-5: Integration Protocol Checker (Non-Repudiation + full sweep)
# ---------------------------------------------------------------------------

class ProtocolCheckerTasks(TaskSet):
    """
    CEN-5 + periodic sweep of all CEN scenarios.
    Calls each integration endpoint and validates the response schema
    against the expected protocol version.
    """

    @tag("CEN-5", "DN4", "non-repudiation")
    @task(5)
    def auditar_nr(self):
        """CEN-5: Non-repudiation audit with HMAC and audit log chain."""
        payload = {
            "sessao_cliente": f"LOCUST_NR_{uuid.uuid4().hex[:6]}",
            "valor": 5500.00,
            "destino": "ECF",
        }
        start = time.perf_counter()
        with self.client.post(
            "/api/v1/auditar/nr",
            json=payload,
            headers=AUTH_HEADERS_NR,
            catch_response=True,
        ) as resp:
            elapsed_ms = (time.perf_counter() - start) * 1000
            metrics.record("CEN-5:auditar_nr", elapsed_ms)
            if resp.status_code == 201:
                data = resp.json()
                if not verify_protocol_cen5(data):
                    resp.failure("CEN-5 protocol mismatch")
                else:
                    resp.success()
            elif resp.status_code == 409:
                resp.success()
            else:
                resp.failure(f"Expected 201 or 409, got {resp.status_code}")

    @tag("CEN-5", "DN4", "audit-log")
    @task(2)
    def check_audit_log(self):
        """Verify audit log endpoint returns valid chain."""
        with self.client.get(
            "/api/v1/audit-log",
            headers=AUTH_HEADERS_NR,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                if "entries" not in data or "chain_integrity" not in data:
                    resp.failure("Audit log missing expected fields")
                else:
                    resp.success()
            else:
                resp.failure(f"Expected 200, got {resp.status_code}")

    @tag("protocol-sweep")
    @task(1)
    def full_protocol_sweep(self):
        """
        Periodic sweep: call all 5 CEN endpoints and verify protocol
        contracts. Logs any mismatches to alert on version drift.
        """
        # CEN-1
        with self.client.post(
            "/api/v1/auditar",
            json=VALID_PAYLOAD,
            headers=AUTH_HEADERS_DN1,
            catch_response=True,
            name="sweep:CEN-1",
        ) as r:
            if r.status_code == 201:
                verify_protocol_cen1(r.json())
            r.success()

        # CEN-2
        with self.client.post(
            "/api/v1/auditar/resilient",
            json=VALID_PAYLOAD,
            headers=AUTH_HEADERS_DN3,
            catch_response=True,
            name="sweep:CEN-2",
        ) as r:
            if r.status_code == 201:
                verify_protocol_cen2(r.json())
            r.success()

        # CEN-3
        with self.client.get(
            "/api/v1/health",
            catch_response=True,
            name="sweep:CEN-3",
        ) as r:
            if r.status_code == 200:
                verify_protocol_cen3(r.json())
            r.success()

        # CEN-4 (auth check)
        with self.client.post(
            "/api/v1/auditar",
            json=VALID_PAYLOAD,
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="sweep:CEN-4",
        ) as r:
            if r.status_code != 401:
                logger.warning("CEN-4 protocol mismatch: expected 401, got %d", r.status_code)
            r.success()

        # CEN-5
        nr_payload = {
            "sessao_cliente": f"SWEEP_NR_{uuid.uuid4().hex[:6]}",
            "valor": 1000.0,
            "destino": "EFD_CONTRIBUICOES",
        }
        with self.client.post(
            "/api/v1/auditar/nr",
            json=nr_payload,
            headers=AUTH_HEADERS_NR,
            catch_response=True,
            name="sweep:CEN-5",
        ) as r:
            if r.status_code == 201:
                verify_protocol_cen5(r.json())
            r.success()


class IntegrationProtocolChecker(HttpUser):
    """
    CEN-5 + Protocol Sweep: Validates non-repudiation endpoint and
    periodically sweeps all 5 CEN scenarios to detect protocol drift.
    """
    tasks = [ProtocolCheckerTasks]
    wait_time = between(2, 6)
    weight = 1


# ---------------------------------------------------------------------------
# Event Hooks — Aggregate metrics at test end
# ---------------------------------------------------------------------------

@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Print INT2 summary report when Locust finishes."""
    report = metrics.report()
    if not report:
        return

    logger.info("=" * 70)
    logger.info("INT2 — LOCUST STRESS TEST SUMMARY (DN1 / DN3)")
    logger.info("=" * 70)

    for scenario, data in sorted(report.items()):
        sla_ok = data["p90_ms"] <= SLA_LATENCY_MS
        status = "PASS" if sla_ok else "FAIL"
        logger.info(
            "  %-30s | n=%-6d | mean=%.1fms | p50=%.1fms | p90=%.1fms | p99=%.1fms | SLA(P90<=500ms): %s",
            scenario,
            data["count"],
            data["mean_ms"],
            data["p50_ms"],
            data["p90_ms"],
            data["p99_ms"],
            status,
        )
        logger.info(
            "  %30s | min=%.1fms | max=%.1fms | SLA conformity=%.1f%% | Alert conformity=%.1f%%",
            "",
            data["min_ms"],
            data["max_ms"],
            data["sla_conformity_pct"],
            data["alert_conformity_pct"],
        )

    logger.info("=" * 70)

    cen1_data = {k: v for k, v in report.items() if k.startswith("CEN-1")}
    if cen1_data:
        all_p90 = [v["p90_ms"] for v in cen1_data.values()]
        worst_p90 = max(all_p90)
        dn1_verdict = "APROVADO" if worst_p90 <= SLA_LATENCY_MS else "REPROVADO"
        logger.info("  DN1 VERDICT: %s (worst P90 = %.1fms, SLA = %dms)", dn1_verdict, worst_p90, SLA_LATENCY_MS)

    cen3_data = report.get("CEN-3:health")
    if cen3_data:
        logger.info("  DN3 Health Check: mean=%.1fms, p90=%.1fms (n=%d)", cen3_data["mean_ms"], cen3_data["p90_ms"], cen3_data["count"])

    logger.info("=" * 70)

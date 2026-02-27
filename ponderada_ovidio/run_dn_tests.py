from fastapi.testclient import TestClient
from core import api
import logging

"""Runner de validações rápidas para DN2/DN3/DN4.

Objetivos:
- Fornecer checks executáveis e legíveis que validem os drivers DN3 e DN4.
- Incluir um cenário de erro (DN2) para demonstrar tratamento de exceções.
"""

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("run_dn_tests")

PAYLOAD_BASE = {
    "sessao_cliente": "SESSAO_TEST",
    "valor": 1500.75,
    "destino": "EFD_ICMS_IPI",
}

HEADERS_VALIDOS = {"account-key": "red-team-account", "app-key": "red-team-app"}
HEADERS_VITIMA = {"account-key": "conta-vip-cliente-asis", "app-key": "red-team-app"}


def run_dn3_rate_limit(client: TestClient) -> tuple[bool, str]:
    """Verifica rate-limiter: espera pelo menos um 201 e ao menos um 429."""
    acct = "test-availability"
    # reset rate limiter state for this account
    api.rate_limiter.reset(acct)

    max_req = api.rate_limiter.max_requests
    ok = 0
    rate_limited = 0
    for i in range(max_req + 1):
        r = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_BASE,
            headers={"account-key": acct, "app-key": "test-app"},
        )
        if r.status_code == 201:
            ok += 1
        elif r.status_code == 429:
            rate_limited += 1

    if ok >= 1 and rate_limited >= 1:
        return True, f"DN3 rate-limit: {ok} success, {rate_limited} rate-limited"
    return False, f"DN3 rate-limit: unexpected results (ok={ok},429={rate_limited})"


def run_dn4_nonrepudiation(client: TestClient) -> tuple[bool, str]:
    """Valida replay, impersonation e signature binding para DN4."""
    # isolate state
    api.audit_log.clear()
    api.clear_replay_cache()

    # 1) replay protection
    r1 = client.post("/api/v1/auditar/nr", json=PAYLOAD_BASE, headers=HEADERS_VALIDOS)
    r2 = client.post("/api/v1/auditar/nr", json=PAYLOAD_BASE, headers=HEADERS_VALIDOS)
    if r1.status_code != 201:
        return False, f"DN4 failed: first NR post returned {r1.status_code}"
    if r2.status_code not in (409, 429):
        return False, f"DN4 failed: replay not detected, second returned {r2.status_code}"

    # 2) impersonation
    r_imp = client.post("/api/v1/auditar/nr", json=PAYLOAD_BASE, headers=HEADERS_VITIMA)
    if r_imp.status_code not in (401, 403, 409):
        return False, f"DN4 failed: impersonation returned {r_imp.status_code}"

    # 3) signature binding
    # use the first successful response to get signature/timestamp
    data = r1.json()
    nr = data.get("non_repudiation", {})
    sig = nr.get("signature")
    ts = nr.get("timestamp")
    if not sig or not ts:
        return False, "DN4 failed: missing signature/timestamp in response"

    altered = {**PAYLOAD_BASE, "valor": 999999.99}
    if api.verify_signature(altered, ts, sig):
        return False, "DN4 failed: signature accepted altered payload"

    # verify audit log chain integrity
    if not api.audit_log.verify_chain():
        return False, "DN4 failed: audit log chain verification failed"

    return True, "DN4 non-repudiation checks passed (replay, impersonation, signature binding, chain)"


def run_dn2_invalid_payload(client: TestClient) -> tuple[bool, str]:
    """Enviar payload inválido para `POST /api/v1/auditar` e esperar HTTP 400.

    Isso demonstra consideração de situações de erro/exceção (DN2) 
    """
    bad_payload = {"sessao_cliente": None, "valor": -10, "destino": "EFD_ICMS_IPI"}
    r = client.post("/api/v1/auditar", json=bad_payload, headers=HEADERS_VALIDOS)
    if r.status_code == 400:
        return True, "DN2 invalid payload correctly rejected (400)"
    return False, f"DN2 invalid payload unexpected status {r.status_code}"


def run_health_check(client: TestClient) -> tuple[bool, str]:
    """Consulta `/api/v1/health` e valida presença de chaves esperadas."""
    r = client.get("/api/v1/health")
    if r.status_code != 200:
        return False, f"Health endpoint returned {r.status_code}"
    data = r.json()
    # check basic fields
    for key in ("status", "uptime_seconds", "total_requests"):
        if key not in data:
            return False, f"Health response missing {key}"
    return True, "Health check OK"


def main():
    client = TestClient(api.app)

    tests = [
        ("DN3 - Rate Limit / Availability", run_dn3_rate_limit),
        ("DN4 - Non-Repudiation", run_dn4_nonrepudiation),
        ("DN2 - Invalid Payload (error handling)", run_dn2_invalid_payload),
        ("API Health Check", run_health_check),
    ]

    results = []
    all_ok = True
    for name, fn in tests:
        ok, msg = fn(client)
        status = "OK" if ok else "FAIL"
        logger.info(f"{name}: {status} - {msg}")
        results.append((name, ok, msg))
        all_ok = all_ok and ok

    # Summary
    passed = sum(1 for _name, ok, _msg in results if ok)
    total = len(results)
    logger.info(f"Summary: {passed}/{total} tests passed")

    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

from fastapi.testclient import TestClient
from core import api

PAYLOAD_BASE = {
    "sessao_cliente": "SESSAO_TEST",
    "valor": 1500.75,
    "destino": "EFD_ICMS_IPI",
}

HEADERS_VALIDOS = {"account-key": "red-team-account", "app-key": "red-team-app"}
HEADERS_VITIMA = {"account-key": "conta-vip-cliente-asis", "app-key": "red-team-app"}


def run_dn3_rate_limit(client: TestClient) -> tuple[bool, str]:
    acct = "test-availability"
    # reset rate limiter state for this account
    api.rate_limiter.reset(acct)

    max_req = api.rate_limiter.max_requests
    ok = 0
    conflict = 0
    for i in range(max_req + 1):
        r = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_BASE,
            headers={"account-key": acct, "app-key": "test-app"},
        )
        if r.status_code == 201:
            ok += 1
        elif r.status_code == 429:
            conflict += 1

    if ok >= 1 and conflict >= 1:
        return True, f"DN3 rate-limit: {ok} success, {conflict} rate-limited"
    return False, f"DN3 rate-limit: unexpected results (ok={ok},429={conflict})"


def run_dn4_nonrepudiation(client: TestClient) -> tuple[bool, str]:
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

    return True, "DN4 non-repudiation checks passed (replay, impersonation, signature binding)"


def main():
    client = TestClient(api.app)

    tests = [
        ("DN3 - Rate Limit / Availability", run_dn3_rate_limit),
        ("DN4 - Non-Repudiation", run_dn4_nonrepudiation),
    ]

    all_ok = True
    for name, fn in tests:
        ok, msg = fn(client)
        status = "OK" if ok else "FAIL"
        print(f"{name}: {status} - {msg}")
        all_ok = all_ok and ok

    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

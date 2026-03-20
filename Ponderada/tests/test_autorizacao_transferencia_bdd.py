import sys
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pytest_bdd import given, parsers, scenarios, then, when

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from core.api import app, audit_log, clear_replay_cache, hash_actor, transaction_history  # noqa: E402
from core.auth_clerk import hash_clerk_actor  # noqa: E402


scenarios("../features/autorizacao_transferencia_segura.feature")


@pytest.fixture(autouse=True)
def limpar_estado_compartilhado() -> None:
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()
    yield
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def contexto() -> Dict[str, Any]:
    return {
        "payload": {
            "sessao_cliente": "pix-nubank-001",
            "valor": 1250.75,
            "destino": "EFD_ICMS_IPI",
        },
        "headers": {},
        "response": None,
        "first_response": None,
        "expected_actor": "",
        "ataque": "",
        "status_esperado": 0,
    }


def _patch_asis_upload_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_asis_upload_file(*args, **kwargs) -> str:
        return "processo-ponderada-001"

    monkeypatch.setattr("core.api.asis_upload_file", _fake_asis_upload_file)


@given("um token JWT valido com identidade consistente de tenant")
def given_token_jwt_valido(contexto: Dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    claims = {
        "sub": "user_nubank_01",
        "org_id": "org_nubank_pagamentos",
        "email": "cliente@nubank.com.br",
    }

    contexto["headers"] = {"Authorization": "Bearer token_jwt_valido"}
    contexto["expected_actor"] = hash_clerk_actor(claims["sub"], claims["org_id"])

    _patch_asis_upload_success(monkeypatch)

    def _jwt_valido_side_effect(token: str) -> Dict[str, Any]:
        if token != "token_jwt_valido":
            raise HTTPException(status_code=401, detail="INT3: Token JWT invalido")
        return claims

    monkeypatch.setattr("core.auth_hybrid.verify_clerk_token", _jwt_valido_side_effect)


@when("solicito autorizacao de transferencia no endpoint hibrido")
def when_solicita_autorizacao_hibrida(client: TestClient, contexto: Dict[str, Any]) -> None:
    contexto["response"] = client.post(
        "/api/v1/auditar/clerk",
        json=contexto["payload"],
        headers=contexto["headers"],
    )


@then("a autorizacao deve ser aprovada com status 201")
def then_autorizacao_aprovada(contexto: Dict[str, Any]) -> None:
    assert contexto["response"].status_code == 201


@then("a resposta deve conter tracking_id e identidade segura")
def then_resposta_identidade_segura(contexto: Dict[str, Any]) -> None:
    body = contexto["response"].json()

    assert body["tracking_id"] == "processo-ponderada-001"
    assert body["identity"]["auth_type"] == "clerk"
    assert body["identity"]["actor"] == contexto["expected_actor"]
    assert len(body["identity"]["actor"]) == 64
    assert "email" not in str(body).lower()
    assert "@" not in str(body)


@then("o acesso cross-tenant ao historico deve ser bloqueado com 403")
def then_cross_tenant_bloqueado(client: TestClient, contexto: Dict[str, Any]) -> None:
    actor_hash = contexto["response"].json()["identity"]["actor"]

    resp_forbidden = client.get(
        f"/api/v1/historico/{actor_hash}",
        headers={"account-key": "tenant-beta-account", "app-key": "tenant-beta-app"},
    )

    assert resp_forbidden.status_code == 403


@given("um timeout de JWKS na primeira tentativa e retry legitimo por API key")
def given_timeout_jwks_retry_api_key(
    contexto: Dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_asis_upload_success(monkeypatch)

    def _side_effect_verify(token: str) -> Dict[str, Any]:
        if token == "token_timeout_jwks":
            raise HTTPException(status_code=503, detail="INT3: Falha ao obter chaves JWKS do Clerk: timeout")
        raise HTTPException(status_code=401, detail="INT3: Token JWT invalido")

    monkeypatch.setattr("core.auth_hybrid.verify_clerk_token", _side_effect_verify)


@when("reenvio a solicitacao de autorizacao no endpoint hibrido")
def when_retry_legitimo(client: TestClient, contexto: Dict[str, Any]) -> None:
    contexto["first_response"] = client.post(
        "/api/v1/auditar/clerk",
        json=contexto["payload"],
        headers={"Authorization": "Bearer token_timeout_jwks"},
    )

    contexto["response"] = client.post(
        "/api/v1/auditar/clerk",
        json=contexto["payload"],
        headers={"account-key": "tenant-alpha-account", "app-key": "tenant-alpha-app"},
    )

    contexto["expected_actor"] = hash_actor("tenant-alpha-account")


@then("o retry legitimo deve ser aprovado com status 201")
def then_retry_legitimo_aprovado(contexto: Dict[str, Any]) -> None:
    assert contexto["first_response"].status_code == 503
    assert contexto["response"].status_code == 201


@then("a primeira tentativa deve falhar de forma controlada sem autorizacao indevida")
def then_falha_controlada_sem_autorizacao(contexto: Dict[str, Any]) -> None:
    body = contexto["first_response"].json()
    assert contexto["first_response"].status_code == 503
    assert "tracking_id" not in body
    assert "identity" not in body


@then("o actor hash deve permanecer consistente com o tenant autenticado")
def then_actor_consistente_tenant(contexto: Dict[str, Any]) -> None:
    body = contexto["response"].json()
    assert body["tracking_id"] == "processo-ponderada-001"
    assert body["identity"]["auth_type"] == "api_key"
    assert body["identity"]["actor"] == contexto["expected_actor"]
    assert body["identity"]["tenant_id"] == "tenant-alpha-account"


@given(parsers.parse('um vetor de ataque "{ataque}" com side_effect "{side_effect}"'))
def given_vetor_ataque(
    contexto: Dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    ataque: str,
    side_effect: str,
) -> None:
    contexto["ataque"] = ataque
    contexto["side_effect"] = side_effect
    _patch_asis_upload_success(monkeypatch)

    expected_side_effect_by_attack = {
        "token_expirado": "jwt_expired_token",
        "assinatura_invalida": "jwt_invalid_signature",
        "claim_adulterado": "identity_claim_forging",
        "replay_transacao": "replay_second_attempt",
    }
    assert expected_side_effect_by_attack.get(ataque) == side_effect, (
        f"Side effect inconsistente para ataque '{ataque}': esperado "
        f"'{expected_side_effect_by_attack.get(ataque)}', recebido '{side_effect}'"
    )

    if ataque == "assinatura_invalida":
        def _jwt_invalid_signature(token: str) -> Dict[str, Any]:
            if token == "token_malicioso":
                raise HTTPException(status_code=401, detail="INT3: Token JWT invalido - invalid signature")
            raise HTTPException(status_code=401, detail="INT3: Token JWT invalido")

        monkeypatch.setattr("core.auth_hybrid.verify_clerk_token", _jwt_invalid_signature)

    if ataque == "token_expirado":
        def _jwt_expired_token(token: str) -> Dict[str, Any]:
            if token == "token_malicioso":
                raise HTTPException(status_code=401, detail="INT3: Token JWT expirado")
            raise HTTPException(status_code=401, detail="INT3: Token JWT invalido")

        monkeypatch.setattr("core.auth_hybrid.verify_clerk_token", _jwt_expired_token)

    if ataque == "claim_adulterado":
        monkeypatch.setattr(
            "core.auth_hybrid.verify_clerk_token",
            lambda token: {"sub": "user_x", "org_id": "org_alpha", "email": "x@y.com"},
        )

        def _identity_claim_forging(claims: Dict[str, Any]) -> Dict[str, Any]:
            raise HTTPException(status_code=403, detail="INT3: claims adulterados detectados")

        monkeypatch.setattr("core.auth_hybrid.extract_clerk_identity", _identity_claim_forging)


@when("envio uma requisicao maliciosa de autorizacao")
def when_envio_requisicao_maliciosa(client: TestClient, contexto: Dict[str, Any]) -> None:
    ataque = contexto["ataque"]

    if ataque in {"assinatura_invalida", "token_expirado", "claim_adulterado"}:
        contexto["response"] = client.post(
            "/api/v1/auditar/clerk",
            json=contexto["payload"],
            headers={"Authorization": "Bearer token_malicioso"},
        )
        return

    if ataque == "replay_transacao":
        headers = {"account-key": "tenant-alpha-account", "app-key": "tenant-alpha-app"}
        primeira = client.post("/api/v1/auditar/nr", json=contexto["payload"], headers=headers)
        segunda = client.post("/api/v1/auditar/nr", json=contexto["payload"], headers=headers)

        assert primeira.status_code == 201
        contexto["response"] = segunda
        return

    raise AssertionError(f"Vetor de ataque nao suportado: {ataque}")


@then(parsers.parse("o sistema deve rejeitar com status {status_esperado:d}"))
def then_rejeicao_status(contexto: Dict[str, Any], status_esperado: int) -> None:
    contexto["status_esperado"] = status_esperado
    assert contexto["response"].status_code == status_esperado


@then("os invariantes de seguranca devem permanecer preservados")
def then_invariantes_preservados(contexto: Dict[str, Any]) -> None:
    body = contexto["response"].json()
    text_body = str(body).lower()

    assert "cliente@nubank.com.br" not in text_body
    assert "user_nubank_01" not in text_body
    assert "@" not in text_body
    assert "email" not in text_body

    if contexto["status_esperado"] == 409:
        assert "replay" in text_body
        assert "tracking_id" not in body

    if contexto["status_esperado"] in {401, 403}:
        assert "tracking_id" not in body
        assert "identity" not in body

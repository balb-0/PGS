"""
Blue Team - INT3 (Integracao: Gestao de Identidade com Clerk)

Valida a autenticacao hibrida (Clerk JWT + API Keys) no endpoint /api/v1/auditar/clerk:
- INT3.1: Validacao de Token JWT Clerk (valido, expirado, invalido, ausente)
- INT3.2: Isolamento de Contas por tenant (DN4 - conta A nao acessa dados de conta B)
- INT3.3: Autenticacao Hibrida (Clerk e API Keys funcionam no mesmo endpoint)
- INT3.4: Conformidade LGPD (actor hasheado, sem PII nos logs de auditoria)
- INT3.5: Integracao com DN4 (nao-repudio preservado em ambos os metodos)
"""

import sys
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.core.api import app, audit_log, transaction_history, clear_replay_cache
from src.core.auth_clerk import JWKSCache, override_jwks_cache


client = TestClient(app)

# ---------------------------------------------------------------------------
# Fixtures e constantes de teste
# ---------------------------------------------------------------------------

HEADERS_API_KEY_ALPHA = {
    "account-key": "tenant-alpha-account",
    "app-key": "tenant-alpha-app",
}

HEADERS_API_KEY_BETA = {
    "account-key": "tenant-beta-account",
    "app-key": "tenant-beta-app",
}

PAYLOAD_VALIDO: Dict[str, Any] = {
    "sessao_cliente": "sessao-int3-01",
    "valor": 3200.0,
    "destino": "EFD_ICMS_IPI",
}

PAYLOAD_ALTERNATIVO: Dict[str, Any] = {
    "sessao_cliente": "sessao-int3-02",
    "valor": 8100.75,
    "destino": "NCM_AUDIT",
}


@pytest.fixture(autouse=True)
def clean_state():
    """Reseta o estado compartilhado antes e depois de cada teste."""
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()
    yield
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()


class _MockJWKSCache(JWKSCache):
    """
    Substituto do cache JWKS que retorna chaves falsas para testes.
    Evita chamadas de rede reais ao Clerk durante a suíte.
    """

    def __init__(self, valid: bool = True):
        super().__init__("http://mock-clerk/.well-known/jwks.json")
        self._valid = valid

    def get_keys(self) -> Dict[str, Any]:
        return {"keys": []}  # Retorno mínimo; jwt.decode será mockado separadamente


def _make_mock_clerk_claims(
    sub: str = "user_abc123",
    org_id: str = "org_alpha",
    email: str = "user@example.com",
) -> Dict[str, Any]:
    """Gera um conjunto de claims JWT simulados para testes Clerk."""
    return {
        "sub": sub,
        "org_id": org_id,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }


# =============================================================================
# INT3.1 — Validação de Token JWT Clerk
# =============================================================================

class TestINT3JWTValidation:
    """
    INT3.1 — Verifica que a API aceita tokens JWT válidos do Clerk e rejeita
    tokens expirados, com assinatura inválida ou ausentes.

    Cada cenário é executado 3 vezes para garantir consistência (TDD/parametrize).
    """

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_1_aceita_token_jwt_valido(self, iteration):
        """INT3.1 — Token JWT Clerk válido deve ser aceito e retornar 201."""
        mock_claims = _make_mock_clerk_claims()
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_valido_simulado"},
            )

        assert response.status_code == 201, f"[iter {iteration}] Esperado 201, obtido {response.status_code}"
        body = response.json()
        assert "tracking_id" in body
        assert body["identity"]["auth_type"] == "clerk"

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_2_rejeita_token_expirado(self, iteration):
        """INT3.1 — Token JWT expirado deve retornar 401."""
        from jose.exceptions import ExpiredSignatureError
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", side_effect=ExpiredSignatureError("expired")):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_expirado"},
            )

        assert response.status_code == 401, f"[iter {iteration}] Esperado 401, obtido {response.status_code}"
        assert "expirado" in response.json()["detail"].lower()

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_3_rejeita_token_assinatura_invalida(self, iteration):
        """INT3.1 — Token com assinatura inválida deve retornar 401."""
        from jose import JWTError
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", side_effect=JWTError("invalid signature")):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_assinatura_invalida"},
            )

        assert response.status_code == 401, f"[iter {iteration}] Esperado 401, obtido {response.status_code}"

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_4_rejeita_sem_autenticacao(self, iteration):
        """INT3.1 — Requisição sem qualquer método de autenticação deve retornar 401."""
        response = client.post(
            "/api/v1/auditar/clerk",
            json=PAYLOAD_VALIDO,
        )

        assert response.status_code == 401, f"[iter {iteration}] Esperado 401, obtido {response.status_code}"
        assert "INT3" in response.json()["detail"]

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_5_rejeita_token_malformado(self, iteration):
        """INT3.1 — Token malformado (não Bearer válido) deve retornar 401."""
        from jose import JWTError
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", side_effect=JWTError("malformed")):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer nao.e.um.jwt.valido"},
            )

        assert response.status_code == 401, f"[iter {iteration}] Esperado 401, obtido {response.status_code}"


# =============================================================================
# INT3.2 — Isolamento de Contas (DN4 - Tenant Isolation)
# =============================================================================

class TestINT3TenantIsolation:
    """
    INT3.2 — Verifica que o isolamento de contas (DN4) é mantido tanto para
    autenticação Clerk quanto para API Keys. Um tenant não deve conseguir
    acessar dados ou histórico de outro tenant.

    Cada cenário é executado 3 vezes para garantir consistência.
    """

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_6_tenants_clerk_geram_actors_distintos(self, iteration):
        """INT3.2 — Organizações Clerk distintas geram actors distintos (isolamento DN4)."""
        claims_alpha = _make_mock_clerk_claims(sub="user_1", org_id="org_alpha")
        claims_beta = _make_mock_clerk_claims(sub="user_2", org_id="org_beta")
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims_alpha):
            resp_alpha = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_alpha"},
            )
        assert resp_alpha.status_code == 201, f"[iter {iteration}]"
        actor_alpha = resp_alpha.json()["identity"]["actor"]

        clear_replay_cache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims_beta):
            resp_beta = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_ALTERNATIVO,
                headers={"Authorization": "Bearer token_beta"},
            )
        assert resp_beta.status_code == 201, f"[iter {iteration}]"
        actor_beta = resp_beta.json()["identity"]["actor"]

        assert actor_alpha != actor_beta, (
            f"[iter {iteration}] Tenants distintos não devem compartilhar o mesmo actor"
        )

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_7_api_key_tenant_isolado_de_clerk_tenant(self, iteration):
        """INT3.2 — Tenant API Key e tenant Clerk geram actors distintos (sem colisão)."""
        mock_claims = _make_mock_clerk_claims(sub="tenant-alpha-account", org_id="org_clerk")
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            resp_clerk = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_clerk"},
            )
        assert resp_clerk.status_code == 201, f"[iter {iteration}]"
        actor_clerk = resp_clerk.json()["identity"]["actor"]

        clear_replay_cache()

        resp_apikey = client.post(
            "/api/v1/auditar/clerk",
            json=PAYLOAD_ALTERNATIVO,
            headers=HEADERS_API_KEY_ALPHA,
        )
        assert resp_apikey.status_code == 201, f"[iter {iteration}]"
        actor_apikey = resp_apikey.json()["identity"]["actor"]

        # Clerk user "tenant-alpha-account" com org_id "org_clerk" ≠ API key "tenant-alpha-account"
        assert actor_clerk != actor_apikey, (
            f"[iter {iteration}] Clerk e API Key com mesmo user_id mas orgs distintas devem ter actors diferentes"
        )

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_8_historico_isolado_entre_tenants_api_key(self, iteration):
        """INT3.2 — Tenant alpha não pode acessar histórico de tenant beta (API Keys)."""
        resp = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_API_KEY_ALPHA,
        )
        assert resp.status_code == 201, f"[iter {iteration}]"
        actor_hash = resp.json()["non_repudiation"]["actor"]

        forbidden = client.get(
            f"/api/v1/historico/{actor_hash}",
            headers=HEADERS_API_KEY_BETA,
        )
        assert forbidden.status_code == 403, (
            f"[iter {iteration}] Tenant beta não deve acessar histórico do tenant alpha"
        )

        allowed = client.get(
            f"/api/v1/historico/{actor_hash}",
            headers=HEADERS_API_KEY_ALPHA,
        )
        assert allowed.status_code == 200, f"[iter {iteration}]"


# =============================================================================
# INT3.3 — Autenticação Híbrida (retrocompatibilidade)
# =============================================================================

class TestINT3HybridAuthentication:
    """
    INT3.3 — Verifica que o endpoint /api/v1/auditar/clerk aceita ambos os métodos
    de autenticação (Clerk JWT e API Keys) de forma transparente.
    """

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_9_api_keys_funcionam_no_endpoint_clerk(self, iteration):
        """INT3.3 — API Keys legadas devem funcionar no endpoint híbrido (retrocompat.)."""
        response = client.post(
            "/api/v1/auditar/clerk",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_API_KEY_ALPHA,
        )

        assert response.status_code == 201, f"[iter {iteration}] Esperado 201, obtido {response.status_code}"
        body = response.json()
        assert body["identity"]["auth_type"] == "api_key"
        assert "tracking_id" in body

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_10_clerk_jwt_funciona_no_endpoint_clerk(self, iteration):
        """INT3.3 — Token Clerk JWT deve funcionar no endpoint híbrido."""
        mock_claims = _make_mock_clerk_claims()
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_clerk_valido"},
            )

        assert response.status_code == 201, f"[iter {iteration}] Esperado 201, obtido {response.status_code}"
        body = response.json()
        assert body["identity"]["auth_type"] == "clerk"
        assert "tracking_id" in body

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_11_resposta_normalizada_contem_campos_esperados(self, iteration):
        """INT3.3 — Resposta normalizada contém identity, non_repudiation e detalhes."""
        mock_claims = _make_mock_clerk_claims()
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_clerk_valido"},
            )

        assert response.status_code == 201, f"[iter {iteration}]"
        body = response.json()

        # Campos de identidade (INT3)
        assert "identity" in body, f"[iter {iteration}] Campo 'identity' ausente"
        assert "auth_type" in body["identity"]
        assert "tenant_id" in body["identity"]
        assert "actor" in body["identity"]

        # Campos de não-repúdio (DN4)
        assert "non_repudiation" in body, f"[iter {iteration}] Campo 'non_repudiation' ausente"
        nr = body["non_repudiation"]
        for field in ("signature", "timestamp", "actor", "receipt", "log_position"):
            assert field in nr, f"[iter {iteration}] Campo '{field}' ausente em non_repudiation"

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_12_api_key_invalida_retorna_403(self, iteration):
        """INT3.3 — API Key inválida no endpoint híbrido deve retornar 403."""
        response = client.post(
            "/api/v1/auditar/clerk",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "conta-invalida", "app-key": "app-invalida"},
        )

        assert response.status_code == 403, f"[iter {iteration}] Esperado 403, obtido {response.status_code}"


# =============================================================================
# INT3.4 — Conformidade LGPD (Pseudonimização)
# =============================================================================

class TestINT3LGPDCompliance:
    """
    INT3.4 — Verifica que dados pessoais não são expostos em logs ou respostas,
    e que a pseudonimização (SHA-256) é aplicada corretamente (conformidade LGPD).
    """

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_13_actor_e_hash_sha256_para_clerk(self, iteration):
        """INT3.4 — Actor Clerk deve ser SHA-256(user_id:org_id), não o valor original."""
        sub = "user_lgpd_test"
        org = "org_lgpd"
        mock_claims = _make_mock_clerk_claims(sub=sub, org_id=org, email="lgpd@test.com")
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_lgpd"},
            )

        assert response.status_code == 201, f"[iter {iteration}]"
        body = response.json()
        actor = body["identity"]["actor"]

        # Verificar que o actor é o hash esperado (user_id:org_id)
        expected_actor = hashlib.sha256(f"{sub}:{org}".encode()).hexdigest()
        assert actor == expected_actor, (
            f"[iter {iteration}] Actor deve ser SHA-256('{sub}:{org}'), obtido: {actor}"
        )

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_14_email_nao_exposto_na_resposta(self, iteration):
        """INT3.4 — Email do usuário Clerk não deve aparecer na resposta (LGPD)."""
        email_real = "usuario.real@empresa.com"
        mock_claims = _make_mock_clerk_claims(email=email_real)
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_clerk"},
            )

        assert response.status_code == 201, f"[iter {iteration}]"
        response_text = response.text

        assert email_real not in response_text, (
            f"[iter {iteration}] Email real '{email_real}' não deve aparecer na resposta (LGPD)"
        )

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_15_actor_api_key_e_hash_sha256(self, iteration):
        """INT3.4 — Actor API Key deve ser SHA-256(account_key), não o valor original."""
        account_key_value = "tenant-alpha-account"
        response = client.post(
            "/api/v1/auditar/clerk",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_API_KEY_ALPHA,
        )

        assert response.status_code == 201, f"[iter {iteration}]"
        body = response.json()
        actor = body["identity"]["actor"]

        expected_actor = hashlib.sha256(account_key_value.encode()).hexdigest()
        assert actor == expected_actor, (
            f"[iter {iteration}] Actor deve ser SHA-256(account_key), obtido: {actor}"
        )
        assert account_key_value not in actor, (
            f"[iter {iteration}] account_key original não deve aparecer no actor (LGPD)"
        )

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_16_user_id_clerk_nao_exposto_nos_logs_de_auditoria(self, iteration):
        """INT3.4 — O user_id original do Clerk não deve aparecer no log de auditoria."""
        sub_original = "user_pii_sensitivo_9999"
        mock_claims = _make_mock_clerk_claims(sub=sub_original, org_id="org_test")
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_pii"},
            )

        assert response.status_code == 201, f"[iter {iteration}]"

        # Verificar que user_id original não está no log de auditoria
        log = audit_log.get_log()
        log_serialized = json.dumps(log)
        assert sub_original not in log_serialized, (
            f"[iter {iteration}] user_id original '{sub_original}' não deve aparecer no audit log (LGPD)"
        )


# =============================================================================
# INT3.5 — Integração com DN4 (Não-Repúdio preservado em ambos os métodos)
# =============================================================================

class TestINT3NonRepudiationIntegration:
    """
    INT3.5 — Verifica que os mecanismos de DN4 (não-repúdio) funcionam corretamente
    tanto para autenticação Clerk quanto para API Keys.
    """

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_17_recibo_digital_presente_com_clerk(self, iteration):
        """INT3.5 — Recibo digital de não-repúdio deve estar presente com auth Clerk."""
        mock_claims = _make_mock_clerk_claims()
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_clerk"},
            )

        assert response.status_code == 201, f"[iter {iteration}]"
        nr = response.json().get("non_repudiation", {})
        receipt = nr.get("receipt", {})

        for field in ("signature", "timestamp", "actor", "tracking_id", "payload_hash"):
            assert field in receipt, f"[iter {iteration}] Campo '{field}' ausente no recibo"
        assert nr.get("alert") is None, f"[iter {iteration}] Alerta de NR inesperado: {nr.get('alert')}"

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_18_recibo_digital_presente_com_api_key(self, iteration):
        """INT3.5 — Recibo digital de não-repúdio deve estar presente com auth API Key."""
        response = client.post(
            "/api/v1/auditar/clerk",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_API_KEY_ALPHA,
        )

        assert response.status_code == 201, f"[iter {iteration}]"
        nr = response.json().get("non_repudiation", {})
        receipt = nr.get("receipt", {})

        for field in ("signature", "timestamp", "actor", "tracking_id", "payload_hash"):
            assert field in receipt, f"[iter {iteration}] Campo '{field}' ausente no recibo"

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_19_transacao_registrada_no_historico_com_tenant_id(self, iteration):
        """INT3.5 — Transação via Clerk deve ser registrada no histórico com tenant_id."""
        mock_claims = _make_mock_clerk_claims(sub="user_hist", org_id="org_hist_test")
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            response = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_hist"},
            )

        assert response.status_code == 201, f"[iter {iteration}]"
        actor = response.json()["identity"]["actor"]

        history = transaction_history.get_history(actor)
        assert len(history) >= 1, f"[iter {iteration}] Histórico vazio após transação Clerk"

        latest = history[-1]
        assert "tenant_id" in latest, f"[iter {iteration}] Campo 'tenant_id' ausente no histórico"
        assert latest["auth_type"] == "clerk", f"[iter {iteration}] auth_type incorreto no histórico"

    @pytest.mark.parametrize("iteration", [1, 2, 3])
    def test_int3_20_cadeia_hash_intacta_apos_transacoes_hibridas(self, iteration):
        """INT3.5 — Cadeia de hash do audit log deve permanecer íntegra após transações híbridas."""
        mock_claims = _make_mock_clerk_claims(sub="user_chain", org_id="org_chain")
        mock_cache = _MockJWKSCache()

        # Transação via Clerk
        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=mock_claims):
            r1 = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_chain_1"},
            )
        assert r1.status_code == 201, f"[iter {iteration}]"

        clear_replay_cache()

        # Transação via API Key
        r2 = client.post(
            "/api/v1/auditar/clerk",
            json=PAYLOAD_ALTERNATIVO,
            headers=HEADERS_API_KEY_ALPHA,
        )
        assert r2.status_code == 201, f"[iter {iteration}]"

        # Verificar integridade da cadeia de hash
        assert audit_log.verify_chain(), (
            f"[iter {iteration}] Cadeia de hash do audit log comprometida após transações híbridas"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

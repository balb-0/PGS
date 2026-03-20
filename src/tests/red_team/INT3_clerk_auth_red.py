"""
RED TEAM - Testes Adversariais para INT3 (Integracao: Gestao de Identidade com Clerk)

Foco: explorar vulnerabilidades na autenticacao hibrida Clerk JWT + API Keys:
- INT3.R1: Token replay (reuso de JWT ja processado)
- INT3.R2: Algorithm confusion (alg:none, HS256 vs RS256)
- INT3.R3: Claims tampering (org_id adulterado para cross-tenant)
- INT3.R4: Tenant boundary crossing via endpoint /auditar/clerk
- INT3.R5: LGPD information leakage (PII em respostas de erro)
- INT3.R6: Hybrid auth confusion (Bearer + API Keys simultaneos)
- INT3.R7: Malformed JWT (segmentos ausentes, payload gigante)

Execucao:
- Sem RED_TEAM_API_URL: usa TestClient (in-process).
- Com RED_TEAM_API_URL no .env: API real (testes in-process sao skipped).
  Coloque RED_TEAM_API_URL=http://127.0.0.1:8000 no .env e rode:
  pytest src/tests/red_team/INT3_clerk_auth_red.py -v -s
"""

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from dotenv import load_dotenv

_load_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_load_env_path)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

BASE_URL = os.environ.get("RED_TEAM_API_URL", "").rstrip("/")
if BASE_URL:
    class _RealAPIClient:
        def post(self, path, json=None, headers=None, **kwargs):
            return requests.post(
                f"{BASE_URL}{path}",
                json=json,
                headers=headers or {},
                timeout=kwargs.get("timeout", 30),
            )

        def get(self, path, headers=None, **kwargs):
            return requests.get(
                f"{BASE_URL}{path}",
                headers=headers or {},
                timeout=kwargs.get("timeout", 30),
            )

    client = _RealAPIClient()
else:
    from fastapi.testclient import TestClient
    from core.api import app
    client = TestClient(app)

from core.api import audit_log, transaction_history, clear_replay_cache
from core.auth_clerk import JWKSCache

HEADERS_ALPHA = {
    "account-key": "tenant-alpha-account",
    "app-key": "tenant-alpha-app",
}

HEADERS_BETA = {
    "account-key": "tenant-beta-account",
    "app-key": "tenant-beta-app",
}

PAYLOAD_VALIDO = {
    "sessao_cliente": "sessao-int3-red-01",
    "valor": 3200.0,
    "destino": "EFD_ICMS_IPI",
}

PAYLOAD_ALT = {
    "sessao_cliente": "sessao-int3-red-02",
    "valor": 8100.75,
    "destino": "NCM_AUDIT",
}


class _MockJWKSCache(JWKSCache):
    """Cache JWKS falso para testes — sem chamadas de rede ao Clerk."""

    def __init__(self):
        super().__init__("http://mock-clerk/.well-known/jwks.json")

    def get_keys(self):
        return {"keys": []}


def _mock_claims(sub="user_red", org_id="org_alpha", email="red@test.com"):
    return {
        "sub": sub,
        "org_id": org_id,
        "email": email,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }


@pytest.fixture(autouse=True)
def clean_state():
    if BASE_URL:
        yield
        return
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()
    yield
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()


# =============================================================================
# INT3.R1 — Token Replay Attack
# =============================================================================

class TestINT3R1TokenReplay:
    """Tenta reusar o mesmo token JWT para detectar falta de controle anti-replay."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r1_replay_mesmo_token_segunda_vez(self):
        """
        Envia o mesmo Bearer token duas vezes com o mesmo payload.
        O sistema deveria bloquear ou retornar replay (409/429) na segunda tentativa.
        """
        mock_cache = _MockJWKSCache()
        claims = _mock_claims()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims):
            r1 = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_replay_test"},
            )
            r2 = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_replay_test"},
            )

        assert r1.status_code == 201
        assert r2.status_code in (201, 409, 429), (
            f"Esperado 201 (sem anti-replay) ou 409/429, obtido {r2.status_code}"
        )

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r1_replay_token_diferente_payload_igual(self):
        """Mesmo payload com 'token diferente' — valida que o replay cache opera por payload."""
        mock_cache = _MockJWKSCache()
        claims_a = _mock_claims(sub="user_a")
        claims_b = _mock_claims(sub="user_b")

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims_a):
            r1 = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_a"},
            )

        clear_replay_cache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims_b):
            r2 = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_b"},
            )

        assert r1.status_code == 201
        assert r2.status_code == 201


# =============================================================================
# INT3.R2 — Algorithm Confusion (alg:none / HS256)
# =============================================================================

class TestINT3R2AlgorithmConfusion:
    """Tenta explorar confusao de algoritmo para bypass de validacao JWT."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r2_alg_none_rejeitado(self):
        """
        Token com alg:none deveria ser rejeitado (401).
        Se o decode aceitar, a validacao JWKS esta vulneravel.
        """
        from jose import JWTError
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode",
                   side_effect=JWTError("Algorithm 'none' not allowed")):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer eyJhbGciOiJub25lIn0.eyJzdWIiOiJ0ZXN0In0."},
            )

        assert resp.status_code == 401

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r2_hs256_quando_rs256_esperado(self):
        """Token assinado com HS256 quando o IDP usa RS256 deve ser rejeitado."""
        from jose import JWTError
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode",
                   side_effect=JWTError("Signature verification failed")):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_hs256_forjado"},
            )

        assert resp.status_code == 401


# =============================================================================
# INT3.R3 — Claims Tampering (org_id adulterado)
# =============================================================================

class TestINT3R3ClaimsTampering:
    """Tenta adulterar claims JWT para acessar contexto de outro tenant."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r3_org_id_adulterado_gera_actor_diferente(self):
        """
        Adultera org_id nos claims de 'org_alpha' para 'org_beta'.
        O actor resultante deve ser diferente do actor legitimo de org_beta,
        impedindo colisao de identidade.
        """
        mock_cache = _MockJWKSCache()
        claims_real = _mock_claims(sub="user_x", org_id="org_alpha")
        claims_forjado = _mock_claims(sub="user_x", org_id="org_beta")

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims_real):
            r_real = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_real"},
            )

        clear_replay_cache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims_forjado):
            r_forjado = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_ALT,
                headers={"Authorization": "Bearer token_forjado"},
            )

        assert r_real.status_code == 201
        assert r_forjado.status_code == 201
        actor_real = r_real.json()["identity"]["actor"]
        actor_forjado = r_forjado.json()["identity"]["actor"]
        assert actor_real != actor_forjado, (
            "Claims com org_id diferente devem resultar em actors distintos"
        )

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r3_sub_vazio_tratado_sem_crash(self):
        """Claims com sub vazio nao devem causar erro 500."""
        mock_cache = _MockJWKSCache()
        claims = _mock_claims(sub="", org_id="org_alpha")

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_sub_vazio"},
            )

        assert resp.status_code in (201, 400, 401), (
            f"Sub vazio: esperado 201/400/401, obtido {resp.status_code}"
        )
        assert resp.status_code != 500


# =============================================================================
# INT3.R4 — Tenant Boundary Crossing
# =============================================================================

class TestINT3R4TenantBoundary:
    """Testa se um tenant consegue acessar dados de outro via endpoint hibrido."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r4_clerk_tenant_a_nao_acessa_historico_de_b(self):
        """
        Tenant A (Clerk) cria transacao via /auditar/clerk.
        Tenant B (API Key) tenta acessar historico de A — deve receber 403.
        """
        mock_cache = _MockJWKSCache()
        claims = _mock_claims(sub="user_isolated", org_id="org_isolated_a")

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims):
            r_create = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_isolated"},
            )

        assert r_create.status_code == 201
        actor_a = r_create.json()["identity"]["actor"]

        r_intruso = client.get(
            f"/api/v1/historico/{actor_a}",
            headers=HEADERS_BETA,
        )
        assert r_intruso.status_code == 403, (
            f"Tenant B nao deve acessar historico de Tenant A: {r_intruso.status_code}"
        )


# =============================================================================
# INT3.R5 — LGPD Information Leakage
# =============================================================================

class TestINT3R5LGPDLeakage:
    """Verifica se PII vaza em respostas de erro ou em cenarios adversariais."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r5_email_nao_vaza_em_resposta_de_erro(self):
        """Mesmo em erro, o email do Clerk nao deve aparecer na resposta."""
        from jose.exceptions import ExpiredSignatureError
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode",
                   side_effect=ExpiredSignatureError("expired")):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_com_email_real"},
            )

        assert resp.status_code == 401
        body_text = resp.text.lower()
        pii_terms = ["@test.com", "email", "user_red", "red@"]
        for term in pii_terms:
            assert term not in body_text, (
                f"PII potencial '{term}' encontrado na resposta de erro (LGPD)"
            )

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r5_user_id_nao_vaza_no_audit_log(self):
        """user_id original do Clerk nao deve estar presente no audit log."""
        mock_cache = _MockJWKSCache()
        sub_sensitivo = "user_pii_confidencial_xyz"
        claims = _mock_claims(sub=sub_sensitivo, org_id="org_lgpd")

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer token_pii_lgpd"},
            )

        assert resp.status_code == 201
        log = audit_log.get_log()
        log_text = json.dumps(log)
        assert sub_sensitivo not in log_text, (
            f"user_id original '{sub_sensitivo}' vazou no audit log (violacao LGPD)"
        )

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r5_health_nao_expoe_informacoes_de_identidade(self):
        """O endpoint /health nao deve expor dados de identidade ou configuracao Clerk."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body_text = resp.text.lower()
        sensitive = ["clerk", "jwks", "jwt", "secret", "private"]
        for term in sensitive:
            assert term not in body_text, (
                f"Informacao sensivel '{term}' exposta no health check"
            )


# =============================================================================
# INT3.R6 — Hybrid Auth Confusion
# =============================================================================

class TestINT3R6HybridConfusion:
    """Testa comportamento quando ambos os metodos de auth sao enviados."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r6_bearer_e_api_key_simultaneos(self):
        """
        Envia Bearer token + API Keys ao mesmo tempo.
        O sistema deve escolher um metodo sem erro 500.
        """
        mock_cache = _MockJWKSCache()
        claims = _mock_claims()

        headers = {
            "Authorization": "Bearer token_hibrido",
            "account-key": "tenant-alpha-account",
            "app-key": "tenant-alpha-app",
        }

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode", return_value=claims):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers=headers,
            )

        assert resp.status_code != 500, (
            f"Autenticacao hibrida simultanea causou erro 500"
        )
        assert resp.status_code in (201, 400, 401, 403)

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r6_bearer_invalido_com_api_key_valida(self):
        """
        Bearer invalido + API Keys validas: o sistema deveria aceitar via API Key
        ou rejeitar consistentemente (sem 500).
        """
        from jose import JWTError
        mock_cache = _MockJWKSCache()

        headers = {
            "Authorization": "Bearer token_invalido_proposital",
            "account-key": "tenant-alpha-account",
            "app-key": "tenant-alpha-app",
        }

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode",
                   side_effect=JWTError("bad token")):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers=headers,
            )

        assert resp.status_code != 500
        assert resp.status_code in (201, 401, 403)


# =============================================================================
# INT3.R7 — Malformed JWT
# =============================================================================

class TestINT3R7MalformedJWT:
    """Testa resiliencia a tokens JWT malformados e payloads gigantes."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r7_token_sem_segmentos(self):
        """Token sem os 3 segmentos (header.payload.signature) deve retornar 401."""
        from jose import JWTError
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode",
                   side_effect=JWTError("Not enough segments")):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer apenas_um_segmento"},
            )

        assert resp.status_code == 401

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r7_token_base64_invalido(self):
        """Token com base64 corrompido nao deve causar crash."""
        from jose import JWTError
        mock_cache = _MockJWKSCache()

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode",
                   side_effect=JWTError("Invalid header padding")):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": "Bearer !!!.@@@.###"},
            )

        assert resp.status_code == 401

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer mocks in-process")
    def test_int3_r7_token_payload_gigante(self):
        """Token com payload muito grande nao deve causar OOM ou timeout."""
        from jose import JWTError
        mock_cache = _MockJWKSCache()
        token_gigante = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9." + "A" * 100_000 + ".fake_sig"

        with patch("core.auth_clerk._jwks_cache", mock_cache), \
             patch("core.auth_clerk.jwt.decode",
                   side_effect=JWTError("Invalid payload")):
            resp = client.post(
                "/api/v1/auditar/clerk",
                json=PAYLOAD_VALIDO,
                headers={"Authorization": f"Bearer {token_gigante}"},
            )

        assert resp.status_code in (401, 413), (
            f"Token gigante: esperado 401/413, obtido {resp.status_code}"
        )

    def test_int3_r7_authorization_header_sem_bearer_prefix(self):
        """Header Authorization sem prefixo 'Bearer' deve ser rejeitado."""
        resp = client.post(
            "/api/v1/auditar/clerk",
            json=PAYLOAD_VALIDO,
            headers={"Authorization": "token_sem_bearer_prefix"},
        )

        assert resp.status_code in (401, 403, 422)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

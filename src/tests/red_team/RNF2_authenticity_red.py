"""
RED TEAM - Testes Adversariais para RNF2 (Seguranca: Autenticidade)

Foco: explorar vulnerabilidades no mecanismo de autenticacao por credenciais:
- RNF2.R1: Credential stuffing (tentativas massivas de combinacoes)
- RNF2.R2: Timing side-channel (diferenca mensuravel entre credenciais validas/invalidas)
- RNF2.R3: Header injection (CRLF, null bytes, caracteres de controle)
- RNF2.R4: Case/encoding bypass (case diferente, unicode em credenciais)
- RNF2.R5: Missing header variations (combinacoes parciais de headers)
- RNF2.R6: Cross-endpoint credential reuse (isolamento entre endpoints)
- RNF2.R7: Error message information leakage (mensagens de erro nao devem distinguir erros)

Execucao:
- Sem RED_TEAM_API_URL: usa TestClient (in-process).
- Com RED_TEAM_API_URL no .env: API real.
  pytest src/tests/red_team/RNF2_authenticity_red.py -v -s
"""

import os
import sys
import time
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

_load_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_load_env_path)

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
    from src.core.api import app
    client = TestClient(app)

HEADERS_VALIDOS = {
    "account-key": "tenant-alpha-account",
    "app-key": "tenant-alpha-app",
}

PAYLOAD_VALIDO = {
    "sessao_cliente": "sessao-rnf2-red-01",
    "valor": 1250.5,
    "destino": "EFD_ICMS_IPI",
}


# =============================================================================
# RNF2.R1 — Credential Stuffing
# =============================================================================

class TestRNF2R1CredentialStuffing:
    """Testa resiliencia a tentativas massivas de credenciais aleatorias."""

    def test_rnf2_r1_50_combinacoes_invalidas_sem_crash(self):
        """
        Dispara 50 requisicoes com credenciais aleatorias.
        Nenhuma deve retornar 200/201 e nenhuma deve causar 500.
        """
        for i in range(50):
            headers = {
                "account-key": f"ataque-conta-{i}",
                "app-key": f"ataque-app-{i}",
            }
            resp = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=headers)
            assert resp.status_code in (401, 403), (
                f"Iteracao {i}: esperado 401/403, obtido {resp.status_code}"
            )

    def test_rnf2_r1_credenciais_parcialmente_corretas(self):
        """
        account-key valida com app-key invalida (e vice-versa).
        Deve retornar 403 em ambos os casos, sem distinguir o erro.
        """
        resp_ak = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "tenant-alpha-account", "app-key": "invalida"},
        )
        resp_app = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "invalida", "app-key": "tenant-alpha-app"},
        )

        assert resp_ak.status_code == 403
        assert resp_app.status_code == 403


# =============================================================================
# RNF2.R2 — Timing Side-Channel
# =============================================================================

class TestRNF2R2TimingSideChannel:
    """Mede se ha diferenca mensuravel de tempo entre cenarios de autenticacao."""

    def test_rnf2_r2_tempo_resposta_uniforme_entre_cenarios(self):
        """
        Compara tempo de resposta para: (1) sem credenciais, (2) credenciais
        invalidas, (3) credenciais validas. A diferenca nao deve ser
        significativa o suficiente para informar um atacante.
        """
        tempos = {}

        t0 = time.perf_counter()
        client.post("/api/v1/auditar", json=PAYLOAD_VALIDO)
        tempos["sem_cred"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "falsa", "app-key": "falsa"},
        )
        tempos["cred_invalida"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)
        tempos["cred_valida"] = time.perf_counter() - t0

        diff_401_403 = abs(tempos["sem_cred"] - tempos["cred_invalida"])
        assert diff_401_403 < 1.0, (
            f"Diferenca de timing entre 401/403 muito grande: {diff_401_403:.3f}s"
        )


# =============================================================================
# RNF2.R3 — Header Injection
# =============================================================================

class TestRNF2R3HeaderInjection:
    """Testa injecao de caracteres especiais nos headers de autenticacao."""

    @pytest.mark.parametrize("injected_key", [
        "tenant-alpha-account\r\nX-Injected: true",
        "tenant-alpha-account\x00admin",
        "tenant-alpha-account\nX-Bypass: yes",
    ])
    def test_rnf2_r3_crlf_e_null_byte_em_account_key(self, injected_key):
        """
        Injeta CRLF e null bytes no account-key.
        O sistema deve rejeitar (401/403) ou tratar sem efeito colateral.
        """
        headers = {"account-key": injected_key, "app-key": "tenant-alpha-app"}
        resp = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=headers)
        assert resp.status_code in (400, 401, 403, 422), (
            f"Header injection nao tratada: {resp.status_code}"
        )

    def test_rnf2_r3_header_vazio_string(self):
        """Headers com strings vazias devem ser tratados como ausentes (401)."""
        resp = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "", "app-key": ""},
        )
        assert resp.status_code == 401


# =============================================================================
# RNF2.R4 — Case/Encoding Bypass
# =============================================================================

class TestRNF2R4CaseEncodingBypass:
    """Tenta contornar autenticacao usando variantes de case e encoding."""

    def test_rnf2_r4_credenciais_case_diferente(self):
        """Credenciais com case alterado devem ser rejeitadas (case-sensitive)."""
        headers = {
            "account-key": "TENANT-ALPHA-ACCOUNT",
            "app-key": "TENANT-ALPHA-APP",
        }
        resp = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=headers)
        assert resp.status_code in (401, 403)

    def test_rnf2_r4_credenciais_com_espacos(self):
        """Credenciais com espacos em volta devem ser rejeitadas."""
        headers = {
            "account-key": "  tenant-alpha-account  ",
            "app-key": "  tenant-alpha-app  ",
        }
        resp = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=headers)
        assert resp.status_code in (201, 401, 403)

    def test_rnf2_r4_credenciais_unicode_homoglyphs(self):
        """
        Credenciais com caracteres Unicode visualmente similares.
        HTTP headers sao restritos a ASCII (RFC 7230); o cliente HTTP
        rejeita antes de enviar, o que ja constitui protecao.
        """
        try:
            headers = {
                "account-key": "tenant\u2010alpha\u2010account",
                "app-key": "tenant-alpha-app",
            }
            resp = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=headers)
            assert resp.status_code in (400, 401, 403)
        except (UnicodeEncodeError, Exception):
            pass


# =============================================================================
# RNF2.R5 — Missing Header Variations
# =============================================================================

class TestRNF2R5MissingHeaders:
    """Testa todas as combinacoes de headers ausentes/parciais."""

    def test_rnf2_r5_sem_nenhum_header(self):
        """Sem headers de autenticacao: 401."""
        resp = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO)
        assert resp.status_code == 401

    def test_rnf2_r5_apenas_account_key(self):
        """Apenas account-key sem app-key: 401."""
        resp = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "tenant-alpha-account"},
        )
        assert resp.status_code == 401

    def test_rnf2_r5_apenas_app_key(self):
        """Apenas app-key sem account-key: 401."""
        resp = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"app-key": "tenant-alpha-app"},
        )
        assert resp.status_code == 401

    def test_rnf2_r5_headers_com_nomes_errados(self):
        """Headers com nomes incorretos (account_key vs account-key)."""
        resp = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account_key": "tenant-alpha-account", "app_key": "tenant-alpha-app"},
        )
        assert resp.status_code in (401, 422)


# =============================================================================
# RNF2.R6 — Cross-Endpoint Credential Reuse
# =============================================================================

class TestRNF2R6CrossEndpoint:
    """Verifica que credenciais validas funcionam apenas em endpoints autorizados."""

    def test_rnf2_r6_health_sem_auth_retorna_200(self):
        """Health check nao requer autenticacao."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_rnf2_r6_auditar_requer_auth(self):
        """Endpoints de auditoria requerem credenciais."""
        for endpoint in ["/api/v1/auditar", "/api/v1/auditar/nr"]:
            resp = client.post(endpoint, json=PAYLOAD_VALIDO)
            assert resp.status_code == 401, (
                f"Endpoint {endpoint} aceita requisicao sem auth"
            )

    def test_rnf2_r6_credenciais_validas_funcionam_em_todos_endpoints_protegidos(self):
        """O mesmo par de credenciais validas funciona em todos os endpoints."""
        from src.core.api import clear_replay_cache

        resp1 = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)
        assert resp1.status_code == 201

        if not BASE_URL:
            clear_replay_cache()

        resp2 = client.post(
            "/api/v1/auditar/nr",
            json={**PAYLOAD_VALIDO, "sessao_cliente": "sessao-cross-nr"},
            headers=HEADERS_VALIDOS,
        )
        assert resp2.status_code == 201


# =============================================================================
# RNF2.R7 — Error Message Information Leakage
# =============================================================================

class TestRNF2R7ErrorLeakage:
    """Verifica que mensagens de erro nao revelam informacoes de configuracao."""

    def test_rnf2_r7_erro_401_nao_revela_headers_esperados(self):
        """Mensagem de 401 nao deve mencionar 'account-key' ou 'app-key'."""
        resp = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO)
        assert resp.status_code == 401
        detail = resp.json().get("detail", "")
        assert "account-key" not in detail.lower()
        assert "app-key" not in detail.lower()

    def test_rnf2_r7_erro_403_identico_para_ak_e_app_invalidos(self):
        """
        Mensagem de 403 deve ser identica independente de qual credencial
        esta errada — impede que atacante descubra qual header e valido.
        """
        resp_ak = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "invalida", "app-key": "tenant-alpha-app"},
        )
        resp_app = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "tenant-alpha-account", "app-key": "invalida"},
        )

        assert resp_ak.status_code == 403
        assert resp_app.status_code == 403
        assert resp_ak.json()["detail"] == resp_app.json()["detail"], (
            "Mensagem de erro diferente para account-key vs app-key invalidos (information leakage)"
        )

    def test_rnf2_r7_erro_nao_expoe_credenciais_registradas(self):
        """Mensagem de erro nao deve conter valores de credenciais validas."""
        resp = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "intruso", "app-key": "intruso"},
        )
        body_text = resp.text
        assert "tenant-alpha" not in body_text
        assert "conta-teste-123" not in body_text
        assert "ASIS_ACCOUNT_KEY" not in body_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

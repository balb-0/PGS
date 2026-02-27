"""
RED TEAM - Testes Adversariais para DN4 (Nao-Repudio)
Foco: explorar bypass de autenticacao, replay e exposicao indevida de trilha de auditoria.

Execução:
- Sem RED_TEAM_API_URL: usa TestClient (in-process). Com RED_TEAM_API_URL no .env: API real (R5 pulado).
  Coloque RED_TEAM_API_URL=http://127.0.0.1:8000 no .env na raiz e rode: pytest src/tests/red_team/DN4_non_repudiation_red.py -v -s
"""

import hashlib
import os
import sys
from pathlib import Path

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

from core.api import audit_log, verify_signature

HEADERS_VALIDOS = {
    "account-key": "red-team-account",
    "app-key": "red-team-app",
}

HEADERS_VITIMA = {
    "account-key": "conta-vip-cliente-asis",
    "app-key": "red-team-app",
}

PAYLOAD_BASE = {
    "sessao_cliente": "SESSAO_RED_DN4",
    "valor": 1500.75,
    "destino": "EFD_ICMS_IPI",
}


@pytest.fixture(autouse=True)
def limpar_log():
    """Isola cenarios que dependem da cadeia de hash e do cache de replay (apenas in-process)."""
    if BASE_URL:
        yield
        return
    from core.api import clear_replay_cache
    audit_log.clear()
    clear_replay_cache()
    yield
    audit_log.clear()
    clear_replay_cache()


class TestDN4RedTeam:
    """Simulacao adversarial para mecanismos de nao-repudio."""

    # ========== DN4.R1: Replay Attack ==========
    def test_replay_payload_identico_deveria_ser_bloqueado(self):
        """
        Esperado (seguro): mesma transacao em janela curta deve ser bloqueada.
        Risco: reprocessamento indevido sem anti-replay.
        """
        resp_1 = client.post("/api/v1/auditar/nr", json=PAYLOAD_BASE, headers=HEADERS_VALIDOS)
        resp_2 = client.post("/api/v1/auditar/nr", json=PAYLOAD_BASE, headers=HEADERS_VALIDOS)

        assert resp_1.status_code == 201
        # Em ambiente resiliente: 409 (Conflict) ou 429 (Too Many Requests)
        assert resp_2.status_code in [409, 429]

    # ========== DN4.R2: Account Impersonation ==========
    def test_impersonacao_por_header_forjado_deveria_falhar(self):
        """
        Esperado (seguro): actor deve depender de autenticacao forte do header.
        Risco: qualquer cliente pode forjar account-key e assumir identidade de terceiro.
        """
        response = client.post("/api/v1/auditar/nr", json=PAYLOAD_BASE, headers=HEADERS_VITIMA)

        # Em ambiente resiliente: 401/403 para identidade nao autenticada
        assert response.status_code in [401, 403]

    # ========== DN4.R3: Signature Binding ==========
    def test_assinatura_nao_aceita_payload_adulterado(self):
        """Valida que o HMAC nao pode ser reutilizado em payload alterado."""
        response = client.post("/api/v1/auditar/nr", json=PAYLOAD_BASE, headers=HEADERS_VALIDOS)
        assert response.status_code == 201

        nr = response.json()["non_repudiation"]
        payload_adulterado = {**PAYLOAD_BASE, "valor": 999999.99}

        assert verify_signature(
            payload_adulterado,
            nr["timestamp"],
            nr["signature"],
        ) is False

    # ========== DN4.R4: Unauthorized Log Access ==========
    def test_consulta_log_com_outra_conta_deveria_ser_negada(self):
        """
        Esperado (seguro): log deveria ser segregado por tenant/ator autenticado.
        Risco: vazamento de trilha de auditoria entre contas.
        """
        client.post("/api/v1/auditar/nr", json=PAYLOAD_BASE, headers=HEADERS_VALIDOS)

        headers_intruso = {
            "account-key": "intruso-sem-vinculo",
            "app-key": "intruso-app",
        }
        response = client.get("/api/v1/audit-log", headers=headers_intruso)

        # Em ambiente resiliente: 401/403
        assert response.status_code in [401, 403]

    # ========== DN4.R5: Chain Tampering Detection ==========
    @pytest.mark.skipif(bool(os.environ.get("RED_TEAM_API_URL")), reason="Requer acesso in-process ao audit_log para adulterar cadeia")
    def test_alerta_dispara_quando_cadeia_e_adulterada(self):
        """Valida deteccao de adulteracao quando hash chain e comprometida."""
        client.post("/api/v1/auditar/nr", json=PAYLOAD_BASE, headers=HEADERS_VALIDOS)

        # Simula adulteracao local de memoria
        audit_log._log[0]["entry_hash"] = hashlib.sha256(b"hash_fraudado").hexdigest()

        response = client.get("/api/v1/audit-log", headers=HEADERS_VALIDOS)
        data = response.json()

        assert response.status_code == 200
        assert data["chain_integrity"] is False
        assert data["chain_alert"] is not None
        assert "ALERTA" in data["chain_alert"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

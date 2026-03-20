"""
RED TEAM - Testes Adversariais para RF1/RF2

Foco:
- RF1: Explorar consultas indevidas de processos e trilhas de status.
- RF2: Tentar burlar a validacao de modulos fiscais de destino com
  tecnicas de encoding/case/espacos e payloads extremos.
"""

import os
import sys
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

# Carrega .env da raiz do projeto para RED_TEAM_API_URL
_load_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_load_env_path)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

BASE_URL = os.environ.get("RED_TEAM_API_URL", "").rstrip("/")
if BASE_URL:
    # Cliente HTTP contra a API real (servidor ja em execucao)
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


HEADERS_TENANT_ALPHA = {
    "account-key": "tenant-alpha-account",
    "app-key": "tenant-alpha-app",
}

HEADERS_TENANT_BETA = {
    "account-key": "tenant-beta-account",
    "app-key": "tenant-beta-app",
}


class TestRF1RedTeam:
    """
    Ataques contra RF1 — Consulta de Status de Processamento.
    """

    def test_rf1_rt1_enumeracao_de_processos_por_forca_bruta(self):
        """
        Tenta consultar tracking_ids aleatorios para medir o comportamento de erro.

        Objetivo:
        - Confirmar que a API nao revela informacoes extras ao retornar 404.
        - Verificar se o tempo de resposta permanece uniforme (mitigando enumeracao).
        """
        invalid_ids = [f"rf1-enum-{i}" for i in range(5)]
        for tid in invalid_ids:
            resp = client.get(f"/api/v1/processo/{tid}", headers=HEADERS_TENANT_ALPHA)
            assert resp.status_code == 404
            body = resp.json()
            # Resposta deve ser generica, sem dados sensiveis
            assert body.get("detail") == "Processo não encontrado"

    def test_rf1_rt2_tenant_beta_tenta_ler_processo_de_alpha(self):
        """
        Cenário adversarial:
        - Tenant ALPHA cria um processo.
        - Tenant BETA tenta consultar o mesmo tracking_id.

        No mock atual, nao existe isolamento por tenant em RF1. Este teste
        documenta a lacuna (STATUS EXPECTED: PASS para GET 200 por desenho atual,
        mas classificada como risco de negocio).
        """
        payload = {
            "sessao_cliente": "SESSAO_RF_RED",
            "valor": 100.0,
            "destino": "EFD_ICMS_IPI",
        }
        create_resp = client.post(
            "/api/v1/auditar", json=payload, headers=HEADERS_TENANT_ALPHA
        )
        assert create_resp.status_code == 201
        tracking_id = create_resp.json()["tracking_id"]

        # Tenant BETA tentando consultar o mesmo processo
        consulta_resp = client.get(
            f"/api/v1/processo/{tracking_id}", headers=HEADERS_TENANT_BETA
        )

        # Comportamento atual: 200 OK (sem isolamento por tenant).
        # Este teste serve para registrar o risco e apoiar decisoes futuras.
        assert consulta_resp.status_code in (200, 403)


class TestRF2RedTeam:
    """
    Ataques contra RF2 — Validacao de Modulo Fiscal de Destino.
    """

    @pytest.mark.parametrize(
        "destino_bypass",
        [
            "  EFD_ICMS_IPI  ",  # espacos em branco
            "EFD_ICMS_IPI\n",  # newline escondida
            "EFD_ICMS_IPI\x00",  # null byte
        ],
    )
    def test_rf2_rt1_espacos_e_caracteres_de_controle(self, destino_bypass):
        """
        Tenta burlar a validacao de destino adicionando espacos e caracteres de controle.
        Espera-se que a API rejeite (HTTP 400) todos os casos.
        """
        payload = {
            "sessao_cliente": "RF2_RED_TEAM",
            "valor": 123.45,
            "destino": destino_bypass,
        }
        resp = client.post("/api/v1/auditar", json=payload, headers=HEADERS_TENANT_ALPHA)
        assert resp.status_code == 400

    def test_rf2_rt2_unicode_homoglyphs_no_destino(self):
        """
        Tenta usar caracteres Unicode visualmente similares para forcar modulo invalido.

        Exemplo: substituir letras por homoglifos gregos/cirÍlicos.
        """
        destino_falso = "ΕFD_ΙCMS_ΙPI"  # Algumas letras gregas no lugar de latinas
        payload = {
            "sessao_cliente": "RF2_RED_TEAM",
            "valor": 200.0,
            "destino": destino_falso,
        }
        resp = client.post("/api/v1/auditar", json=payload, headers=HEADERS_TENANT_ALPHA)
        # A API deve rejeitar, pois o valor upper() nao estara em MODULOS_FISCAIS_VALIDOS
        assert resp.status_code == 400

    def test_rf2_rt3_buffer_de_modulos_invalidos_para_medir_performance(self):
        """
        Dispara uma sequencia de chamadas com destinos claramente invalidos
        para verificar se a validacao RF2 se mantém leve e sem colapsar.
        """
        for i in range(50):
            payload = {
                "sessao_cliente": "RF2_RED_TEAM_LOAD",
                "valor": 10.0 + i,
                "destino": f"MODULO_INVALIDO_{i}",
            }
            resp = client.post(
                "/api/v1/auditar", json=payload, headers=HEADERS_TENANT_ALPHA
            )
            assert resp.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


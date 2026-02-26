"""
RED TEAM - Testes Adversariais para DN2 (Integridade de Dados)
Foco: Explorar limites de resiliência e quebra de validação.

Execução:
- Sem RED_TEAM_API_URL: usa TestClient (in-process). Com RED_TEAM_API_URL (no .env ou no shell): API real.
  Coloque RED_TEAM_API_URL=http://127.0.0.1:8000 no .env na raiz do projeto e rode: pytest src/tests/red_team/DN2_validation_red.py -v
"""

import os
import sys
import time
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
    # Cliente HTTP contra a API real (servidor já em execução)
    class _RealAPIClient:
        def post(self, path, json=None, headers=None, **kwargs):
            return requests.post(
                f"{BASE_URL}{path}",
                json=json,
                headers=headers or {},
                timeout=kwargs.get("timeout", 30),
            )

    client = _RealAPIClient()
else:
    from fastapi.testclient import TestClient
    from core.api import app
    client = TestClient(app)

HEADERS = {"account-key": "red-team-target", "app-key": "attack-vector-01"}

class TestDN2RedTeam:
    """
    Simulação de ataques para validar a resiliência do Ativo de Software.
    """

    # ========== DN2.R1: Injection & Malicious Payloads ==========
    def test_ataque_script_injection(self):
        """Tenta injetar scripts no campo de sessão para quebrar a integridade."""
        payload = {
            "sessao_cliente": "<script>alert('xss')</script>",
            "valor": 100.0,
            "destino": "modulo_icms"
        }
        response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
        # O sistema deve tratar como string ou rejeitar, mas nunca processar.
        assert response.status_code == 201 
        assert "tracking_id" in response.json()

    # ========== DN2.R2: Numerical Extreme Cases ==========
    @pytest.mark.parametrize("extreme_value", ["inf", "nan", 1e308])
    def test_numeros_extremos_e_invalidos(self, extreme_value):
        """Valida se a API é resiliente a valores numéricos que quebram cálculos."""
        payload = {
            "sessao_cliente": "target_user",
            "valor": extreme_value,
            "destino": "modulo_ipi"
        }
        response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
        
        # Sistemas resilientes devem rejeitar valores não finitos (HTTP 400)
        assert response.status_code == 400
        assert "maior que zero" in response.json()["detail"].lower()

    # ========== DN2.R3: Schema Pollution (DoS attempt) ==========
    def test_poluicao_de_schema_massiva(self):
        """Envia 5.000 campos extras para tentar causar lentidão no validador."""
        payload = {
            "sessao_cliente": "heavy_user",
            "valor": 500,
            "destino": "modulo_pis"
        }
        # Adicionando 5000 campos inúteis
        for i in range(5000):
            payload[f"junk_field_{i}"] = "random_data_to_exhaust_resources"

        start_time = time.time()
        response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
        end_time = time.time()

        # O tempo de resposta não deve degradar muito além do SLA e do sleep de fallback
        assert (end_time - start_time) < 1.500 
        assert response.status_code == 201

    # ========== DN2.R4: Type Juggling Attack ==========
    def test_envio_de_tipos_complexos_no_valor(self):
        """Tenta enviar uma lista no lugar do valor numérico."""
        payload = {
            "sessao_cliente": "hacker_01",
            "valor": [100, 200, "malicious"], # Lista em vez de float
            "destino": "modulo_confis"
        }
        response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
        
        # A API deve detectar que não é um número e rejeitar (HTTP 400)
        assert response.status_code == 400
        assert "maior que zero" in response.json()["detail"].lower()
        assert "tracking_id" not in response.json()

    # ========== DN2.R5: Large Payload Strings ==========
    def test_buffer_overflow_simulado_strings(self):
        """Envia uma string de 1MB no campo destino para testar limites de memória."""
        payload = {
            "sessao_cliente": "user_normal",
            "valor": 100,
            "destino": "A" * (1024 * 1024) # 1 Megabyte de caracteres
        }
        response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
        
        # A API deve ser capaz de lidar ou limitar o tamanho do payload
        assert response.status_code in [201, 413] # Created ou Payload Too Large


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
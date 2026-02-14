"""
RED TEAM - Testes Adversariais para DN3 (Disponibilidade e Resiliência)
Foco: Explorar limites de resiliência dos mecanismos de rate limiting,
circuit breaker, idempotência e health check.
"""

import sys
import time
import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.mock_api import app  # noqa: E402
import core.mock_api as mock_api_module  # noqa: E402
from core.availability import (  # noqa: E402
    rate_limiter,
    circuit_breaker,
    health_checker,
    idempotency_store,
    CircuitState,
)


client = TestClient(app)
HEADERS = {"account-key": "red-team-target", "app-key": "attack-vector-dn3"}


def reset_availability_state():
    """Garante que cada teste começa com estado limpo dos singletons DN3."""
    rate_limiter.reset()
    circuit_breaker.reset()
    health_checker.reset()
    idempotency_store.clear()


@pytest.fixture(autouse=True)
def _speed_up_mock_api_sleep(monkeypatch: pytest.MonkeyPatch):
    """
    A mock API simula processamento com asyncio.sleep(random.uniform(0.1, 0.5)).
    Para manter o Red Team rápido/reprodutível, zeramos o delay por padrão.
    """
    monkeypatch.setattr(mock_api_module.random, "uniform", lambda _a, _b: 0.0)


class TestDN3RedTeam:
    """
    Simulação de ataques para validar a resiliência do Ativo de Software (DN3).
    Cenários baseados em `RedTeamparaDisponibilidade.md`.
    """

    # ========== DN3.R1: Rate Limit Bypass por Header Spoofing ==========
    def test_dn3_r1_rate_limit_bypass_por_header_spoofing(self):
        """
        Envia rajadas com várias account-keys para tentar burlar o rate limit.

        Objetivo: validar que a API continua respondendo (não entra em falha 5xx)
        e que o health check permanece operacional, mesmo com muitas chaves.
        """
        reset_availability_state()

        total_accounts = 100
        for i in range(total_accounts):
            headers = {
                "account-key": f"spoofed-account-{i}",
                "app-key": "attack-vector-dn3-r1",
                "idempotency-key": f"r1-{i}",
            }
            payload = {
                "sessao_cliente": f"user-{i}",
                "valor": 10,
                "destino": "modulo_dn3_r1",
            }
            resp = client.post("/api/v1/auditar/resilient", json=payload, headers=headers)

            # Não pode quebrar com 5xx — mesmo que rate limit/regras sejam acionadas
            assert resp.status_code in (201, 400, 429, 503)

        # A API ainda deve responder ao health check
        health_resp = client.get("/api/v1/health")
        assert health_resp.status_code == 200
        body = health_resp.json()
        assert "status" in body
        assert body["status"] in ("healthy", "degraded")

    # ========== DN3.R2: Circuit Breaker Race Condition ==========
    def test_dn3_r2_circuit_breaker_race_condition(self):
        """
        Dispara múltiplas threads chamando success/failure em paralelo.

        Objetivo: verificar se o estado final é consistente e se o contador
        de falhas nunca fica negativo (inspirado em DN3.R2 da documentação).
        """
        reset_availability_state()

        failure_threads = []
        success_threads = []
        total_threads = 50

        def register_failure():
            for _ in range(20):
                circuit_breaker.record_failure()

        def register_success():
            for _ in range(20):
                circuit_breaker.record_success()

        # Metade das threads focadas em falhas, metade em sucessos
        for _ in range(total_threads // 2):
            failure_threads.append(threading.Thread(target=register_failure))
            success_threads.append(threading.Thread(target=register_success))

        for t in failure_threads + success_threads:
            t.start()
        for t in failure_threads + success_threads:
            t.join()

        # Asserções mínimas de consistência
        assert circuit_breaker.failure_count >= 0
        assert circuit_breaker.state in (
            CircuitState.CLOSED,
            CircuitState.OPEN,
            CircuitState.HALF_OPEN,
        )

    # ========== DN3.R3: Idempotency Key Collision (Hash) ==========
    def test_dn3_r3_idempotency_key_collision_payload_diferente(self):
        """
        Usa a MESMA idempotency-key com payloads diferentes.

        Objetivo: verificar se a API sempre retorna o primeiro resultado
        armazenado, marcando a resposta subsequente como replay.
        """
        reset_availability_state()

        headers = {
            **HEADERS,
            "idempotency-key": "fixed-idempotency-key-r3",
        }

        payload_1 = {
            "sessao_cliente": "cliente-r3",
            "valor": 100,
            "destino": "modulo_dn3_r3_v1",
        }
        payload_2 = {
            "sessao_cliente": "cliente-r3",
            "valor": 999999,
            "destino": "modulo_dn3_r3_v2",
        }

        resp1 = client.post("/api/v1/auditar/resilient", json=payload_1, headers=headers)
        assert resp1.status_code == 201
        data1 = resp1.json()

        resp2 = client.post("/api/v1/auditar/resilient", json=payload_2, headers=headers)
        assert resp2.status_code == 201
        data2 = resp2.json()

        # A segunda resposta deve ser um replay da primeira
        assert data2["tracking_id"] == data1["tracking_id"]
        assert data2["detalhes"]["volume_processado"] == data1["detalhes"]["volume_processado"]
        assert data2["detalhes"]["modulo"] == data1["detalhes"]["modulo"]
        # Importante: no mock atual, o replay é sinalizado no nível raiz,
        # mas o bloco `availability.idempotent_replay` permanece False.
        assert data2["idempotent_replay"] is True
        assert data2["availability"]["idempotent_replay"] is False

    # ========== DN3.R4: Health Check Information Leakage ==========
    def test_dn3_r4_health_check_information_leakage(self):
        """
        Verifica se o endpoint público de health não vaza dados sensíveis.
        """
        reset_availability_state()

        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()

        # O contrato público deve ser enxuto e não expor detalhes internos.
        forbidden_keys = {"dependencies", "stack", "traceback", "filesystem_path", "ip"}
        assert not (forbidden_keys & set(body.keys()))

        # Campos esperados pelo design atual
        assert "status" in body
        assert "uptime_seconds" in body
        assert "error_rate_percent" in body
        assert "circuit_breaker" in body

    # ========== DN3.R5: Slowloris / Connection Exhaustion ==========
    def test_dn3_r5_slowloris_connection_exhaustion_simples(self):
        """
        Simula várias requisições 'lentas' para o endpoint resiliente.

        Não reproduz um Slowloris real (nível TCP), mas gera carga
        com o maior `asyncio.sleep` possível dentro do mock.
        """
        reset_availability_state()

        # Para simular pior caso, forçamos o delay máximo do mock durante este teste.
        mock_api_module.random.uniform = lambda _a, _b: 0.5

        start = time.time()

        for i in range(10):
            headers = {
                "account-key": "slowloris-tester",
                "app-key": "attack-vector-dn3-r5",
                "idempotency-key": f"slow-{i}",
            }
            payload = {
                "sessao_cliente": "slow_user",
                "valor": 10,
                "destino": "modulo_dn3_r5",
            }
            resp = client.post("/api/v1/auditar/resilient", json=payload, headers=headers)
            # Não pode dar erro 5xx em cascata
            assert resp.status_code in (201, 400, 429, 503)

        total = time.time() - start

        # Mesmo sob carga, o health check deve responder rapidamente
        health_start = time.time()
        health_resp = client.get("/api/v1/health")
        health_latency = time.time() - health_start

        assert health_resp.status_code == 200
        # Tolerância generosa, mas documenta o SLA desejado
        assert health_latency < 1.0
        # O teste em si não deve demorar "demais" (não é exato, mas indicativo)
        assert total < 10 * 1.0

    # ========== DN3.R6: Rate Limit Memory Exhaustion ==========
    def test_dn3_r6_rate_limit_memory_exhaustion(self):
        """
        Envia muitas account-keys com strings grandes para inflar o dicionário.

        Este teste não vai até 1MB por chave para evitar DoS no ambiente
        de testes, mas demonstra o crescimento sem limites do `_requests`.
        """
        reset_availability_state()

        num_keys = 50
        key_size = 2_000  # 2KB por chave (simulação reduzida)

        for i in range(num_keys):
            big_key = f"R6-{i}-" + ("X" * (key_size - len(f"R6-{i}-")))
            headers = {
                "account-key": big_key,
                "app-key": "attack-vector-dn3-r6",
                "idempotency-key": f"r6-{i}",
            }
            payload = {
                "sessao_cliente": "memory_attack",
                "valor": 1,
                "destino": "modulo_dn3_r6",
            }
            resp = client.post("/api/v1/auditar/resilient", json=payload, headers=headers)
            assert resp.status_code in (201, 400, 429, 503)

        # O dicionário interno deve ter crescido proporcionalmente ao número de chaves
        assert len(rate_limiter._requests) >= num_keys  # type: ignore[attr-defined]

    # ========== DN3.R8: Idempotency Store Unbounded Growth ==========
    def test_dn3_r8_idempotency_store_unbounded_growth(self):
        """
        Envia muitas chaves de idempotência únicas e verifica crescimento do store.

        Este teste documenta o comportamento de crescimento ilimitado do
        `IdempotencyStore`, conforme descrito em RedTeamparaDisponibilidade.md.
        """
        reset_availability_state()

        num_requests = 200  # valor reduzido para ambiente de teste

        for i in range(num_requests):
            headers = {
                # Alterna account-key para contornar rate limiting (DN3.R1),
                # evidenciando que o IdempotencyStore cresce sem limites/TTL.
                "account-key": f"idempo-attacker-{i}",
                "app-key": "attack-vector-dn3-r8",
                "idempotency-key": f"unique-idempo-{i}",
            }
            payload = {
                "sessao_cliente": "idempo_user",
                "valor": 42,
                "destino": "modulo_dn3_r8",
            }
            resp = client.post("/api/v1/auditar/resilient", json=payload, headers=headers)
            assert resp.status_code in (201, 400, 429, 503)

        # O store deve refletir o número de chaves únicas enviadas (sem TTL/eviction)
        assert idempotency_store.size() >= num_requests


if __name__ == "__main__":
    # Execução direta para debug local
    pytest.main([__file__, "-v", "-s"])


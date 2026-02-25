"""
RED TEAM - Testes Adversariais para DN1 (Tempo de Resposta / SLA)
Foco: Tentar degradar a latência da API para quebrar o SLA que o Blue Team aferição valida.
"""

import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.api import app

client = TestClient(app)
HEADERS = {"account-key": "red-team-target", "app-key": "attack-vector-01"}

# Mesmos critérios do Blue Team (response_time.py) para atacar o mesmo SLA
SLA_ALVO_MS = 500
LIMITE_ALERTA_MS = 650  # 30% acima do SLA


def _metricas(tempos_ms, limite_ms):
    """Calcula min, max, média e p95 (percentil 95) dos tempos em ms."""
    if not tempos_ms:
        return {}
    ordenado = sorted(tempos_ms)
    n = len(ordenado)
    p95_idx = int(n * 0.95) - 1 if n > 1 else 0
    p95 = ordenado[p95_idx] if ordenado else 0
    dentro = sum(1 for t in tempos_ms if t <= limite_ms)
    return {
        "min_ms": round(min(tempos_ms), 2),
        "max_ms": round(max(tempos_ms), 2),
        "media_ms": round(sum(tempos_ms) / n, 2),
        "p95_ms": round(p95, 2),
        "dentro_sla": dentro,
        "total": n,
        "conformidade_pct": round(100 * dentro / n, 1),
    }


def _log_metricas(met, limite_ms, nome):
    """Imprime resumo das métricas no formato legível."""
    print(f"\n  [RED] {nome}")
    print(f"        min={met['min_ms']}ms | max={met['max_ms']}ms | média={met['media_ms']}ms | p95={met['p95_ms']}ms")
    print(f"        dentro do SLA (≤{limite_ms}ms): {met['dentro_sla']}/{met['total']} ({met['conformidade_pct']}%)")


class TestDN1RedTeamResponseTime:
    """
    Simulação de ataques para tentar quebrar o SLA de latência (DN1).
    """

    # ---------- Passo 1: Baseline (uma requisição normal) ----------
    def test_baseline_uma_requisicao_dentro_do_sla(self):
        """
        Uma única requisição válida deve responder dentro do SLA.
        Se falhar aqui, o ambiente (ex.: TestClient) já está lento; os ataques pioram.
        """
        print("\n  [RED] Baseline: 1 requisição válida, limite SLA =", LIMITE_ALERTA_MS, "ms")
        payload = {
            "sessao_cliente": "red_baseline",
            "valor": 100.0,
            "destino": "modulo_icms",
        }
        start = time.perf_counter()
        response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"        tempo = {elapsed_ms:.2f}ms | status = {response.status_code}")
        assert response.status_code == 201
        assert elapsed_ms < LIMITE_ALERTA_MS, (
            f"Baseline já fora do SLA: {elapsed_ms:.2f}ms (limite {LIMITE_ALERTA_MS}ms)"
        )

    # ---------- Passo 2a: Ataque por burst (muitas requisições em sequência) ----------
    def test_burst_muitas_requisicoes_sequenciais_nao_degradam_sla(self):
        """
        Envia muitas requisições válidas em sequência rápida.
        Objetivo: ver se a API (ou o processamento interno) degrada e estoura o SLA.
        Critério: pelo menos 90% das requisições dentro do limite (igual ao Blue Team).
        """
        num_requisicoes = 600
        print(f"\n  [RED] Burst: {num_requisicoes} requisições em sequência, limite = {LIMITE_ALERTA_MS}ms")
        payload = {
            "sessao_cliente": "red_burst",
            "valor": 200.0,
            "destino": "modulo_pis",
        }
        tempos_ms = []

        for i in range(num_requisicoes):
            start = time.perf_counter()
            response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
            elapsed_ms = (time.perf_counter() - start) * 1000
            tempos_ms.append(elapsed_ms)
            if response.status_code != 201:
                print(f"        round {i+1}: status {response.status_code}")
            assert response.status_code == 201

        met = _metricas(tempos_ms, LIMITE_ALERTA_MS)
        _log_metricas(met, LIMITE_ALERTA_MS, "Burst – resumo")

        assert met["conformidade_pct"] >= 90, (
            f"Burst degradou SLA: {met['conformidade_pct']}% dentro do limite "
            f"(média {met['media_ms']}ms, p95 {met['p95_ms']}ms, pior {met['max_ms']}ms)"
        )

    # ---------- Passo 2b: Ataque por payload pesado (schema pollution) ----------
    def test_payload_pesado_muitos_campos_resposta_dentro_do_limite(self):
        """
        Envia um JSON com muitos campos extras para forçar parsing/validação pesada.
        Objetivo: ver se o tempo de resposta estoura o SLA (DoS por payload grande).
        Critério: a requisição deve ser atendida em < 650ms (aceita ou rejeitada).
        """
        num_campos = 70_000
        chars_por_campo = 300
        print(f"\n  [RED] Payload pesado: {num_campos} campos extras, {chars_por_campo} chars/campo")
        payload = {
            "sessao_cliente": "red_heavy",
            "valor": 500,
            "destino": "modulo_confis",
        }
        for i in range(num_campos):
            payload[f"junk_field_{i}"] = "x" * chars_por_campo

        start = time.perf_counter()
        response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"        tempo = {elapsed_ms:.2f}ms | status = {response.status_code}")
        assert response.status_code in [201, 400], f"Status inesperado: {response.status_code}"
        assert elapsed_ms < LIMITE_ALERTA_MS, (
            f"Payload pesado estourou SLA: {elapsed_ms:.2f}ms (limite {LIMITE_ALERTA_MS}ms)"
        )

    # ---------- Passo 2c: Ataque por string gigante no campo destino ----------
    def test_payload_string_gigante_resposta_dentro_do_limite(self):
        """
        Envia uma string de 2MB no campo destino para estressar parsing e memória.
        Objetivo: tentar quebrar o SLA ou provocar 413/timeout.
        """
        tamanho_mb = 10
        tamanho_bytes = tamanho_mb * 1024 * 1024
        print(f"\n  [RED] String gigante: campo destino com {tamanho_mb}MB ({tamanho_bytes} chars)")
        payload = {
            "sessao_cliente": "red_bigstring",
            "valor": 100,
            "destino": "A" * tamanho_bytes,
        }

        start = time.perf_counter()
        response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
        elapsed_ms = (time.perf_counter() - start) * 1000

        print(f"        tempo = {elapsed_ms:.2f}ms | status = {response.status_code}")
        # 201 aceito, 400 rejeitado, 413 payload too large
        assert response.status_code in [201, 400, 413], f"Status inesperado: {response.status_code}"
        assert elapsed_ms < LIMITE_ALERTA_MS, (
            f"String gigante estourou SLA: {elapsed_ms:.2f}ms (limite {LIMITE_ALERTA_MS}ms)"
        )

    # ---------- Passo 3a: Ataque por concorrência (múltiplas requisições ao mesmo tempo) ----------
    def test_burst_concorrente_multiplas_requisicoes_simultaneas(self):
        """
        Dispara várias requisições em paralelo (threads) para simular pico de tráfego.
        Objetivo: a contenção no processamento deve fazer a latência estourar o SLA.
        Critério: pelo menos 90% dentro do limite (igual ao Blue Team).
        """
        num_workers = 60
        requests_per_worker = 12
        total = num_workers * requests_per_worker
        print(f"\n  [RED] Burst concorrente: {num_workers} workers × {requests_per_worker} req = {total} req simultâneas")
        payload = {"sessao_cliente": "red_concurrent", "valor": 150.0, "destino": "modulo_icms"}
        tempos_ms = []

        def worker(_id):
            cli = TestClient(app)
            local_times = []
            for _ in range(requests_per_worker):
                start = time.perf_counter()
                r = cli.post("/api/v1/auditar", json=payload, headers=HEADERS)
                local_times.append((time.perf_counter() - start) * 1000)
                assert r.status_code == 201
            return local_times

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(worker, i) for i in range(num_workers)]
            for fut in as_completed(futures):
                tempos_ms.extend(fut.result())

        met = _metricas(tempos_ms, LIMITE_ALERTA_MS)
        _log_metricas(met, LIMITE_ALERTA_MS, "Burst concorrente – resumo")

        assert met["conformidade_pct"] >= 90, (
            f"Concorrência quebrou SLA: {met['conformidade_pct']}% dentro do limite "
            f"(média {met['media_ms']}ms, p95 {met['p95_ms']}ms, max {met['max_ms']}ms)"
        )

    # ---------- Passo 3b: Burst + payload pesado (volume + parsing pesado) ----------
    def test_burst_pesado_requisicoes_grandes_sequenciais(self):
        """
        Muitas requisições em sequência, cada uma com payload grande (muitos campos).
        Objetivo: degradar por volume + custo de parsing repetido.
        """
        num_requisicoes = 100
        num_campos_junk = 40_000
        chars_por_campo = 120
        print(f"\n  [RED] Burst pesado: {num_requisicoes} req × ({num_campos_junk} campos, {chars_por_campo} chars)")
        tempos_ms = []
        base_payload = {
            "sessao_cliente": "red_burst_heavy",
            "valor": 300,
            "destino": "modulo_pis",
        }

        for i in range(num_requisicoes):
            payload = dict(base_payload)
            for j in range(num_campos_junk):
                payload[f"junk_{j}"] = "y" * chars_por_campo
            start = time.perf_counter()
            response = client.post("/api/v1/auditar", json=payload, headers=HEADERS)
            elapsed_ms = (time.perf_counter() - start) * 1000
            tempos_ms.append(elapsed_ms)
            assert response.status_code in [201, 400]

        met = _metricas(tempos_ms, LIMITE_ALERTA_MS)
        _log_metricas(met, LIMITE_ALERTA_MS, "Burst pesado – resumo")

        assert met["conformidade_pct"] >= 90, (
            f"Burst pesado quebrou SLA: {met['conformidade_pct']}% dentro do limite "
            f"(média {met['media_ms']}ms, p95 {met['p95_ms']}ms)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

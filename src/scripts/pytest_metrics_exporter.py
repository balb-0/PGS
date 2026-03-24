#!/usr/bin/env python3
"""
T6 — Exporter de métricas de massa de testes (modelo Pull do Prometheus).

Servidor HTTP que expõe métricas pytest em /metrics para o Prometheus fazer scrape.
Executa pytest periodicamente e atualiza os gauges.

Métricas: pytest_tests_total, pytest_tests_passed

Uso:
  python src/scripts/pytest_metrics_exporter.py
  python src/scripts/pytest_metrics_exporter.py --port 9092 --interval 300

Variáveis de ambiente:
  PYTEST_EXPORTER_PORT: Porta HTTP (default: 9092)
  PYTEST_EXPORTER_INTERVAL: Intervalo entre execuções do pytest em segundos (default: 300)
  PROJECT_ROOT: Raiz do projeto (default: diretório do script/../../)
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

# Carrega .env da raiz do projeto (opcional)
_load_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _load_env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_load_env_path)
    except ImportError:
        pass

from prometheus_client import Gauge, start_http_server

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent.parent))
TESTS_PATH = PROJECT_ROOT / "src" / "tests"

# Gauges no registry padrão (Prometheus faz scrape)
pytest_tests_total = Gauge(
    "pytest_tests_total",
    "Total de testes na suíte (Dashboard Qualidade - Massa de testes)",
)
pytest_tests_passed = Gauge(
    "pytest_tests_passed",
    "Total de testes que passaram (Dashboard Qualidade - Massa de testes)",
)


def run_pytest() -> tuple[int, int, int]:
    """
    Executa pytest e retorna (total, passed, failed).
    """
    cmd = [
        sys.executable, "-m", "pytest",
        str(TESTS_PATH),
        "-q", "--tb=no", "--no-header",
    ]
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    output = result.stdout + result.stderr

    passed = 0
    failed = 0
    skipped = 0
    error = 0

    m_passed = re.search(r"(\d+)\s+passed", output)
    m_failed = re.search(r"(\d+)\s+failed", output)
    m_skipped = re.search(r"(\d+)\s+skipped", output)
    m_error = re.search(r"(\d+)\s+error", output)

    if m_passed:
        passed = int(m_passed.group(1))
    if m_failed:
        failed = int(m_failed.group(1))
    if m_skipped:
        skipped = int(m_skipped.group(1))
    if m_error:
        error = int(m_error.group(1))

    total = passed + failed + skipped + error
    if total == 0 and "passed" in output:
        total = passed if passed > 0 else 1

    return total, passed, failed + error


def update_metrics() -> None:
    """Executa pytest e atualiza os gauges."""
    if not TESTS_PATH.exists():
        pytest_tests_total.set(0)
        pytest_tests_passed.set(0)
        return
    try:
        total, passed, _ = run_pytest()
        pytest_tests_total.set(total)
        pytest_tests_passed.set(passed)
    except Exception:
        pytest_tests_total.set(0)
        pytest_tests_passed.set(0)


def run_periodically(interval_seconds: int) -> None:
    """Thread que executa pytest a cada interval_seconds."""
    while True:
        update_metrics()
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exporter de métricas pytest para Prometheus (modelo Pull)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PYTEST_EXPORTER_PORT", "9092")),
        help="Porta HTTP para o endpoint /metrics (default: 9092)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("PYTEST_EXPORTER_INTERVAL", "300")),
        help="Intervalo entre execuções do pytest em segundos (default: 300)",
    )
    args = parser.parse_args()

    if not TESTS_PATH.exists():
        print(f"Diretório de testes não encontrado: {TESTS_PATH}", file=sys.stderr)
        return 1

    # Inicia servidor HTTP PRIMEIRO (endpoint disponível imediatamente)
    start_http_server(args.port, addr="0.0.0.0")
    print(f"Exporter rodando em http://localhost:{args.port}/metrics")
    print(f"Pytest executado a cada {args.interval}s. Pressione Ctrl+C para encerrar.")

    # Thread para atualizar métricas periodicamente (pytest demora ~30-60s na primeira vez)
    thread = threading.Thread(target=run_periodically, args=(args.interval,), daemon=True)
    thread.start()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
T6 — Coleta de métricas de massa de testes (pytest).

Executa pytest e exibe as métricas no terminal. Para expor ao Prometheus
(modelo Pull), use pytest_metrics_exporter.py.

Métricas: pytest_tests_total, pytest_tests_passed

Uso:
  python src/scripts/collect_pytest_metrics.py          # exibe métricas
  python src/scripts/collect_pytest_metrics.py --json   # saída JSON

Para modelo Pull (Prometheus scrape):
  python src/scripts/pytest_metrics_exporter.py --port 9092
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Carrega .env da raiz do projeto (opcional)
_load_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _load_env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_load_env_path)
    except ImportError:
        pass

# -----------------------------------------------------------------------------
# Configuração
# -----------------------------------------------------------------------------
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent.parent.parent))
TESTS_PATH = PROJECT_ROOT / "src" / "tests"


def parse_junit_xml(xml_path: Path) -> tuple[int, int, int]:
    """Parseia JUnit XML e retorna (total, passed, failed)."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(xml_path)
    root = tree.getroot()
    total = int(root.get("tests", 0))
    failures = int(root.get("failures", 0))
    errors = int(root.get("errors", 0))
    skipped = int(root.get("skipped", 0))
    passed = total - failures - errors - skipped
    return total, max(0, passed), failures + errors


def run_pytest() -> tuple[int, int, int]:
    """Executa pytest e retorna (total, passed, failed)."""
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

    passed = failed = skipped = error = 0
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Executa pytest e exibe métricas (T6)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saída em JSON",
    )
    parser.add_argument(
        "--junitxml",
        metavar="PATH",
        help="Usar JUnit XML existente (ex: pytest-report.xml)",
    )
    args = parser.parse_args()

    if args.junitxml:
        xml_path = Path(args.junitxml)
        if not xml_path.is_absolute():
            xml_path = PROJECT_ROOT / xml_path
        if not xml_path.exists():
            print(f"Arquivo não encontrado: {xml_path}", file=sys.stderr)
            return 1
        total, passed, failed = parse_junit_xml(xml_path)
    else:
        if not TESTS_PATH.exists():
            print(f"Diretório de testes não encontrado: {TESTS_PATH}", file=sys.stderr)
            return 1
        total, passed, failed = run_pytest()

    if args.json:
        print(json.dumps({
            "pytest_tests_total": total,
            "pytest_tests_passed": passed,
            "pytest_tests_failed": failed,
        }))
    else:
        print(f"pytest: {total} total, {passed} passed, {failed} failed")
        print("Para expor ao Prometheus (Pull): python src/scripts/pytest_metrics_exporter.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())

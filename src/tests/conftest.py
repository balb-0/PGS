"""
Configuração global do pytest para o projeto ASIS.

Garante que o diretório raiz do projeto (g06) esteja em sys.path para
imports consistentes (src.core.*), evitando métricas Prometheus duplicadas
quando core.api é importado por caminhos diferentes (core vs src.core).
"""
from pathlib import Path

import pytest

# Raiz do projeto: src/tests/conftest.py -> parent.parent.parent = g06
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_repo_root))

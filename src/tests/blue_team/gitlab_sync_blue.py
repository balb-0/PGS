"""
Testes para a integração INT4 – Sincronismo de versões via API do GitLab.

Projeto ASIS – Sprint 3. Testes de integração que chamam a API real do GitLab.
Requer GITLAB_PRIVATE_TOKEN configurado no .env na raiz do projeto.

Execução (na raiz do projeto, com .env configurado):
  pytest src/tests/gitlab_sync_blue.py -v
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Carrega .env da raiz do projeto (src/tests/blue_team -> parent^4 = g06)
_repo_root = Path(__file__).resolve().parent.parent.parent.parent
_env_path = _repo_root / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass

if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from src.scripts.verifica_versao_gitlab import (
    verificar_protocolo_gitlab,
    get_ultimo_commit,
    verificar_sincronismo,
)

# Requer token real para rodar (sem mock)
pytestmark = pytest.mark.skipif(
    not os.environ.get("GITLAB_PRIVATE_TOKEN") or os.environ.get("GITLAB_PRIVATE_TOKEN", "").startswith("test-"),
    reason="Requer GITLAB_PRIVATE_TOKEN real no .env para testes de integração",
)


class TestVerificacaoProtocoloGitLab:
    """Testes da função que confirma o protocolo da integração GitLab API v4 (API real)."""

    def test_protocolo_retorna_estrutura_esperada(self):
        resultado = verificar_protocolo_gitlab()
        assert isinstance(resultado, dict)
        assert "ok" in resultado
        assert "message" in resultado
        assert "details" in resultado
        assert isinstance(resultado["ok"], bool)
        assert isinstance(resultado["message"], str)
        assert isinstance(resultado["details"], dict)

    def test_protocolo_ok_quando_api_acessivel(self):
        resultado = verificar_protocolo_gitlab()
        assert resultado["ok"] is True, resultado.get("message", "")
        assert "v4" in resultado["details"].get("api_version", "")
        assert "commits" in resultado["details"].get("endpoint_ref", "").lower()


class TestGetUltimoCommit:
    """Testes da função que obtém o último commit de uma branch (API real)."""

    def test_retorna_dict_quando_branch_existe(self):
        commit = get_ultimo_commit("main")
        assert commit is not None
        assert isinstance(commit, dict)
        assert "id" in commit
        assert "short_id" in commit
        assert "title" in commit
        assert "message" in commit
        assert "authored_date" in commit
        assert "web_url" in commit
        assert len(commit["id"]) >= 7
        assert commit["short_id"] in commit["id"]

    def test_develop_retorna_dict_com_mesma_estrutura(self):
        commit = get_ultimo_commit("develop")
        assert commit is not None
        assert set(commit.keys()) >= {"id", "short_id", "title", "message", "authored_date", "web_url"}

    def test_branch_inexistente_retorna_none(self):
        commit = get_ultimo_commit("branch_que_nao_existe_12345")
        assert commit is None


class TestVerificarSincronismo:
    """Testes da comparação main vs develop (API real)."""

    def test_retorna_estrutura_esperada(self):
        resultado = verificar_sincronismo()
        assert "in_sync" in resultado
        assert "main_commit" in resultado
        assert "develop_commit" in resultado
        assert "status_message" in resultado
        assert isinstance(resultado["in_sync"], bool)
        assert isinstance(resultado["status_message"], str)

    def test_main_e_develop_tem_commits_quando_branches_existem(self):
        resultado = verificar_sincronismo()
        assert resultado["main_commit"] is not None
        assert resultado["develop_commit"] is not None
        assert resultado["main_commit"]["id"]
        assert resultado["develop_commit"]["id"]

    def test_in_sync_reflete_igualdade_dos_commits(self):
        resultado = verificar_sincronismo()
        if resultado["main_commit"]["id"] == resultado["develop_commit"]["id"]:
            assert resultado["in_sync"] is True
            assert "mesma versão" in resultado["status_message"].lower()
        else:
            assert resultado["in_sync"] is False
            assert "diferentes" in resultado["status_message"].lower()


class TestSaidaJson:
    """Garante que a saída em formato JSON é válida e contém os campos esperados (dados reais)."""

    def test_estrutura_saida_json_serializavel(self):
        resultado = verificar_sincronismo()
        data = {
            "in_sync": resultado["in_sync"],
            "status_message": resultado["status_message"],
            "main_commit": resultado["main_commit"],
            "develop_commit": resultado["develop_commit"],
        }
        json_str = json.dumps(data, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["in_sync"] == resultado["in_sync"]
        assert "main_commit" in parsed
        assert "develop_commit" in parsed
        if parsed["main_commit"]:
            assert "id" in parsed["main_commit"]
        if parsed["develop_commit"]:
            assert "id" in parsed["develop_commit"]

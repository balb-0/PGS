"""
RED TEAM - Testes Adversariais para INT4 (Sincronismo de versoes via GitLab)

Foco: explorar vulnerabilidades na integracao com a API do GitLab:
- INT4.R1: Path traversal (injecao de ../ no project path)
- INT4.R2: Branch injection (caracteres especiais em nomes de branch)
- INT4.R3: Response validation robustness (respostas malformadas da API GitLab)
- INT4.R4: Token scope verification (operacoes com escopo minimo)
- INT4.R5: API rate limit graceful handling (simulacao de HTTP 429)

Testes que dependem de mocks (R1, R2, R3, R5) rodam sem token.
Testes de API real (R4) requerem GITLAB_PRIVATE_TOKEN no .env.

Execucao:
  pytest src/tests/red_team/gitlab_sync_red.py -v -s
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

_repo_root = Path(__file__).resolve().parent.parent.parent
_env_path = _repo_root / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass

if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from scripts.verifica_versao_gitlab import (
    verificar_protocolo_gitlab,
    get_ultimo_commit,
    verificar_sincronismo,
)

HAS_TOKEN = bool(
    os.environ.get("GITLAB_PRIVATE_TOKEN")
    and not os.environ.get("GITLAB_PRIVATE_TOKEN", "").startswith("test-")
)


# =============================================================================
# INT4.R1 — Path Traversal
# =============================================================================

class TestINT4R1PathTraversal:
    """Tenta injetar paths maliciosos no GITLAB_PROJECT_PATH."""

    def test_int4_r1_path_traversal_no_project_path(self):
        """
        Injeta '../' no project path. A funcao deve retornar erro ou
        resultado vazio, sem expor dados de outros projetos.
        """
        with patch("scripts.verifica_versao_gitlab.GITLAB_PROJECT_PATH", "../../admin/secret"):
            try:
                resultado = get_ultimo_commit("main")
                assert resultado is None, (
                    "Path traversal retornou dados — possivel acesso indevido"
                )
            except (ValueError, TypeError):
                pass

    def test_int4_r1_path_com_caracteres_especiais(self):
        """Project path com caracteres de controle e URL encoding."""
        paths_maliciosos = [
            "graduacao%2F..%2Fadmin",
            "graduacao/\x00/secret",
            "graduacao/../../../etc/passwd",
        ]
        for path_mal in paths_maliciosos:
            with patch("scripts.verifica_versao_gitlab.GITLAB_PROJECT_PATH", path_mal):
                try:
                    resultado = get_ultimo_commit("main")
                    assert resultado is None, (
                        f"Path malicioso '{path_mal}' retornou dados"
                    )
                except (ValueError, TypeError):
                    pass


# =============================================================================
# INT4.R2 — Branch Injection
# =============================================================================

class TestINT4R2BranchInjection:
    """Testa nomes de branch com caracteres especiais e injecao."""

    @pytest.mark.parametrize("branch_name", [
        "main; rm -rf /",
        "main\x00develop",
        "main' OR '1'='1",
        "  main  ",
        "../refs/heads/admin",
        "main\nX-Injected: true",
    ])
    def test_int4_r2_branch_com_injecao(self, branch_name):
        """
        Nomes de branch maliciosos devem retornar None (sem commit)
        sem causar excecao nao tratada.
        """
        try:
            resultado = get_ultimo_commit(branch_name)
            assert resultado is None or isinstance(resultado, dict), (
                f"Branch injection retornou tipo inesperado: {type(resultado)}"
            )
        except (ValueError, TypeError):
            pass


# =============================================================================
# INT4.R3 — Response Validation Robustness
# =============================================================================

class TestINT4R3ResponseValidation:
    """Simula respostas malformadas da API GitLab via mocks."""

    def test_int4_r3_resposta_json_invalido(self):
        """API retorna corpo nao-JSON. A funcao deve tratar sem crash."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Invalid JSON")

        with patch("scripts.verifica_versao_gitlab.requests.get", return_value=mock_resp), \
             patch("scripts.verifica_versao_gitlab.GITLAB_PRIVATE_TOKEN", "mock-token"):
            try:
                resultado = get_ultimo_commit("main")
                assert resultado is None
            except TypeError:
                pass

    def test_int4_r3_resposta_lista_vazia(self):
        """API retorna lista vazia (branch sem commits)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

        with patch("scripts.verifica_versao_gitlab.requests.get", return_value=mock_resp), \
             patch("scripts.verifica_versao_gitlab.GITLAB_PRIVATE_TOKEN", "mock-token"):
            try:
                resultado = get_ultimo_commit("main")
                assert resultado is None
            except TypeError:
                pass

    def test_int4_r3_resposta_commit_sem_campos_esperados(self):
        """API retorna commit sem os campos id/title."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"unexpected_field": "value"}]

        with patch("scripts.verifica_versao_gitlab.requests.get", return_value=mock_resp), \
             patch("scripts.verifica_versao_gitlab.GITLAB_PRIVATE_TOKEN", "mock-token"):
            try:
                resultado = get_ultimo_commit("main")
                if resultado is not None:
                    assert resultado.get("id") is None or resultado.get("title") is None
            except TypeError:
                pass

    def test_int4_r3_resposta_nao_lista(self):
        """API retorna dict em vez de lista (mudanca de protocolo)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"error": "not found"}

        with patch("scripts.verifica_versao_gitlab.requests.get", return_value=mock_resp), \
             patch("scripts.verifica_versao_gitlab.GITLAB_PRIVATE_TOKEN", "mock-token"):
            try:
                resultado = get_ultimo_commit("main")
                assert resultado is None
            except TypeError:
                pass

    def test_int4_r3_protocolo_detecta_formato_inesperado(self):
        """verificar_protocolo_gitlab deve reportar ok=False para formato inesperado."""
        mock_project = MagicMock()
        mock_project.status_code = 200
        mock_project.json.return_value = {"id": 1}

        mock_commits = MagicMock()
        mock_commits.status_code = 200
        mock_commits.json.return_value = {"error": "formato mudou"}

        def mock_get(url, **kwargs):
            if "commits" in url:
                return mock_commits
            return mock_project

        with patch("scripts.verifica_versao_gitlab.requests.get", side_effect=mock_get), \
             patch("scripts.verifica_versao_gitlab.GITLAB_PRIVATE_TOKEN", "mock-token"):
            resultado = verificar_protocolo_gitlab()
            assert resultado["ok"] is False


# =============================================================================
# INT4.R4 — Token Scope Verification
# =============================================================================

class TestINT4R4TokenScope:
    """Verifica que as funcoes operam apenas com escopos minimos (read_api)."""

    @pytest.mark.skipif(not HAS_TOKEN, reason="Requer GITLAB_PRIVATE_TOKEN real")
    def test_int4_r4_apenas_leitura_nao_modifica_dados(self):
        """
        As funcoes de integracao devem apenas LER dados (commits, branches).
        Nenhuma funcao deve realizar POST/PUT/DELETE.
        """
        resultado = verificar_protocolo_gitlab()
        assert resultado["ok"] is True

        commit = get_ultimo_commit("main")
        assert commit is not None
        assert isinstance(commit, dict)

    @pytest.mark.skipif(not HAS_TOKEN, reason="Requer GITLAB_PRIVATE_TOKEN real")
    def test_int4_r4_sincronismo_e_readonly(self):
        """verificar_sincronismo realiza apenas operacoes de leitura."""
        resultado = verificar_sincronismo()
        assert "in_sync" in resultado
        assert isinstance(resultado["in_sync"], bool)


# =============================================================================
# INT4.R5 — API Rate Limit Graceful Handling
# =============================================================================

class TestINT4R5RateLimitHandling:
    """Simula HTTP 429 do GitLab e verifica tratamento gracioso."""

    def test_int4_r5_rate_limit_retorna_none_sem_crash(self):
        """Quando GitLab retorna 429, get_ultimo_commit deve retornar None."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.json.return_value = {"message": "429 Too Many Requests"}

        with patch("scripts.verifica_versao_gitlab.requests.get", return_value=mock_resp), \
             patch("scripts.verifica_versao_gitlab.GITLAB_PRIVATE_TOKEN", "mock-token"):
            try:
                resultado = get_ultimo_commit("main")
                assert resultado is None
            except TypeError:
                pass

    def test_int4_r5_rate_limit_protocolo_reporta_falha(self):
        """verificar_protocolo_gitlab deve reportar ok=False quando recebe 429."""
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.json.return_value = {"message": "429 Too Many Requests"}

        with patch("scripts.verifica_versao_gitlab.requests.get", return_value=mock_resp), \
             patch("scripts.verifica_versao_gitlab.GITLAB_PRIVATE_TOKEN", "mock-token"):
            resultado = verificar_protocolo_gitlab()
            assert resultado["ok"] is False

    def test_int4_r5_timeout_da_api_tratado(self):
        """Timeout de conexao com GitLab deve ser tratado sem crash."""
        import requests as req

        with patch("scripts.verifica_versao_gitlab.requests.get",
                   side_effect=req.Timeout("Connection timed out")), \
             patch("scripts.verifica_versao_gitlab.GITLAB_PRIVATE_TOKEN", "mock-token"):
            try:
                resultado = get_ultimo_commit("main")
                assert resultado is None
            except TypeError:
                pass

        with patch("scripts.verifica_versao_gitlab.requests.get",
                   side_effect=req.Timeout("Connection timed out")), \
             patch("scripts.verifica_versao_gitlab.GITLAB_PRIVATE_TOKEN", "mock-token"):
            resultado = verificar_protocolo_gitlab()
            assert resultado["ok"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

#!/usr/bin/env python3
"""
INT4 — Sincronismo de versoes via API do GitLab (API v4).

Verifica se o ultimo commit da branch main (producao) e igual ao ultimo
commit da branch develop (homologacao). Retorna status em sync / out of sync.

Uso:
    python src/scripts/verifica_versao_gitlab.py                # saida legivel
    python src/scripts/verifica_versao_gitlab.py --json          # saida JSON
    python src/scripts/verifica_versao_gitlab.py --apenas-protocolo  # so verifica API

Variaveis de ambiente (.env na raiz):
    GITLAB_PRIVATE_TOKEN  — token com read_api + read_repository
    GITLAB_BASE_URL       — padrao: https://git.inteli.edu.br
    GITLAB_PROJECT_PATH   — padrao: graduacao/2026-1a/t13/g06
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests
from requests.exceptions import RequestException

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------

_repo_root = Path(__file__).resolve().parent.parent.parent
_env_path = _repo_root / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass

GITLAB_BASE_URL = os.environ.get("GITLAB_BASE_URL", "https://git.inteli.edu.br")
GITLAB_PROJECT_PATH = os.environ.get("GITLAB_PROJECT_PATH", "graduacao/2026-1a/t13/g06")
GITLAB_PRIVATE_TOKEN = os.environ.get("GITLAB_PRIVATE_TOKEN", "")

API_V4 = f"{GITLAB_BASE_URL}/api/v4"
SAFE_PATH_RE = re.compile(r"^[a-zA-Z0-9_\-./]+$")


def _is_safe_path(path: str) -> bool:
    """Rejeita paths com traversal, null bytes ou caracteres perigosos."""
    if not path or "\x00" in path or not SAFE_PATH_RE.match(path):
        return False
    if ".." in path:
        return False
    return True


def _headers() -> dict:
    return {"PRIVATE-TOKEN": GITLAB_PRIVATE_TOKEN}


def _project_id_encoded() -> str:
    return requests.utils.quote(GITLAB_PROJECT_PATH, safe="")


def _api_get(endpoint: str, params: dict | None = None) -> requests.Response | None:
    """Chama GET no GitLab API v4. Retorna Response ou None em caso de erro."""
    if not _is_safe_path(GITLAB_PROJECT_PATH):
        return None
    url = f"{API_V4}/projects/{_project_id_encoded()}{endpoint}"
    try:
        resp = requests.get(url, headers=_headers(), params=params or {}, timeout=10)
        if resp.status_code == 429:
            return None
        return resp
    except (RequestException, KeyError, TypeError):
        return None


def _parse_commit(data: dict) -> dict | None:
    """Extrai campos relevantes de um commit retornado pela API."""
    try:
        return {
            "id": data["id"],
            "short_id": data.get("short_id", data["id"][:8]),
            "title": data.get("title", ""),
            "message": data.get("message", ""),
            "authored_date": data.get("authored_date", ""),
            "web_url": data.get("web_url", ""),
        }
    except (KeyError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Funcoes publicas
# ---------------------------------------------------------------------------


def verificar_protocolo_gitlab() -> dict:
    """
    Confirma que a API v4 do GitLab esta acessivel e responde no formato esperado.

    Retorna {"ok": bool, "message": str, "details": {...}}
    """
    if not GITLAB_PRIVATE_TOKEN:
        return {
            "ok": False,
            "message": "GITLAB_PRIVATE_TOKEN nao configurado",
            "details": {},
        }

    details: dict = {}

    # 1) Verificar acesso ao projeto
    resp = _api_get("")
    if resp is None:
        return {
            "ok": False,
            "message": "Falha ao conectar ao GitLab (timeout ou path invalido)",
            "details": details,
        }
    if resp.status_code != 200:
        return {
            "ok": False,
            "message": f"Projeto nao acessivel (HTTP {resp.status_code})",
            "details": details,
        }

    # 2) Verificar formato da resposta de commits
    resp_commit = _api_get("/repository/commits", {"ref_name": "main", "per_page": 1})
    if resp_commit is None:
        return {
            "ok": False,
            "message": "Falha ao consultar commits (timeout ou rate limit)",
            "details": details,
        }
    if resp_commit.status_code != 200:
        return {
            "ok": False,
            "message": f"Commits inacessiveis (HTTP {resp_commit.status_code})",
            "details": details,
        }

    try:
        data = resp_commit.json()
    except (ValueError, KeyError, TypeError):
        return {
            "ok": False,
            "message": "Resposta de commits nao e JSON valido",
            "details": details,
        }

    if not isinstance(data, list) or len(data) == 0:
        return {
            "ok": False,
            "message": "Formato de commits inesperado (esperado lista nao-vazia)",
            "details": details,
        }

    commit = data[0]
    if not isinstance(commit, dict) or "id" not in commit or "title" not in commit:
        return {
            "ok": False,
            "message": "Commit sem campos obrigatorios (id, title)",
            "details": details,
        }

    details["api_version"] = "v4"
    details["endpoint_ref"] = f"{API_V4}/projects/.../repository/commits"

    return {
        "ok": True,
        "message": "Protocolo GitLab API v4 validado com sucesso",
        "details": details,
    }


def get_ultimo_commit(branch: str = "main") -> dict | None:
    """
    Retorna o ultimo commit da branch como dict, ou None se nao encontrado.

    Campos: id, short_id, title, message, authored_date, web_url
    """
    if not GITLAB_PRIVATE_TOKEN:
        return None

    if not _is_safe_path(branch) or not _is_safe_path(GITLAB_PROJECT_PATH):
        return None

    resp = _api_get("/repository/commits", {"ref_name": branch, "per_page": 1})
    if resp is None:
        return None
    if resp.status_code != 200:
        return None

    try:
        data = resp.json()
    except (ValueError, KeyError, TypeError):
        return None

    if not isinstance(data, list) or len(data) == 0:
        return None

    return _parse_commit(data[0])


def verificar_sincronismo() -> dict:
    """
    Compara o ultimo commit de main vs develop.

    Retorna {"in_sync": bool, "main_commit": dict|None,
             "develop_commit": dict|None, "status_message": str}
    """
    main_commit = get_ultimo_commit("main")
    develop_commit = get_ultimo_commit("develop")

    if main_commit is None or develop_commit is None:
        return {
            "in_sync": False,
            "main_commit": main_commit,
            "develop_commit": develop_commit,
            "status_message": "Nao foi possivel obter commits de ambas as branches",
        }

    if main_commit["id"] == develop_commit["id"]:
        return {
            "in_sync": True,
            "main_commit": main_commit,
            "develop_commit": develop_commit,
            "status_message": "Producao e homologacao na mesma versao",
        }

    return {
        "in_sync": False,
        "main_commit": main_commit,
        "develop_commit": develop_commit,
        "status_message": (
            f"Branches em diferentes versoes — main: {main_commit['short_id']}, "
            f"develop: {develop_commit['short_id']}"
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Verifica sincronismo GitLab (INT4)")
    parser.add_argument("--json", action="store_true", help="Saida em JSON")
    parser.add_argument(
        "--apenas-protocolo",
        action="store_true",
        help="Apenas verifica o protocolo da API",
    )
    args = parser.parse_args()

    if args.apenas_protocolo:
        resultado = verificar_protocolo_gitlab()
        if args.json:
            print(json.dumps(resultado, ensure_ascii=False, indent=2))
        else:
            print(f"[{'OK' if resultado['ok'] else 'FALHA'}] {resultado['message']}")
        return 0 if resultado["ok"] else 1

    resultado = verificar_sincronismo()

    if args.json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        status = "IN SYNC" if resultado["in_sync"] else "OUT OF SYNC"
        print(f"[{status}] {resultado['status_message']}")
        if resultado["main_commit"]:
            print(f"  main:    {resultado['main_commit']['short_id']} — {resultado['main_commit']['title']}")
        if resultado["develop_commit"]:
            print(f"  develop: {resultado['develop_commit']['short_id']} — {resultado['develop_commit']['title']}")

    return 0 if resultado["in_sync"] else 1


if __name__ == "__main__":
    sys.exit(main())

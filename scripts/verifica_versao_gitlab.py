#!/usr/bin/env python3
"""
Integração INT4 – Sincronismo de versões via API do GitLab (REST API v4).

Script de orquestração que verifica se a versão em produção (último commit da main)
corresponde à versão homologada (último commit da develop), garantindo governança
do ciclo de vida do software (SDLC).

Uso:
  python scripts/verifica_versao_gitlab.py
  python scripts/verifica_versao_gitlab.py --json

Requisitos: GITLAB_PRIVATE_TOKEN no .env na raiz do projeto.
Opcional: GITLAB_BASE_URL, GITLAB_PROJECT_PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Carrega .env da raiz do projeto (opcional)
_load_env_path = Path(__file__).resolve().parent.parent / ".env"
if _load_env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_load_env_path)
    except ImportError:
        pass

import requests

# -----------------------------------------------------------------------------
# Configuração (variáveis de ambiente)
# -----------------------------------------------------------------------------
GITLAB_BASE_URL = os.environ.get("GITLAB_BASE_URL", "https://git.inteli.edu.br").rstrip("/")
GITLAB_PROJECT_PATH = os.environ.get("GITLAB_PROJECT_PATH", "graduacao/2026-1a/t13/g06")
GITLAB_PRIVATE_TOKEN = os.environ.get("GITLAB_PRIVATE_TOKEN", "")

# Assinatura da integração (Sprint 3)
GITLAB_API_VERSION = "v4"
COMMITS_ENDPOINT_REF = "GET /projects/:id/repository/commits (ref_name, per_page)"


def _api_url(path: str) -> str:
    """Monta URL base da API GitLab v4."""
    return f"{GITLAB_BASE_URL}/api/v4{path}"


def _headers() -> dict:
    """Headers para autenticação na API GitLab."""
    if not GITLAB_PRIVATE_TOKEN:
        raise ValueError(
            "GITLAB_PRIVATE_TOKEN não definido. Configure no .env na raiz do projeto."
        )
    return {"PRIVATE-TOKEN": GITLAB_PRIVATE_TOKEN}


def verificar_protocolo_gitlab() -> dict:
    """
    Verifica a última mudança do protocolo da integração GitLab.

    Confirma que a API v4 está acessível e que o endpoint de commits retorna
    o formato esperado. Retorna status do protocolo ou indica mudanças.

    Retorno:
        dict com chaves: ok (bool), message (str), details (dict opcional).
    """
    result = {"ok": False, "message": "", "details": {}}
    project_id_encoded = GITLAB_PROJECT_PATH.replace("/", "%2F")

    try:
        # 1) Verificar acesso ao projeto (endpoint genérico da API v4)
        project_url = _api_url(f"/projects/{project_id_encoded}")
        r = requests.get(project_url, headers=_headers(), timeout=10)
        if r.status_code == 401:
            result["message"] = "Token inválido ou sem permissão (401)"
            result["details"]["status_code"] = 401
            return result
        if r.status_code == 404:
            result["message"] = "Projeto não encontrado (404)"
            result["details"]["status_code"] = 404
            return result
        if r.status_code != 200:
            result["message"] = f"API retornou status inesperado: {r.status_code}"
            result["details"]["status_code"] = r.status_code
            return result

        # 2) Verificar endpoint de commits (assinatura da integração)
        commits_url = _api_url(
            f"/projects/{project_id_encoded}/repository/commits?ref_name=main&per_page=1"
        )
        r_commits = requests.get(commits_url, headers=_headers(), timeout=10)
        if r_commits.status_code != 200:
            result["message"] = (
                f"Endpoint de commits retornou {r_commits.status_code}. "
                "Possível mudança no protocolo da API."
            )
            result["details"]["commits_status"] = r_commits.status_code
            return result

        data = r_commits.json()
        if not isinstance(data, list):
            result["message"] = "Resposta de commits não é uma lista; protocolo pode ter mudado."
            result["details"]["response_type"] = type(data).__name__
            return result
        if len(data) >= 1:
            commit = data[0]
            if "id" not in commit or "title" not in commit:
                result["message"] = "Formato do commit diferente do esperado (id/title)."
                result["details"]["keys"] = list(commit.keys())
                return result

        result["ok"] = True
        result["message"] = f"Protocolo GitLab API {GITLAB_API_VERSION} confirmado."
        result["details"]["api_version"] = GITLAB_API_VERSION
        result["details"]["endpoint_ref"] = COMMITS_ENDPOINT_REF
        return result

    except requests.RequestException as e:
        result["message"] = f"Erro de conexão com o GitLab: {e!s}"
        result["details"]["error"] = str(e)
        return result


def get_ultimo_commit(ref_name: str) -> dict | None:
    """
    Obtém o último commit de uma branch via GitLab API v4.

    Args:
        ref_name: Nome da branch (ex: main, develop).

    Returns:
        dict com id, short_id, title, message, authored_date, web_url;
        ou None em caso de erro.
    """
    project_id_encoded = GITLAB_PROJECT_PATH.replace("/", "%2F")
    url = _api_url(
        f"/projects/{project_id_encoded}/repository/commits?ref_name={ref_name}&per_page=1"
    )
    try:
        r = requests.get(url, headers=_headers(), timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        if not isinstance(data, list) or len(data) == 0:
            return None
        commit = data[0]
        return {
            "id": commit.get("id"),
            "short_id": commit.get("short_id"),
            "title": commit.get("title"),
            "message": commit.get("message"),
            "authored_date": commit.get("authored_date"),
            "web_url": commit.get("web_url"),
        }
    except (requests.RequestException, (KeyError, TypeError)):
        return None


def verificar_sincronismo() -> dict:
    """
    Compara último commit da main (produção) com o último da develop (homologação).

    Returns:
        dict com: in_sync (bool), main_commit, develop_commit, status_message.
    """
    main_commit = get_ultimo_commit("main")
    develop_commit = get_ultimo_commit("develop")

    if main_commit is None:
        return {
            "in_sync": False,
            "main_commit": None,
            "develop_commit": develop_commit,
            "status_message": "Não foi possível obter o último commit da main.",
        }
    if develop_commit is None:
        return {
            "in_sync": False,
            "main_commit": main_commit,
            "develop_commit": None,
            "status_message": "Não foi possível obter o último commit da develop.",
        }

    in_sync = main_commit["id"] == develop_commit["id"]
    return {
        "in_sync": in_sync,
        "main_commit": main_commit,
        "develop_commit": develop_commit,
        "status_message": (
            "Produção (main) e homologação (develop) estão na mesma versão."
            if in_sync
            else "Produção (main) e homologação (develop) estão em versões diferentes."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verifica sincronismo entre versão em produção (main) e homologada (develop) via GitLab API v4."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Saída em JSON (para integração com cron/scripts).",
    )
    parser.add_argument(
        "--apenas-protocolo",
        action="store_true",
        help="Apenas executa a verificação do protocolo da API (não compara commits).",
    )
    args = parser.parse_args()

    if not GITLAB_PRIVATE_TOKEN:
        print("Erro: GITLAB_PRIVATE_TOKEN não definido. Configure no .env na raiz do projeto.", file=sys.stderr)
        return 1

    if args.apenas_protocolo:
        resultado = verificar_protocolo_gitlab()
        if args.json:
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
        else:
            print(resultado["message"])
            if not resultado["ok"]:
                return 1
        return 0

    # Verificação de protocolo opcional antes do sincronismo (pode falhar e ainda assim tentar commits)
    proto = verificar_protocolo_gitlab()
    if not proto["ok"] and not args.json:
        print(f"Aviso (protocolo): {proto['message']}", file=sys.stderr)

    resultado = verificar_sincronismo()

    if args.json:
        out = {
            "in_sync": resultado["in_sync"],
            "status_message": resultado["status_message"],
            "main_commit": resultado["main_commit"],
            "develop_commit": resultado["develop_commit"],
            "protocol_check": proto,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if resultado["in_sync"] else 1

    # Saída legível
    print("=== Sincronismo de versões (GitLab API v4) ===")
    print(resultado["status_message"])
    if resultado["main_commit"]:
        c = resultado["main_commit"]
        print(f"  Main (produção):    {c['short_id']} - {c['title']}")
    if resultado["develop_commit"]:
        c = resultado["develop_commit"]
        print(f"  Develop (homolog):  {c['short_id']} - {c['title']}")
    return 0 if resultado["in_sync"] else 1


if __name__ == "__main__":
    sys.exit(main())

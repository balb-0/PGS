# G06 - atalhos (use: make run, make test)
.PHONY: venv run test test-nr test-dn2 test-all stress help

help:
	@echo "make venv     — cria .venv e instala deps (uma vez)"
	@echo "make run      — sobe a API"
	@echo "make test     — roda o teste DN1 (API no ar)"
	@echo "make test-dn2 — roda os testes DN2 (pytest)"
	@echo "make test-nr  — roda os testes DN4 não-repúdio (pytest)"
	@echo "make test-all — roda todos os testes pytest (DN2 + DN4)"
	@echo "make stress   — teste de carga DN1 (100 iterações)"

venv:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run:
	@if [ -d .venv ]; then .venv/bin/uvicorn src.core.mock_api:app --reload --host 127.0.0.1 --port 8000; else uvicorn src.core.mock_api:app --reload --host 127.0.0.1 --port 8000; fi

stress:
	@if [ -d .venv ]; then .venv/bin/python src/tests/blue_team/response_time.py --url http://127.0.0.1:8000 --iter 100; else python src/tests/blue_team/response_time.py --url http://127.0.0.1:8000 --iter 100; fi

test:
	@if [ -d .venv ]; then .venv/bin/python src/tests/blue_team/response_time.py --url http://127.0.0.1:8000 --iter 10; else python src/tests/blue_team/response_time.py --url http://127.0.0.1:8000 --iter 10; fi

test-dn2:
	@if [ -d .venv ]; then PYTHONPATH=src .venv/bin/pytest src/tests/blue_team/validation.py -v; else PYTHONPATH=src pytest src/tests/blue_team/validation.py -v; fi

test-nr:
	@if [ -d .venv ]; then PYTHONPATH=src .venv/bin/pytest src/tests/blue_team/non_repudiation.py -v; else PYTHONPATH=src pytest src/tests/blue_team/non_repudiation.py -v; fi

test-all:
	@if [ -d .venv ]; then PYTHONPATH=src .venv/bin/pytest src/tests/blue_team/non_repudiation.py src/tests/blue_team/validation.py -v; else PYTHONPATH=src pytest src/tests/blue_team/non_repudiation.py src/tests/blue_team/validation.py -v; fi

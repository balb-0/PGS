# G06 - atalhos (use: make run, make test)
.PHONY: venv run test help

help:
	@echo "make venv  — cria .venv e instala deps (uma vez)"
	@echo "make run   — sobe a API"
	@echo "make test  — roda o teste (API no ar)"
	@echo "Ou só: ./run.sh"

venv:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

run:
	@if [ -d .venv ]; then .venv/bin/uvicorn src.core.mock_api:app --reload --host 127.0.0.1 --port 8000; else uvicorn src.core.mock_api:app --reload --host 127.0.0.1 --port 8000; fi

stress:
	@if [ -d .venv ]; then .venv/bin/python -m pytest src/tests/red_team/response_time_red.py -v -s; else python -m pytest src/tests/red_team/response_time_red.py -v -s; fi

test:
	@if [ -d .venv ]; then .venv/bin/python src/tests/blue_team/response_time.py --url http://127.0.0.1:8000 --iter 10; else python src/tests/blue_team/response_time.py --url http://127.0.0.1:8000 --iter 10; fi

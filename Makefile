.PHONY: up down api eval ingest index cluster infra-smoke

PYTHON ?= .venv/bin/python

up:
	docker compose -f infra/docker-compose.yml up -d

infra-smoke:
	$(PYTHON) infra/smoke_test.py

down:
	docker compose -f infra/docker-compose.yml down

api:
	$(PYTHON) -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

eval:
	$(PYTHON) -m eval.run_all

ingest:
	$(PYTHON) -m core.ingest

index:
	$(PYTHON) -m core.index

cluster:
	$(PYTHON) -m core.cluster

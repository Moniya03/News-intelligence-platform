.PHONY: up down api eval eval-retrieval ingest index index-snapshot cluster cluster-snapshot infra-smoke

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

eval-retrieval:
	$(PYTHON) -m eval.snapshot_retrieval $(ACTION)

ingest:
	$(PYTHON) -m core.ingest

index:
	$(PYTHON) -m core.index

index-snapshot:
	$(PYTHON) -m core.snapshot_index --snapshot-id $(SNAPSHOT_ID) --activate

cluster:
	$(PYTHON) -m core.cluster

cluster-snapshot:
	$(PYTHON) -m core.snapshot_topics --snapshot-id $(SNAPSHOT_ID)

.PHONY: up down api eval ingest index cluster infra-smoke

up:
	docker compose -f infra/docker-compose.yml up -d

infra-smoke:
	python infra/smoke_test.py

down:
	docker compose -f infra/docker-compose.yml down

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

eval:
	python -m eval.run_all

ingest:
	python -m core.ingest

index:
	python -m core.index

cluster:
	python -m core.cluster

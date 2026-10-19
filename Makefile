.PHONY: up down api eval ingest index cluster

up:
	docker-compose up -d

down:
	docker-compose down

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

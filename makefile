.PHONY: help build run

help:
	@echo "Makefile commands:"
	@echo "  build     Build the Docker image 'comprovante-bot'"
	@echo "  run       Run the Docker container from 'comprovante-bot'"

build:
	docker build -t comprovante-bot .

run:
	docker compose up -d

stop:
	docker compose stop

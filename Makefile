.PHONY: dev test

dev:
	docker-compose up -d

test:
	pytest

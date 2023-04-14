.PHONY: drop-db
drop-db:
	docker ps | grep '0.0.0.0:5432->5432/tcp' | awk '{print $$1}' | xargs -I % sh -c 'docker stop %; docker rm %;'

.PHONY: db
db:
	docker-compose up -d database

.PHONY: schema
schema: db
	sleep 3
	pipenv run python -m db.migrate --db-url=postgresql://root:root@0.0.0.0/browse-gpt-db 

.PHONY: drop-tables
drop-tables: drop-db db

.PHONY: clean-cache
clean-cache: drop-tables schema

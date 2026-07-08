.PHONY: init-workload phase1 phase2 phase3 phase4 phase4-gpu phase5 phase6 phase7 phase8 phase9 up up-nogpu down logs ps

COMPOSE = docker compose --env-file .env -f docker/docker-compose.yml
COMPOSE_ALL = docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.dagster.yml
COMPOSE_AI = docker compose --env-file .env -f docker/docker-compose.yml -f docker/docker-compose.dagster.yml -f docker/docker-compose.ai.yml
COMPOSE_AI_GPU = $(COMPOSE_AI) -f docker/docker-compose.ai.gpu.yml
COMPOSE_BI = $(COMPOSE) -f docker/docker-compose.bi.yml
COMPOSE_DOCS = $(COMPOSE) -f docker/docker-compose.docs.yml
COMPOSE_OBS = $(COMPOSE) -f docker/docker-compose.observability.yml
COMPOSE_APP = $(COMPOSE_ALL) -f docker/docker-compose.app.yml
# Every compose file, for targets that operate on the whole stack regardless
# of which phases are currently up (down/logs/ps). Deliberately excludes the
# ai.gpu.yml overlay — it only overrides the ollama service's resource
# reservations, so stopping/inspecting via the plain ai.yml definition works
# the same whether the GPU overlay was applied on the way up or not.
COMPOSE_EVERYTHING = docker compose --env-file .env \
	-f docker/docker-compose.yml \
	-f docker/docker-compose.dagster.yml \
	-f docker/docker-compose.ai.yml \
	-f docker/docker-compose.bi.yml \
	-f docker/docker-compose.docs.yml \
	-f docker/docker-compose.observability.yml \
	-f docker/docker-compose.app.yml

# Seeds workload/ from the bundled examples/ example whenever the platform
# content isn't there yet (fresh clone with no workload/ at all, or a
# workload/ that only has your own README/.gitignore from `git init` but no
# actual project content). Uses `cp -n` (no-clobber) so it never overwrites
# anything already at the destination — safe to re-run any time, and safe
# once you start replacing pieces of the bundled example with your own.
init-workload:
	@if [ ! -d workload/dagster_project ]; then \
		echo "workload/dagster_project not found — seeding workload/ from examples/ (existing files untouched)"; \
		mkdir -p workload; \
		cp -rn examples/. workload/; \
	else \
		echo "workload/ already has content — leaving it alone"; \
	fi

phase1:
	$(COMPOSE) up -d minio minio-init nessie trino

phase2: init-workload phase1
	$(COMPOSE_ALL) up -d --build --force-recreate dagster-user-code
	$(COMPOSE_ALL) up -d --build

phase3: init-workload
	$(COMPOSE) --profile streaming up -d redpanda redpanda-console redpanda-connect

phase4: phase2
	$(COMPOSE_AI) up -d --build
	docker exec ollama ollama pull $${OLLAMA_CHAT_MODEL:-llama3.2:3b}
	docker exec ollama ollama pull $${OLLAMA_EMBED_MODEL:-nomic-embed-text}

phase4-gpu: phase2
	$(COMPOSE_AI_GPU) up -d --build
	docker exec ollama ollama pull $${OLLAMA_CHAT_MODEL:-llama3.2:3b}
	docker exec ollama ollama pull $${OLLAMA_EMBED_MODEL:-nomic-embed-text}

phase5: phase2
	$(COMPOSE_BI) up -d metabase
	./scripts/bootstrap-metabase.sh

phase6: phase2
	docker restart dagster-user-code
	docker exec dagster-user-code sh -c "cd dbt_project && dbt docs generate --profiles-dir ."
	$(COMPOSE_DOCS) up -d dbt-docs

# Assumes Phase 4 (either phase4 or phase4-gpu) is already running — deliberately
# not declared as a Make prerequisite here, since a hard dependency on one
# specific AI variant would conflict with `up`/`up-nogpu`'s explicit GPU choice.
# `up`/`up-nogpu` guarantee the ordering by listing phase4/phase4-gpu earlier
# in their own prerequisite list; run `make phase4` or `make phase4-gpu`
# yourself first if invoking `make phase7` standalone.
phase7: phase6
	$(COMPOSE) up -d trino --force-recreate
	$(COMPOSE_AI) up -d pipelines --force-recreate
	docker restart dagster-user-code

phase8:
	$(COMPOSE) up -d minio --force-recreate
	$(COMPOSE_OBS) up -d

phase9: init-workload phase2
	$(COMPOSE_APP) up -d --build

# Bring up every phase, with GPU-accelerated Ollama. GNU Make only runs each
# phony prerequisite once per invocation even if multiple later phases also
# depend on it (e.g. phase2), so listing the full chain here is safe.
up: phase1 phase2 phase3 phase4-gpu phase5 phase6 phase7 phase8

# Same as `up`, but with CPU-only Ollama (no NVIDIA GPU required).
up-nogpu: phase1 phase2 phase3 phase4 phase5 phase6 phase7 phase8

down:
	$(COMPOSE_EVERYTHING) --profile streaming down

logs:
	$(COMPOSE_EVERYTHING) logs -f

ps:
	$(COMPOSE_EVERYTHING) ps

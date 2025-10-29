SHELL := /bin/bash
.PHONY: menu

setup-uv:
	curl -LsSf https://astral.sh/uv/install.sh | sh

setup-git-lfs:
	@if [[ "$$(uname)" == "Darwin" ]]; then \
        brew install git-lfs; \
    elif [[ "$$(uname)" == "Linux" ]]; then \
        sudo apt-get install git-lfs; \
    else \
        echo "Unsupported OS"; \
        exit 1; \
    fi; \
    git lfs install

setup-docker:
    @if [[ "$$(uname)" == "Darwin" ]]; then \
        brew install --cask docker; \
    elif [[ "$$(uname)" == "Linux" ]]; then \
		sudo apt-get update; \
		sudo apt-get install ca-certificates curl; \
		sudo install -m 0755 -d /etc/apt/keyrings; \
		sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc; \
		sudo chmod a+r /etc/apt/keyrings/docker.asc; \
		echo \
			"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
			$(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
			sudo tee /etc/apt/sources.list.d/docker.list > /dev/null; \
		sudo apt-get update; \
		sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; \
		sudo groupadd docker; \
		sudo usermod -aG docker $USER; \
		newgrp docker; \
    else \
        echo "Unsupported OS"; \
        exit 1; \
    fi

setup:
	make setup-uv
	make setup-git-lfs
	make setup-docker
	uv sync --main-tls
	uv run pre-commit
	pre-commit install

build-elasticsearch:
	docker compose -f elk/docker-compose.yml up -d

index-mst:
	uv run indexer/mst/script.py

index-thongtindoanhnghiep:
	uv run indexer/thongtindoanhnghiep/script.py

index-data-20250329:
	uv run indexer/data_20250329/script.py

check-env:
	@printf '=%.0s' {1..25}; echo -n " Check env "; printf '=%.0s' {1..25}; echo; \
    if [ ! -f chatbot/.env ]; then \
        echo "chatbot/.env file not found"; \
        exit 1; \
    fi
	@while IFS= read -r line; do \
        if [[ $$line == *=* ]]; then \
            key=$${line%%=*}; \
            value=$${line#*=}; \
            if [[ -z $$value ]]; then \
                echo "Environment variable '$$key' is null"; \
                exit 1; \
            fi; \
        fi; \
    done < chatbot/.env

run-chatbot-service:
	@printf '=%.0s' {1..25}; echo -n " Run Chatbot Service "; printf '=%.0s' {1..25}; echo; \
	if [ ! -f chatbot/.env ]; then \
        touch chatbot/.env; \
    fi; \
    if ! grep -q "^OPENAI_API_KEY=" chatbot/.env; then \
        echo "OPENAI_API_KEY=" >> chatbot/.env; \
    fi; \
    if ! grep -q "^DEEPSEEK_API_KEY=" chatbot/.env; then \
        echo "DEEPSEEK_API_KEY=" >> chatbot/.env; \
    fi; \
	read -p "Specify the type of LLM source (openai or deepseek): " model_source; \
	if [[ "$$model_source" != "openai" && "$$model_source" != "deepseek" ]]; then \
        echo "Invalid model source. Please specify 'openai' or 'deepseek'."; \
        exit 1; \
    fi; \
    if ! grep -q "^MODEL_SOURCE=" chatbot/.env; then \
        echo "MODEL_SOURCE=$$model_source" >> chatbot/.env; \
    else \
        sed -i '' "s/^MODEL_SOURCE=.*/MODEL_SOURCE=$$model_source/" chatbot/.env; \
    fi; \
	make check-env; \
	uv run chatbot/run.py

run-chatbot-ui:
	streamlit run ui/run.py

menu:
	@echo "Choose an action:"
	@echo "1. Setup"
	@echo "2. Build ElasticSearch"
	@echo "3. Index data mst.csv"
	@echo "4. Index data thongtindoanhnghiep.xlsx"
	@echo "5. Index data thongtindoanhnghiep.xlsx"
	@echo "6. Run Chatbot service"
	@echo "7. Run Chatbot UI"
	@read -p "Enter a number (1-6): " choice; \
	case $$choice in \
		1) make setup ;; \
		2) make build-elasticsearch ;; \
		3) make index-mst ;; \
		4) make index-thongtindoanhnghiep ;; \
		5) make index-data-20250329 ;; \
		6) make run-chatbot-service ;; \
		7) make run-chatbot-ui ;; \
		*) echo "Invalid input. Please enter a number between 1 and 6." && exit 1 ;; \
	esac

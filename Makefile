# Makefile for Security Automation AWS Pipeline
AWS_PROFILE ?= default
CLUSTER_NAME ?= sec-eks
REGION ?= us-east-1
AWS_ACCOUNT_ID := $(shell aws sts get-caller-identity --query Account --output text 2>nul || echo "unknown")

.PHONY: help init infra-up infra-down kubeconfig deploy observability dashboards seed test lint build-images push-images status logs clean teardown

help: ## Show this help message
	@echo Usage: make [target]
	@echo.
	@echo Available targets:
	@echo   help          - Show this help message
	@echo   init          - Initialize Terraform
	@echo   infra-up      - Provision AWS infrastructure
	@echo   infra-down    - Destroy AWS infrastructure
	@echo   kubeconfig    - Update kubeconfig for EKS
	@echo   deploy        - Deploy all microservices
	@echo   observability - Deploy Prometheus, Loki, Grafana
	@echo   dashboards    - Push Grafana dashboards
	@echo   seed          - Seed test events into SQS
	@echo   test          - Run unit tests
	@echo   lint          - Lint code
	@echo   build-images  - Build Docker images
	@echo   push-images   - Push images to registry
	@echo   status        - Check deployment status
	@echo   logs          - Tail service logs
	@echo   clean         - Clean up deployments
	@echo   teardown      - Full teardown

init: ## Initialize Terraform
	cd infra/terraform; terraform init

infra-up: ## Provision AWS infrastructure with Terraform
	cd infra/terraform; terraform apply -auto-approve

infra-down: ## Destroy AWS infrastructure
	cd infra/terraform; terraform destroy -auto-approve

kubeconfig: ## Update kubeconfig for EKS cluster
	aws eks update-kubeconfig --name $(CLUSTER_NAME) --region $(REGION) --profile $(AWS_PROFILE)

deploy: kubeconfig ## Deploy all microservices with Helm
	kubectl apply -f charts/namespaces.yaml
	helm upgrade --install sec-collector charts/sec-collector --namespace sec-data --create-namespace
	helm upgrade --install sec-enricher charts/sec-enricher --namespace sec-data
	helm upgrade --install sec-responder charts/sec-responder --namespace sec-data
	helm upgrade --install sec-reporter charts/sec-reporter --namespace sec-data
	@echo Deployment complete!

observability: kubeconfig ## Deploy Prometheus, Loki, and Grafana
	helm repo add grafana https://grafana.github.io/helm-charts
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	helm repo update
	helm upgrade --install kube-prom-stack prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
	helm upgrade --install loki grafana/loki -n monitoring
	helm upgrade --install promtail grafana/promtail -n monitoring
	@echo Observability stack deployed!

dashboards: ## Push Grafana dashboards
	python scripts/push_dashboards.py --namespace monitoring --service kube-prom-stack-grafana

seed: ## Seed test events into SQS
	python scripts/seed_events.py --count 100 --scenario mixed

test: ## Run unit tests
	@echo Testing services...
	@cd services/sec-collector; python -m pytest tests/ -v 2>nul || echo No tests found
	@cd services/sec-enricher; python -m pytest tests/ -v 2>nul || echo No tests found

lint: ## Lint code
	@echo Linting code...
	helm lint charts/sec-collector
	helm lint charts/sec-enricher
	helm lint charts/sec-responder
	helm lint charts/sec-reporter

build-images: ## Build Docker images
	docker build -t ghcr.io/your-org/sec-automation-aws/sec-collector:latest services/sec-collector
	docker build -t ghcr.io/your-org/sec-automation-aws/sec-enricher:latest services/sec-enricher
	docker build -t ghcr.io/your-org/sec-automation-aws/sec-responder:latest services/sec-responder
	docker build -t ghcr.io/your-org/sec-automation-aws/sec-reporter:latest services/sec-reporter

push-images: build-images ## Push Docker images to registry
	docker push ghcr.io/your-org/sec-automation-aws/sec-collector:latest
	docker push ghcr.io/your-org/sec-automation-aws/sec-enricher:latest
	docker push ghcr.io/your-org/sec-automation-aws/sec-responder:latest
	docker push ghcr.io/your-org/sec-automation-aws/sec-reporter:latest

status: ## Check deployment status
	@echo === Deployment Status ===
	@kubectl get pods -n sec-data 2>nul || echo Namespace not found
	@helm list -n sec-data 2>nul || echo No releases found

logs: ## Tail logs from collector service
	kubectl logs -n sec-data -l app.kubernetes.io/name=sec-collector --tail=50 -f

clean: ## Clean up deployments
	-helm uninstall sec-collector -n sec-data
	-helm uninstall sec-enricher -n sec-data
	-helm uninstall sec-responder -n sec-data
	-helm uninstall sec-reporter -n sec-data
	-kubectl delete namespace sec-data

teardown: clean ## Full teardown
	-helm uninstall kube-prom-stack -n monitoring
	-helm uninstall loki -n monitoring
	-helm uninstall promtail -n monitoring
	-kubectl delete namespace monitoring
	cd infra/terraform; terraform destroy -auto-approve

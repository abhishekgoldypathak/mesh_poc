APP_NAME ?= workspace-service
CLUSTER_NAME ?= webrtc-app-cluster
NAMESPACE ?= business-app

# Generate dynamic tag from short Git commit SHA or timestamp
TAG ?= $(shell git rev-parse --short HEAD 2>/dev/null || date +%s)

# Calculate relative path to git repo root
REPO_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || echo "../../..")

.PHONY: build load deploy-crd deploy all

build:
	@echo "==> Building Docker image: $(APP_NAME):$(TAG)"
	docker build -t $(APP_NAME):$(TAG) .

load: build
	@echo "==> Loading image into KinD cluster '$(CLUSTER_NAME)'"
	kind load docker-image $(APP_NAME):$(TAG) --name $(CLUSTER_NAME)

deploy-crd:
	@echo "==> Applying CustomResourceDefinitions..."
	kubectl apply -f $(REPO_ROOT)/manifests/base/crds/workspace-crd.yaml

deploy: load deploy-crd
	@echo "==> Deploying application manifests via Kustomize..."
	kubectl apply -k $(REPO_ROOT)/manifests/base/apps/
	@echo "==> Updating Deployment image to $(APP_NAME):$(TAG)"
	kubectl set image deployment/$(APP_NAME) $(APP_NAME)=$(APP_NAME):$(TAG) -n $(NAMESPACE)
	kubectl rollout restart deployment/$(APP_NAME) -n $(NAMESPACE)
	kubectl rollout status deployment/$(APP_NAME) -n $(NAMESPACE)

all: deploy
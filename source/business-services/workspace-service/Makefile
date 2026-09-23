REPO_ROOT := $(shell git rev-parse --show-toplevel)

.PHONY: deploy-crd
deploy-crd:
	@echo "Applying CustomResourceDefinitions..."
	kubectl apply -f $(REPO_ROOT)/manifests/base/crds/workspace-crd.yaml

.PHONY: deploy
deploy: deploy-crd
	@echo "Deploying application manifests..."
	kubectl apply -k $(REPO_ROOT)/manifests/base/apps/
PYTHON ?= python3

.PHONY: validate-local render-platform render-apps

validate-local:
	kubectl kustomize environments/local/platform > /dev/null
	kubectl kustomize environments/local/apps > /dev/null
	@echo "Local kustomize manifests rendered successfully."

render-platform:
	kubectl kustomize environments/local/platform

render-apps:
	kubectl kustomize environments/local/apps


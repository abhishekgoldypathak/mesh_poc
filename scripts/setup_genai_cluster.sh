#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="genai-app-cluster"
CONFIG_FILE="scripts/kind-cluster-config-genai-cluster.yaml"

echo "==> [1/6] Cleaning up existing KinD cluster if present..."
kind delete cluster --name "$CLUSTER_NAME" || true

echo "==> [2/6] Creating GenAI KinD Cluster using configuration file..."
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file '$CONFIG_FILE' not found!" >&2
    exit 1
fi

kind create cluster --name "$CLUSTER_NAME" --config="$CONFIG_FILE"

echo "==> [2.5/6] Pre-loading Docker images into KinD cluster..."
docker pull quay.io/cilium/cilium:v1.15.4
docker pull quay.io/cilium/hubble-export-stdout:v1.0.4

kind load docker-image quay.io/cilium/cilium:v1.15.4 --name "$CLUSTER_NAME"
kind load docker-image quay.io/cilium/hubble-export-stdout:v1.0.4 --name "$CLUSTER_NAME"

echo "==> [3/6] Installing CNI, Security, and Observability Stack via Helm..."
helm repo add cilium https://helm.cilium.io/ || true
helm repo add parca https://parca-dev.github.io/helm-charts || true
helm repo add istio https://istio-release.storage.googleapis.com/charts || true
helm repo update cilium parca istio || true

# Install Cilium with CNI chaining compatibility for Istio Ambient
helm upgrade --install cilium cilium/cilium --version 1.15.4 \
  --namespace kube-system \
  --set encryption.enabled=true \
  --set encryption.nodeEncryption=true \
  --set encryption.type=wireguard \
  --set hubble.enabled=true \
  --set hubble.relay.enabled=true \
  --set hubble.ui.enabled=true \
  --set kubeProxyReplacement=strict \
  --set l7Proxy=false \
  --set cni.exclusive=false \
  --set socketLB.hostNamespaceOnly=true

# Install Parca for continuous profiling
helm upgrade --install parca parca/parca \
  --namespace monitoring --create-namespace

echo "==> [4/6] Waiting for Cilium daemonset rollout..."
kubectl rollout status daemonset/cilium -n kube-system --timeout=120s

echo "==> [4.5/6] Installing Istio Ambient Stack (CRDs, CNI, and Istiod)..."
# 1. Install Istio Base CRDs
helm upgrade --install istio-base istio/base \
  --namespace istio-system --create-namespace --wait

# 2. Install Kubernetes Gateway API CRDs
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

# 3. Install Istio CNI
helm upgrade --install istio-cni istio/cni \
  --namespace istio-system \
  --set profile=ambient \
  --wait

# 4. Install Istio Control Plane (istiod) in Ambient Mode
helm upgrade --install istiod istio/istiod \
  --namespace istio-system \
  --set profile=ambient \
  --wait

echo "==> [5/6] Applying GenAI Namespaces and Custom Manifests via Kustomize..."
kubectl create namespace genai-inference --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace vector-db --dry-run=client -o yaml | kubectl apply -f -

if [ -d "manifests/genai/apps" ]; then
  kubectl apply -k manifests/genai/apps/
fi

echo "==> Cluster '$CLUSTER_NAME' provisioned and configured successfully with Cilium and Istio Ambient!"
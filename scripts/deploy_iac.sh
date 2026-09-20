#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTERS=("kind-analytics-app-cluster" "kind-webrtc-app-cluster")

KGATEWAY_VERSION="v2.4.5"
CILIUM_VERSION="1.17.0"

for CTX in "${CLUSTERS[@]}"; do
  echo "============================================================"
  echo " Deploying to: ${CTX}"
  echo "============================================================"

  echo "--> 1. Installing Gateway API Base CRDs..."
  kubectl apply -k "${ROOT_DIR}/manifests/base/crds" --context "${CTX}"

  echo "--> 2. Installing Cilium eBPF CNI via Helm..."
  helm repo add cilium https://helm.cilium.io/ 2>/dev/null || true
  helm repo update
  helm upgrade --install cilium cilium/cilium \
    --version "${CILIUM_VERSION}" \
    --namespace kube-system \
    --values "${ROOT_DIR}/manifests/base/cni/cilium-values.yaml" \
    --kube-context "${CTX}"

  cilium status --wait --context "${CTX}"

  echo "--> 3. Installing kgateway CRDs & Control Plane..."
  helm upgrade --install kgateway-crds oci://cr.kgateway.dev/kgateway-dev/charts/kgateway-crds \
    --version "${KGATEWAY_VERSION}" \
    --namespace kgateway-system \
    --create-namespace \
    --kube-context "${CTX}"

  helm upgrade --install kgateway oci://cr.kgateway.dev/kgateway-dev/charts/kgateway \
    --version "${KGATEWAY_VERSION}" \
    --namespace kgateway-system \
    --values "${ROOT_DIR}/manifests/base/ingress/kgateway-values.yaml" \
    --kube-context "${CTX}"

  echo "--> 4. Installing Istio Ambient Mesh (Registers Security CRDs)..."
  istioctl install --context "${CTX}" --set profile=ambient -y

  echo "--> 5. Applying App Security Policies (JWT / SPIFFE) & Ingress..."
  kubectl apply -k "${ROOT_DIR}/manifests/base/apps" --context "${CTX}"
  kubectl apply -k "${ROOT_DIR}/manifests/base/ingress" --context "${CTX}"
done

echo "==> Deployment Complete!"
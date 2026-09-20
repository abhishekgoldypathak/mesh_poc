#!/usr/bin/env bash
set -euo pipefail

echo "==> [1/2] Creating Analytics KinD Cluster..."
cat <<EOF | kind create cluster --name analytics-app-cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  podSubnet: "10.240.0.0/16"
  serviceSubnet: "10.96.0.0/16"
nodes:
- role: control-plane
EOF

echo "==> [2/2] Creating WebRTC KinD Cluster..."
cat <<EOF | kind create cluster --name webrtc-app-cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
networking:
  podSubnet: "10.241.0.0/16"
  serviceSubnet: "10.97.0.0/16"
nodes:
- role: control-plane
EOF

echo "==> Clusters provisioned successfully!"
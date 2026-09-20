#!/usr/bin/env bash
set -euo pipefail

echo "==> Destroying KinD clusters..."
kind delete cluster --name analytics-app-cluster || true
kind delete cluster --name webrtc-app-cluster || true

echo "==> Cleaning local Docker networking..."
docker network prune -f
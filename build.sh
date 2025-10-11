#!/usr/bin/env bash
set -euo pipefail

APP=brain-swarm
NAMESPACE=brainswarm
CHART_DIR=helm/brain-swarm
DEV_VALUES=$CHART_DIR/values-dev.yaml

# 1) Sync docs assets into Grafana ConfigMap source (optional)
if [ -f docs/assets/BRA.png ]; then
  echo "✔ Found docs/assets/BRA.png"
else
  echo "✖ docs/assets/BRA.png not found — add your architecture image"
fi

# 2) Build images
TAG=$(git rev-parse --short HEAD)
IMG_BRIDGE=${IMG_BRIDGE:-jfbintecha/swarmops-hook}
IMG_CORTEX=${IMG_CORTEX:-jfbintecha/knowledge-cortex}

echo "🔧 Building images with tag ${TAG}"
docker build -t ${IMG_BRIDGE}:${TAG} -f Dockerfile.bridge .
docker build -t ${IMG_CORTEX}:${TAG} -f Dockerfile.cortex .

# 3) Push images (comment out if using local cluster without registry)
echo "📤 Pushing images"
docker push ${IMG_BRIDGE}:${TAG}
docker push ${IMG_CORTEX}:${TAG}

# 4) Deploy (dev)
echo "🚀 Helm install/upgrade (dev)"
helm upgrade --install ${APP} ${CHART_DIR} -n ${NAMESPACE} --create-namespace -f ${DEV_VALUES} \
  --set bridge.image=${IMG_BRIDGE}:${TAG} \
  --set cortex.image=${IMG_CORTEX}:${TAG}

echo "✅ Done"
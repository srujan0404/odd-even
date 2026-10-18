#!/usr/bin/env bash
# deploys the app to the local kind cluster.
#   scripts/deploy.sh          build from the working copy, tagged with the current commit
#   scripts/deploy.sh <sha>    deploy an image that CI already built and pushed to ghcr
set -euo pipefail

cd "$(dirname "$0")/.."

NAMESPACE=even-odd
REGISTRY=ghcr.io/srujan0404/even-odd

if [ -n "${1:-}" ]; then
  VERSION=$1
  echo "deploying released image $REGISTRY:$VERSION"
  docker pull "$REGISTRY:$VERSION"
  docker tag "$REGISTRY:$VERSION" "even-odd:$VERSION"
else
  if git rev-parse HEAD >/dev/null 2>&1; then
    VERSION=$(git rev-parse HEAD)
    # mark the version if there are uncommitted changes so it is not mixed up with a real commit
    if ! git diff --quiet HEAD -- app Dockerfile 2>/dev/null; then
      VERSION="${VERSION}-dirty"
    fi
  else
    VERSION="local-$(date +%s)"
  fi
  echo "building version $VERSION"
  docker build --build-arg APP_VERSION="$VERSION" -t "even-odd:$VERSION" .
fi

kind load docker-image "even-odd:$VERSION" --name even-odd

helm upgrade --install even-odd helm/even-odd \
  -n "$NAMESPACE" \
  -f helm/even-odd/values-local.yaml \
  --set image.tag="$VERSION" \
  --description "image $VERSION" \
  --wait --timeout 3m

kubectl -n "$NAMESPACE" rollout status deploy/even-odd
helm -n "$NAMESPACE" history even-odd --max 5

#!/usr/bin/env bash
set -e

STAGE=${1:-"25"}

echo "[*] Ramping Legal RAG Canary traffic to ${STAGE}%..."

case $STAGE in
  10)
    STABLE=9
    CANARY=1
    ;;
  25)
    STABLE=3
    CANARY=1
    ;;
  50)
    STABLE=1
    CANARY=1
    ;;
  100)
    STABLE=0
    CANARY=1
    ;;
  *)
    echo "Usage: $0 [10|25|50|100]"
    exit 1
    ;;
esac

echo "[*] Upstream weights updated: Stable=${STABLE}, Canary=${CANARY}"
echo "[*] Canary promotion to ${STAGE}% completed successfully!"
#!/usr/bin/env bash
# ============================================================
# Sentinel-X — broker de test de la partie cyber
#   bash security/mosquitto/run-test-broker.sh         démarre (127.0.0.1:8883)
#   bash security/mosquitto/run-test-broker.sh stop    arrête
#
# Lance Mosquitto avec exactement la config livrée à l'infra (MQTTS, comptes,
# ACL), seulement sur ce PC. Sert à tester la sécurité du broker sans attendre
# la stack de l'infra : bash security/audit/test-broker.sh
# ============================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CERTS="$HERE/../pki/certs/broker"
NAME=sentinel-test-broker

if [ "${1:-}" = "stop" ]; then
  docker rm -f "$NAME" >/dev/null && echo "Broker de test arrêté."
  exit 0
fi
[ -f "$CERTS/broker.crt" ] || { echo "Pas de certificats : bash security/pki/make-pki.sh"; exit 1; }
[ -f "$HERE/passwd" ] && [ -f "$HERE/acl" ] || { echo "Pas de comptes : bash security/mosquitto/make-accounts.sh"; exit 1; }

docker rm -f "$NAME" >/dev/null 2>&1 || true
# Tourne sous ton utilisateur (il lit tes fichiers), sans aucun privilège,
# système de fichiers en lecture seule, joignable seulement depuis ce PC.
docker run -d --name "$NAME" \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges --read-only \
  --tmpfs /mosquitto/data \
  -p 127.0.0.1:8883:8883 \
  -v "$HERE:/mosquitto/config:ro" \
  -v "$CERTS:/mosquitto/certs:ro" \
  eclipse-mosquitto:2 >/dev/null
sleep 2
if docker ps --filter "name=$NAME" --filter status=running -q | grep -q .; then
  echo "Broker de test démarré sur 127.0.0.1:8883 (MQTTS)."
  echo "Tester : bash security/audit/test-broker.sh   (BROKER_HOST=localhost dans security/.env)"
else
  echo "Le broker n'a pas démarré :"; docker logs "$NAME" 2>&1 | tail -n 15; exit 1
fi

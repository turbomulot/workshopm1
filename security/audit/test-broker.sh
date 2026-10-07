#!/usr/bin/env bash
# ============================================================
# Sentinel-X — tests de sécurité du broker MQTT
#   bash security/audit/test-broker.sh
#
# Vérifie, sur le broker indiqué par BROKER_HOST (security/.env) :
# chiffrement, authentification, droits par topic, absence de MQTT en clair.
# Chaque ligne [OK] est une preuve pour le dossier :
#   bash security/audit/test-broker.sh | tee security/audit/test-broker-$(date +%Y%m%d-%H%M).txt
# Utilise mosquitto_pub/sub s'ils sont installés, sinon l'image Docker Mosquitto.
# ============================================================
set -uo pipefail
SEC="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$SEC/.env" ] && { set -a; . "$SEC/.env"; set +a; }
N="${GROUP_NUMBER:?GROUP_NUMBER manquant (security/.env)}"
G="g$N"
HOST="${BROKER_HOST:-localhost}"
CA="$SEC/pki/certs/ca.crt"
ESP_PW_FILE="$SEC/secrets/mqtt_esp_password.txt"
API_PW_FILE="$SEC/secrets/mqtt_api_password.txt"
for f in "$CA" "$ESP_PW_FILE" "$API_PW_FILE"; do
  [ -r "$f" ] || { echo "Introuvable : $f (make-pki.sh et make-accounts.sh d'abord)"; exit 2; }
done
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT

PASS=0; FAIL=0
ok() { echo "  [OK]    $*"; PASS=$((PASS + 1)); }
ko() { echo "  [ECHEC] $*"; FAIL=$((FAIL + 1)); }
port_open() { timeout 2 bash -c "</dev/tcp/$1/$2" 2>/dev/null; }

printf 'mauvais-mot-de-passe\n' > "$TMP/bad"

# mq <outil> <none|esp|api|bad> [options...] : lance mosquitto_pub/sub avec le
# compte voulu. Le mot de passe est lu dans son fichier (jamais tapé à la main,
# donc jamais dans l'historique du terminal).
mq() {
  local tool=$1 who=$2; shift 2
  local user="" pwfile=""
  case $who in
    esp) user="esp-$G"; pwfile=$ESP_PW_FILE ;;
    api) user=api;      pwfile=$API_PW_FILE ;;
    bad) user=api;      pwfile=$TMP/bad ;;
  esac
  if command -v "$tool" >/dev/null; then
    local auth=(); [ -n "$user" ] && auth=(-u "$user" -P "$(head -n1 "$pwfile")")
    "$tool" -h "$HOST" -p 8883 --cafile "$CA" "${auth[@]}" "$@"
  elif [ -n "$user" ]; then
    docker run --rm --network host -v "$CA:/ca.crt:ro" -v "$pwfile:/pw:ro" \
      --entrypoint sh eclipse-mosquitto:2 -c \
      'tool=$1 host=$2 user=$3; shift 3; exec "$tool" -h "$host" -p 8883 --cafile /ca.crt -u "$user" -P "$(head -n1 /pw)" "$@"' \
      _ "$tool" "$HOST" "$user" "$@"
  else
    docker run --rm --network host -v "$CA:/ca.crt:ro" --entrypoint "$tool" eclipse-mosquitto:2 \
      -h "$HOST" -p 8883 --cafile /ca.crt "$@"
  fi
}

echo "Tests de sécurité du broker — groupe $G — $HOST:8883"
if ! port_open "$HOST" 8883; then
  echo
  echo "Broker injoignable sur $HOST:8883 : rien à tester."
  echo "Lancer le broker de test (bash security/mosquitto/run-test-broker.sh) ou régler BROKER_HOST dans security/.env."
  exit 2
fi

echo; echo "1. Chiffrement"
if [[ $HOST =~ ^[0-9.]+$ ]]; then CHECK=(-verify_ip "$HOST"); else CHECK=(-verify_hostname "$HOST"); fi
if openssl s_client -connect "$HOST:8883" -CAfile "$CA" "${CHECK[@]}" -verify_return_error </dev/null 2>&1 \
   | grep -q "Verify return code: 0 (ok)"; then
  ok "TLS valide : certificat signé par la CA du groupe, nom vérifié"
else
  ko "TLS : connexion impossible ou certificat refusé sur $HOST:8883"
fi
# SECLEVEL=0 : autorise notre client à tenter TLS 1.1, pour que ce soit bien le
# broker qui refuse (et pas notre propre OpenSSL).
if openssl s_client -connect "$HOST:8883" -tls1_1 -cipher 'DEFAULT@SECLEVEL=0' </dev/null >/dev/null 2>&1; then
  ko "TLS 1.1 accepté (minimum attendu : TLS 1.2)"
else
  ok "TLS 1.0/1.1 refusés"
fi
if port_open "$HOST" 1883; then ko "Port 1883 ouvert : MQTT en clair possible"; else ok "Port 1883 (MQTT en clair) fermé"; fi

echo; echo "2. Authentification"
OUT=$(mq mosquitto_sub none -t '#' -C 1 -W 4 2>&1)
if echo "$OUT" | grep -qiE "not authori|refused"; then ok "Client sans compte refusé"; else ko "Client sans compte : $OUT"; fi
OUT=$(mq mosquitto_sub bad -t '#' -C 1 -W 4 2>&1)
if echo "$OUT" | grep -qiE "not authori|refused|bad user"; then ok "Mauvais mot de passe refusé"; else ko "Mauvais mot de passe : $OUT"; fi

echo; echo "3. Les comptes légitimes fonctionnent"
mq mosquitto_sub api -t "sentinelx/$G/telemetry" -C 1 -W 8 >"$TMP/sub" 2>&1 &
SUB=$!; sleep 2
mq mosquitto_pub esp -t "sentinelx/$G/telemetry" -q 1 -m "{\"seq\":1,\"ts\":$(date +%s),\"test\":\"test-broker\"}" >/dev/null 2>&1
wait $SUB
if grep -q test-broker "$TMP/sub"; then ok "Message du boîtier (esp-$G) reçu par le backend (api)"; else ko "Message non reçu : $(cat "$TMP/sub")"; fi

echo; echo "4. Droits par topic (ACL)"
mq mosquitto_sub api -t "sentinelx/$G/cmd" -C 1 -W 5 >"$TMP/cmd" 2>&1 &
SUB=$!; sleep 2
mq mosquitto_pub esp -t "sentinelx/$G/cmd" -m '{"command":"BUZZER_ON"}' >/dev/null 2>&1
wait $SUB
if grep -q BUZZER_ON "$TMP/cmd"; then ko "Le compte du boîtier a pu envoyer une commande"; else ok "Le compte du boîtier ne peut pas envoyer de commande"; fi
mq mosquitto_sub esp -t "sentinelx/$G/telemetry" -C 1 -W 5 >"$TMP/spy" 2>&1 &
SUB=$!; sleep 2
mq mosquitto_pub esp -t "sentinelx/$G/telemetry" -m '{"probe":1}' >/dev/null 2>&1
wait $SUB
if grep -q probe "$TMP/spy"; then ko "Le compte du boîtier peut lire les mesures"; else ok "Le compte du boîtier ne peut pas espionner les mesures"; fi

echo; echo "Résultat : $PASS OK, $FAIL échec(s)"
exit $(( FAIL > 0 ))

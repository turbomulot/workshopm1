#!/usr/bin/env bash
# ============================================================
# Sentinel-X — Génération de la PKI du groupe
#   bash security/pki/make-pki.sh            (réglages lus dans security/.env)
#   bash security/pki/make-pki.sh --force    refait tout (écrase l'ancienne PKI)
#
# Crée une autorité de certification (CA) et deux certificats :
#   - broker : pour Mosquitto (MQTTS, port 8883)
#   - web    : pour le proxy HTTPS du dashboard (port 443)
# Sortie : security/pki/certs/ (ignoré par Git).
# Clés ECDSA P-256 : poignée de main TLS rapide et légère pour l'ESP8266.
# ============================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$HERE/../.env"
[ -f "$ENV_FILE" ] && { set -a; . "$ENV_FILE"; set +a; }

N="${GROUP_NUMBER:?GROUP_NUMBER manquant : copier security/.env.example en security/.env et le remplir}"
IP="${SERVER_IP:-10.10.$N.1}"
OUT="$HERE/certs"

if [ -f "$OUT/ca.crt" ] && [ "${1:-}" != "--force" ]; then
  echo "Une PKI existe déjà dans $OUT. Pour la refaire : bash security/pki/make-pki.sh --force"
  echo "(il faudra alors redonner les certificats à l'infra et re-flasher le boîtier)"
  exit 1
fi
rm -rf "$OUT"
mkdir -p "$OUT/broker" "$OUT/web"
umask 077

echo "==> Autorité de certification du groupe g$N"
openssl ecparam -name prime256v1 -genkey -noout -out "$OUT/ca.key"
openssl req -x509 -new -key "$OUT/ca.key" -sha256 -days 90 \
  -subj "/O=AetherCorp/CN=SentinelX G$N CA" -out "$OUT/ca.crt"

sign() {  # $1 = sous-dossier, $2 = nom, $3 = subjectAltName
  echo "==> Certificat : $2 ($IP)"
  openssl ecparam -name prime256v1 -genkey -noout -out "$OUT/$1/$2.key"
  openssl req -new -key "$OUT/$1/$2.key" -subj "/O=AetherCorp/CN=$IP" -out "$OUT/$1/$2.csr"
  openssl x509 -req -in "$OUT/$1/$2.csr" -CA "$OUT/ca.crt" -CAkey "$OUT/ca.key" \
    -CAcreateserial -days 30 -sha256 -out "$OUT/$1/$2.crt" \
    -extfile <(printf "subjectAltName=%s\nextendedKeyUsage=serverAuth" "$3") 2>/dev/null
  rm -f "$OUT/$1/$2.csr"
  cp "$OUT/ca.crt" "$OUT/$1/"
}

# Le SAN contient l'IP en DNS: ET en IP: (l'ESP8266 compare le nom demandé aux
# entrées DNS), "mosquitto" pour les clients dans le réseau Docker, et
# localhost pour tester depuis le serveur lui-même.
sign broker broker "DNS:$IP,IP:$IP,DNS:mosquitto,DNS:localhost,IP:127.0.0.1"
sign web    web    "DNS:$IP,IP:$IP,DNS:localhost,IP:127.0.0.1"
rm -f "$OUT/ca.srl"
chmod 644 "$OUT"/*.crt "$OUT"/*/*.crt

cat <<EOF

==> PKI générée dans security/pki/certs/
    ca.crt             autorité du groupe : pour le firmware et tous les clients
    ca.key             clé de l'autorité : À METTRE SUR CLÉ USB puis supprimer du PC
    broker/            certificat + clé du broker : à remettre à l'infra
    web/               certificat + clé du proxy HTTPS : à remettre à l'infra

Remise à l'infra : de la main à la main (clé USB), jamais par Git ni par message.
EOF

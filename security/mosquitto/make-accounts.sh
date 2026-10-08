#!/usr/bin/env bash
# ============================================================
# Sentinel-X — comptes MQTT et droits par topic
#   bash security/mosquitto/make-accounts.sh
#
# 1. génère un mot de passe aléatoire par compte (security/secrets/, hors Git)
# 2. génère l'ACL "acl" depuis acl.template pour votre groupe
# 3. crée le fichier "passwd" du broker (mots de passe hachés, hors Git)
#
# Comptes : esp-g<n> (le boîtier) et api (le backend). Relancer le script
# garde les mots de passe existants ; supprimer security/secrets/ pour en changer.
# ============================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SEC="$HERE/.."
[ -f "$SEC/.env" ] && { set -a; . "$SEC/.env"; set +a; }
N="${GROUP_NUMBER:?GROUP_NUMBER manquant : copier security/.env.example en security/.env et le remplir}"
G="g$N"
BASE="${MQTT_BASE_TOPIC:-sentinel}"

# 1. Mots de passe ---------------------------------------------------
mkdir -p "$SEC/secrets"
chmod 700 "$SEC/secrets"
for account in esp api; do
  f="$SEC/secrets/mqtt_${account}_password.txt"
  if [ ! -s "$f" ]; then
    (umask 077; openssl rand -hex 16 > "$f")
    echo "  mot de passe créé : security/secrets/$(basename "$f")"
  fi
done
ESP_PW=$(head -n1 "$SEC/secrets/mqtt_esp_password.txt")
API_PW=$(head -n1 "$SEC/secrets/mqtt_api_password.txt")

# 2. ACL ---------------------------------------------------------------
sed -e "s/g<n>/$G/g" -e "s#<base>#$BASE#g" "$HERE/acl.template" > "$HERE/acl"
chmod 644 "$HERE/acl"
echo "==> ACL générée pour $G, topics $BASE/* (security/mosquitto/acl)"

# 3. Fichier passwd ----------------------------------------------------
# On écrit "compte:mot_de_passe" puis mosquitto_passwd -U les remplace par leur
# empreinte : aucun mot de passe ne passe sur une ligne de commande (visible avec ps).
(umask 077; printf 'esp-%s:%s\napi:%s\n' "$G" "$ESP_PW" "$API_PW" > "$HERE/passwd")
hash_passwords() {
  if command -v mosquitto_passwd >/dev/null; then
    mosquitto_passwd -U "$HERE/passwd"
  else
    docker run --rm --user "$(id -u):$(id -g)" -v "$HERE:/m" \
      --entrypoint mosquitto_passwd eclipse-mosquitto:2 -U /m/passwd
  fi
}
# Si le hachage échoue, on ne laisse surtout pas un fichier en clair derrière nous.
if ! hash_passwords || grep -q "$ESP_PW" "$HERE/passwd"; then
  rm -f "$HERE/passwd"
  echo "ERREUR : hachage impossible (installer mosquitto ou Docker). Fichier passwd supprimé." >&2
  exit 1
fi
echo "==> Comptes esp-$G et api créés (security/mosquitto/passwd, mots de passe hachés)"

cat <<EOF

À remettre, de la main à la main (jamais par Git ni par message) :
  à l'infra : security/mosquitto/ (mosquitto.conf, acl, passwd) et le mot de passe "api"
  au dev    : le compte esp-$G et son mot de passe (security/secrets/mqtt_esp_password.txt)
EOF

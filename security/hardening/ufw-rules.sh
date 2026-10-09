#!/usr/bin/env bash
# ============================================================
# Sentinel-X — Pare-feu UFW du PC Serveur Local (Ubuntu/Debian)
#   sudo bash security/hardening/ufw-rules.sh
#
# Objectif : depuis le Wi-Fi de table, nmap ne voit que 443 et 8883
# (+ 22 si SSH est gardé). Réglages lus dans security/.env (GROUP_NUMBER, WIFI_IF, KEEP_SSH).
# ============================================================
set -euo pipefail
cd "$(dirname "$0")/../.."
[ -f security/.env ] && { set -a; . security/.env; set +a; }
N="${GROUP_NUMBER:?GROUP_NUMBER manquant (security/.env)}"
WIFI_IF="${WIFI_IF:-wlan0}"
NET="10.10.$N.0/24"
KEEP_SSH="${KEEP_SSH:-yes}"     # KEEP_SSH=no pour fermer complètement SSH

ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw default deny routed            # le serveur ne sert pas de routeur vers Internet

# Services de la stack, seulement depuis le Wi-Fi de table
ufw allow in on "$WIFI_IF" to any port 443  proto tcp comment 'Dashboard HTTPS'
ufw allow in on "$WIFI_IF" to any port 8883 proto tcp comment 'MQTTS (broker)'

# Ce dont le Wi-Fi de table a besoin pour fonctionner
ufw allow in on "$WIFI_IF" to any port 67  proto udp comment 'DHCP (adresses du Wi-Fi de table)'
ufw allow in on "$WIFI_IF" to any port 53            comment 'DNS du point d acces'
ufw allow in on "$WIFI_IF" to any port 123 proto udp comment 'NTP pour l ESP8266 (TLS)'

if [ "$KEEP_SSH" = "yes" ]; then
  ufw limit in on "$WIFI_IF" from "$NET" to any port 22 proto tcp comment 'SSH (cles), limite anti-brute-force'
fi

# Rien d'autre : la base (5432) et le service vision (5001) ne sont pas
# exposés du tout (base dans le réseau Docker, vision sur 127.0.0.1).

ufw logging on
ufw --force enable
ufw status verbose

cat <<EOF

==> Pare-feu actif. Vérifie depuis un AUTRE poste du Wi-Fi de table :
      nmap -p- 10.10.$N.1
    Attendu : 443 et 8883 ouverts (22 si SSH gardé), tout le reste fermé.
EOF

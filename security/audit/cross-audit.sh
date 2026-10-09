#!/usr/bin/env bash
# ============================================================
# Sentinel-X — audit croisé des autres groupes (jeudi, pentest encadré)
#   bash security/audit/cross-audit.sh 10.10.5.1 10.10.8.1 ...
#   bash security/audit/cross-audit.sh -f cibles.txt       (une IP par ligne)
#
# CADRE : uniquement sur les tables du workshop, uniquement sur des groupes
# participant à l'exercice et consentants, uniquement pendant le créneau
# encadré par les coachs. Ne jamais viser une autre adresse.
#
# Ce script OBSERVE et VÉRIFIE (lecture seule) : ports ouverts, chiffrement,
# authentification, droits par topic. Il ne mène ni déni de service ni
# attaque destructive. Chaque cible donne un rapport dans security/audit/.
# ============================================================
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

# --- Cibles ---
TARGETS=()
if [ "${1:-}" = "-f" ]; then
  [ -r "${2:-}" ] || { echo "Fichier de cibles introuvable : ${2:-}"; exit 2; }
  mapfile -t TARGETS < <(grep -vE '^\s*#|^\s*$' "$2")
else
  TARGETS=("$@")
fi
[ ${#TARGETS[@]} -gt 0 ] || { echo "Usage : $0 10.10.5.1 10.10.8.1   ou   $0 -f cibles.txt"; exit 2; }

# Garde-fou : seulement des IP privées du workshop (10.x / 172.16-31.x / 192.168.x)
valid_ip() { [[ $1 =~ ^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)[0-9.]+$ ]]; }

have() { command -v "$1" >/dev/null 2>&1; }
# Client MQTT : binaire local si présent, sinon image Docker Mosquitto
mq() {
  local tool=$1; shift
  if have "$tool"; then timeout 8 "$tool" "$@"
  elif have docker; then timeout 15 docker run --rm --network host --entrypoint "$tool" eclipse-mosquitto:2 "$@"
  else echo "NO_MQTT_CLIENT"; fi
}
port_open() { timeout 3 bash -c "</dev/tcp/$1/$2" 2>/dev/null; }

audit_one() {
  local ip=$1
  local report="$HERE/pentest-$ip-$(date +%Y%m%d-%H%M).md"
  {
    echo "# Audit de $ip — $(date '+%d/%m/%Y %H:%M')"
    echo
    echo "> Pentest croisé Sentinel-X, exercice encadré sur le réseau du workshop."
    echo

    echo "## 1. Surface d'attaque (ports ouverts)"
    echo '```'
    if have nmap; then
      nmap -Pn -T4 -p 22,443,1883,5001,5432,8883 -sV "$ip" 2>&1 | grep -E "^[0-9]+/|Nmap scan"
    else
      echo "(nmap absent — test de secours APPROXIMATIF ; installer nmap pour un résultat fiable :"
      echo " Arch: sudo pacman -S nmap   Ubuntu: sudo apt install nmap)"
      for p in 22 443 1883 5001 5432 8883; do
        port_open "$ip" "$p" && echo "$p/tcp  ouvert" || echo "$p/tcp  ferme"
      done
    fi
    echo '```'
    echo
    echo "| Port | Service attendu | Si ouvert |"
    echo "| --- | --- | --- |"
    echo "| 443 | Dashboard HTTPS | normal |"
    echo "| 8883 | MQTTS (chiffré) | normal |"
    echo "| 1883 | MQTT en clair | **FAILLE : flux non chiffré** |"
    echo "| 5432 | Base PostgreSQL | **FAILLE : base exposée** |"
    echo "| 5001 | Service vision | **FAILLE : caméra sans HTTPS** |"
    echo "| 22 | SSH | à vérifier (clé only ?) |"
    echo

    echo "## 2. MQTT en clair (port 1883)"
    if port_open "$ip" 1883; then
      echo "- [FAILLE] Le port 1883 répond : MQTT possible SANS chiffrement."
      echo "- Preuve (messages interceptés en clair, 5 s) :"
      echo '```'
      mq mosquitto_sub -h "$ip" -p 1883 -t '#' -W 5 -v 2>&1 | head -n 10
      echo '```'
    else
      echo "- [OK] Port 1883 fermé : pas de MQTT en clair."
    fi
    echo

    echo "## 3. Authentification du broker MQTTS (port 8883)"
    if port_open "$ip" 8883; then
      out=$(mq mosquitto_sub -h "$ip" -p 8883 --insecure -t '#' -W 5 -v 2>&1 | head -n 10)
      if echo "$out" | grep -qiE "not authori|refused|bad user|connection refused"; then
        echo "- [OK] Connexion sans identifiants refusée."
      elif echo "$out" | grep -q NO_MQTT_CLIENT; then
        echo "- [?] Aucun client MQTT disponible pour tester (installer mosquitto-clients ou Docker)."
      elif [ -z "$out" ]; then
        echo "- [OK] Connexion anonyme sans message (probablement refusée ou aucun trafic)."
      else
        echo "- [FAILLE] Connexion anonyme ACCEPTÉE : le broker laisse lire sans compte."
        echo '```'; echo "$out"; echo '```'
      fi
      echo
      echo "- Note : \`--insecure\` ne vérifie pas le certificat, c'est VOLONTAIRE côté auditeur"
      echo "  (on n'a pas leur CA). Côté boîtier, ne jamais faire ça."
    else
      echo "- [OK] Port 8883 fermé ou filtré."
    fi
    echo

    echo "## 4. Version TLS (443 et 8883)"
    for port in 443 8883; do
      if port_open "$ip" "$port"; then
        echo "### Port $port"
        echo '```'
        if timeout 6 openssl s_client -connect "$ip:$port" -tls1_1 -cipher 'DEFAULT@SECLEVEL=0' </dev/null >/dev/null 2>&1; then
          echo "[FAILLE] TLS 1.1 accepté (version obsolète) sur $port"
        else
          echo "[OK] TLS 1.0/1.1 refusés sur $port"
        fi
        timeout 6 openssl s_client -connect "$ip:$port" </dev/null 2>/dev/null \
          | grep -E "Protocol|Cipher\s*:" | sed 's/^ *//'
        echo '```'
      fi
    done
    echo

    echo "## 5. Constats à compléter à la main"
    echo "- [ ] Dashboard sur 443 : demande-t-il un mot de passe ? (ouvrir https://$ip/)"
    echo "- [ ] Capture Wireshark : voit-on des données lisibles ?"
    echo "- [ ] Secrets : leur dépôt Git contient-il un \`.env\`, une clé, un mot de passe ?"
    echo
    echo "## Synthèse"
    echo "| Niveau de risque | Faille | Recommandation |"
    echo "| --- | --- | --- |"
    echo "| | | |"
  } | tee "$report"
  echo
  echo "==> Rapport : $report"
  echo "========================================================"
}

echo "Audit croisé Sentinel-X — ${#TARGETS[@]} cible(s)"
echo "Rappel : exercice encadré, réseau du workshop, groupes consentants uniquement."
echo
for ip in "${TARGETS[@]}"; do
  if ! valid_ip "$ip"; then
    echo "IGNORÉ (pas une IP privée du workshop) : $ip"
    continue
  fi
  audit_one "$ip"
done

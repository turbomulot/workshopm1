#!/usr/bin/env bash
# ============================================================
# Sentinel-X — auto-audit du PC Serveur Local (jeudi matin, avant le pentest)
#   sudo bash security/audit/self-audit.sh
#
# Vérifie ce qu'un attaquant regarderait en premier, et écrit un rapport
# horodaté dans security/audit/ (à joindre au dossier). À lancer sur le PC
# serveur, avec la stack de l'infra démarrée. Réglages : security/.env
# Complète par un nmap lancé depuis UN AUTRE poste du Wi-Fi de table :
# un scan local ne passe pas par le pare-feu.
# ============================================================
set -uo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
[ -f security/.env ] && { set -a; . security/.env; set +a; }
N="${GROUP_NUMBER:-?}"
REPORT="security/audit/auto-audit-$(date +%Y%m%d-%H%M).txt"
GIT=(git -c safe.directory="$ROOT")
PASS=0; FAIL=0; SKIP=0

exec > >(tee "$REPORT") 2>&1
ok()   { echo "  [OK]      $*"; PASS=$((PASS + 1)); }
ko()   { echo "  [FAILLE]  $*"; FAIL=$((FAIL + 1)); }
skip() { echo "  [?]       $*"; SKIP=$((SKIP + 1)); }
have() { command -v "$1" >/dev/null 2>&1; }

echo "Auto-audit Sentinel-X — groupe $N — $(date '+%d/%m/%Y %H:%M') — $(hostname)"
[ "$(id -u)" -eq 0 ] || echo "(lancé sans sudo : certains contrôles seront marqués [?])"

echo; echo "1. Ports en écoute sur le réseau (hors 127.0.0.1)"
EXPECTED=" 22 53 67 123 443 8883 "
if have ss; then
  while read -r proto addr; do
    port=${addr##*:}; host=${addr%:*}
    case "$host" in 127.*|"[::1]"|::1) continue ;; esac
    if [[ $EXPECTED == *" $port "* ]]; then ok "$proto $addr (attendu)"
    else ko "$proto $addr ouvert sur le réseau (inattendu)"; fi
  done < <(ss -H -lntu | awk '{print $1, $5}' | sort -u)
  if ss -H -lnt | awk '{print $4}' | grep -qE '^127\.0\.0\.1:5001$'; then ok "service vision limité à 127.0.0.1:5001"
  elif ss -H -lnt | awk '{print $4}' | grep -qE ':5001$'; then ko "service vision (5001) joignable depuis le réseau"
  else skip "service vision non lancé"; fi
else skip "commande ss absente"; fi

echo; echo "2. Pare-feu"
if have ufw && [ "$(id -u)" -eq 0 ]; then
  S=$(ufw status verbose)
  echo "$S" | grep -q "Status: active" && ok "UFW actif" || ko "UFW inactif"
  echo "$S" | grep -q "deny (incoming)" && ok "entrées refusées par défaut" || ko "politique d'entrée trop permissive"
else skip "UFW non vérifiable (absent ou sans sudo)"; fi

echo; echo "3. SSH"
if have sshd && [ "$(id -u)" -eq 0 ]; then
  C=$(sshd -T 2>/dev/null)
  echo "$C" | grep -qi "^passwordauthentication no" && ok "mots de passe SSH interdits (clés uniquement)" || ko "SSH accepte les mots de passe"
  echo "$C" | grep -qi "^permitrootlogin no" && ok "connexion root interdite" || ko "connexion root SSH possible"
elif ! have sshd; then ok "pas de serveur SSH installé"
else skip "SSH non vérifiable sans sudo"; fi

echo; echo "4. Conteneurs Docker"
if have docker && docker info >/dev/null 2>&1; then
  CONTAINERS=$(docker ps -q)
  [ -z "$CONTAINERS" ] && skip "aucun conteneur en cours d'exécution"
  for c in $CONTAINERS; do
    read -r name user priv < <(docker inspect --format '{{.Name}} {{if .Config.User}}{{.Config.User}}{{else}}root{{end}} {{.HostConfig.Privileged}}' "$c")
    name=${name#/}
    [ "$priv" = "false" ] && ok "$name : non privilégié" || ko "$name : conteneur PRIVILÉGIÉ"
    docker inspect --format '{{range .Mounts}}{{.Source}} {{end}}' "$c" | grep -q docker.sock \
      && ko "$name : socket Docker monté (prise de contrôle de l'hôte possible)" || ok "$name : pas de socket Docker monté"
    if [ "$user" != "root" ]; then ok "$name : tourne sous l'utilisateur $user"
    else skip "$name : démarre en root (à justifier : certaines images, comme postgres, abandonnent ensuite leurs droits)"; fi
  done
  docker info --format '{{.SecurityOptions}}' | grep -q "no-new-privileges" \
    && ok "daemon : no-new-privileges" || skip "daemon : no-new-privileges non activé (security/hardening/docker-daemon.json)"
else skip "Docker absent ou arrêté"; fi

echo; echo "5. Certificats"
for crt in security/pki/certs/ca.crt; do
  if [ -r "$crt" ]; then
    openssl x509 -in "$crt" -noout -checkend $((3 * 86400)) >/dev/null && ok "CA valide encore au moins 3 jours" || ko "CA expirée ou proche de l'expiration"
  else skip "$crt absent ou illisible"; fi
done

echo; echo "6. Secrets"
[ -d security/secrets ] && [ "$(stat -c %a security/secrets)" = "700" ] && ok "security/secrets réservé au propriétaire (700)" || skip "security/secrets absent ou droits différents de 700"
LEAK=$("${GIT[@]}" ls-files | grep -E '(\.key|\.pem|\.p12|passwd|\.pcap|^\.env|/\.env|secrets/|secrets\.h)$' | grep -v example || true)
[ -z "$LEAK" ] && ok "aucun fichier secret suivi par Git" || ko "fichiers sensibles suivis par Git : $LEAK"
if have trivy; then
  for img in $(docker ps --format '{{.Image}}' 2>/dev/null | sort -u); do
    trivy image -q --severity CRITICAL --exit-code 1 "$img" >/dev/null 2>&1 && ok "trivy : pas de CVE critique dans $img" || ko "trivy : CVE critique dans $img"
  done
else skip "trivy absent (scan des images)"; fi

echo; echo "7. Broker MQTT (security/audit/test-broker.sh)"
BH="${BROKER_HOST:-localhost}"
if timeout 2 bash -c "</dev/tcp/$BH/8883" 2>/dev/null; then
  if bash security/audit/test-broker.sh > /tmp/sx-test.$$ 2>&1; then ok "tous les tests de sécurité du broker passent ($BH:8883)"
  else ko "certains tests du broker échouent :"; grep ECHEC /tmp/sx-test.$$ | sed 's/^/          /'; fi
  rm -f /tmp/sx-test.$$
else skip "broker injoignable sur $BH:8883 (stack non lancée ou BROKER_HOST à régler)"; fi

echo; echo "Bilan : $PASS OK, $FAIL faille(s), $SKIP non vérifié(s)"
echo "Rapport : $REPORT"
echo "À faire aussi depuis un autre poste : nmap -p- -sV 10.10.$N.1"
exit $(( FAIL > 0 ))

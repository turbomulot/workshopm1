# Durcissement du PC serveur

Exigence « Hardening Système » du sujet. Cible mesurable : depuis un autre poste du Wi-Fi de table, `nmap -p- 10.10.<n>.1` ne montre que **443** et **8883** (et 22 si SSH est gardé). À appliquer sur le PC serveur, avec la personne infra.

## Ordre d'application

1. **Pare-feu** — `sudo bash security/hardening/ufw-rules.sh`. Il lit `GROUP_NUMBER`, `WIFI_IF` et `KEEP_SSH` dans `security/.env`. Il ouvre 443 et 8883 sur le Wi-Fi de table, plus DHCP, DNS et NTP, sans quoi les postes et le boîtier n'obtiennent ni adresse ni heure. Tout le reste est refusé.
2. **Le piège Docker** — un port publié par Docker passe outre UFW. L'infra doit publier ses ports sur l'IP du Wi-Fi de table uniquement (`10.10.<n>.1:8883:8883`), jamais sur toutes les interfaces, et ne jamais publier la base ni l'API interne. Vérification : `sudo ss -lntu`, puis le `nmap` depuis un autre poste.
3. **SSH** — copier `sshd-sentinel.conf` dans `/etc/ssh/sshd_config.d/99-sentinel.conf` (clés uniquement, pas de root). **Tester une connexion par clé dans un second terminal avant de recharger**, sinon on se bloque dehors. Ajouter `fail2ban`. Si personne n'a besoin de SSH, le désactiver (`sudo systemctl disable --now sshd` sur Arch, `ssh` sur Ubuntu).
4. **Docker** — copier `docker-daemon.json` dans `/etc/docker/daemon.json`, puis `sudo systemctl restart docker`. Pas de `userns-remap` : il empêche les conteneurs de lire les certificats et comptes montés. L'isolation se fait conteneur par conteneur ; exigences pour l'infra : utilisateur non root quand l'image le permet, `cap_drop: ALL`, système de fichiers en lecture seule, `no-new-privileges`, jamais `privileged` ni le socket Docker monté. `self-audit.sh` le vérifie.

## Installation des outils (Arch / Ubuntu)

| Outil | Arch | Ubuntu / Debian |
| --- | --- | --- |
| Pare-feu | `sudo pacman -S ufw` | `sudo apt install ufw` |
| Anti brute-force SSH | `sudo pacman -S fail2ban` | `sudo apt install fail2ban` |
| Audit système | `sudo pacman -S lynis` | `sudo apt install lynis` |
| Scan réseau | `sudo pacman -S nmap` | `sudo apt install nmap` |

## Preuves à garder (pour le dossier et le jury)

- `sudo lynis audit system` avant / après : l'écart de score chiffre le travail.
- `nmap -p- 10.10.<n>.1` depuis un autre poste : capture d'écran de la surface réduite.
- `sudo bash security/audit/self-audit.sh` : rapport horodaté dans `security/audit/`.

## Secrets

- Avant de rendre le code : `git ls-files` ne doit lister aucun certificat, clé, mot de passe ni `.env` (`self-audit.sh` section 6 le vérifie).
- La clé de la CA (`security/pki/certs/ca.key`) quitte le PC après génération (clé USB).

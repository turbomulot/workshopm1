# Matrice de sécurité — Sentinel-X

Chaque ligne relie une menace à sa contre-mesure, à son responsable et à la preuve à montrer au jury.

États :
- **Prouvé** : vérifié pour de vrai, la preuve (sortie de commande, capture) est gardée pour le dossier.
- **Fourni** : livré par la cyber dans `security/`, reste à vérifier une fois en place sur le serveur.
- **Exigence** : règle à respecter par l'infra ou le dev, vérifiée par la cyber (`self-audit.sh`, `test-broker.sh`, pentest).

## Flux et accès

| Menace | Contre-mesure | Responsable | Preuve | État |
| --- | --- | --- | --- | --- |
| Écoute du Wi-Fi (sniffing) | MQTTS (TLS 1.2 minimum) avec la CA du groupe ; Wi-Fi de table en WPA2 | Cyber (TLS), infra (Wi-Fi) | Wireshark sur 8883 : uniquement du « TLS Application Data » | Fourni |
| Faux broker (homme du milieu) | Le boîtier n'accepte que la CA du groupe, après synchro NTP ; jamais `setInsecure()` | Dev, règles de la cyber (`docs/tls-esp8266.md`) | Faux broker refusé (erreur TLS sur le port série) | Exigence |
| Certificat contrefait | CA propre au groupe, clé de la CA hors du PC, certificats nommés avec l'IP du serveur | Cyber (`pki/`) | `openssl verify` : nom du serveur accepté, autre nom refusé | Prouvé |
| Client MQTT inconnu | Aucun client anonyme, mots de passe aléatoires de 128 bits, hachés côté broker | Cyber (`mosquitto/`) | `test-broker.sh` : client sans compte et mauvais mot de passe refusés | Prouvé |
| Compte volé utilisé hors de son rôle | ACL : le boîtier ne lit que ses commandes, ne peut ni commander ni espionner | Cyber (`mosquitto/acl.template`) | `test-broker.sh` : écriture sur `cmd` et lecture des mesures refusées | Prouvé |
| MQTT en clair | Seul le port 8883 (TLS) est ouvert, jamais 1883 | Cyber (config), infra (ports) | `test-broker.sh` : port 1883 fermé | Prouvé |
| Accès libre à la caméra | Service vision limité à 127.0.0.1, accès réseau par un proxy HTTPS avec identifiant | Cyber (correctif), infra (proxy) | Depuis un autre poste : `curl http://<serveur>:5001/video` échoue | Fourni |
| Lecture des données par un site tiers (CORS) | Origines autorisées explicites au lieu de `*` | Cyber (correctif) | En-tête `Access-Control-Allow-Origin` absent pour une autre origine | Fourni |
| Dashboard et API en clair | Dashboard et API servis uniquement en HTTPS (certificat `web/`), avec identifiant | Infra | Cadenas dans le navigateur, 401 sans identifiant | Exigence |

## Données

| Menace | Contre-mesure | Responsable | Preuve | État |
| --- | --- | --- | --- | --- |
| Injection de commande vers le boîtier | Liste blanche des commandes dans le firmware | Dev, règles de la cyber | Commande inconnue sans effet | Exigence |
| Injection SQL / données forgées | Requêtes paramétrées, valeurs non numériques rejetées | Infra / dev (backend) | Payload `DROP TABLE` sans effet | Exigence |
| Rejeu de messages capturés | `seq` + `ts` dans chaque mesure, rejet des doublons et des messages trop anciens | Dev (firmware), infra / dev (backend) | Message rejoué rejeté | Exigence |
| Fuite de secrets dans Git | `.gitignore` des secrets, secrets générés hors du repo, `git status` vérifié avant chaque commit | Cyber | `self-audit.sh` section 6 : aucun fichier sensible suivi | Fourni |

## Serveur

| Menace | Contre-mesure | Responsable | Preuve | État |
| --- | --- | --- | --- | --- |
| Ports inutiles exposés | UFW refus par défaut ; seuls 443 et 8883 (+ DHCP, DNS, NTP du Wi-Fi de table) | Cyber (`hardening/ufw-rules.sh`), appliqué avec l'infra | `nmap -p-` depuis un autre poste | Fourni |
| Contournement d'UFW par Docker | Ports publiés sur l'IP du Wi-Fi de table uniquement, base et API interne jamais publiées | Infra | `self-audit.sh` section 1 (`ss -lntu`) | Exigence |
| Brute-force SSH | Clés uniquement, root interdit, `ufw limit`, fail2ban | Cyber (`hardening/`) | `self-audit.sh` section 3 (`sshd -T`) | Fourni |
| Évasion d'un conteneur | Non-root quand l'image le permet, `cap_drop: ALL`, lecture seule, `no-new-privileges`, jamais `privileged` ni socket Docker | Infra, réglages du daemon par la cyber | `self-audit.sh` section 4 | Exigence |
| DoS sur le broker | Connexions, taille des messages et files bornées | Cyber (`mosquitto.conf`) | Broker stable pendant un flood (`docker stats`) | Fourni |
| Disque rempli par les logs | Logs Docker bornés à 3 × 10 Mo par conteneur | Cyber (`docker-daemon.json`) | `docker system df` | Fourni |

## Failles trouvées dans le code existant (audit du mardi 6 octobre)

| # | Faille | Gravité | Correction |
| --- | --- | --- | --- |
| 1 | Service vision sur `0.0.0.0:5001`, HTTP clair, sans authentification : flux caméra et journal visibles par tout le réseau | Élevée | Corrigé : écoute sur 127.0.0.1 |
| 2 | `Access-Control-Allow-Origin: *` sur le service vision | Moyenne | Corrigé : liste d'origines autorisées |
| 3 | Serveur de développement Flask utilisé pour la démo | Faible | Atténué : joignable seulement en local |
| 4 | Dashboard servi par le serveur de dev Vite (`host: true`, HTTP) | Moyenne | Exigence infra : build statique en HTTPS |
| 5 | Commandes `POST /api/v1/commands` prévues sans authentification | Moyenne | Exigence : API joignable uniquement via le proxy HTTPS avec identifiant |

## Schémas à joindre au dossier

- Schéma réseau : point d'accès, sous-réseau de table, IP, ports ouverts.
- Schéma des flux chiffrés : boîtier → MQTTS → broker → backend ; navigateur → HTTPS → proxy → dashboard / vision.

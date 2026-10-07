# Rapport d'audit — Sentinel-X

À remplir le jeudi (journée Hacking Day). Cadre : **uniquement** sur les tables du workshop, sur le réseau du workshop, entre groupes participants à l'exercice. Rien en dehors de ce périmètre.

---

## 0. Audit du code existant (mardi 6 octobre)

Revue du code de l'équipe sur `main` (commit 919c043) : service vision `webcam-detection/stream_detection.py` et dashboard `frontend/`.

| # | Constat | Risque | Preuve | Correction |
| --- | --- | --- | --- | --- |
| 1 | `app.run(host="0.0.0.0", port=5001)` : flux caméra, détection et journal accessibles par tout le réseau, en HTTP clair, sans authentification | Élevé (vie privée, reconnaissance) | `curl http://<serveur>:5001/video` depuis un autre poste | Corrigé : écoute sur 127.0.0.1 ; accès réseau via un proxy HTTPS avec identifiant (exigence infra) |
| 2 | `Access-Control-Allow-Origin: *` | Moyen (lecture par un site tiers) | En-tête visible dans toutes les réponses | Corrigé : origines autorisées explicites (`FRONTEND_ORIGINS`) |
| 3 | Serveur de développement Flask exposé | Faible | `app.run` | Atténué : uniquement en local derrière le proxy |
| 4 | Dashboard servi par le serveur de dev Vite (`host: true`, HTTP) | Moyen | `vite.config.js` | Exigence infra : build statique servi en HTTPS |
| 5 | `POST /api/v1/commands` prévu sans authentification | Moyen (déclenchement du buzzer à distance) | `frontend/src/services/api.js` | Exigence infra / dev : API joignable uniquement via le proxy HTTPS avec identifiant |

## 1. Auto-audit de notre stack (jeudi matin)

Lancer `sudo bash security/audit/self-audit.sh` sur le PC serveur : il vérifie automatiquement ports, pare-feu, SSH, conteneurs, certificats, secrets, puis lance `test-broker.sh` (chiffrement, comptes, ACL). Il écrit un rapport horodaté dans `security/audit/`, à joindre en annexe. Compléter par le `nmap` lancé depuis un autre poste (ligne 1) et les tests manuels ci-dessous.

Teste ta propre table comme un attaquant, pour fermer les trous avant le pentest croisé.

| # | Test | Commande / méthode | Résultat attendu | Observé |
| --- | --- | --- | --- | --- |
| 1 | Surface d'attaque | `nmap -p- -sV 10.10.<n>.1` | Seuls 443, 8883 (+22) répondent | |
| 2 | MQTT sans identifiants | `test-broker.sh` | Refusé | |
| 3 | ACL respectée | `test-broker.sh` (écrire sur `cmd` avec le compte du boîtier) | Refusé | |
| 4 | Faux broker | `openssl s_client` avec certificat non signé | ESP refuse la connexion | |
| 5 | Rejeu | republier un `telemetry` capté | Backend rejette (seq/ts) | |
| 6 | DoS API | flood `POST /api/v1/alerts` sans clé | 401 + rate limit, dashboard stable | |
| 7 | Secrets | `self-audit.sh` (fichiers suivis par Git) + `trivy image` | Aucun secret, pas de CVE critique | |

## 2. Audit croisé (jeudi après-midi)

Lancer `bash security/audit/cross-audit.sh -f security/audit/cibles.txt` (IP des groupes données par les coachs) : il produit un pré-rapport par cible dans `security/audit/` (ports ouverts, MQTT en clair, broker anonyme, version TLS). Compléter chaque rapport à la main (dashboard protégé ? Wireshark ? secrets dans leur Git ?), puis recopier ci-dessous.

Une entrée par faille trouvée sur une autre table.

### Cible : groupe ___

- **Périmètre testé** :
- **Méthode / outil** (Nmap, Wireshark, Metasploit…) :
- **Constat** :
- **Niveau de risque** : critique / élevé / moyen / faible
- **Preuve** (capture horodatée) :
- **Recommandation** :

*(dupliquer ce bloc par faille)*

## 3. Défense de notre stack

Attaques reçues pendant le pentest croisé et comment elles ont été bloquées.

| Attaque reçue | Origine | Bloquée par | Preuve |
| --- | --- | --- | --- |
| | | | |

## 4. Synthèse

- Failles critiques trouvées chez les autres : 
- Failles sur notre stack corrigées avant/pendant : 
- Points forts de notre défense : 

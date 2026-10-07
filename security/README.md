# Sécurité — Sentinel-X

Partie cybersécurité du projet : chiffrement de bout en bout, comptes et droits du broker, durcissement du serveur, audit et pentest. Ce dossier est autonome : il ne dépend ni de la stack de l'infra, ni du firmware, mais il leur fournit leurs certificats, la configuration de sécurité du broker et les règles à respecter.

## Démarrage rapide

```bash
cp security/.env.example security/.env          # GROUP_NUMBER, SERVER_IP (choisie avec l'infra)
bash security/pki/make-pki.sh                    # autorité du groupe + certificats
bash security/mosquitto/make-accounts.sh         # comptes MQTT, ACL, passwd
bash security/mosquitto/run-test-broker.sh       # broker de test sur ce PC
bash security/audit/test-broker.sh               # vérifications de sécurité du broker
```

Il faut `openssl` et Docker (ou `mosquitto` installé sur le PC).

## Contenu

| Dossier | Contenu |
| --- | --- |
| [`pki/`](pki/) | Autorité de certification du groupe et certificats ECDSA (MQTTS et HTTPS). |
| [`mosquitto/`](mosquitto/) | Config du broker : MQTTS uniquement, comptes, droits par topic ; broker de test. |
| [`hardening/`](hardening/) | Durcissement du PC serveur : pare-feu UFW, SSH par clé, réglages du daemon Docker. |
| [`audit/`](audit/) | `test-broker.sh` (sécurité du broker) et `self-audit.sh` (contrôle complet du serveur). |
| [`docs/`](docs/) | Matrice de sécurité, rapport d'audit, exigences TLS du boîtier. |

## Ce que la cyber fournit aux autres

| À qui | Quoi | Comment |
| --- | --- | --- |
| Infra | Certificats `broker/` et `web/`, config du broker (`mosquitto/`), mot de passe du compte `api` | Clé USB, jamais par Git ni par message |
| Dev (boîtier) | `ca.crt`, compte `esp-g<n>` et son mot de passe, règles TLS (`docs/tls-esp8266.md`) | Clé USB, jamais par Git ni par message |
| Toute l'équipe | Les exigences de sécurité de la matrice (`docs/matrice-securite.md`) | Dans ce dépôt |

## Rien de secret dans Git

Sont ignorés par Git : les certificats et clés (`pki/certs/`), les mots de passe (`secrets/`), les comptes du broker (`mosquitto/passwd`, `mosquitto/acl`), les fichiers `.env` et les captures `.pcap`. La clé de la CA (`ca.key`) ne reste pas sur le PC : elle va sur la clé USB du responsable cyber.

Avant chaque commit, vérifier avec `git status` qu'aucun de ces fichiers n'apparaît. `self-audit.sh` contrôle aussi qu'aucun fichier sensible n'est suivi par Git.

## Planning cyber

1. **PKI et comptes** — dès que l'IP du serveur est fixée.
2. **Broker** — remise de la config à l'infra, puis `test-broker.sh` sur la vraie stack (`BROKER_HOST` = IP du serveur).
3. **Boîtier** — vérifier avec le dev les règles TLS ; capture Wireshark sur le port 8883 comme preuve.
4. **Durcissement** — `hardening/` sur le PC serveur, avec l'infra.
5. **Jeudi** — `sudo bash security/audit/self-audit.sh` le matin, pentest croisé l'après-midi, puis `docs/rapport-audit.md`.

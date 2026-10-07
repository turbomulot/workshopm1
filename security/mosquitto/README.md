# Broker MQTT sécurisé (Mosquitto)

Configuration de sécurité du broker, livrée par la cyber à l'infra : MQTTS uniquement (TLS sur 8883, rien en clair sur 1883), aucun client anonyme, un compte par client et des droits par topic.

## Fichiers

| Fichier | Rôle | Dans Git ? |
| --- | --- | --- |
| `mosquitto.conf` | MQTTS sur 8883, authentification obligatoire, limites anti-DoS | Oui |
| `acl.template` | Droits par topic, modèle avec `g<n>` | Oui |
| `acl` | Droits par topic pour votre groupe, généré par `make-accounts.sh` | Non |
| `passwd` | Comptes et empreintes des mots de passe, généré par `make-accounts.sh` | Non |
| `make-accounts.sh` | Crée les mots de passe, l'ACL et le `passwd` | Oui |
| `run-test-broker.sh` | Lance un broker de test sur ce PC avec cette config | Oui |

## Créer les comptes

```bash
bash security/mosquitto/make-accounts.sh
```

Deux comptes, chacun limité à ce dont il a besoin :

| Compte | Qui | Peut écrire | Peut lire |
| --- | --- | --- | --- |
| `esp-g<n>` | Le boîtier ESP8266 | `telemetry`, `event`, `status` | `cmd` (ses commandes) |
| `api` | Le backend du dashboard | `cmd` | tout `sentinelx/g<n>/#` |

Le boîtier ne peut donc ni envoyer de commandes, ni espionner les mesures. Un compte volé reste cantonné à son rôle.

## Tester sans attendre l'infra

```bash
bash security/mosquitto/run-test-broker.sh     # broker de test sur 127.0.0.1:8883
bash security/audit/test-broker.sh             # 8 vérifications de sécurité
bash security/mosquitto/run-test-broker.sh stop
```

## Ce que l'infra doit respecter (contrat)

- Monter `security/mosquitto/` en `/mosquitto/config` et `security/pki/certs/broker/` en `/mosquitto/certs`, en lecture seule.
- Publier **uniquement** le port 8883, sur l'IP du Wi-Fi de table, jamais sur toutes les interfaces : un port publié par Docker passe outre le pare-feu UFW.
- Le broker tourne sous l'utilisateur 1883 : `broker.key` et `passwd` doivent lui appartenir (`sudo chown 1883:1883 ...`), en droits 600, jamais en lecture pour tous.
- Le backend se connecte avec le compte `api`, en vérifiant le certificat du broker avec `ca.crt`.

Une fois la stack de l'infra lancée, `test-broker.sh` (avec `BROKER_HOST` = IP du serveur dans `security/.env`) vérifie que le contrat est respecté.

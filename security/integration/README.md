# Intégration — ce que la cyber remet à l'équipe

Tout ce dossier sert à brancher la sécurité sur le projet existant, **sans
changer la logique** : mêmes topics `sentinel/*`, mêmes commandes, même dashboard.
On passe juste le transport de MQTT clair (1883) à MQTTS chiffré (8883).

| Fichier | Pour qui | Quoi en faire |
| --- | --- | --- |
| `docker-compose.backend.yml` | Nino (serveur) | Remplace le `backend/docker-compose.yml` : broker 8883 TLS, base non exposée, backend en `mqtts://`. |
| `firmware/main.cpp` | Dev (boîtier) | Remplace `src/main.cpp` : MQTTS + certificat vérifié, mêmes capteurs/écran. Compilé OK. |
| `firmware/secrets.example.h` | Dev | Modèle de `secrets.h` (jamais commité). |

Les certificats et les comptes viennent des scripts de `security/` :
`make-pki.sh` puis `make-accounts.sh` produisent `pki/certs/`, `mosquitto/passwd`
et `mosquitto/acl` (déjà au format `sentinel/*`). Procédure complète :
`security/docs/MIGRATION-MQTTS.md`.

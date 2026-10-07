# Mission SENTINEL-X

Workshop EPSI Bac+4 2026-27.

## Contenu du dépôt

| Dossier | Contenu |
| --- | --- |
| [frontend/](frontend/) | Dashboard de supervision et page Employés & badges (React + Vite) |
| [backend/](backend/) | API capteurs / actionneurs : MQTT → PostgreSQL, REST + socket.io (Node.js) |
| [webcam-detection/](webcam-detection/) | Service vision : détection de personnes YOLO, flux webcam, registre employés et badges QR (Python) |
| [docs/](docs/) | Comptes rendus et guide de reprise développeur web |

Voir le README de chaque dossier pour l'installation et le lancement.

Le [compte rendu global du 6 octobre 2026](docs/COMPTE_RENDU_AJOUTS_2026-10-06.md) récapitule les fichiers ajoutés pour les badges QR et les commandes pour reprendre sur un autre PC. Le [guide de reprise DEV web](docs/REPRISE_DEV_WEB_BADGES.md) détaille le contrat API des badges et l'intégration dans le dashboard.

## Comment les briques se parlent

```
ESP8266 --MQTT--> Mosquitto --> backend --REST + socket.io--> frontend (dashboard)
                                  ^                              |
                                  |                              v
webcam --> service vision --POST /api/v1/alerts--+   service vision --/video /status /logs--> frontend
              |                                                   --/api/v1/employees...--> page badges
              v
      SQLite (.data/) : employés, badges QR, validations
```

- Le **frontend** lit les capteurs, l'historique, les alertes et l'état du boîtier sur le backend
  (`VITE_API_URL`), la caméra / détection sur le service vision (`VITE_AI_URL`), et les badges
  sur le même service vision via le proxy `/access-api` (`VITE_ACCESS_API_URL`).
- Le **backend** reçoit les mesures du boîtier par MQTT et les pousse au dashboard en temps réel.
- Le **service vision** lit aussi les QR codes des badges et les valide contre son registre SQLite local.
  Il peut enregistrer ses détections dans le backend via `POST /api/v1/alerts` (pas encore branché).

Démarrage rapide en local (sans matériel) :

```bash
cd backend && cp .env.example .env && docker compose up -d --build
docker compose run --rm backend node simulate-esp.js     # faux ESP8266, dans un autre terminal
cd ../frontend && cp .env.example .env && npm install && npm run dev
```

Pour la caméra et les badges, voir le [README du module vision](webcam-detection/README.md).

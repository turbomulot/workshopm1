# Mission SENTINEL-X

Workshop EPSI Bac+4 2026-27.

## Contenu du dépôt

| Dossier | Contenu |
| --- | --- |
| [frontend/](frontend/) | Dashboard de supervision (React + Vite) |
| [backend/](backend/) | API capteurs / actionneurs : MQTT → PostgreSQL, REST + socket.io (Node.js) |
| [webcam-detection/](webcam-detection/) | Service IA : détection de personnes sur la webcam (Python, YOLOv8) |

Voir le README de chaque dossier pour l'installation et le lancement.

## Comment les briques se parlent

```
ESP8266 --MQTT--> Mosquitto --> backend --REST + socket.io--> frontend (dashboard)
                                  ^                              |
                                  |                              v
webcam --> service IA --POST /api/v1/alerts--+        service IA --/video /status /logs--> frontend
```

- Le **frontend** lit les capteurs, l'historique, les alertes et l'état du boîtier sur le backend
  (`VITE_API_URL`), et la caméra / détection sur le service IA (`VITE_AI_URL`).
- Le **backend** reçoit les mesures du boîtier par MQTT et les pousse au dashboard en temps réel.
- Le **service IA** peut aussi enregistrer ses détections dans le backend via `POST /api/v1/alerts`.

Démarrage rapide en local (sans matériel) :

```bash
cd backend && cp .env.example .env && docker compose up -d --build
docker compose run --rm backend node simulate-esp.js     # faux ESP8266, dans un autre terminal
cd ../frontend && cp .env.example .env && npm install && npm run dev
```

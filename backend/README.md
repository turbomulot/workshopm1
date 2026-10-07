# SENTINEL-X — Backend

Tourne sur le PC Serveur Local. Il reçoit les mesures du boîtier ESP8266 par MQTT, les enregistre dans PostgreSQL, les pousse au dashboard en temps réel (socket.io) et expose une API REST.

Stack : Node.js 20, Express, socket.io, MQTT.js, PostgreSQL.

```
ESP8266 --MQTT--> Mosquitto --> backend --socket.io / REST--> dashboard
                                   |
                               PostgreSQL
service IA webcam --POST /api/v1/alerts--> backend
```

## Brancher le backend dans la pile INFRA

Le `docker-compose.yml` de la racine (branche `Infra-cyber`) a un emplacement « API du DEV ». Service à y mettre :

```yaml
  api:
    <<: *hardening
    build: ./backend
    container_name: sentinel-api
    user: "10001:10001"
    read_only: true
    cap_drop: [ALL]
    ports: ["127.0.0.1:3000:3000"]
    environment:
      MQTT_URL: mqtts://mosquitto:8883
      MQTT_USERNAME: api
      MQTT_PASSWORD_FILE: /run/secrets/mqtt_api_password
      MQTT_CA_FILE: /certs/ca.crt
      MQTT_BASE_TOPIC: "sentinelx/g${GROUP_NUMBER:-3}"
      MQTT_CMD_FORMAT: command
      PGHOST: db
      PGUSER: sentinel
      PGDATABASE: sentinel
      PGPASSWORD_FILE: /run/secrets/db_password
    secrets: [db_password, mqtt_api_password]
    volumes: [./security/pki/certs/ca.crt:/certs/ca.crt:ro]
    depends_on:
      db: { condition: service_healthy }
      mosquitto: { condition: service_started }
    networks: [back]
```

Et dans le `Caddyfile`, pour servir l'API et le temps réel en HTTPS :

```
	handle /api/* {
		reverse_proxy 127.0.0.1:3000
	}
	handle /socket.io/* {
		reverse_proxy 127.0.0.1:3000
	}
```

À savoir :

- Le temps réel passe par socket.io, donc par le chemin `/socket.io/` et non `/ws`.
- Le backend crée ses propres tables, `api_measurements` et `api_alerts`. Il ne touche pas à celles de `infra/db/init.sql` et peut tourner à côté du pont `bridge`.
- Le compte MQTT `api` suffit : lecture de `sentinelx/g<n>/#`, écriture sur `sentinelx/g<n>/cmd`.
- Le conteneur n'écrit rien sur disque et fonctionne avec n'importe quel utilisateur non root.

## Lancer le backend seul (développement)

Le dossier contient une pile autonome : un broker MQTT en clair, une base et le backend.

```bash
cd backend
cp .env.example .env        # puis changer POSTGRES_PASSWORD
docker compose up -d --build
docker compose logs -f backend
```

L'API répond sur http://localhost:3000 et le broker sur le port 1883. La base n'est joignable que depuis le réseau Docker.

Pour tester sans le boîtier, lancer le faux ESP dans un autre terminal :

```bash
docker compose run --rm backend node simulate-esp.js
```

Il publie une mesure toutes les 2 secondes et rejoue un scénario en boucle (passage devant le capteur de présence, puis fuite de gaz). Il affiche aussi les commandes reçues.

Arrêt : `docker compose down` (ajouter `-v` pour effacer aussi la base).

## Variables d'environnement

Aucun secret n'est écrit dans le code. Le backend lit :

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `PORT` | port d'écoute de l'API | `3000` |
| `MQTT_URL` | adresse du broker (`mqtt://` ou `mqtts://`) | `mqtt://mosquitto:1883` |
| `MQTT_USERNAME` | compte du broker | vide (connexion anonyme) |
| `MQTT_PASSWORD` ou `MQTT_PASSWORD_FILE` | mot de passe, ou chemin d'un fichier qui le contient | vide |
| `MQTT_CA_FILE` | certificat de l'autorité qui a signé le broker (TLS) | vide (autorités du système) |
| `MQTT_BASE_TOPIC` | racine des topics | `sentinel` |
| `MQTT_CMD_FORMAT` | format des commandes : `state` ou `command` | `state` |
| `PGHOST`, `PGPORT`, `PGUSER`, `PGDATABASE` | connexion PostgreSQL | valeurs du pilote |
| `PGPASSWORD` ou `PGPASSWORD_FILE` | mot de passe de la base, ou chemin d'un fichier | vide |
| `CORS_ORIGIN` | origine autorisée pour le dashboard | `*` |
| `DEVICE_OFFLINE_AFTER_S` | délai sans message avant « hors ligne » | `15` |

La pile autonome lit en plus, dans `backend/.env` (modèle : [.env.example](.env.example)) : `API_PORT`, `MQTT_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`.

## Topics MQTT

Le backend s'abonne à `<MQTT_BASE_TOPIC>/#` et comprend deux contrats. Il n'y a rien à choisir en réception : c'est la fin du topic qui décide.

### Contrat par défaut (`MQTT_BASE_TOPIC=sentinel`, `MQTT_CMD_FORMAT=state`)

| Topic | Sens | Message |
| --- | --- | --- |
| `sentinel/sensors` | ESP → backend | `{ "temp": 24.5, "hum": 52.1, "gas": 120, "pir": 0, "ts": 1791280000 }` |
| `sentinel/alerts` | ESP → backend | `{ "type": "gas" \| "motion" \| "temp", "level": "warn" \| "critical", "value": 640 }` |
| `sentinel/cmd` | backend → ESP | `{ "buzzer": true, "led": "red" \| "green" \| "off" }` |

### Firmware du groupe (`MQTT_BASE_TOPIC=sentinelx/g<n>`, `MQTT_CMD_FORMAT=command`)

| Topic | Sens | Message |
| --- | --- | --- |
| `sentinelx/g<n>/telemetry` | ESP → backend | `{ "seq": 1, "ts": 1791280000, "t": 24.5, "h": 52.1, "gas": 120, "pir": 0, "rssi": -61 }` |
| `sentinelx/g<n>/event` | ESP → backend | `{ "type": "pir", "value": 1, "ts": 1791280000 }` |
| `sentinelx/g<n>/status` | ESP → backend | texte `online` ou `offline` (Last Will) |
| `sentinelx/g<n>/cmd` | backend → ESP | `{ "command": "BUZZER_ON" }`, une commande par message |

- Un événement `pir` devient une alerte `motion` (`critical` à 1, `info` à 0). Les autres événements sont enregistrés tels quels.
- `offline` sur `status` met le boîtier hors ligne tout de suite, sans attendre le délai.
- `led: "red"` envoie `LED_RED_ON` puis `LED_GREEN_OFF` ; `"green"` l'inverse ; `"off"` éteint les deux.

### Dans les deux cas

- `ts` est l'heure Unix en secondes. Une petite valeur (temps depuis l'allumage) est remplacée par l'heure de réception.
- Une valeur de capteur absente ou invalide est enregistrée vide, le reste de la mesure est gardé.
- Un message qui n'est pas du JSON, ou une alerte dont le `type` ou le `level` est inconnu, est ignoré et signalé dans les logs.
- Si le broker tombe, le backend se reconnecte seul toutes les 2 secondes.

## API REST

| Méthode | Route | Rôle |
| --- | --- | --- |
| POST | `/api/v1/alerts` | enregistre une alerte (capteurs ou IA webcam) et la diffuse au dashboard |
| GET | `/api/v1/alerts?limit=20` | dernières alertes, de la plus récente à la plus ancienne (200 max) |
| GET | `/api/v1/history?sensor=temp&limit=100` | historique des mesures, de la plus ancienne à la plus récente (1000 max) |
| GET | `/api/v1/status` | état du boîtier |
| POST | `/api/v1/commands` | envoie une commande au boîtier |

### POST /api/v1/alerts

```json
{ "source": "vision", "type": "person_detected", "value": { "people": 1, "confidence": 0.87 }, "timestamp": "2026-10-07T09:30:00Z" }
```

- `source` : `esp8266` ou `vision`.
- `type` : chaîne non vide, 50 caractères au plus.
- `value` : obligatoire, de n'importe quel type JSON.
- `timestamp` : date ISO 8601.
- `level` (facultatif) : `info`, `warn` ou `critical`.

Réponse `201` avec l'alerte enregistrée, ou `400` avec `{ "error": "..." }` si le body est invalide.

### GET /api/v1/history

- Sans `sensor` : `[{ "id", "timestamp", "temp", "hum", "gas", "pir" }]`.
- Avec `sensor` (`temp`, `hum`, `gas` ou `pir`) : `[{ "timestamp", "value" }]`.

### GET /api/v1/status

```json
{
  "online": true,
  "lastSeen": "2026-10-07T09:30:02.000Z",
  "mqttConnected": true,
  "actuators": { "buzzer": false, "led": "off" },
  "latest": { "id": 42, "timestamp": "2026-10-07T09:30:02.000Z", "temp": 24.5, "hum": 52.1, "gas": 120, "pir": 0 }
}
```

`online` passe à `false` quand le boîtier n'a rien publié depuis `DEVICE_OFFLINE_AFTER_S` secondes. `actuators` est la dernière commande envoyée : le boîtier ne confirme pas son état réel.

### POST /api/v1/commands

```json
{ "buzzer": true, "led": "red" }
```

Un seul des deux champs suffit : l'autre garde sa dernière valeur. Réponse `{ "ok": true, "actuators": { "buzzer", "led" } }`, `400` si le body est invalide, `503` si le broker est injoignable.

## Temps réel (socket.io)

Le dashboard se connecte à la même adresse que l'API. Événements émis par le backend :

| Événement | Contenu | Quand |
| --- | --- | --- |
| `sensors` | une mesure, au format de `/history` | à chaque mesure reçue du boîtier |
| `alert` | une alerte, au format de `/alerts` | à chaque alerte ou événement MQTT, et à chaque `POST /api/v1/alerts` |
| `status` | l'objet de `/status` | à la connexion, quand le boîtier passe en ligne ou hors ligne, après une commande |

## Sécurité

- L'API n'a pas d'authentification. Dans la pile INFRA elle n'écoute que sur `127.0.0.1` et c'est Caddy qui la protège (HTTPS et mot de passe).
- La pile autonome de ce dossier sert au développement : son broker accepte les connexions anonymes en clair. Ne pas l'exposer sur un réseau partagé.

## Structure

```
backend/
  src/index.js        démarrage, traitement des messages MQTT, état du boîtier
  src/config.js       lecture des variables d'environnement et des secrets
  src/db.js           tables PostgreSQL, enregistrement et lecture
  src/mqtt.js         connexion au broker, reconnexion, publication des commandes
  src/routes.js       routes REST et validation des bodies
  simulate-esp.js     faux ESP8266
  Dockerfile
  docker-compose.yml  pile autonome de développement
  mosquitto/          configuration du broker de développement
```

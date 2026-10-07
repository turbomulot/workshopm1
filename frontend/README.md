# SENTINEL-X — Dashboard de supervision

Interface web de supervision du boîtier SENTINEL-X : capteurs (DHT22, MQ-2, PIR), graphiques temps réel, flux caméra, résultat de l'IA, alertes et commande des actionneurs.

Stack : React 18, Vite 5, Recharts, CSS classique.

## Lancer le projet

```bash
cd frontend
npm install
npm run dev
```

Le dashboard est disponible sur http://localhost:5173.

Le dashboard combine deux services :

- le **service IA** (`webcam-detection/stream_detection.py`, http://127.0.0.1:5001) pour la caméra,
  la détection et son journal : voir le [README du module vision](../webcam-detection/README.md) ;
- le **backend** (`backend/`, http://localhost:3000) pour les capteurs, l'historique, les alertes du
  boîtier et les actionneurs : voir le [README du backend](../backend/README.md).

Chaque service est facultatif : s'il ne répond pas, sa partie du dashboard affiche « No data » et
le reste continue de fonctionner. Pour tout tester sans matériel ni service, mettre
`VITE_USE_MOCK=true`.

### Brancher le backend

```bash
# 1. Lancer le backend et son faux ESP8266 (voir backend/README.md)
cd backend && docker compose up -d --build
docker compose run --rm backend node simulate-esp.js

# 2. Pointer le dashboard vers lui
cd ../frontend
cp .env.example .env        # VITE_API_URL=http://localhost:3000 (ou le port API_PORT de backend/.env)
npm run dev
```

Les cartes capteurs, les graphiques et les alertes se mettent alors à jour en temps réel
(socket.io), et le panneau de contrôle commande le boîtier.

## Sources de données

Copier `.env.example` en `.env` pour changer les adresses :

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `VITE_AI_URL` | service IA : caméra, détection, journal | `http://127.0.0.1:5001` |
| `VITE_API_URL` | backend capteurs / actionneurs (REST + socket.io) | vide (indisponible) |
| `VITE_WS_URL` | adresse du temps réel si elle diffère de l'API | `VITE_API_URL` |
| `VITE_USE_MOCK` | `true` = tout simuler, sans aucun service | `false` |

Relancer `npm run dev` après modification. Les services doivent autoriser l'origine du dashboard (CORS).

## Structure

```
src/
  components/   composants d'affichage (ne font aucun appel réseau)
  pages/        Dashboard.jsx : assemble les composants
  hooks/        useSentinelData.js : charge et met à jour toutes les données
  services/     api.js : seul fichier qui parle au service IA et au backend (fetch + socket.io),
                traduit leurs réponses vers le format du dashboard
  data/         mockData.js : simulateur utilisé quand VITE_USE_MOCK=true
  utils/        calcul des statuts, formatage
  styles/       global.css (variables, grille), components.css
  config.js     URLs, intervalle de rafraîchissement, seuils d'affichage
```

Flux des données : `api.js` -> `useSentinelData` -> `Dashboard` -> composants.

Le dashboard interroge les services toutes les 2 secondes. Quand le backend est configuré, ses événements socket.io (`sensors`, `alert`, `status`) arrivent en plus instantanément.

Chaque source est indépendante : si l'une ne répond pas, ses données s'affichent comme indisponibles et le reste continue de fonctionner.

## Service IA (en place)

Servi par `webcam-detection/stream_detection.py`. `api.js` traduit ses réponses vers le format du dashboard.

| Méthode | Route | Réponse |
| --- | --- | --- |
| GET | `/video` | flux MJPEG (`multipart/x-mixed-replace`) avec les personnes encadrées |
| GET | `/status` | `{ detection, personnes, latence_ms, heure }` |
| GET | `/logs` | `[{ id, heure, niveau, message }]`, `niveau` : `INFO`, `ALERTE` ou `ERREUR` |

Le service est utilisé tel quel, `api.js` complète ce qu'il ne fournit pas :

- `heure` (`HH:MM:SS`) est replacée sur la date du jour pour obtenir un `timestamp`.
- La caméra est considérée hors ligne si `heure` a plus de `CAMERA_TIMEOUT_MS` (`config.js`) : le service doit donc tourner sur une machine à la même heure que le dashboard.
- La confiance est lue dans le dernier message du journal (`confiance 0.87`), elle peut donc dater de quelques secondes.

Le niveau de menace est déduit de la confiance : `HIGH` à partir de `HIGH_THREAT_CONFIDENCE` (`config.js`), `MEDIUM` en dessous. Chaque ligne du journal devient une alerte du dashboard.

## Backend (en place)

Servi par `backend/` (voir son [README](../backend/README.md) pour le contrat complet). `api.js` traduit ses réponses vers le format du dashboard.

| Besoin du dashboard | Route du backend | Traduction faite par `api.js` |
| --- | --- | --- |
| dernière mesure | GET `/api/v1/status` → `latest` | `{ temp, hum, gas, pir }` → `{ temperature, humidity, gas, motion }` |
| historique | GET `/api/v1/history?limit=30` | même traduction, du plus ancien au plus récent |
| alertes | GET `/api/v1/alerts?limit=20` | `type` `temp` → `temperature`, `level` `warn` → `warning`, `source` `vision` → `ai` ; le `message` est construit à partir du type, du niveau et de la valeur ; `id` préfixé `api-` |
| état du boîtier | GET `/api/v1/status` | `actuators.led` (`red` / `green` / `off`) → `ledRed` / `ledGreen` ; `ip` n'existe pas (`--`) |
| commande | POST `/api/v1/commands` | `BUZZER_ON` → `{ buzzer: true }`, `LED_RED_ON` → `{ led: "red" }`, `LED_*_OFF` → `{ led: "off" }`, `ALARM_STOP` → `{ buzzer: false, led: "green" }` |
| temps réel | socket.io sur `VITE_API_URL` | événements `sensors`, `alert`, `status` → messages `{ type: sensor \| alert \| status, data }` |

À savoir :

- Le backend n'a qu'une LED à la fois (`red`, `green` ou `off`) : allumer la rouge éteint la verte, et inversement.
- `online` vient du backend : il passe à `false` quand le boîtier (ou le faux ESP) n'a rien publié depuis `DEVICE_OFFLINE_AFTER_S` secondes, et le dashboard affiche alors « OFFLINE ».
- Le backend doit autoriser l'origine du dashboard (`CORS_ORIGIN`, `*` par défaut).

## Format interne du dashboard

C'est le format produit par `api.js` et par `data/mockData.js`, consommé par le hook et les composants :

- mesure : `{ timestamp, temperature, humidity, gas, motion }`
- alerte : `{ id, timestamp, type, message, level }` avec `level` : `info`, `warning` ou `critical`
- état du boîtier : `{ online, ip, lastSeen, actuators: { buzzer, ledGreen, ledRed } }`
- détection IA : `{ timestamp, cameraOnline, humanDetected, people, confidence (0 à 1), threatLevel: LOW | MEDIUM | HIGH }`
- commandes : `BUZZER_ON`, `BUZZER_OFF`, `LED_GREEN_ON`, `LED_GREEN_OFF`, `LED_RED_ON`, `LED_RED_OFF`, `ALARM_STOP`
- `timestamp` : date ISO 8601 (`2026-10-06T10:42:00.000Z`)

Si les routes d'un service changent, seul `src/services/api.js` est à modifier.

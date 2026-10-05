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

Par défaut il tourne avec des **données simulées** : aucun backend n'est nécessaire.

## Brancher le backend

Copier `.env.example` en `.env`, puis :

```
VITE_USE_MOCK=false
VITE_API_URL=http://<ip-du-pc-serveur>:3000
```

Relancer `npm run dev`. Le backend doit autoriser l'origine du dashboard (CORS).

## Structure

```
src/
  components/   composants d'affichage (ne font aucun appel réseau)
  pages/        Dashboard.jsx : assemble les composants
  hooks/        useSentinelData.js : charge et met à jour toutes les données
  services/     api.js : seul fichier qui parle au backend (fetch + WebSocket)
  data/         mockData.js : simulateur utilisé quand VITE_USE_MOCK=true
  utils/        calcul des statuts, formatage
  styles/       global.css (variables, grille), components.css
  config.js     URLs, intervalle de rafraîchissement, seuils d'affichage
```

Flux des données : `api.js` -> `useSentinelData` -> `Dashboard` -> composants.

Le dashboard interroge l'API toutes les 2 secondes. Si un WebSocket est disponible, les mises à jour arrivent en plus instantanément.

## Contrat d'API attendu

| Méthode | Route | Réponse |
| --- | --- | --- |
| GET | `/api/v1/sensors/latest` | `{ timestamp, temperature, humidity, gas, motion }` |
| GET | `/api/v1/sensors/history?limit=30` | tableau du même objet, du plus ancien au plus récent |
| GET | `/api/v1/alerts?limit=20` | `[{ id, timestamp, type, message, level }]` |
| GET | `/api/v1/ai/latest` | `{ timestamp, humanDetected, confidence, threatLevel }` |
| GET | `/api/v1/status` | `{ online, ip, lastSeen, actuators: { buzzer, ledGreen, ledRed } }` |
| POST | `/api/v1/commands` | body `{ "command": "BUZZER_ON" }`, réponse `{ ok, actuators }` |
| GET | `/api/v1/camera/stream` | flux MJPEG (`multipart/x-mixed-replace`) |
| WS | `/ws` | messages `{ type, data }` |

Détails :

- `timestamp` : date ISO 8601 (`2026-10-06T10:42:00.000Z`)
- `motion`, `humanDetected` : booléens
- `confidence` : nombre entre 0 et 1
- `threatLevel` : `LOW`, `MEDIUM` ou `HIGH`
- `level` : `info`, `warning` ou `critical`
- commandes : `BUZZER_ON`, `BUZZER_OFF`, `LED_GREEN_ON`, `LED_GREEN_OFF`, `LED_RED_ON`, `LED_RED_OFF`, `ALARM_STOP`
- WebSocket : `type` vaut `sensor`, `alert`, `ai` ou `status`, et `data` a le même format que la route GET correspondante

Si les routes définitives sont différentes, seul `src/services/api.js` est à modifier.

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

Par défaut il affiche la **caméra et la détection IA réelles**, servies par
`webcam-detection/stream_detection.py` sur http://127.0.0.1:5001 (voir le
[README du module vision](../webcam-detection/README.md) pour le lancer). Les capteurs et les actionneurs
n'ont pas encore de backend : ils s'affichent « No data ».

## Sources de données

Copier `.env.example` en `.env` pour changer les adresses :

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `VITE_AI_URL` | service IA : caméra, détection, journal | `http://127.0.0.1:5001` |
| `VITE_API_URL` | backend capteurs / actionneurs | vide (indisponible) |
| `VITE_USE_MOCK` | `true` = tout simuler, sans aucun service | `false` |

Relancer `npm run dev` après modification. Les services doivent autoriser l'origine du dashboard (CORS).

## Structure

```
src/
  components/   composants d'affichage (ne font aucun appel réseau)
  pages/        Dashboard.jsx : assemble les composants
  hooks/        useSentinelData.js : charge et met à jour toutes les données
  services/     api.js : seul fichier qui parle au service IA et au backend (fetch + WebSocket)
  data/         mockData.js : simulateur utilisé quand VITE_USE_MOCK=true
  utils/        calcul des statuts, formatage
  styles/       global.css (variables, grille), components.css
  config.js     URLs, intervalle de rafraîchissement, seuils d'affichage
```

Flux des données : `api.js` -> `useSentinelData` -> `Dashboard` -> composants.

Le dashboard interroge les services toutes les 2 secondes. Si un WebSocket est disponible, les mises à jour arrivent en plus instantanément.

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

## Contrat d'API attendu pour le backend (à venir)

| Méthode | Route | Réponse |
| --- | --- | --- |
| GET | `/api/v1/sensors/latest` | `{ timestamp, temperature, humidity, gas, motion }` |
| GET | `/api/v1/sensors/history?limit=30` | tableau du même objet, du plus ancien au plus récent |
| GET | `/api/v1/alerts?limit=20` | `[{ id, timestamp, type, message, level }]`, ajoutées à celles du service IA |
| GET | `/api/v1/status` | `{ online, ip, lastSeen, actuators: { buzzer, ledGreen, ledRed } }` |
| POST | `/api/v1/commands` | body `{ "command": "BUZZER_ON" }`, réponse `{ ok, actuators }` |
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

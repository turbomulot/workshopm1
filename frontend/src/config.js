export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

// Service IA (webcam-detection/stream_detection.py) : flux caméra, détection, journal.
// 127.0.0.1 et non localhost : sous Windows, localhost tente d'abord l'IPv6,
// que le service n'écoute pas, et chaque requête perd environ 2 secondes.
export const AI_URL = import.meta.env.VITE_AI_URL || 'http://127.0.0.1:5001'

// Backend capteurs / actionneurs (backend/). Tant que VITE_API_URL est vide,
// ces données sont affichées comme indisponibles.
export const API_URL = import.meta.env.VITE_API_URL || null

// Temps réel : le backend utilise socket.io, servi à la même adresse que l'API
// (chemin /socket.io/). VITE_WS_URL ne sert que si le temps réel passe par une
// autre adresse que l'API (reverse proxy séparé).
export const WS_URL = API_URL ? import.meta.env.VITE_WS_URL || API_URL : null

// Une URL caméra explicite est respectée même en mode simulé (capteurs mockés,
// vraie webcam). Sinon : le flux du service IA, ou rien en mode simulé.
export const CAMERA_STREAM_URL =
  import.meta.env.VITE_CAMERA_URL || (USE_MOCK ? null : `${AI_URL}/video`)

export const POLL_INTERVAL_MS = 2000
export const HISTORY_LENGTH = 30

// Seuils utilisés uniquement pour l'affichage (couleur des cartes, statut global).
// La détection d'anomalies est faite côté IA / backend.
export const THRESHOLDS = {
  temperature: { warning: 35, critical: 45 },
  humidity: { warning: 75, critical: 90 },
  gas: { warning: 300, critical: 600 },
}

// Confiance de l'IA à partir de laquelle une personne vue est classée menace HIGH.
export const HIGH_THREAT_CONFIDENCE = 0.8

// Sans nouvelle analyse du service IA pendant ce délai, la caméra est considérée hors ligne.
export const CAMERA_TIMEOUT_MS = 10000

export const GAS_UNIT = 'ppm'

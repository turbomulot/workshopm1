export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000'
export const WS_URL = import.meta.env.VITE_WS_URL || `${API_URL.replace(/^http/, 'ws')}/ws`

// An explicit camera URL also works while sensor data remains simulated.
export const CAMERA_STREAM_URL = import.meta.env.VITE_CAMERA_URL || (
  USE_MOCK ? null : `${API_URL}/api/v1/camera/stream`
)

export const POLL_INTERVAL_MS = 2000
export const HISTORY_LENGTH = 30

// Seuils utilisés uniquement pour l'affichage (couleur des cartes, statut global).
// La détection d'anomalies est faite côté IA / backend.
export const THRESHOLDS = {
  temperature: { warning: 35, critical: 45 },
  humidity: { warning: 75, critical: 90 },
  gas: { warning: 300, critical: 600 },
}

export const GAS_UNIT = 'ppm'

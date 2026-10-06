import {
  AI_URL,
  API_URL,
  WS_URL,
  USE_MOCK,
  HISTORY_LENGTH,
  HIGH_THREAT_CONFIDENCE,
  CAMERA_TIMEOUT_MS,
} from '../config'
import * as mock from '../data/mockData'

async function request(baseUrl, path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, options)
  if (!response.ok) {
    throw new Error(`API error ${response.status} on ${path}`)
  }
  return response.json()
}

// --- Service IA : traduit ses réponses vers le format du dashboard ---

const LOG_LEVELS = {
  ALERTE: { type: 'ai', level: 'critical' },
  ERREUR: { type: 'camera', level: 'warning' },
  INFO: { type: 'ai', level: 'info' },
}

// Le service ne donne que l'heure (HH:MM:SS) : on la replace sur la date du jour.
// Une heure dans le futur vient de la veille (journal lu juste après minuit).
function toTimestamp(heure) {
  if (!heure) return null
  const [hours, minutes, seconds] = heure.split(':').map(Number)
  const date = new Date()
  date.setHours(hours, minutes, seconds, 0)
  if (date.getTime() - Date.now() > 60000) date.setDate(date.getDate() - 1)
  return date.toISOString()
}

// /status ne contient pas la confiance : elle n'apparaît que dans les messages
// du journal (« ... confiance 0.87) »). On lit donc le message le plus récent.
function lastConfidence(logs) {
  for (let i = logs.length - 1; i >= 0; i -= 1) {
    const match = /confiance (\d+(?:\.\d+)?)/.exec(logs[i].message)
    if (match) return Number(match[1])
  }
  return null
}

// /status : { detection, personnes, latence_ms, heure }
// Si la caméra ne répond plus, le service arrête l'analyse et /status reste figé :
// la caméra est donc considérée en ligne tant que « heure » est récente.
function toDetection(status, logs) {
  const timestamp = toTimestamp(status.heure)
  const cameraOnline =
    Boolean(timestamp) && Math.abs(Date.now() - new Date(timestamp)) < CAMERA_TIMEOUT_MS
  const humanDetected = cameraOnline && Boolean(status.detection)
  const confidence = humanDetected ? lastConfidence(logs) : null
  let threatLevel = 'LOW'
  if (humanDetected) threatLevel = confidence >= HIGH_THREAT_CONFIDENCE ? 'HIGH' : 'MEDIUM'

  return {
    timestamp,
    cameraOnline,
    humanDetected,
    people: humanDetected ? status.personnes || 0 : 0,
    confidence,
    threatLevel,
    latencyMs: status.latence_ms,
  }
}

// /logs : [{ id, heure, niveau, message }, ...]
function toAlert(log) {
  return {
    id: `ai-${log.id}`,
    timestamp: toTimestamp(log.heure),
    message: log.message,
    ...(LOG_LEVELS[log.niveau] || LOG_LEVELS.INFO),
  }
}

// --- Données du dashboard ---
// Les fonctions qui dépendent du backend renvoient null (ou une liste vide)
// tant qu'il n'est pas configuré : le dashboard affiche alors « pas de donnée ».

// { timestamp, temperature, humidity, gas, motion }
export async function getLatestSensorData() {
  if (USE_MOCK) return mock.getLatestSensorData()
  if (!API_URL) return null
  return request(API_URL, '/api/v1/sensors/latest')
}

// [{ timestamp, temperature, humidity, gas, motion }, ...] du plus ancien au plus récent
export async function getSensorHistory(limit = HISTORY_LENGTH) {
  if (USE_MOCK) return mock.getSensorHistory()
  if (!API_URL) return []
  return request(API_URL, `/api/v1/sensors/history?limit=${limit}`)
}

// [{ id, timestamp, type, message, level }, ...]
// Réunit le journal du service IA et, quand il existe, les alertes du backend.
export async function getAlerts(limit = 20) {
  if (USE_MOCK) return mock.getAlerts()

  const sources = [request(AI_URL, '/logs').then((logs) => logs.map(toAlert))]
  if (API_URL) sources.push(request(API_URL, `/api/v1/alerts?limit=${limit}`))

  const results = await Promise.allSettled(sources)
  const available = results.filter((result) => result.status === 'fulfilled')
  if (available.length === 0) throw results[0].reason
  return available.flatMap((result) => result.value)
}

// { timestamp, cameraOnline, humanDetected, people, confidence (0 à 1, ou null si inconnue),
//   threatLevel: LOW | MEDIUM | HIGH, latencyMs }
export async function getAIDetection() {
  if (USE_MOCK) return mock.getAIDetection()
  const [status, logs] = await Promise.all([
    request(AI_URL, '/status'),
    request(AI_URL, '/logs').catch(() => []),
  ])
  return toDetection(status, logs)
}

// { online, ip, lastSeen, actuators: { buzzer, ledGreen, ledRed } }
export async function getDeviceStatus() {
  if (USE_MOCK) return mock.getDeviceStatus()
  if (!API_URL) return null
  return request(API_URL, '/api/v1/status')
}

// Réponse attendue : { ok, actuators: { buzzer, ledGreen, ledRed } }
export async function sendCommand(command) {
  if (USE_MOCK) return mock.sendCommand(command)
  if (!API_URL) throw new Error('Backend not configured')
  return request(API_URL, '/api/v1/commands', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  })
}

// Messages attendus : { type: 'sensor' | 'alert' | 'ai' | 'status', data: {...} }
// Retourne une fonction pour fermer la connexion.
export function connectWebSocket(onMessage) {
  if (USE_MOCK || !WS_URL) return () => {}

  let socket
  let retryTimer
  let closed = false

  function open() {
    socket = new WebSocket(WS_URL)
    socket.onmessage = (event) => {
      try {
        onMessage(JSON.parse(event.data))
      } catch {
        console.warn('WebSocket: message ignoré (JSON invalide)')
      }
    }
    socket.onclose = () => {
      if (!closed) retryTimer = setTimeout(open, 3000)
    }
  }

  open()

  return () => {
    closed = true
    clearTimeout(retryTimer)
    socket.close()
  }
}

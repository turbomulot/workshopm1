import { io } from 'socket.io-client'
import {
  AI_URL,
  API_URL,
  WS_URL,
  USE_MOCK,
  HISTORY_LENGTH,
  HIGH_THREAT_CONFIDENCE,
  CAMERA_TIMEOUT_MS,
  GAS_UNIT,
} from '../config'
import * as mock from '../data/mockData'

// Seul fichier qui parle au service IA et au backend. Chaque réponse est traduite
// vers le format du dashboard (celui de data/mockData.js) : les composants et le
// hook ne connaissent pas les contrats des services.

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

// /status : { detection, personnes, latence_ms, heure, confiance?, camera_connected? }
// Si la caméra ne répond plus, le service arrête l'analyse et /status reste figé :
// la caméra est donc considérée en ligne tant que « heure » est récente.
function toDetection(status, logs) {
  const timestamp = toTimestamp(status.heure)
  const cameraOnline =
    Boolean(timestamp) &&
    status.camera_connected !== false &&
    Math.abs(Date.now() - new Date(timestamp)) < CAMERA_TIMEOUT_MS
  const humanDetected = cameraOnline && Boolean(status.detection)
  // Les versions récentes du service donnent la confiance dans /status ; les
  // anciennes seulement dans les messages du journal.
  const confidence = humanDetected
    ? (typeof status.confiance === 'number' ? status.confiance : lastConfidence(logs))
    : null
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
function toAIAlert(log) {
  return {
    id: `ai-${log.id}`,
    timestamp: toTimestamp(log.heure),
    message: log.message,
    ...(LOG_LEVELS[log.niveau] || LOG_LEVELS.INFO),
  }
}

// --- Backend (backend/README.md) : traduit ses réponses vers le format du dashboard ---

// Mesure du backend : { id, timestamp, temp, hum, gas, pir }
function toReading(measurement) {
  if (!measurement) return null
  return {
    timestamp: measurement.timestamp,
    temperature: measurement.temp ?? null,
    humidity: measurement.hum ?? null,
    gas: measurement.gas ?? null,
    motion: measurement.pir === null || measurement.pir === undefined ? null : Boolean(measurement.pir),
  }
}

// Le backend nomme les capteurs et les niveaux à sa façon.
const SENSOR_NAMES = { temp: 'temperature', hum: 'humidity', gas: 'gas', motion: 'motion' }
const LEVEL_NAMES = { info: 'info', warn: 'warning', critical: 'critical' }

const SENSOR_MESSAGES = {
  temperature: { warning: 'Temperature anomaly', critical: 'Critical temperature reached' },
  humidity: { warning: 'High humidity level', critical: 'Critical humidity level' },
  gas: { warning: 'Abnormal gas level', critical: 'High gas level detected' },
  motion: { info: 'Zone clear', warning: 'Motion detected', critical: 'Motion detected' },
}
const SENSOR_UNITS = { temperature: '°C', humidity: '%', gas: GAS_UNIT }

// Le backend n'envoie pas de phrase : on la construit à partir du type et de la valeur.
function describeAlert(source, type, level, value) {
  if (source === 'vision') {
    const people = typeof value === 'object' && value !== null ? value.people : null
    const confidence = typeof value === 'object' && value !== null ? value.confidence : null
    const details = []
    if (people) details.push(`${people} ${people > 1 ? 'people' : 'person'}`)
    if (typeof confidence === 'number') details.push(`${Math.round(confidence * 100)}%`)
    const base = type === 'person_detected' ? 'Human detected by camera' : `Camera: ${type}`
    return details.length ? `${base} (${details.join(', ')})` : base
  }

  const base = SENSOR_MESSAGES[type]?.[level]
  if (base) {
    const unit = SENSOR_UNITS[type]
    return typeof value === 'number' && unit ? `${base} (${value} ${unit})` : base
  }
  return typeof value === 'number' ? `${type}: ${value}` : type
}

// Alerte du backend : { id, timestamp, source, type, level, value }
// Même traduction pour la liste REST et les messages socket.io, pour que les ids
// coïncident et que le hook puisse dédoublonner.
function toBackendAlert(alert) {
  const type = alert.source === 'vision' ? 'ai' : SENSOR_NAMES[alert.type] || alert.type
  const level = LEVEL_NAMES[alert.level] || 'info'
  return {
    id: `api-${alert.id}`,
    timestamp: alert.timestamp,
    type,
    level,
    message: describeAlert(alert.source, type, level, alert.value),
  }
}

// Le backend ne connaît qu'une LED à la fois (red / green / off) ; le dashboard
// affiche deux lampes indépendantes.
function toActuators(actuators) {
  if (!actuators) return undefined
  return {
    buzzer: Boolean(actuators.buzzer),
    ledGreen: actuators.led === 'green',
    ledRed: actuators.led === 'red',
  }
}

// Statut du backend : { online, lastSeen, mqttConnected, actuators: { buzzer, led }, latest }
function toDeviceStatus(status) {
  return {
    online: Boolean(status.online),
    ip: null,
    lastSeen: status.lastSeen,
    mqttConnected: Boolean(status.mqttConnected),
    actuators: toActuators(status.actuators),
  }
}

// Commandes du panneau de contrôle -> body de POST /api/v1/commands ({ buzzer, led }).
const COMMANDS = {
  BUZZER_ON: { buzzer: true },
  BUZZER_OFF: { buzzer: false },
  LED_GREEN_ON: { led: 'green' },
  LED_GREEN_OFF: { led: 'off' },
  LED_RED_ON: { led: 'red' },
  LED_RED_OFF: { led: 'off' },
  ALARM_STOP: { buzzer: false, led: 'green' },
}

// --- Données du dashboard ---
// Les fonctions qui dépendent du backend renvoient null (ou une liste vide)
// tant qu'il n'est pas configuré : le dashboard affiche alors « pas de donnée ».

// { timestamp, temperature, humidity, gas, motion }
// Le backend n'a pas de route « dernière mesure » : elle est dans /status.latest.
export async function getLatestSensorData() {
  if (USE_MOCK) return mock.getLatestSensorData()
  if (!API_URL) return null
  const status = await request(API_URL, '/api/v1/status')
  return toReading(status.latest)
}

// [{ timestamp, temperature, humidity, gas, motion }, ...] du plus ancien au plus récent
export async function getSensorHistory(limit = HISTORY_LENGTH) {
  if (USE_MOCK) return mock.getSensorHistory()
  if (!API_URL) return []
  const measurements = await request(API_URL, `/api/v1/history?limit=${limit}`)
  return measurements.map(toReading)
}

// [{ id, timestamp, type, message, level }, ...]
// Réunit le journal du service IA et, quand il existe, les alertes du backend.
export async function getAlerts(limit = 20) {
  if (USE_MOCK) return mock.getAlerts()

  const sources = [request(AI_URL, '/logs').then((logs) => logs.map(toAIAlert))]
  if (API_URL) {
    sources.push(
      request(API_URL, `/api/v1/alerts?limit=${limit}`).then((alerts) => alerts.map(toBackendAlert))
    )
  }

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

// { online, ip, lastSeen, mqttConnected, actuators: { buzzer, ledGreen, ledRed } }
export async function getDeviceStatus() {
  if (USE_MOCK) return mock.getDeviceStatus()
  if (!API_URL) return null
  return toDeviceStatus(await request(API_URL, '/api/v1/status'))
}

// command : BUZZER_ON, BUZZER_OFF, LED_GREEN_ON, LED_GREEN_OFF, LED_RED_ON, LED_RED_OFF, ALARM_STOP
// Réponse : { ok, actuators: { buzzer, ledGreen, ledRed } }
export async function sendCommand(command) {
  if (USE_MOCK) return mock.sendCommand(command)
  if (!API_URL) throw new Error('Backend not configured')
  const body = COMMANDS[command]
  if (!body) throw new Error(`Unknown command: ${command}`)
  const result = await request(API_URL, '/api/v1/commands', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return { ok: Boolean(result.ok), actuators: toActuators(result.actuators) }
}

// Temps réel : le backend pousse ses événements socket.io « sensors », « alert »
// et « status ». Ils sont traduits en { type: 'sensor' | 'alert' | 'status', data }.
// Retourne une fonction pour fermer la connexion.
export function connectWebSocket(onMessage) {
  if (USE_MOCK || !WS_URL) return () => {}

  const socket = io(WS_URL, {
    reconnectionDelay: 3000,
    reconnectionDelayMax: 3000,
  })

  socket.on('sensors', (measurement) => {
    const reading = toReading(measurement)
    if (reading) onMessage({ type: 'sensor', data: reading })
  })
  socket.on('alert', (alert) => onMessage({ type: 'alert', data: toBackendAlert(alert) }))
  socket.on('status', (status) => onMessage({ type: 'status', data: toDeviceStatus(status) }))
  socket.on('connect_error', (error) => console.warn('socket.io:', error.message))

  return () => socket.disconnect()
}

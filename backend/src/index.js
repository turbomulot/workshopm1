import http from 'node:http'
import express from 'express'
import cors from 'cors'
import { Server } from 'socket.io'
import { config } from './config.js'
import * as db from './db.js'
import { startMqtt } from './mqtt.js'
import { createRoutes } from './routes.js'

const ALERT_TYPES = ['gas', 'motion', 'temp']
const ALERT_LEVELS = ['warn', 'critical']

const app = express()
const server = http.createServer(app)
const io = new Server(server, { cors: { origin: config.corsOrigin } })

// --- État du boîtier, gardé en mémoire ---
const device = {
  lastSeen: null,
  online: false,
  latest: null,
  actuators: { buzzer: false, led: 'off' },

  status() {
    return {
      online: this.online,
      lastSeen: this.lastSeen ? new Date(this.lastSeen).toISOString() : null,
      mqttConnected: broker.isConnected(),
      actuators: this.actuators,
      latest: this.latest,
    }
  },

  setActuators(actuators) {
    this.actuators = actuators
    io.emit('status', this.status())
  },

  // Appelé à chaque message du boîtier, et chaque seconde pour détecter son silence.
  refreshOnline(seen = false) {
    if (seen) this.lastSeen = Date.now()
    const online = this.lastSeen !== null && Date.now() - this.lastSeen < config.offlineAfterMs
    if (online !== this.online) {
      this.online = online
      console.log(`[boîtier] ${online ? 'en ligne' : 'hors ligne'}`)
      io.emit('status', this.status())
    }
  },
}

function numberOrNull(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

// « ts » est l'heure Unix du boîtier (en secondes). Un boîtier sans horloge envoie
// son temps depuis l'allumage : dans ce cas on garde l'heure de réception.
function toDate(ts) {
  if (typeof ts !== 'number' || ts < 1e9) return new Date()
  return new Date(ts < 1e12 ? ts * 1000 : ts)
}

// Mesure : { temp, hum, gas, pir, ts }. Le firmware du groupe nomme ces champs t et h.
async function handleSensors(payload) {
  const measurement = {
    ts: toDate(payload.ts),
    temp: numberOrNull(payload.temp ?? payload.t),
    hum: numberOrNull(payload.hum ?? payload.h),
    gas: numberOrNull(payload.gas) === null ? null : Math.round(payload.gas),
    pir: payload.pir === 1 || payload.pir === true ? 1 : payload.pir === 0 || payload.pir === false ? 0 : null,
  }
  if (Object.values(measurement).filter((value) => value !== null).length === 1) {
    console.warn('[mqtt] mesure ignorée (aucune valeur exploitable)')
    return
  }

  device.refreshOnline(true)
  let saved
  try {
    saved = await db.saveMeasurement(measurement)
  } catch (error) {
    // Base indisponible : le dashboard reçoit quand même la mesure en direct.
    console.error('[db] mesure non enregistrée :', error.message)
    const { ts, ...values } = measurement
    saved = { timestamp: ts.toISOString(), ...values }
  }
  device.latest = saved
  io.emit('sensors', saved)
}

// Alerte : { type, level, value }
async function handleAlert(payload) {
  if (!ALERT_TYPES.includes(payload.type) || !ALERT_LEVELS.includes(payload.level)) {
    console.warn('[mqtt] alerte ignorée (type ou level inconnu)')
    return
  }
  device.refreshOnline(true)
  const alert = await db.saveAlert({
    ts: new Date(),
    source: 'esp8266',
    type: payload.type,
    level: payload.level,
    value: numberOrNull(payload.value),
  })
  io.emit('alert', alert)
}

// Événement du firmware du groupe : { type, value, ts }, publié à chaque changement
// d'état d'un capteur. « pir » devient une alerte de mouvement.
async function handleEvent(payload) {
  if (typeof payload.type !== 'string' || !/^\w{1,32}$/.test(payload.type)) {
    console.warn('[mqtt] événement ignoré (type invalide)')
    return
  }
  device.refreshOnline(true)
  const value = numberOrNull(payload.value)
  const motion = payload.type === 'pir'
  const alert = await db.saveAlert({
    ts: toDate(payload.ts),
    source: 'esp8266',
    type: motion ? 'motion' : payload.type,
    level: motion ? (value ? 'critical' : 'info') : null,
    value,
  })
  io.emit('alert', alert)
}

// Statut annoncé par le boîtier lui-même : « online » à la connexion, « offline »
// publié par le broker dès que le boîtier disparaît (Last Will).
function handleStatus(text) {
  if (text === 'online') device.refreshOnline(true)
  if (text === 'offline') {
    device.lastSeen = null
    device.refreshOnline()
  }
}

// Les deux contrats sont acceptés : sensors / alerts, et telemetry / event / status
// (firmware du groupe). « cmd » porte nos propres commandes : rien à faire.
const broker = startMqtt((leaf, payload) => {
  if (leaf === 'status') return handleStatus(payload)
  if (payload === null || typeof payload !== 'object' || Array.isArray(payload)) return undefined
  if (leaf === 'sensors' || leaf === 'telemetry') return handleSensors(payload)
  if (leaf === 'alerts') return handleAlert(payload)
  if (leaf === 'event') return handleEvent(payload)
  return undefined
})

// --- API REST ---
app.use(cors({ origin: config.corsOrigin }))
app.use(express.json({ limit: '10kb' }))

app.use('/api/v1', createRoutes({ device, broker, io }))

app.use((req, res) => res.status(404).json({ error: 'Route inconnue' }))
app.use((error, req, res, next) => {
  if (error.type === 'entity.parse.failed') return res.status(400).json({ error: 'JSON invalide' })
  if (error.type === 'entity.too.large') return res.status(413).json({ error: 'Body trop volumineux' })
  console.error('[api]', error.message)
  return res.status(500).json({ error: 'Erreur interne' })
})

// Chaque dashboard qui se connecte reçoit tout de suite l'état du boîtier.
io.on('connection', (socket) => socket.emit('status', device.status()))

setInterval(() => device.refreshOnline(), 1000)

await db.initDb()
server.listen(config.port, () => console.log(`[api] à l'écoute sur le port ${config.port}`))

function stop() {
  server.close(() => process.exit(0))
  setTimeout(() => process.exit(0), 2000)
}
process.on('SIGTERM', stop)
process.on('SIGINT', stop)

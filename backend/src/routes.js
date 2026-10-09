import { Router } from 'express'
import { config } from './config.js'
import * as db from './db.js'

const ALERT_SOURCES = ['esp8266', 'vision']
const ALERT_LEVELS = ['info', 'warn', 'critical']
const LED_VALUES = ['red', 'green', 'off']

function readLimit(value, fallback, max) {
  if (value === undefined) return fallback
  const limit = Number(value)
  return Number.isInteger(limit) && limit >= 1 ? Math.min(limit, max) : null
}

// Renvoie le message d'erreur, ou null si le body est valide.
function validateAlert(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return 'body JSON attendu'
  if (!ALERT_SOURCES.includes(body.source)) return `source : ${ALERT_SOURCES.join(' ou ')}`
  if (typeof body.type !== 'string' || !body.type.trim() || body.type.length > 50) {
    return 'type : chaîne non vide (50 caractères max)'
  }
  if (!('value' in body)) return 'value : obligatoire'
  if (typeof body.timestamp !== 'string' || Number.isNaN(Date.parse(body.timestamp))) {
    return 'timestamp : date ISO 8601'
  }
  if (body.level !== undefined && !ALERT_LEVELS.includes(body.level)) {
    return `level (optionnel) : ${ALERT_LEVELS.join(', ')}`
  }
  return null
}

function validateCommand(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return 'body JSON attendu'
  if (body.buzzer === undefined && body.led === undefined) return 'buzzer ou led attendu'
  if (body.buzzer !== undefined && typeof body.buzzer !== 'boolean') return 'buzzer : booléen'
  if (body.led !== undefined && !LED_VALUES.includes(body.led)) return `led : ${LED_VALUES.join(', ')}`
  return null
}

// Messages à publier sur le topic cmd, selon le format attendu par le boîtier.
// request : ce que le dashboard veut changer. state : l'état complet qui en résulte.
function toMqttMessages(request, state) {
  if (config.cmdFormat === 'state') return [state]

  // Firmware du groupe : une commande par action, et deux LED indépendantes.
  const commands = []
  if (request.buzzer !== undefined) commands.push(request.buzzer ? 'BUZZER_ON' : 'BUZZER_OFF')
  if (request.led !== undefined) {
    commands.push(request.led === 'red' ? 'LED_RED_ON' : 'LED_RED_OFF')
    commands.push(request.led === 'green' ? 'LED_GREEN_ON' : 'LED_GREEN_OFF')
  }
  return commands.map((command) => ({ command }))
}

// Express 4 ne transmet pas seul les erreurs des routes async au gestionnaire d'erreurs.
const wrap = (handler) => (req, res, next) => handler(req, res, next).catch(next)

// device : état du boîtier tenu par index.js. broker : connexion MQTT. io : socket.io.
export function createRoutes({ device, broker, io }) {
  const router = Router()

  // Changements d'état des capteurs et détections de l'IA webcam.
  router.post('/alerts', wrap(async (req, res) => {
    const error = validateAlert(req.body)
    if (error) return res.status(400).json({ error })

    const { source, type, value, timestamp, level } = req.body
    const alert = await db.saveAlert({ ts: new Date(timestamp), source, type: type.trim(), level, value })
    io.emit('alert', alert)
    return res.status(201).json(alert)
  }))

  router.get('/alerts', wrap(async (req, res) => {
    const limit = readLimit(req.query.limit, 20, 200)
    if (limit === null) return res.status(400).json({ error: 'limit : entier positif' })
    return res.json(await db.getAlerts(limit))
  }))

  router.get('/history', wrap(async (req, res) => {
    const { sensor } = req.query
    if (sensor !== undefined && !db.SENSOR_COLUMNS.includes(sensor)) {
      return res.status(400).json({ error: `sensor : ${db.SENSOR_COLUMNS.join(', ')}` })
    }
    const limit = readLimit(req.query.limit, 100, 1000)
    if (limit === null) return res.status(400).json({ error: 'limit : entier positif' })
    return res.json(await db.getHistory(limit, sensor))
  }))

  router.get('/status', (req, res) => {
    res.json(device.status())
  })

  router.post('/commands', wrap(async (req, res) => {
    const error = validateCommand(req.body)
    if (error) return res.status(400).json({ error })

    // Le firmware attend toujours les deux champs : on complète avec le dernier état connu.
    const command = { ...device.actuators }
    if (req.body.buzzer !== undefined) command.buzzer = req.body.buzzer
    if (req.body.led !== undefined) command.led = req.body.led

    try {
      await broker.publishCommands(toMqttMessages(req.body, command))
    } catch (publishError) {
      return res.status(503).json({ error: publishError.message })
    }
    device.setActuators(command)
    return res.json({ ok: true, actuators: command })
  }))

  return router
}

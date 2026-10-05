import { HISTORY_LENGTH, POLL_INTERVAL_MS } from '../config'
import { getSensorStatus } from '../utils/status'

// Simulateur : reproduit le format exact attendu du backend.
// Il rejoue un scénario en boucle (détection de mouvement, puis fuite de gaz)
// pour pouvoir tester tous les états du dashboard sans matériel.

const ALERT_MESSAGES = {
  temperature: { warning: 'Temperature anomaly', critical: 'Critical temperature reached' },
  humidity: { warning: 'High humidity level', critical: 'Critical humidity level' },
  gas: { warning: 'Gas level rising', critical: 'High gas level detected' },
  motion: { critical: 'Motion detected' },
}

const state = { temperature: 24.5, humidity: 52, gas: 120, motion: false }
const actuators = { buzzer: false, ledGreen: true, ledRed: false }
const lastStatus = {}
let aiDetection = { humanDetected: false, confidence: 0, threatLevel: 'LOW' }
let history = []
let alerts = []
let tick = 0
let nextAlertId = 1

function drift(value, amplitude, min, max) {
  const next = value + (Math.random() - 0.5) * amplitude
  return Math.min(max, Math.max(min, next))
}

function addAlert(type, level, message, timestamp) {
  alerts = [{ id: nextAlertId++, timestamp, type, level, message }, ...alerts].slice(0, 50)
}

function step(date) {
  tick += 1
  const timestamp = date.toISOString()
  const gasLeak = tick % 55 >= 40 && tick % 55 < 48
  const motion = tick % 25 >= 20
  const humanSeen = tick % 25 >= 21

  const temperatureTarget = gasLeak ? 31 : 24.5
  state.temperature = drift(state.temperature + (temperatureTarget - state.temperature) * 0.1, 0.4, 15, 60)
  state.humidity = drift(state.humidity + (52 - state.humidity) * 0.1, 1.5, 20, 95)
  state.gas = drift(state.gas + ((gasLeak ? 700 : 120) - state.gas) * 0.35, 20, 40, 1023)
  state.motion = motion

  const reading = {
    timestamp,
    temperature: Math.round(state.temperature * 10) / 10,
    humidity: Math.round(state.humidity),
    gas: Math.round(state.gas),
    motion: state.motion,
  }

  for (const sensor of Object.keys(ALERT_MESSAGES)) {
    const status = getSensorStatus(sensor, reading[sensor])
    if (status !== 'normal' && status !== lastStatus[sensor]) {
      addAlert(sensor, status, ALERT_MESSAGES[sensor][status], timestamp)
    }
    lastStatus[sensor] = status
  }

  if (humanSeen && !aiDetection.humanDetected) {
    addAlert('ai', 'critical', 'Human detected by camera', timestamp)
  }
  const confidence = humanSeen ? 0.82 + Math.random() * 0.14 : 0
  aiDetection = {
    timestamp,
    humanDetected: humanSeen,
    confidence: Math.round(confidence * 100) / 100,
    threatLevel: !humanSeen ? 'LOW' : confidence > 0.86 ? 'HIGH' : 'MEDIUM',
  }

  history = [...history, reading].slice(-HISTORY_LENGTH)
  return reading
}

const startTime = Date.now() - HISTORY_LENGTH * POLL_INTERVAL_MS
addAlert('system', 'info', 'Sentinel-X node connected', new Date(startTime).toISOString())
for (let i = 1; i <= HISTORY_LENGTH; i++) {
  step(new Date(startTime + i * POLL_INTERVAL_MS))
}

export async function getLatestSensorData() {
  return step(new Date())
}

export async function getSensorHistory() {
  return history
}

export async function getAlerts() {
  return alerts
}

export async function getAIDetection() {
  return aiDetection
}

export async function getDeviceStatus() {
  return {
    online: true,
    ip: '192.168.10.15',
    lastSeen: new Date().toISOString(),
    actuators: { ...actuators },
  }
}

export async function sendCommand(command) {
  switch (command) {
    case 'BUZZER_ON':
      actuators.buzzer = true
      break
    case 'BUZZER_OFF':
      actuators.buzzer = false
      break
    case 'LED_GREEN_ON':
      actuators.ledGreen = true
      break
    case 'LED_GREEN_OFF':
      actuators.ledGreen = false
      break
    case 'LED_RED_ON':
      actuators.ledRed = true
      break
    case 'LED_RED_OFF':
      actuators.ledRed = false
      break
    case 'ALARM_STOP':
      actuators.buzzer = false
      actuators.ledRed = false
      actuators.ledGreen = true
      break
    default:
      throw new Error(`Unknown command: ${command}`)
  }
  addAlert('system', 'info', `Command ${command} sent`, new Date().toISOString())
  return { ok: true, actuators: { ...actuators } }
}

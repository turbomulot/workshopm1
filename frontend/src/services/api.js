import { API_URL, WS_URL, USE_MOCK, HISTORY_LENGTH } from '../config'
import * as mock from '../data/mockData'

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!response.ok) {
    throw new Error(`API error ${response.status} on ${path}`)
  }
  return response.json()
}

// { timestamp, temperature, humidity, gas, motion }
export function getLatestSensorData() {
  if (USE_MOCK) return mock.getLatestSensorData()
  return request('/api/v1/sensors/latest')
}

// [{ timestamp, temperature, humidity, gas, motion }, ...] du plus ancien au plus récent
export function getSensorHistory(limit = HISTORY_LENGTH) {
  if (USE_MOCK) return mock.getSensorHistory()
  return request(`/api/v1/sensors/history?limit=${limit}`)
}

// [{ id, timestamp, type, message, level }, ...]
export function getAlerts(limit = 20) {
  if (USE_MOCK) return mock.getAlerts()
  return request(`/api/v1/alerts?limit=${limit}`)
}

// { timestamp, humanDetected, confidence (0 à 1), threatLevel: LOW | MEDIUM | HIGH }
export function getAIDetection() {
  if (USE_MOCK) return mock.getAIDetection()
  return request('/api/v1/ai/latest')
}

// { online, ip, lastSeen, actuators: { buzzer, ledGreen, ledRed } }
export function getDeviceStatus() {
  if (USE_MOCK) return mock.getDeviceStatus()
  return request('/api/v1/status')
}

// Réponse attendue : { ok, actuators: { buzzer, ledGreen, ledRed } }
export function sendCommand(command) {
  if (USE_MOCK) return mock.sendCommand(command)
  return request('/api/v1/commands', {
    method: 'POST',
    body: JSON.stringify({ command }),
  })
}

// Messages attendus : { type: 'sensor' | 'alert' | 'ai' | 'status', data: {...} }
// Retourne une fonction pour fermer la connexion.
export function connectWebSocket(onMessage) {
  if (USE_MOCK) return () => {}

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

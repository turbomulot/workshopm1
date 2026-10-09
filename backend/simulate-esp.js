// Faux ESP8266 : publie des mesures toutes les 2 s sur sentinel/sensors, et de temps
// en temps une alerte sur sentinel/alerts, pour tester sans le boîtier branché.
// La racine « sentinel » se change avec MQTT_BASE_TOPIC.
//
//   Dans Docker :  cd backend, puis docker compose run --rm backend node simulate-esp.js
//   Sur le PC   :  cd backend, npm install, npm run simulate   (broker sur localhost:1883)
import 'dotenv/config'
import mqtt from 'mqtt'

const MQTT_URL = process.env.MQTT_URL || 'mqtt://localhost:1883'
const BASE_TOPIC = process.env.MQTT_BASE_TOPIC || 'sentinel'
const PERIOD_MS = 2000

// Mêmes seuils que le dashboard (frontend/src/config.js).
const THRESHOLDS = {
  temp: { warn: 35, critical: 45 },
  gas: { warn: 300, critical: 600 },
}

const client = mqtt.connect(MQTT_URL, {
  username: process.env.MQTT_USERNAME || undefined,
  password: process.env.MQTT_PASSWORD || undefined,
  reconnectPeriod: 2000,
})

const state = { temp: 24.5, hum: 52, gas: 120 }
const lastLevel = {}
let tick = 0
let lastPir = 0

function drift(value, target, pull, noise, min, max) {
  const next = value + (target - value) * pull + (Math.random() - 0.5) * noise
  return Math.min(max, Math.max(min, next))
}

function levelOf(sensor, value) {
  if (value >= THRESHOLDS[sensor].critical) return 'critical'
  if (value >= THRESHOLDS[sensor].warn) return 'warn'
  return null
}

function publish(topic, payload) {
  client.publish(topic, JSON.stringify(payload), { qos: 1 })
  console.log(topic, JSON.stringify(payload))
}

// Scénario rejoué en boucle : passage devant le PIR, puis fuite de gaz qui chauffe la pièce.
function step() {
  if (!client.connected) return
  tick += 1
  const gasLeak = tick % 60 >= 40 && tick % 60 < 50
  const pir = tick % 25 >= 20 ? 1 : 0

  state.temp = drift(state.temp, gasLeak ? 38 : 24.5, 0.12, 0.4, 10, 60)
  state.hum = drift(state.hum, 52, 0.1, 1.5, 20, 95)
  state.gas = drift(state.gas, gasLeak ? 720 : 120, 0.35, 20, 40, 1023)

  const sensors = {
    temp: Math.round(state.temp * 10) / 10,
    hum: Math.round(state.hum * 10) / 10,
    gas: Math.round(state.gas),
    pir,
    ts: Math.floor(Date.now() / 1000),
  }
  publish(`${BASE_TOPIC}/sensors`, sensors)

  // Une alerte à chaque changement de niveau, comme le ferait le firmware.
  for (const sensor of Object.keys(THRESHOLDS)) {
    const level = levelOf(sensor, sensors[sensor])
    if (level && level !== lastLevel[sensor]) {
      publish(`${BASE_TOPIC}/alerts`, { type: sensor, level, value: sensors[sensor] })
    }
    lastLevel[sensor] = level
  }
  if (pir && !lastPir) publish(`${BASE_TOPIC}/alerts`, { type: 'motion', level: 'critical', value: 1 })
  lastPir = pir
}

client.on('connect', () => {
  console.log(`Simulateur connecté à ${MQTT_URL}`)
  client.subscribe(`${BASE_TOPIC}/cmd`)
})
client.on('reconnect', () => console.log('Reconnexion au broker...'))
client.on('error', (error) => console.error('Erreur MQTT :', error.message))
client.on('message', (topic, buffer) => console.log(`>> commande reçue : ${buffer.toString()}`))

setInterval(step, PERIOD_MS)

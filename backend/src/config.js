import 'dotenv/config'
import fs from 'node:fs'

// Un secret peut venir d'une variable (MQTT_PASSWORD) ou d'un fichier monté par
// Docker (MQTT_PASSWORD_FILE=/run/secrets/...). Le fichier est prioritaire.
function secret(name) {
  const file = process.env[`${name}_FILE`]
  if (file) return fs.readFileSync(file, 'utf8').trim()
  return process.env[name] || undefined
}

const baseTopic = (process.env.MQTT_BASE_TOPIC || 'sentinel').replace(/\/+$/, '')

// Toute la configuration vient des variables d'environnement (.env ou docker-compose).
// La connexion PostgreSQL est lue par le pilote : PGHOST, PGPORT, PGUSER, PGDATABASE.
export const config = {
  port: Number(process.env.PORT || 3000),
  mqttUrl: process.env.MQTT_URL || 'mqtt://mosquitto:1883',
  mqttUsername: process.env.MQTT_USERNAME || undefined,
  mqttPassword: secret('MQTT_PASSWORD'),
  // Certificat de l'autorité qui a signé le broker (mqtts:// avec une PKI maison).
  mqttCaFile: process.env.MQTT_CA_FILE || undefined,
  // Racine des topics : « sentinel », ou « sentinelx/g3 » avec le firmware du groupe.
  baseTopic,
  // Format des commandes envoyées au boîtier :
  //   state   -> un message { "buzzer": bool, "led": "red" | "green" | "off" }
  //   command -> un message { "command": "BUZZER_ON" } par action (firmware du groupe)
  cmdFormat: process.env.MQTT_CMD_FORMAT === 'command' ? 'command' : 'state',
  dbPassword: secret('PGPASSWORD'),
  corsOrigin: process.env.CORS_ORIGIN || '*',
  offlineAfterMs: Number(process.env.DEVICE_OFFLINE_AFTER_S || 15) * 1000,
}

export const TOPICS = {
  all: `${baseTopic}/#`,
  cmd: `${baseTopic}/cmd`,
}

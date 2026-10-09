import fs from 'node:fs'
import mqtt from 'mqtt'
import { config, TOPICS } from './config.js'

// Connexion au broker. La bibliothèque se reconnecte seule (toutes les 2 s) et
// se réabonne : une coupure du broker ne fait jamais tomber le backend.
// onMessage(leaf, payload) reçoit chaque message publié sous la racine des topics :
// leaf est la fin du topic (« sensors », « cmd »...), payload le JSON décodé,
// sauf pour « status » qui est du texte brut (online / offline).
export function startMqtt(onMessage) {
  const client = mqtt.connect(config.mqttUrl, {
    username: config.mqttUsername,
    password: config.mqttPassword,
    ca: config.mqttCaFile ? fs.readFileSync(config.mqttCaFile) : undefined,
    reconnectPeriod: 2000,
    connectTimeout: 5000,
  })

  client.on('connect', () => {
    console.log(`[mqtt] connecté à ${config.mqttUrl}, abonnement à ${TOPICS.all}`)
    client.subscribe(TOPICS.all, { qos: 1 }, (error) => {
      if (error) console.error('[mqtt] abonnement refusé :', error.message)
    })
  })
  client.on('reconnect', () => console.log('[mqtt] reconnexion...'))
  client.on('close', () => console.log('[mqtt] déconnecté'))
  client.on('error', (error) => console.error('[mqtt] erreur :', error.message))

  client.on('message', (topic, buffer) => {
    const leaf = topic.slice(config.baseTopic.length + 1)
    let payload = buffer.toString()
    if (leaf !== 'status') {
      try {
        payload = JSON.parse(payload)
      } catch {
        console.warn(`[mqtt] message ignoré sur ${topic} (JSON invalide)`)
        return
      }
    }
    // Un message mal formé ne doit pas interrompre la réception des suivants.
    Promise.resolve()
      .then(() => onMessage(leaf, payload))
      .catch((error) => console.error(`[mqtt] traitement de ${topic} échoué :`, error.message))
  })

  function publish(message) {
    return new Promise((resolve, reject) => {
      client.publish(TOPICS.cmd, JSON.stringify(message), { qos: 1 }, (error) =>
        error ? reject(error) : resolve()
      )
    })
  }

  return {
    isConnected: () => client.connected,

    // Publie un ou plusieurs messages de commande vers le boîtier.
    // Rejette si le broker est injoignable.
    async publishCommands(messages) {
      if (!client.connected) throw new Error('Broker MQTT injoignable')
      for (const message of messages) await publish(message)
    },
  }
}

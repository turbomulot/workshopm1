import { useCallback, useEffect, useState } from 'react'
import { HISTORY_LENGTH, POLL_INTERVAL_MS } from '../config'
import {
  connectWebSocket,
  getAIDetection,
  getAlerts,
  getDeviceStatus,
  getLatestSensorData,
  getSensorHistory,
  sendCommand,
} from '../services/api'

// Centralise toutes les données du dashboard.
// connected : au moins une source (service IA ou backend) répond.
// Le polling sert de base, le WebSocket (si disponible) pousse les mises à jour instantanées.
export function useSentinelData() {
  const [latest, setLatest] = useState(null)
  const [history, setHistory] = useState([])
  const [alerts, setAlerts] = useState([])
  const [detection, setDetection] = useState(null)
  const [device, setDevice] = useState(null)
  const [connected, setConnected] = useState(false)

  const addReading = useCallback((reading) => {
    setLatest(reading)
    setHistory((previous) => {
      const last = previous[previous.length - 1]
      if (last && last.timestamp === reading.timestamp) return previous
      return [...previous, reading].slice(-HISTORY_LENGTH)
    })
  }, [])

  useEffect(() => {
    let active = true

    // Chaque source est indépendante : une panne des capteurs ne masque pas la caméra.
    // Une source en panne ou pas encore branchée vaut null (affiché « pas de donnée »).
    async function refresh() {
      const results = await Promise.allSettled([
        getLatestSensorData(),
        getAlerts(),
        getAIDetection(),
        getDeviceStatus(),
      ])
      if (!active) return

      const [reading, alertList, aiResult, status] = results.map((result) =>
        result.status === 'fulfilled' ? result.value : null
      )
      if (reading) addReading(reading)
      else setLatest(null)
      if (alertList) setAlerts(alertList)
      setDetection(aiResult)
      setDevice(status)
      setConnected(Boolean(reading || alertList || aiResult || status))
    }

    getSensorHistory()
      .then((points) => active && setHistory(points))
      .catch(() => {})
      .finally(refresh)

    const timer = setInterval(refresh, POLL_INTERVAL_MS)

    const disconnect = connectWebSocket((message) => {
      if (message.type === 'sensor') addReading(message.data)
      if (message.type === 'ai') setDetection(message.data)
      if (message.type === 'status') setDevice(message.data)
      if (message.type === 'alert') {
        setAlerts((previous) =>
          previous.some((alert) => alert.id === message.data.id)
            ? previous
            : [message.data, ...previous]
        )
      }
    })

    return () => {
      active = false
      clearInterval(timer)
      disconnect()
    }
  }, [addReading])

  const runCommand = useCallback(async (command) => {
    const result = await sendCommand(command)
    if (result.actuators) {
      setDevice((previous) => ({ ...previous, actuators: result.actuators }))
    }
    return result
  }, [])

  return { latest, history, alerts, detection, device, connected, runCommand }
}

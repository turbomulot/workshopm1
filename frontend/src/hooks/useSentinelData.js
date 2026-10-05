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

    async function refresh() {
      try {
        const [reading, alertList, aiResult, status] = await Promise.all([
          getLatestSensorData(),
          getAlerts(),
          getAIDetection(),
          getDeviceStatus(),
        ])
        if (!active) return
        addReading(reading)
        setAlerts(alertList)
        setDetection(aiResult)
        setDevice(status)
        setConnected(true)
      } catch {
        if (active) setConnected(false)
      }
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

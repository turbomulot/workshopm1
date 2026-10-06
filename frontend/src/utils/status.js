import { THRESHOLDS } from '../config'

const SEVERITY = { normal: 0, warning: 1, critical: 2 }

const ISSUE_MESSAGES = {
  gas: { warning: 'Gas level is high', critical: 'Gas leak detected' },
  motion: { critical: 'Intrusion detected' },
  temperature: { warning: 'Temperature is high', critical: 'Critical temperature' },
  humidity: { warning: 'Humidity is high', critical: 'Critical humidity' },
}

export function getSensorStatus(sensor, value) {
  if (value === null || value === undefined) return 'normal'
  if (sensor === 'motion') return value ? 'critical' : 'normal'

  const limits = THRESHOLDS[sensor]
  if (!limits) return 'normal'
  if (value >= limits.critical) return 'critical'
  if (value >= limits.warning) return 'warning'
  return 'normal'
}

export function getAIStatus(detection) {
  if (!detection || !detection.humanDetected) return 'normal'
  return detection.threatLevel === 'HIGH' ? 'critical' : 'warning'
}

export function worstStatus(statuses) {
  return statuses.reduce(
    (worst, status) => (SEVERITY[status] > SEVERITY[worst] ? status : worst),
    'normal'
  )
}

// Liste des problèmes en cours, du plus grave au moins grave.
export function getIssues(latest, detection) {
  const issues = []

  if (latest) {
    for (const sensor of Object.keys(ISSUE_MESSAGES)) {
      const status = getSensorStatus(sensor, latest[sensor])
      if (status !== 'normal') {
        issues.push({ key: sensor, status, message: ISSUE_MESSAGES[sensor][status] })
      }
    }
  }

  const aiStatus = getAIStatus(detection)
  if (aiStatus !== 'normal') {
    const message = detection.people > 1 ? `${detection.people} people seen on camera` : 'Human seen on camera'
    issues.push({ key: 'ai', status: aiStatus, message })
  }
  if (detection?.cameraOnline === false) {
    issues.push({ key: 'camera', status: 'warning', message: 'Camera is offline' })
  }

  return issues.sort((a, b) => SEVERITY[b.status] - SEVERITY[a.status])
}

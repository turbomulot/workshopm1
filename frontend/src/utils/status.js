import { THRESHOLDS } from '../config'

const SEVERITY = { normal: 0, warning: 1, critical: 2 }

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

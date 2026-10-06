import StatusBadge from './StatusBadge'
import { getAIStatus } from '../utils/status'
import { formatTime } from '../utils/format'

export default function AIDetection({ detection }) {
  // detection vaut null tant que le service IA ne répond pas.
  const available = Boolean(detection)
  const status = available ? getAIStatus(detection) : 'offline'
  const human = Boolean(detection?.humanDetected)
  // La confiance n'est connue que lorsqu'une personne est en vue.
  const hasConfidence = available && detection.confidence !== null && detection.confidence !== undefined
  const confidence = hasConfidence ? Math.round(detection.confidence * 100) : 0
  const badge = human ? 'Human detected' : 'No threat'

  return (
    <section className="panel ai" data-status={status}>
      <div className="panel__header">
        <h2 className="panel__title">AI detection</h2>
        <StatusBadge status={status} label={available ? badge : 'Unavailable'} />
      </div>

      <dl className="ai__rows">
        <div className="ai__row">
          <dt>Human detected</dt>
          <dd>{available ? (human ? 'YES' : 'NO') : '--'}</dd>
        </div>
        <div className="ai__row">
          <dt>People in view</dt>
          <dd>{detection?.people ?? '--'}</dd>
        </div>
        <div className="ai__row">
          <dt>Confidence</dt>
          <dd>{hasConfidence ? `${confidence}%` : '--'}</dd>
        </div>
        <div className="ai__row">
          <dt>Threat level</dt>
          <dd>{detection?.threatLevel || '--'}</dd>
        </div>
        <div className="ai__row">
          <dt>Last analysis</dt>
          <dd>{formatTime(detection?.timestamp)}</dd>
        </div>
      </dl>

      <div className="ai__meter" aria-hidden="true">
        <div className="ai__meter-fill" style={{ width: `${confidence}%` }} />
      </div>
    </section>
  )
}

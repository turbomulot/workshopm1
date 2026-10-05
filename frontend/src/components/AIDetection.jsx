import StatusBadge from './StatusBadge'
import { getAIStatus } from '../utils/status'
import { formatTime } from '../utils/format'

export default function AIDetection({ detection }) {
  const status = getAIStatus(detection)
  const human = Boolean(detection?.humanDetected)
  const confidence = detection ? Math.round(detection.confidence * 100) : 0

  return (
    <section className="panel ai" data-status={status}>
      <div className="panel__header">
        <h2 className="panel__title">AI detection</h2>
        <StatusBadge status={status} label={human ? 'Human detected' : 'No threat'} />
      </div>

      <dl className="ai__rows">
        <div className="ai__row">
          <dt>Human detected</dt>
          <dd>{human ? 'YES' : 'NO'}</dd>
        </div>
        <div className="ai__row">
          <dt>Confidence</dt>
          <dd>{confidence}%</dd>
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

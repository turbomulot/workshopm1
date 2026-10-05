import StatusBadge from './StatusBadge'

const STATUS_LABELS = {
  normal: 'Normal',
  warning: 'Warning',
  critical: 'Critical',
}

export default function SensorCard({ label, source, value, unit, status = 'normal' }) {
  return (
    <article className="sensor-card" data-status={status}>
      <div className="sensor-card__top">
        <h3 className="sensor-card__label">{label}</h3>
        <StatusBadge status={status} label={STATUS_LABELS[status]} />
      </div>
      <p className="sensor-card__value">
        {value}
        {unit && <span className="sensor-card__unit">{unit}</span>}
      </p>
      <p className="sensor-card__source">{source}</p>
    </article>
  )
}

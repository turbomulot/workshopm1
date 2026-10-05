import StatusBadge from './StatusBadge'

const STATUS_LABELS = {
  normal: 'Normal',
  warning: 'Warning',
  critical: 'Critical',
}

// children : visualisation affichée sous la valeur (graphique, timeline...).
export default function SensorCard({ label, source, value, unit, status = 'normal', children }) {
  return (
    <article className="sensor-card" data-status={status}>
      <div className="sensor-card__top">
        <div>
          <h3 className="sensor-card__label">{label}</h3>
          <p className="sensor-card__source">{source}</p>
        </div>
        <StatusBadge status={status} label={STATUS_LABELS[status]} />
      </div>
      <p className="sensor-card__value">
        {value}
        {unit && <span className="sensor-card__unit">{unit}</span>}
      </p>
      {children && <div className="sensor-card__visual">{children}</div>}
    </article>
  )
}

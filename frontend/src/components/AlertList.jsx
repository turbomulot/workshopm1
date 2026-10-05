import { formatTime } from '../utils/format'

export default function AlertList({ alerts, limit = 20 }) {
  const sorted = [...alerts]
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, limit)

  return (
    <section className="panel alerts">
      <div className="panel__header">
        <h2 className="panel__title">Alerts</h2>
        <span className="panel__count">{alerts.length}</span>
      </div>

      {sorted.length === 0 ? (
        <p className="alerts__empty">No alert recorded.</p>
      ) : (
        <ul className="alerts__list">
          {sorted.map((alert) => (
            <li key={alert.id} className="alert" data-level={alert.level}>
              <span className="alert__time">{formatTime(alert.timestamp)}</span>
              <div className="alert__content">
                <p className="alert__message">{alert.message}</p>
                <p className="alert__meta">
                  {alert.type} / {alert.level}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

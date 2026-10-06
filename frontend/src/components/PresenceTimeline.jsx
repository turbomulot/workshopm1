import { formatTime } from '../utils/format'

// Une barre par mesure : pleine quand le PIR a détecté une présence.
export default function PresenceTimeline({ history }) {
  if (history.length === 0) {
    return <p className="chart__empty">Waiting for data</p>
  }

  return (
    <div className="timeline">
      <div className="timeline__bars">
        {history.map((point) => (
          <span
            key={point.timestamp}
            className={`timeline__bar ${point.motion ? 'timeline__bar--active' : ''}`}
            title={`${formatTime(point.timestamp)} : ${point.motion ? 'motion' : 'clear'}`}
          />
        ))}
      </div>
      <div className="timeline__axis">
        <span>{formatTime(history[0].timestamp)}</span>
        <span>{formatTime(history[history.length - 1].timestamp)}</span>
      </div>
    </div>
  )
}

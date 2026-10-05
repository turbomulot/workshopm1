import StatusBadge from './StatusBadge'
import { formatTime } from '../utils/format'

const STATUS_LABELS = {
  normal: 'ONLINE',
  warning: 'WARNING',
  critical: 'CRITICAL',
  offline: 'OFFLINE',
}

export default function Header({ status, device, lastUpdate }) {
  return (
    <header className="header">
      <div>
        <h1 className="header__title">SENTINEL-X</h1>
        <p className="header__subtitle">Industrial Monitoring System</p>
      </div>

      <div className="header__right">
        <dl className="header__meta">
          <div>
            <dt>Edge node</dt>
            <dd>{device?.ip || '--'}</dd>
          </div>
          <div>
            <dt>Last update</dt>
            <dd>{formatTime(lastUpdate)}</dd>
          </div>
        </dl>
        <StatusBadge status={status} label={STATUS_LABELS[status]} size="large" />
      </div>
    </header>
  )
}

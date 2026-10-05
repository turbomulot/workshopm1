import { formatTime } from '../utils/format'

export default function Header({ device, lastUpdate }) {
  return (
    <header className="header">
      <div className="header__brand">
        <h1 className="header__title">SENTINEL-X</h1>
        <p className="header__subtitle">Industrial Monitoring System</p>
      </div>

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
    </header>
  )
}

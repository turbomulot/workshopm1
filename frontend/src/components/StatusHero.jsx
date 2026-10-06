const STATUS_LABELS = {
  normal: 'ONLINE',
  warning: 'WARNING',
  critical: 'CRITICAL',
  offline: 'OFFLINE',
}

function getMessage(status, issues, hasSensors) {
  if (status === 'offline') {
    return {
      headline: 'Connection lost.',
      detail: 'The dashboard cannot reach the Sentinel-X server.',
    }
  }
  if (issues.length === 0) {
    return {
      headline: 'All clear.',
      detail: hasSensors
        ? 'Every sensor is within its normal range.'
        : 'No one on camera. Sensors are not connected yet.',
    }
  }
  const [main, ...others] = issues
  return {
    headline: `${main.message}.`,
    detail: others.length
      ? `Also: ${others.map((issue) => issue.message).join(' · ')}`
      : 'No other alert in progress.',
  }
}

// Bandeau principal : résume l'état du site en une phrase.
export default function StatusHero({ status, issues, hasSensors = true }) {
  const { headline, detail } = getMessage(status, issues, hasSensors)

  return (
    <section className="hero" data-status={status} aria-live="polite">
      <div className="hero__text">
        <span className="hero__state">{STATUS_LABELS[status]}</span>
        <p className="hero__headline">{headline}</p>
        <p className="hero__detail">{detail}</p>
      </div>
      <div className="hero__orb" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </section>
  )
}

export default function StatusBadge({ status, label, size = 'small' }) {
  return (
    <span className={`status-badge status-badge--${size}`} data-status={status}>
      <span className="status-badge__dot" />
      {label}
    </span>
  )
}

import { useState } from 'react'

// on : true / false, ou undefined tant que l'état de l'actionneur est inconnu.
function Indicator({ label, on }) {
  const state = on ? 'ON' : 'OFF'

  return (
    <div className="control__indicator">
      <span className={`control__lamp ${on ? 'control__lamp--on' : ''}`} />
      <span>{label}</span>
      <strong>{on === undefined ? '--' : state}</strong>
    </div>
  )
}

export default function ControlPanel({ actuators, onCommand, disabled = false }) {
  const [pending, setPending] = useState(null)
  const [error, setError] = useState(null)
  const state = actuators || {}

  async function handleClick(command) {
    setPending(command)
    setError(null)
    try {
      await onCommand(command)
    } catch {
      setError(`Command ${command} failed`)
    } finally {
      setPending(null)
    }
  }

  const buttons = [
    { command: 'BUZZER_ON', label: 'Buzzer on' },
    { command: 'BUZZER_OFF', label: 'Buzzer off' },
    {
      command: state.ledGreen ? 'LED_GREEN_OFF' : 'LED_GREEN_ON',
      label: state.ledGreen ? 'Green LED off' : 'Green LED on',
    },
    {
      command: state.ledRed ? 'LED_RED_OFF' : 'LED_RED_ON',
      label: state.ledRed ? 'Red LED off' : 'Red LED on',
    },
  ]

  return (
    <section className="panel control">
      <div className="panel__header">
        <h2 className="panel__title">Control panel</h2>
      </div>

      <div className="control__indicators">
        <Indicator label="Buzzer" on={state.buzzer} />
        <Indicator label="Green LED" on={state.ledGreen} />
        <Indicator label="Red LED" on={state.ledRed} />
      </div>

      <div className="control__buttons">
        {buttons.map((button) => (
          <button
            key={button.command}
            type="button"
            className="button"
            disabled={disabled || pending !== null}
            onClick={() => handleClick(button.command)}
          >
            {button.label}
          </button>
        ))}
        <button
          type="button"
          className="button button--danger"
          disabled={disabled || pending !== null}
          onClick={() => handleClick('ALARM_STOP')}
        >
          Stop alarm
        </button>
      </div>

      {error && <p className="control__error">{error}</p>}
    </section>
  )
}

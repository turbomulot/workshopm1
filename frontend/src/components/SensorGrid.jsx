import SensorCard from './SensorCard'
import SensorChart from './SensorChart'
import PresenceTimeline from './PresenceTimeline'
import { GAS_UNIT, THRESHOLDS } from '../config'
import { getSensorStatus } from '../utils/status'
import { formatTime } from '../utils/format'

const SENSORS = [
  {
    key: 'temperature',
    label: 'Temperature',
    source: 'DHT22',
    unit: '°C',
    format: (value) => value.toFixed(1),
  },
  {
    key: 'humidity',
    label: 'Humidity',
    source: 'DHT22',
    unit: '%',
    format: (value) => Math.round(value),
  },
  {
    key: 'gas',
    label: 'Gas / Smoke',
    source: 'MQ-2',
    unit: GAS_UNIT,
    format: (value) => Math.round(value),
  },
  {
    key: 'motion',
    label: 'Presence',
    source: 'PIR HC-SR501',
    format: (value) => (value ? 'Intrusion detected' : 'Clear'),
  },
]

export default function SensorGrid({ data, history }) {
  const chartData = history.map((point) => ({ ...point, time: formatTime(point.timestamp) }))

  return (
    <section className="sensor-grid" aria-label="Sensors">
      {SENSORS.map((sensor) => {
        const value = data ? data[sensor.key] : null
        const hasValue = value !== null && value !== undefined
        const status = getSensorStatus(sensor.key, value)

        return (
          <SensorCard
            key={sensor.key}
            label={sensor.label}
            source={sensor.source}
            value={hasValue ? sensor.format(value) : '--'}
            unit={hasValue ? sensor.unit : null}
            status={status}
          >
            {sensor.key === 'motion' ? (
              <PresenceTimeline history={history} />
            ) : (
              <SensorChart
                label={sensor.label}
                data={chartData}
                dataKey={sensor.key}
                unit={sensor.unit}
                status={status}
                threshold={THRESHOLDS[sensor.key].warning}
              />
            )}
          </SensorCard>
        )
      })}
    </section>
  )
}

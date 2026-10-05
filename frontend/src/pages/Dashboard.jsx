import Header from '../components/Header'
import SensorGrid from '../components/SensorGrid'
import SensorChart from '../components/SensorChart'
import CameraFeed from '../components/CameraFeed'
import AIDetection from '../components/AIDetection'
import AlertList from '../components/AlertList'
import ControlPanel from '../components/ControlPanel'
import { useSentinelData } from '../hooks/useSentinelData'
import { CAMERA_STREAM_URL, GAS_UNIT, THRESHOLDS } from '../config'
import { getAIStatus, getSensorStatus, worstStatus } from '../utils/status'
import { formatTime } from '../utils/format'

function getGlobalStatus(connected, device, latest, detection) {
  if (!connected || device?.online === false) return 'offline'
  if (!latest) return 'normal'
  return worstStatus([
    getSensorStatus('temperature', latest.temperature),
    getSensorStatus('humidity', latest.humidity),
    getSensorStatus('gas', latest.gas),
    getSensorStatus('motion', latest.motion),
    getAIStatus(detection),
  ])
}

export default function Dashboard() {
  const { latest, history, alerts, detection, device, connected, runCommand } = useSentinelData()

  const chartData = history.map((point) => ({ ...point, time: formatTime(point.timestamp) }))
  const globalStatus = getGlobalStatus(connected, device, latest, detection)

  return (
    <div className="dashboard">
      <Header status={globalStatus} device={device} lastUpdate={latest?.timestamp} />

      <main className="dashboard__content">
        <SensorGrid data={latest} />

        <div className="dashboard__charts">
          <SensorChart title="Temperature" data={chartData} dataKey="temperature" unit="°C" threshold={THRESHOLDS.temperature.warning} />
          <SensorChart title="Humidity" data={chartData} dataKey="humidity" unit="%" threshold={THRESHOLDS.humidity.warning} />
          <SensorChart title="Gas level" data={chartData} dataKey="gas" unit={GAS_UNIT} threshold={THRESHOLDS.gas.warning} />
        </div>

        <div className="dashboard__bottom">
          <CameraFeed streamUrl={CAMERA_STREAM_URL} />
          <div className="dashboard__column">
            <AIDetection detection={detection} />
            <ControlPanel actuators={device?.actuators} onCommand={runCommand} disabled={!connected} />
          </div>
          <AlertList alerts={alerts} />
        </div>
      </main>
    </div>
  )
}

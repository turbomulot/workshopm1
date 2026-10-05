import Header from '../components/Header'
import StatusHero from '../components/StatusHero'
import SensorGrid from '../components/SensorGrid'
import CameraFeed from '../components/CameraFeed'
import AIDetection from '../components/AIDetection'
import AlertList from '../components/AlertList'
import ControlPanel from '../components/ControlPanel'
import { useSentinelData } from '../hooks/useSentinelData'
import { CAMERA_STREAM_URL } from '../config'
import { getIssues, worstStatus } from '../utils/status'

export default function Dashboard() {
  const { latest, history, alerts, detection, device, connected, runCommand } = useSentinelData()

  const offline = !connected || device?.online === false
  const issues = offline ? [] : getIssues(latest, detection)
  const globalStatus = offline ? 'offline' : worstStatus(issues.map((issue) => issue.status))

  return (
    <div className="dashboard">
      <Header device={device} lastUpdate={latest?.timestamp} />

      <main className="layout">
        <div className="layout__main">
          <StatusHero status={globalStatus} issues={issues} />
          <SensorGrid data={latest} history={history} />
          <AlertList alerts={alerts} />
        </div>

        <aside className="layout__side">
          <CameraFeed streamUrl={CAMERA_STREAM_URL} />
          <AIDetection detection={detection} />
          <ControlPanel actuators={device?.actuators} onCommand={runCommand} disabled={!connected} />
        </aside>
      </main>
    </div>
  )
}

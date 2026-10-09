import { useEffect, useState } from 'react'

// streamUrl : URL d'un flux MJPEG (ou d'une image) servi par le backend / script IA.
// online : la caméra envoie des images. Quand elle revient, le flux est rechargé.
export default function CameraFeed({ streamUrl, online = true }) {
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)

  // A stopped server leaves the MJPEG image failed or frozen on its last frame:
  // open a fresh connection whenever the camera comes back.
  useEffect(() => {
    setFailed(false)
    if (online) setAttempt((value) => value + 1)
  }, [streamUrl, online])

  const live = Boolean(streamUrl) && online && !failed

  return (
    <section className="panel camera">
      <div className="panel__header">
        <h2 className="panel__title">Live camera</h2>
        <span className={`camera__indicator ${live ? 'camera__indicator--live' : ''}`}>
          <span className="camera__indicator-dot" />
          {live ? 'LIVE' : 'CAMERA OFFLINE'}
        </span>
      </div>

      <div className="camera__frame">
        {live ? (
          <img
            key={attempt}
            className="camera__stream"
            src={streamUrl}
            alt="Sentinel-X camera stream"
            onError={() => setFailed(true)}
          />
        ) : (
          <div className="camera__placeholder">
            <p className="camera__placeholder-title">No video signal</p>
            <p className="camera__placeholder-text">
              {streamUrl && failed ? 'The stream is unreachable.' : 'Waiting for the camera stream.'}
            </p>
            {streamUrl && <button type="button" onClick={() => { setAttempt((value) => value + 1); setFailed(false) }}>Réessayer le flux</button>}
          </div>
        )}
      </div>
    </section>
  )
}

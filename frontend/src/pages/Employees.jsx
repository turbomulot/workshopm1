import { useEffect, useRef, useState } from 'react'
import CameraFeed from '../components/CameraFeed'
import { ACCESS_VIDEO_URL, accessRequest, readAccessToken, saveAccessToken } from '../services/accessApi'

const RESULT = { valid: 'Badge valide', disabled: 'Badge désactivé', unknown: 'Badge inconnu' }
const FACE_RESULT = { valid: 'Accès accepté', disabled: 'Fiche désactivée', refused: 'Vérification refusée' }
const SOURCE = { camera: 'Webcam (QR)', manual: 'Test manuel', face: 'Visage' }
const RESULT_CLASS = { valid: 'is-valid', disabled: 'is-disabled', refused: 'is-disabled', unknown: 'is-unknown' }
const date = (value) => new Date(value).toLocaleString('fr-FR')

function readPhoto(file) {
  if (!file) return Promise.resolve(null)
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 2_000_000) {
    return Promise.reject(new Error('Choisir une photo JPEG, PNG ou WebP de 2 Mo maximum.'))
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('Impossible de lire la photo.'))
    reader.readAsDataURL(file)
  })
}

export default function Employees() {
  const [token, setToken] = useState(readAccessToken)
  const [key, setKey] = useState('')
  const [employees, setEmployees] = useState([])
  const [events, setEvents] = useState([])
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const [liveError, setLiveError] = useState('')
  const [busy, setBusy] = useState(false)
  const [search, setSearch] = useState('')
  const [badge, setBadge] = useState(null)
  const [cameras, setCameras] = useState([])
  const badgeURL = useRef(null)

  const clearBadge = () => {
    if (badgeURL.current) URL.revokeObjectURL(badgeURL.current)
    badgeURL.current = null
    setBadge(null)
  }

  const logout = () => {
    saveAccessToken('')
    setToken('')
    setEmployees([])
    setEvents([])
    setStatus(null)
    clearBadge()
  }

  useEffect(() => () => {
    if (badgeURL.current) URL.revokeObjectURL(badgeURL.current)
  }, [])

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    accessRequest('/api/v1/employees', token, { signal: controller.signal })
      .then(setEmployees)
      .catch((cause) => {
        if (cause.name !== 'AbortError') setError(cause.message)
      })
    accessRequest('/api/v1/cameras', token, { signal: controller.signal })
      .then(setCameras)
      .catch((cause) => {
        if (cause.name !== 'AbortError') setError(cause.message)
      })
    return () => controller.abort()
  }, [token])

  async function selectCamera(event) {
    setError('')
    try {
      setCameras(await accessRequest('/api/v1/camera', token, { method: 'PUT', body: { index: Number(event.target.value) } }))
    } catch (cause) { setError(cause.message) }
  }

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    let timer
    async function refresh() {
      try {
        const [camera, history] = await Promise.all([
          accessRequest('/api/v1/access/status', token, { signal: controller.signal }),
          accessRequest('/api/v1/access/events', token, { signal: controller.signal }),
        ])
        if (controller.signal.aborted) return
        setStatus(camera)
        setEvents(history)
        setLiveError('')
      } catch (cause) {
        if (controller.signal.aborted) return
        setStatus(null)
        setLiveError(cause.message)
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(refresh, 1000)
      }
    }
    refresh()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [token])

  async function login(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const supplied = key.trim()
      const rows = await accessRequest('/api/v1/employees', supplied)
      saveAccessToken(supplied)
      setToken(supplied)
      setEmployees(rows)
      setKey('')
    } catch (cause) {
      setError(cause instanceof TypeError ? 'Serveur caméra inaccessible. Vérifier son lancement sur le port 5001.' : cause.message)
    } finally { setBusy(false) }
  }

  async function createEmployee(event) {
    event.preventDefault()
    const form = event.currentTarget
    const fields = new FormData(form)
    setBusy(true)
    setError('')
    try {
      const photoFile = fields.get('photo')
      const photo = await readPhoto(photoFile?.size ? photoFile : null)
      const row = await accessRequest('/api/v1/employees', token, {
        method: 'POST', body: { first_name: fields.get('first_name'), last_name: fields.get('last_name'), photo },
      })
      setEmployees((rows) => [row, ...rows])
      form.reset()
    } catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }

  async function updateEmployee(employee, rotate = false) {
    if (rotate && !window.confirm('Renouveler ce badge ? Son ancien QR deviendra immédiatement invalide.')) return
    setBusy(true)
    setError('')
    try {
      const row = await accessRequest(`/api/v1/employees/${employee.id}${rotate ? '/badge/rotate' : ''}`, token, {
        method: rotate ? 'POST' : 'PATCH', ...(rotate ? {} : { body: { active: !employee.active } }),
      })
      setEmployees((rows) => rows.map((item) => item.id === row.id ? row : item))
      if (badge?.employee.id === row.id) clearBadge()
    } catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }

  async function enrollFace(employee) {
    setBusy(true)
    setError('')
    try {
      const row = await accessRequest(`/api/v1/employees/${employee.id}/faces`, token, { method: 'POST' })
      setEmployees((rows) => rows.map((item) => item.id === row.id ? row : item))
    } catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }

  async function eraseFace(employee) {
    if (!window.confirm(`Effacer les ${employee.faces} capture(s) du visage de ${employee.first_name} ${employee.last_name} ?`)) return
    setBusy(true)
    setError('')
    try {
      const row = await accessRequest(`/api/v1/employees/${employee.id}/faces`, token, { method: 'DELETE' })
      setEmployees((rows) => rows.map((item) => item.id === row.id ? row : item))
    } catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }

  async function startFaceCheck() {
    setError('')
    try {
      const check = await accessRequest('/api/v1/faces/check', token, { method: 'POST' })
      setStatus((current) => current && { ...current, face_check: check })
    } catch (cause) { setError(cause.message) }
  }

  async function showBadge(employee) {
    setBusy(true)
    setError('')
    try {
      const png = await accessRequest(`/api/v1/employees/${employee.id}/badge.png`, token, { blob: true })
      clearBadge()
      const url = URL.createObjectURL(png)
      badgeURL.current = url
      setBadge({ employee, url })
    } catch (cause) { setError(cause.message) }
    finally { setBusy(false) }
  }

  const query = search.toLocaleLowerCase('fr-FR')
  const visible = employees.filter((row) => `${row.first_name} ${row.last_name}`.toLocaleLowerCase('fr-FR').includes(query))
  const fresh = status?.timestamp && Date.now() - new Date(status.timestamp).getTime() < 5000
  const cameraReady = status?.camera_connected && fresh
  const faceEngine = status?.face_engine
  const faceReady = cameraReady && faceEngine?.state === 'ready'
  const faceCheck = status?.face_check
  const checking = faceCheck?.state === 'running'

  return (
    <main className="access-page">
      <header className="access-heading">
        <div><p className="access-eyebrow">CONTRÔLE PAR BADGE</p><h1>Employés & badges</h1><p>Une fiche, un QR individuel, une validation visible en direct.</p></div>
        {token && <button type="button" onClick={logout}>Fermer la session</button>}
      </header>
      <p className="access-note">Le badge indique la fiche enregistrée, sans prouver l’identité de son porteur. La photo sert à une vérification visuelle. La reconnaissance faciale ne concerne que les employés dont le visage a été enregistré ici, avec leur accord ; leurs empreintes restent sur ce serveur et s’effacent depuis leur fiche.</p>
      {error && <p className="access-error" role="alert">{error}</p>}
      {!token ? (
        <section className="panel access-login">
          <h2>Accès superviseur</h2>
          <p>Saisir la clé locale du serveur caméra pour gérer les employés et consulter les validations.</p>
          <form onSubmit={login}>
            <label>Clé superviseur<input type="password" required value={key} onChange={(event) => setKey(event.target.value)} autoComplete="off" /></label>
            <button className="access-primary" disabled={busy}>{busy ? 'Connexion…' : 'Ouvrir la gestion des badges'}</button>
          </form>
        </section>
      ) : (
        <>
          <div className="access-live-grid">
            <CameraFeed streamUrl={ACCESS_VIDEO_URL} online={Boolean(cameraReady)} />
            <div className="access-side">
              <section className="panel access-card">
                <h2>Lecture en direct</h2>
                {cameras.length > 0 && <label>Caméra
                  <select value={cameras.find((camera) => camera.current)?.index ?? ''} onChange={selectCamera}>
                    {cameras.map((camera) => <option key={camera.index} value={camera.index}>{camera.name}</option>)}
                  </select>
                </label>}
                <p className={`access-pill ${cameraReady ? 'is-valid' : 'is-unknown'}`}>{cameraReady ? 'Caméra connectée' : 'Caméra indisponible'}</p>
                {liveError && <p className="access-error" role="alert">{liveError} L’historique affiché peut être ancien.</p>}
                {status?.error && <p>{status.error}</p>}
                {cameraReady && <p>{status.personnes} personne(s) · {status.fps ?? 0} images/s · YOLO {status.latence_ms} ms · traitement {status.traitement_ms} ms</p>}
                <p>Présenter le QR face à la caméra, devant le torse, sans masquer le badge.</p>
                {!cameraReady || !status.badges?.length ? <p className="access-muted">Aucun badge lisible actuellement.</p> : (
                  <ul className="access-observations">{status.badges.map((item, index) => (
                    <li key={index}>
                      <strong>{item.employee ? `${item.employee.first_name} ${item.employee.last_name}` : 'Badge non enregistré'}</strong>
                      <span className={`access-pill is-${item.result}`}>{RESULT[item.result]}</span>
                      <small>{item.association === 'clear' ? `Badge dans le rectangle ${item.person_index + 1}` : 'Association à une personne non confirmée'}</small>
                    </li>
                  ))}</ul>
                )}
              </section>
              <section className="panel access-card">
                <div className="access-row">
                  <h2>Reconnaissance faciale</h2>
                  <span className={`access-pill ${faceReady ? 'is-valid' : 'is-unknown'}`}>{faceReady ? 'Active' : faceEngine?.state === 'loading' || faceEngine?.state === 'starting' ? 'Chargement…' : 'Indisponible'}</span>
                </div>
                {faceEngine && faceEngine.state !== 'ready' && <p className="access-muted">{faceEngine.message}</p>}
                {faceReady && (!status.faces?.length ? <p className="access-muted">Aucun visage détecté.</p> : (
                  <ul className="access-observations">{status.faces.map((face, index) => (
                    <li key={index}>
                      <strong>{face.name || 'Visage inconnu'}</strong>
                      {face.authenticated
                        ? <span className="access-pill is-valid">Authentifié par le visage · badge inutile</span>
                        : face.name && <span className={`access-pill ${face.active ? 'is-valid' : 'is-disabled'}`}>{face.active ? 'Fiche active · non authentifié' : 'Fiche désactivée'}</span>}
                      {face.score > 0 && <small>Ressemblance {Math.round(face.score * 100)} %</small>}
                    </li>
                  ))}</ul>
                ))}
                <p>La vérification se fait par étapes : reconnaissance de face, tête à gauche, tête à droite, menton levé, puis confirmation de face. Une photo ne peut pas reproduire ces gestes. Réussie, elle authentifie l’employé sans badge tant que son visage reste visible.</p>
                {faceEngine?.auto_check && <p className="access-muted">Démarrage automatique : la vérification se lance seule dès qu’un employé enregistré, à la fiche active, est reconnu face à la caméra.</p>}
                <button type="button" className="access-primary" disabled={!faceReady || checking} onClick={startFaceCheck}>{checking ? 'Vérification en cours…' : 'Vérifier l’accès par visage'}</button>
                {checking && <div className="access-check" aria-live="polite">
                  <small>{faceCheck.auto ? 'Vérification automatique · ' : ''}Étape {faceCheck.step} sur {faceCheck.total}</small>
                  <strong>{faceCheck.instruction}</strong>
                  <small>{faceCheck.remaining_s} s restante(s)</small>
                </div>}
                {faceCheck?.steps?.length > 0 && <ol className="access-steps">
                  {faceCheck.steps.map((step) => <li key={step.key} className={step.state}>{step.label}</li>)}
                </ol>}
                {faceCheck && !checking && <p className={`access-pill ${RESULT_CLASS[faceCheck.state]}`} role="status">{FACE_RESULT[faceCheck.state]} · {faceCheck.message}</p>}
              </section>
            </div>
          </div>
          <div className="access-management-grid">
            <section className="panel access-card">
              <h2>Créer une fiche employé</h2>
              <form onSubmit={createEmployee} className="access-form">
                <label>Prénom<input name="first_name" maxLength={80} required autoComplete="given-name" /></label>
                <label>Nom<input name="last_name" maxLength={80} required autoComplete="family-name" /></label>
                <label>Photo facultative<input name="photo" type="file" accept="image/jpeg,image/png,image/webp" /><small>JPEG, PNG ou WebP · 2 Mo maximum</small></label>
                <button className="access-primary" disabled={busy}>{busy ? 'Traitement…' : 'Créer la fiche et son badge'}</button>
              </form>
            </section>
            <section className="panel access-card">
              <div className="access-row"><h2>Registre des employés</h2><span>{employees.length} fiche(s)</span></div>
              <label>Rechercher<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Nom ou prénom" /></label>
              {!visible.length && <p className="access-muted">{employees.length ? 'Aucun résultat.' : 'Créer une première fiche pour générer un badge.'}</p>}
              <ul className="access-employees">{visible.map((employee) => (
                <li key={employee.id}>
                  {employee.photo ? <img className="access-avatar" src={employee.photo} alt={`Photo de ${employee.first_name} ${employee.last_name}`} /> : <span className="access-avatar access-avatar--empty" aria-hidden="true">{employee.first_name.slice(0, 1)}{employee.last_name.slice(0, 1)}</span>}
                  <div className="access-employee-info"><strong>{employee.first_name} {employee.last_name}</strong>
                    <span className={`access-pill ${employee.active ? 'is-valid' : 'is-disabled'}`}>{employee.active ? 'Badge actif' : 'Badge désactivé'}</span>
                    <small>{employee.faces ? `Visage enregistré · ${employee.faces} capture(s)` : 'Visage non enregistré'}</small>
                  </div>
                  <div className="access-actions">
                    <button type="button" disabled={busy || !employee.active} onClick={() => showBadge(employee)}>Afficher le QR</button>
                    <button type="button" disabled={busy} onClick={() => updateEmployee(employee)}>{employee.active ? 'Désactiver' : 'Réactiver'}</button>
                    <button type="button" disabled={busy} onClick={() => updateEmployee(employee, true)}>Renouveler</button>
                    <button type="button" disabled={busy || !faceReady} title="Seule cette personne face à la caméra" onClick={() => enrollFace(employee)}>{employee.faces ? 'Ajouter une capture' : 'Enregistrer le visage'}</button>
                    {employee.faces > 0 && <button type="button" disabled={busy} onClick={() => eraseFace(employee)}>Effacer le visage</button>}
                  </div>
                </li>
              ))}</ul>
            </section>
          </div>
          {badge && <section className="panel access-badge" aria-label="Badge à télécharger">
            <div><h2>{badge.employee.first_name} {badge.employee.last_name}</h2><p>Présenter ce QR devant le torse. Le nom apparaît seulement si l’association est claire et le badge reste visible.</p>
              <a className="access-download" href={badge.url} download={`badge-${badge.employee.id}.png`}>Télécharger le QR PNG</a>
              <button type="button" onClick={clearBadge}>Fermer l’aperçu</button>
            </div>
            <img src={badge.url} alt={`QR du badge de ${badge.employee.first_name} ${badge.employee.last_name}`} />
          </section>}
          <section className="panel access-card">
            <h2>Dernières validations</h2>
            <p className="access-muted">Une validation par badge concerne un badge, pas toutes les personnes visibles ; les scans identiques sont espacés d’au moins 5 secondes. Une validation par visage correspond à une vérification complète, défis compris.</p>
            {!events.length ? <p>Aucune validation enregistrée.</p> : <div className="access-table-wrap"><table className="access-table">
              <thead><tr><th>Heure</th><th>Fiche associée</th><th>Résultat</th><th>Source</th></tr></thead>
              <tbody>{events.map((item) => <tr key={item.id}><td>{date(item.timestamp)}</td><td>{item.employee_id ? `${item.first_name} ${item.last_name}` : 'Aucune'}</td><td><span className={`access-pill ${RESULT_CLASS[item.result]}`}>{(item.source === 'face' ? FACE_RESULT : RESULT)[item.result]}</span></td><td>{SOURCE[item.source] ?? item.source}</td></tr>)}</tbody>
            </table></div>}
          </section>
        </>
      )}
    </main>
  )
}

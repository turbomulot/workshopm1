// Isolated from api.js: sensor mocks and the DEV team's API remain independent.
export const ACCESS_API_URL = (import.meta.env.VITE_ACCESS_API_URL || '/access-api').replace(/\/$/, '')
export const ACCESS_VIDEO_URL = `${ACCESS_API_URL}/video`

export async function accessRequest(path, token, { method = 'GET', body, signal, blob = false } = {}) {
  const response = await fetch(`${ACCESS_API_URL}${path}`, {
    method,
    signal,
    cache: 'no-store',
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (!response.ok) {
    const details = await response.json().catch(() => ({}))
    const error = new Error(details.error || `Service badges indisponible (HTTP ${response.status}).`)
    error.status = response.status
    throw error
  }
  return blob ? response.blob() : response.json()
}

export function readAccessToken() {
  try { return sessionStorage.getItem('sentinel-access-token') || '' } catch { return '' }
}

export function saveAccessToken(token) {
  try {
    if (token) sessionStorage.setItem('sentinel-access-token', token)
    else sessionStorage.removeItem('sentinel-access-token')
  } catch { /* Session remains usable when browser storage is disabled. */ }
}

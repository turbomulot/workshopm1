import pg from 'pg'
import { config } from './config.js'

// Sans mot de passe ici, le pilote lit PGPASSWORD.
const pool = new pg.Pool({ password: config.dbPassword })

// Une erreur sur une connexion inactive (base redémarrée) ne doit pas arrêter le backend.
pool.on('error', (error) => console.error('[db] connexion perdue :', error.message))

// Tables préfixées « api_ » : la base peut aussi contenir celles d'un autre service.
const SCHEMA = `
  CREATE TABLE IF NOT EXISTS api_measurements (
    id   BIGSERIAL PRIMARY KEY,
    ts   TIMESTAMPTZ NOT NULL,
    temp DOUBLE PRECISION,
    hum  DOUBLE PRECISION,
    gas  INTEGER,
    pir  SMALLINT
  );
  CREATE INDEX IF NOT EXISTS api_measurements_ts_idx ON api_measurements (ts DESC);

  CREATE TABLE IF NOT EXISTS api_alerts (
    id     BIGSERIAL PRIMARY KEY,
    ts     TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    type   TEXT NOT NULL,
    level  TEXT,
    value  JSONB
  );
  CREATE INDEX IF NOT EXISTS api_alerts_ts_idx ON api_alerts (ts DESC);
`

const SENSOR_COLUMNS = ['temp', 'hum', 'gas', 'pir']

// La base peut démarrer après le backend : on réessaie avant d'abandonner.
export async function initDb(attempts = 20) {
  for (let attempt = 1; ; attempt += 1) {
    try {
      await pool.query(SCHEMA)
      console.log('[db] prête')
      return
    } catch (error) {
      if (attempt >= attempts) throw error
      console.log(`[db] indisponible (${error.message}), nouvel essai dans 2 s`)
      await new Promise((resolve) => setTimeout(resolve, 2000))
    }
  }
}

function toMeasurement(row) {
  return {
    id: Number(row.id),
    timestamp: row.ts.toISOString(),
    temp: row.temp,
    hum: row.hum,
    gas: row.gas,
    pir: row.pir,
  }
}

function toAlert(row) {
  return {
    id: Number(row.id),
    timestamp: row.ts.toISOString(),
    source: row.source,
    type: row.type,
    level: row.level,
    value: row.value,
  }
}

export async function saveMeasurement({ ts, temp, hum, gas, pir }) {
  const { rows } = await pool.query(
    'INSERT INTO api_measurements (ts, temp, hum, gas, pir) VALUES ($1, $2, $3, $4, $5) RETURNING *',
    [ts, temp, hum, gas, pir]
  )
  return toMeasurement(rows[0])
}

// Les `limit` dernières mesures, de la plus ancienne à la plus récente.
// Avec `sensor` : uniquement [{ timestamp, value }] pour ce capteur.
export async function getHistory(limit, sensor) {
  const { rows } = await pool.query('SELECT * FROM api_measurements ORDER BY ts DESC, id DESC LIMIT $1', [limit])
  const measurements = rows.reverse().map(toMeasurement)
  if (!sensor) return measurements
  return measurements.map((measurement) => ({ timestamp: measurement.timestamp, value: measurement[sensor] }))
}

export async function saveAlert({ ts, source, type, level, value }) {
  const { rows } = await pool.query(
    'INSERT INTO api_alerts (ts, source, type, level, value) VALUES ($1, $2, $3, $4, $5) RETURNING *',
    [ts, source, type, level ?? null, JSON.stringify(value ?? null)]
  )
  return toAlert(rows[0])
}

// Les `limit` dernières alertes, de la plus récente à la plus ancienne.
export async function getAlerts(limit) {
  const { rows } = await pool.query('SELECT * FROM api_alerts ORDER BY ts DESC, id DESC LIMIT $1', [limit])
  return rows.map(toAlert)
}

export { SENSOR_COLUMNS }

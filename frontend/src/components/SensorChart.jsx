import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const FONT = "'Inter Variable', sans-serif"
const AXIS_TICK = { fill: '#6c6f76', fontSize: 11, fontFamily: FONT }

// La courbe est noire en temps normal et prend la couleur de l'alerte sinon.
const LINE_COLORS = {
  normal: '#14161a',
  warning: '#d9860a',
  critical: '#e5382d',
  offline: '#a9acb3',
}

export default function SensorChart({ label, data, dataKey, unit, status = 'normal', threshold }) {
  if (data.length === 0) {
    return <p className="chart__empty">Waiting for data</p>
  }

  const color = LINE_COLORS[status]
  const gradientId = `chart-fill-${dataKey}`

  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 6, right: 4, bottom: 0, left: -18 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.16} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#eceae5" vertical={false} />
          <XAxis
            dataKey="time"
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={{ stroke: '#dedcd6' }}
            minTickGap={60}
          />
          <YAxis
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            tickCount={3}
            domain={[
              (min) => (Number.isFinite(min) ? Math.floor(min - Math.max(1, min * 0.1)) : 0),
              (max) => (Number.isFinite(max) ? Math.ceil(max + Math.max(1, max * 0.1)) : 1),
            ]}
            allowDecimals={false}
            width={52}
          />
          <Tooltip
            formatter={(value) => [`${value} ${unit}`, label]}
            contentStyle={{
              background: '#14161a',
              border: 'none',
              borderRadius: 10,
              fontSize: 12,
              fontFamily: FONT,
            }}
            labelStyle={{ color: '#a9acb3' }}
            itemStyle={{ color: '#ffffff', fontWeight: 600 }}
            cursor={{ stroke: '#c9c7c1' }}
          />
          {threshold !== undefined && (
            <ReferenceLine
              y={threshold}
              stroke="#d9860a"
              strokeDasharray="4 4"
              label={{
                value: 'Warning',
                fill: '#6c6f76',
                fontSize: 10,
                fontFamily: FONT,
                position: 'insideTopRight',
              }}
            />
          )}
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, stroke: '#ffffff', strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

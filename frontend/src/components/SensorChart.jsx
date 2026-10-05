import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const AXIS_TICK = { fill: '#7b8798', fontSize: 11 }

export default function SensorChart({ title, data, dataKey, unit, color = '#3987e5', threshold }) {
  const last = data.length ? data[data.length - 1][dataKey] : null

  return (
    <section className="panel chart">
      <div className="panel__header">
        <h2 className="panel__title">{title}</h2>
        <span className="chart__current">{last !== null ? `${last} ${unit}` : '--'}</span>
      </div>

      <div className="chart__body">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
            <CartesianGrid stroke="#1f2a3a" vertical={false} />
            <XAxis
              dataKey="time"
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={{ stroke: '#2a3649' }}
              minTickGap={40}
            />
            <YAxis
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
              domain={[
                (min) => Math.floor(min - Math.max(1, min * 0.1)),
                (max) => Math.ceil(max + Math.max(1, max * 0.1)),
              ]}
              allowDecimals={false}
              width={48}
            />
            <Tooltip
              formatter={(value) => [`${value} ${unit}`, title]}
              contentStyle={{
                background: '#18212e',
                border: '1px solid #2a3649',
                borderRadius: 6,
                fontSize: 12,
              }}
              labelStyle={{ color: '#a4b0c0' }}
              itemStyle={{ color: '#e8edf4' }}
              cursor={{ stroke: '#3a475c' }}
            />
            {threshold !== undefined && (
              <ReferenceLine
                y={threshold}
                stroke="#fab219"
                strokeDasharray="4 4"
                label={{ value: 'Warning', fill: '#a4b0c0', fontSize: 10, position: 'insideTopRight' }}
              />
            )}
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

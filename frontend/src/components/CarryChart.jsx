import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__title mono">{label}</div>
      <div className="chart-tooltip__row">
        <span>Annualized carry</span>
        <span className="mono">{p.annualized_rate_pct.toFixed(3)}%</span>
      </div>
      <div className="chart-tooltip__row">
        <span>Fit quality (R²)</span>
        <span className="mono">{p.r_squared.toFixed(3)}</span>
      </div>
    </div>
  );
}

export default function CarryChart({ data }) {
  return (
    <div>
      <p className="plain-narration">
        Holding a gold contract for longer costs a little extra, like a storage fee. This shows that cost,
        stretched out to what it would be over a full year.
      </p>
      <div className="chart-panel">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="var(--hairline)" vertical={false} />
            <XAxis
              dataKey="trade_date"
              tick={{ fontFamily: "var(--font-mono)", fontSize: 10, fill: "var(--ink-soft)" }}
              axisLine={{ stroke: "var(--hairline-strong)" }}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              tickFormatter={(v) => `${v.toFixed(1)}%`}
              tick={{ fontFamily: "var(--font-mono)", fontSize: 11, fill: "var(--ink-soft)" }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <ReferenceLine y={0} stroke="var(--hairline-strong)" />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="annualized_rate_pct"
              stroke="var(--gold)"
              strokeWidth={1.75}
              dot={false}
              activeDot={{ r: 5, fill: "var(--gold)" }}
              isAnimationActive={true}
              animationDuration={800}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="chart-caption">
          Backed out purely from that day's own contract curve — no external gold-lease-rate data used.
        </p>
      </div>
    </div>
  );
}

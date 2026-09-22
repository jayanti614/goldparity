import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import InfoTip from "./InfoTip";

function pctTick(v) {
  return `${(v * 100).toFixed(2)}%`;
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__title mono">{label}</div>
      {payload.map((p) => (
        <div className="chart-tooltip__row" key={p.dataKey}>
          <span>{p.name}</span>
          <span className="mono">{pctTick(p.value)}</span>
        </div>
      ))}
    </div>
  );
}

export default function SignalDecomposition({ signals }) {
  const data = [...signals]
    .sort((a, b) => a.symbol.localeCompare(b.symbol))
    .map((s) => ({
      symbol: s.symbol,
      "Purity effect": s.purity_effect_pct,
      "Roll-down effect": s.roll_down_effect_pct,
      "Residual signal": s.residual_signal_pct,
    }));

  return (
    <div>
      <p className="plain-narration">
        Not every price difference is a real opportunity. Most of it is explained by boring mechanics — this
        chart shows how much.
      </p>
      <div className="legend-key">
        <span className="legend-key__item">
          <i className="legend-swatch legend-swatch--purity" /> Purity effect
          <InfoTip>Some contracts are made of very slightly less pure gold. This is the price difference that explains — not a real opportunity.</InfoTip>
        </span>
        <span className="legend-key__item">
          <i className="legend-swatch legend-swatch--rolldown" /> Roll-down effect
          <InfoTip>Contracts expire on different days, and prices naturally drift a little as expiry approaches. This is that drift — also not a real opportunity.</InfoTip>
        </span>
        <span className="legend-key__item">
          <i className="legend-swatch legend-swatch--residual" /> Residual signal
          <InfoTip>What's left over after removing the two boring effects above. This is the real, tradeable gap — if there is one.</InfoTip>
        </span>
      </div>

      <div className="chart-panel">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="var(--hairline)" vertical={false} />
            <XAxis dataKey="symbol" tick={{ fontFamily: "var(--font-mono)", fontSize: 12, fill: "var(--ink-soft)" }} axisLine={{ stroke: "var(--hairline-strong)" }} tickLine={false} />
            <YAxis tickFormatter={pctTick} tick={{ fontFamily: "var(--font-mono)", fontSize: 11, fill: "var(--ink-soft)" }} axisLine={false} tickLine={false} width={64} />
            <ReferenceLine y={0} stroke="var(--hairline-strong)" />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: "var(--gold-wash)" }} />
            <Bar dataKey="Purity effect" fill="var(--gold-wash)" stroke="var(--gold)" strokeWidth={1} radius={[2, 2, 2, 2]} isAnimationActive={true} animationDuration={600} />
            <Bar dataKey="Roll-down effect" fill="var(--hairline-strong)" radius={[2, 2, 2, 2]} isAnimationActive={true} animationDuration={600} animationBegin={100} />
            <Bar dataKey="Residual signal" fill="var(--gold)" radius={[2, 2, 2, 2]} isAnimationActive={true} animationDuration={600} animationBegin={200} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

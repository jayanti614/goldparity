import { useEffect, useState } from "react";
import { CartesianGrid, Dot, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";

const SYMBOLS = ["GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"];

function pctTick(v) {
  return `${(v * 100).toFixed(2)}%`;
}

function FlaggedDot(props) {
  const { cx, cy, payload } = props;
  if (!payload.is_flagged) return null;
  return <Dot cx={cx} cy={cy} r={4} fill="var(--loss)" stroke="var(--paper-raised)" strokeWidth={1} />;
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__title mono">{label}</div>
      <div className="chart-tooltip__row">
        <span>Residual</span>
        <span className="mono">{pctTick(p.residual_signal_pct)}</span>
      </div>
      {p.is_flagged && <div className="chart-tooltip__flag">Flagged as statistically unusual</div>}
    </div>
  );
}

export default function SignalHistoryChart() {
  const [symbol, setSymbol] = useState("GOLDPETAL");
  const [history, setHistory] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setHistory(null);
    api
      .signalHistory(symbol)
      .then((d) => !cancelled && setHistory(d))
      .catch((e) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  return (
    <div className="chart-panel">
      <p className="plain-narration plain-narration--tight">
        Pick a contract to see its price gap over time. The line is usually near zero — spikes are days worth
        noticing.
      </p>
      <div className="symbol-tabs" role="tablist" aria-label="Select contract">
        {SYMBOLS.map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={s === symbol}
            className={`symbol-tab ${s === symbol ? "is-active" : ""}`}
            onClick={() => setSymbol(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {error && <p className="state-message state-message--error">{error}</p>}
      {!error && !history && <p className="state-message">Loading history…</p>}

      {history && history.length > 0 && (
        <>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={history} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid stroke="var(--hairline)" vertical={false} />
              <XAxis
                dataKey="trade_date"
                tick={{ fontFamily: "var(--font-mono)", fontSize: 10, fill: "var(--ink-soft)" }}
                axisLine={{ stroke: "var(--hairline-strong)" }}
                tickLine={false}
                minTickGap={40}
              />
              <YAxis tickFormatter={pctTick} tick={{ fontFamily: "var(--font-mono)", fontSize: 11, fill: "var(--ink-soft)" }} axisLine={false} tickLine={false} width={64} />
              <ReferenceLine y={0} stroke="var(--hairline-strong)" />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="residual_signal_pct"
                stroke="var(--gold)"
                strokeWidth={1.75}
                dot={<FlaggedDot />}
                activeDot={{ r: 5, fill: "var(--gold)" }}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
          <p className="chart-caption">Red dots mark days this contract's price gap was unusual compared to its own recent history.</p>
        </>
      )}
    </div>
  );
}

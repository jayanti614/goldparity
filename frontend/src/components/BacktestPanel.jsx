import InfoTip from "./InfoTip";

function fmtPct(v, digits = 3) {
  const sign = v > 0 ? "+" : "";
  return `${sign}${(v * 100).toFixed(digits)}%`;
}

function verdictTone(summary) {
  if (summary.ci_low_pct == null) return "neutral";
  if (summary.ci_low_pct > 0) return "gain";
  if (summary.ci_high_pct < 0) return "loss";
  return "neutral";
}

function CIWhisker({ summary }) {
  if (summary.ci_low_pct == null) return null;
  const { ci_low_pct: lo, ci_high_pct: hi, mean_return_pct: mean } = summary;
  // Symmetric scale around 0, padded a bit beyond the widest bound.
  const bound = Math.max(Math.abs(lo), Math.abs(hi), Math.abs(mean)) * 1.3 || 0.001;
  const toPct = (v) => ((v + bound) / (2 * bound)) * 100;

  return (
    <div className="ci-whisker">
      <div className="ci-whisker__track">
        <div className="ci-whisker__zero" style={{ left: `${toPct(0)}%` }} />
        <div
          className="ci-whisker__range"
          style={{ left: `${toPct(lo)}%`, width: `${toPct(hi) - toPct(lo)}%` }}
        />
        <div className="ci-whisker__mean" style={{ left: `${toPct(mean)}%` }} />
      </div>
      <div className="ci-whisker__labels mono">
        <span>{fmtPct(lo)}</span>
        <span>mean {fmtPct(mean)}</span>
        <span>{fmtPct(hi)}</span>
      </div>
    </div>
  );
}

export default function BacktestPanel({ summary }) {
  const tone = verdictTone(summary);

  return (
    <div>
      {summary.ci_low_pct != null && (
        <p className="plain-narration">
          In short: out of {summary.n_trades} times this system would have made a trade,{" "}
          {Math.round(summary.win_rate * summary.n_trades)} would have made money — but that's not the same as
          proving a real edge. See the verdict below for the honest statistical answer.
        </p>
      )}

      <div className={`verdict-banner verdict-banner--${tone}`}>
        <p>{summary.verdict}</p>
      </div>

      {summary.ci_low_pct != null && (
        <div className="backtest-stats">
          <div className="backtest-stat">
            <div className="backtest-stat__label">Trades</div>
            <div className="backtest-stat__value mono">{summary.n_trades}</div>
          </div>
          <div className="backtest-stat">
            <div className="backtest-stat__label">Win rate</div>
            <div className="backtest-stat__value mono">{(summary.win_rate * 100).toFixed(1)}%</div>
          </div>
          <div className="backtest-stat">
            <div className="backtest-stat__label">Mean net return / trade</div>
            <div className="backtest-stat__value mono">{fmtPct(summary.mean_return_pct)}</div>
          </div>
          <div className="backtest-stat">
            <div className="backtest-stat__label">
              {Math.round(summary.ci_level * 100)}% confidence interval{" "}
              <InfoTip>
                Instead of trusting one lucky (or unlucky) average, we reshuffle the trades thousands of times to
                see the realistic range of outcomes. If that range includes zero, we can't honestly claim an edge.
              </InfoTip>
            </div>
            <CIWhisker summary={summary} />
          </div>
        </div>
      )}

      {summary.trades.length > 0 && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Contract</th>
                <th>Entry</th>
                <th>Exit</th>
                <th>
                  Side <InfoTip>"Long spread" means betting the gap closes upward; "short spread" means betting it closes downward.</InfoTip>
                </th>
                <th>Entry residual</th>
                <th>Exit residual</th>
                <th>Net return</th>
              </tr>
            </thead>
            <tbody>
              {summary.trades.map((t, i) => (
                <tr key={i}>
                  <td className="mono">{t.symbol}</td>
                  <td className="mono">{t.entry_date}</td>
                  <td className="mono">{t.exit_date}</td>
                  <td>{t.direction === 1 ? "Long spread" : "Short spread"}</td>
                  <td className="mono">{fmtPct(t.entry_residual_pct)}</td>
                  <td className="mono">{fmtPct(t.exit_residual_pct)}</td>
                  <td className={`mono ${t.net_return_pct >= 0 ? "is-gain" : "is-loss"}`}>
                    {fmtPct(t.net_return_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

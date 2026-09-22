function fmtPct(v) {
  const sign = v > 0 ? "+" : "";
  return `${sign}${(v * 100).toFixed(3)}%`;
}

export default function ContractTicker({ signals }) {
  const ordered = [...signals].sort((a, b) => a.symbol.localeCompare(b.symbol));

  return (
    <div className="ticker">
      {ordered.map((s) => {
        const positive = s.residual_signal_pct >= 0;
        return (
          <div className="ticker__item" key={s.symbol}>
            <div className="ticker__symbol">
              {s.symbol}
              {s.is_flagged && <span className="ticker__flag" title="Statistically unusual today">unusual</span>}
            </div>
            <div className="ticker__price mono">₹{s.price_per_gram_999.toFixed(2)}/g</div>
            <div className={`ticker__delta mono ${positive ? "is-gain" : "is-loss"}`}>
              {positive ? "▲" : "▼"} {fmtPct(s.residual_signal_pct)}
            </div>
            <div className="ticker__word">{positive ? "pricier than the others" : "cheaper than the others"}</div>
          </div>
        );
      })}
    </div>
  );
}

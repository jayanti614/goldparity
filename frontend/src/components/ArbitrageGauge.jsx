import InfoTip from "./InfoTip";
import { useCountUp } from "../hooks/useCountUp";

const SIZE = 280;
const STROKE = 18;
const R = (SIZE - STROKE) / 2;
const CIRC = Math.PI * R; // semicircle length

function scoreColor(score) {
  if (score >= 70) return "var(--gold-bright)";
  if (score >= 35) return "var(--gold)";
  return "var(--ink-soft)";
}

function scoreLabel(score) {
  if (score >= 85) return "Unusually wide";
  if (score >= 70) return "Wider than usual";
  if (score >= 35) return "Typical range";
  return "Unusually tight";
}

function narrate({ score, richest_symbol, cheapest_symbol }) {
  if (score >= 70) {
    return `Right now, the ${richest_symbol} contract is priced noticeably higher than ${cheapest_symbol} — a wider gap than on most days.`;
  }
  if (score >= 35) {
    return `The ${richest_symbol} contract is priced a little higher than ${cheapest_symbol} today — nothing unusual.`;
  }
  return `${richest_symbol} and ${cheapest_symbol} are priced almost identically today — an unusually calm day.`;
}

export default function ArbitrageGauge({ data }) {
  const { score, richest_symbol, cheapest_symbol, spread_pct } = data;
  const animatedScore = useCountUp(score);
  const pct = Math.max(0, Math.min(100, animatedScore)) / 100;
  const dashOffset = CIRC * (1 - pct);

  return (
    <div>
      <p className="plain-narration">{narrate(data)}</p>

      <div className="gauge-block">
        <div className="gauge-svg-wrap">
          <svg width={SIZE} height={SIZE / 2 + STROKE} viewBox={`0 0 ${SIZE} ${SIZE / 2 + STROKE}`}>
            <path
              d={`M ${STROKE / 2} ${SIZE / 2} A ${R} ${R} 0 0 1 ${SIZE - STROKE / 2} ${SIZE / 2}`}
              fill="none"
              stroke="var(--hairline-strong)"
              strokeWidth={STROKE}
              strokeLinecap="round"
            />
            <path
              d={`M ${STROKE / 2} ${SIZE / 2} A ${R} ${R} 0 0 1 ${SIZE - STROKE / 2} ${SIZE / 2}`}
              fill="none"
              stroke={scoreColor(score)}
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={CIRC}
              strokeDashoffset={dashOffset}
            />
          </svg>
          <div className="gauge-readout">
            <div className="gauge-readout__score mono">{Math.round(animatedScore)}</div>
            <div className="gauge-readout__label">{scoreLabel(score)}</div>
          </div>
        </div>

        <dl className="gauge-detail">
          <div className="gauge-detail__row">
            <dt>
              Arbitrage score <InfoTip>
                A 0-100 score for how unusual today's price gap is, compared to every other day GoldParity has
                seen. It's not a fixed number we picked — it's ranked against this market's own history, so 83
                genuinely means "wider than 83% of days so far."
              </InfoTip>
            </dt>
            <dd className="mono">{score}</dd>
          </div>
          <div className="gauge-detail__row">
            <dt>Priciest contract today</dt>
            <dd className="mono">{richest_symbol}</dd>
          </div>
          <div className="gauge-detail__row">
            <dt>Cheapest contract today</dt>
            <dd className="mono">{cheapest_symbol}</dd>
          </div>
          <div className="gauge-detail__row">
            <dt>
              Gap between them <InfoTip>
                The price difference between the priciest and cheapest contract today, after adjusting for
                purity and unit size so it's a fair comparison.
              </InfoTip>
            </dt>
            <dd className="mono">{(spread_pct * 100).toFixed(3)}%</dd>
          </div>
        </dl>
      </div>
    </div>
  );
}

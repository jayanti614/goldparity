import { useState } from "react";
import Modal from "./Modal";

const FEATURES = [
  {
    title: "Purity-adjusted fair value",
    blurb: "Normalizes all 4 contracts onto one common, 999-purity, per-gram basis.",
    status: "built",
  },
  {
    title: "Signal decomposition",
    blurb: "Splits every mispricing into purity effect, roll-down effect, and real residual signal.",
    status: "built",
  },
  {
    title: "Rolling anomaly detection",
    blurb: "Flags a contract only when it's a genuine outlier against its own trailing history.",
    status: "built",
  },
  {
    title: "Walk-forward backtest",
    blurb: "Replays every flagged signal as a real trade — next-day entry, no lookahead.",
    status: "built",
  },
  {
    title: "Statistical honesty check",
    blurb: "Bootstrap confidence intervals that are willing to say \"no edge\" when that's the truth.",
    status: "built",
  },
  {
    title: "Implied carry rate",
    blurb: "Backs out the market's own cost-of-carry from its curve — no external data used.",
    status: "built",
  },
  {
    title: "Delivery-risk filter",
    blurb: "Excludes trades that would run into MCX's staggered-delivery tender window.",
    status: "built",
  },
  {
    title: "AI convergence predictor",
    blurb: "A trained model replacing the rule-based detector — predicts whether a flagged gap is likely to close or persist.",
    status: "planned",
    detail:
      "Planned for the offline build. We'll train this on the full history collected by then, using the rule-based detector's flags as a labeled starting point.",
  },
  {
    title: "Trust ledger & track record",
    blurb: "Every signal's real outcome gets logged permanently, building a public, verifiable trust score over time.",
    status: "planned",
    detail:
      "Planned for the offline build. Rather than open-ended user reviews with no history behind them, trust here comes from a permanent, auditable record of what the system actually called and what happened next.",
  },
  {
    title: "Mobile app & push alerts",
    blurb: "Native/PWA alerts the moment a new signal fires.",
    status: "planned",
    detail: "Planned for the offline build, once the core signal engine has enough live history to alert on.",
  },
  {
    title: "Broker & algo-platform API",
    blurb: "Lets brokers or algo platforms plug these signals directly into their own trading systems.",
    status: "planned",
    detail: "Planned for the offline build — a clean API surface on top of the endpoints already running today.",
  },
  {
    title: "Multi-commodity expansion",
    blurb: "Extending the same cross-contract logic to silver (SILVER / SILVERM / SILVERMIC).",
    status: "planned",
    detail:
      "Silver has the same multi-contract structure as gold on MCX, so the entire pipeline built here should carry over with only the reference data changing.",
  },
  {
    title: "Hindi / English toggle",
    blurb: "A bilingual UI for India's retail commodity trading base.",
    status: "planned",
    detail: "Planned for the offline build, once the core dashboard layout is finalized.",
  },
];

export default function RoadmapGrid() {
  const [openFeature, setOpenFeature] = useState(null);

  return (
    <>
      <div className="roadmap-grid">
        {FEATURES.map((f) => (
          <button
            key={f.title}
            className={`feature-tile feature-tile--${f.status}`}
            onClick={() => f.status === "planned" && setOpenFeature(f)}
          >
            <div className="feature-tile__top">
              <span className={`status-badge status-badge--${f.status}`}>
                {f.status === "built" ? "Live" : "In progress"}
              </span>
            </div>
            <div className="feature-tile__title">{f.title}</div>
            <p className="feature-tile__blurb">{f.blurb}</p>
          </button>
        ))}
      </div>

      {openFeature && (
        <Modal title={openFeature.title} onClose={() => setOpenFeature(null)}>
          <p>{openFeature.detail}</p>
        </Modal>
      )}
    </>
  );
}

export default function AboutSection({ status }) {
  const builtCount = status ? status.phases.filter((p) => p.status === "built").length : null;

  return (
    <div className="about">
      <div className="about__col">
        <h3 className="about__subhead">What this is</h3>
        <p>
          MCX lists four gold futures contracts — GOLDM, GOLDTEN, GOLDGUINEA, and GOLDPETAL — all backed by the
          same metal, just in different sizes and purities. GoldParity watches all four, adjusts for the
          differences that don't matter (unit size, purity, time to expiry), and shows what's left over: the
          real, tradeable gap between them, if any exists on a given day.
        </p>
        <p>
          Every claim this dashboard makes is checked against its own history before it's shown — including the
          honest possibility that, on a given sample, there's no edge worth acting on.
        </p>
      </div>

      <div className="about__col">
        <h3 className="about__subhead">What's built vs. what's still coming</h3>
        <p>
          {builtCount != null
            ? `${builtCount} of ${status.phases.length} build phases are live right now.`
            : "Loading build status…"}{" "}
          The data pipeline, normalization, mispricing detection, backtest engine, and this dashboard are all
          working end to end on real MCX data. The trust ledger, the AI convergence model, and the
          broker-facing API are still ahead — see the roadmap above for exactly what's live versus planned, and
          click any "in progress" tile for details.
        </p>
        <p>
          This is a hackathon submission (Hack in Hills '26, Problem Statement #03 — Commodity Derivatives
          Intelligence) and an educational/analytical tool. Nothing here is investment advice, and nobody
          involved is a SEBI-registered advisor.
        </p>
      </div>
    </div>
  );
}

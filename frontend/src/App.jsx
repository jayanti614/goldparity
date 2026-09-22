import { useEffect, useState } from "react";
import { api } from "./api/client";
import Header from "./components/Header";
import IntroBanner from "./components/IntroBanner";
import ArbitrageGauge from "./components/ArbitrageGauge";
import ContractTicker from "./components/ContractTicker";
import SignalDecomposition from "./components/SignalDecomposition";
import SignalHistoryChart from "./components/SignalHistoryChart";
import BacktestPanel from "./components/BacktestPanel";
import CarryChart from "./components/CarryChart";
import RoadmapGrid from "./components/RoadmapGrid";
import AboutSection from "./components/AboutSection";
import Reveal from "./components/Reveal";
import { GaugeIcon, LayersIcon, TrendIcon, FlaskIcon, ClockIcon, MapIcon, InfoIcon } from "./components/icons";

function SectionHead({ icon, title, sub, note }) {
  return (
    <div className="section__head">
      <h2 className="section__title">
        {icon}
        {title}
        {sub && <span className="section__title-sub">({sub})</span>}
      </h2>
      {note && <span className="section__note">{note}</span>}
    </div>
  );
}

export default function App() {
  const [status, setStatus] = useState(null);
  const [latest, setLatest] = useState(null);
  const [latestError, setLatestError] = useState(null);
  const [backtest, setBacktest] = useState(null);
  const [carryHistory, setCarryHistory] = useState(null);

  useEffect(() => {
    api.status().then(setStatus).catch(() => {});
    api
      .latestSignals()
      .then(setLatest)
      .catch((e) => setLatestError(e.message));
    api.backtest().then(setBacktest).catch(() => {});
    api.carryHistory().then(setCarryHistory).catch(() => {});
  }, []);

  return (
    <>
      <Header latestDate={latest?.trade_date} />
      <IntroBanner />

      <main className="page">
        <section className="section" id="today">
          <SectionHead icon={<GaugeIcon />} title="Today's read" note="Arbitrage score" />

          {latestError && (
            <p className="state-message state-message--error">
              {latestError.includes("No signals")
                ? "No data loaded yet — run generate_sample_data.py, run_pipeline.py and run_analytics.py on the backend first."
                : latestError}
            </p>
          )}
          {!latestError && !latest && <p className="state-message">Loading…</p>}
          {latest && (
            <>
              <ArbitrageGauge data={latest.arbitrage_score} />
              <ContractTicker signals={latest.signals} />
            </>
          )}
        </section>

        <Reveal>
          <section className="section" id="decomposition">
            <SectionHead icon={<LayersIcon />} title="Why the prices differ" sub="signal decomposition" note="Today, by contract" />
            {latest && <SignalDecomposition signals={latest.signals} />}
          </section>
        </Reveal>

        <Reveal>
          <section className="section" id="history">
            <SectionHead icon={<TrendIcon />} title="Price gap over time" sub="residual history" note="Full loaded window" />
            <SignalHistoryChart />
          </section>
        </Reveal>

        <Reveal>
          <section className="section" id="backtest">
            <SectionHead icon={<FlaskIcon />} title="Does this actually work?" sub="backtest & statistical honesty" note="Bootstrap, 95% CI" />
            {backtest && <BacktestPanel summary={backtest} />}
          </section>
        </Reveal>

        <Reveal>
          <section className="section" id="carry">
            <SectionHead icon={<ClockIcon />} title="Cost of holding gold longer" sub="implied carry rate" note="Annualized, market-wide" />
            {carryHistory && carryHistory.length > 0 && <CarryChart data={carryHistory} />}
          </section>
        </Reveal>

        <Reveal>
          <section className="section" id="roadmap">
            <SectionHead icon={<MapIcon />} title="Roadmap" note="Built vs. in progress" />
            <RoadmapGrid />
          </section>
        </Reveal>

        <Reveal>
          <section className="section" id="about">
            <SectionHead icon={<InfoIcon />} title="About" />
            <AboutSection status={status} />
          </section>
        </Reveal>
      </main>

      <footer className="site-footer page">
        GoldParity — Team Tech Tribe — Hack in Hills '26 — Educational/analytical tool, not investment advice.
      </footer>
    </>
  );
}

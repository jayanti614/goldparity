export default function Header({ latestDate }) {
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <div className="wordmark">
          GoldParity
          <span className="wordmark__tagline">Cross-contract mispricing intelligence for MCX gold futures</span>
        </div>
        <div className="live-indicator">
          <span className="live-dot" aria-hidden="true" />
          {latestDate ? `Data through ${latestDate}` : "Loading data…"}
        </div>
      </div>
    </header>
  );
}

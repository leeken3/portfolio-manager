import { useEffect, useMemo, useState } from "react";

type PortfolioRequest = {
  cash_balance: number;
  holdings: Array<{
    symbol: string;
    shares: number;
    average_cost: number;
    current_price: number;
    sector: string;
    asset_type: "stock" | "etf";
  }>;
  watchlist: Array<{
    symbol: string;
    target_buy_price: number;
    current_price: number;
  }>;
  market_factors: string[];
};

type PortfolioScores = {
  diversification: number;
  quality: number;
  momentum: number;
  valuation: number;
  income: number;
  risk: number;
  overall: number;
};

type BuySellZone = {
  symbol: string;
  current_price: number;
  support_level: number;
  resistance_level: number;
  buy_conviction: number;
  sell_conviction: number;
  reasoning: string[];
};

type PortfolioAnalysis = {
  portfolio_value: number;
  cash_balance: number;
  cost_basis: number;
  unrealized_gain_loss: number;
  unrealized_gain_loss_pct: number;
  overall_rating: number;
  risk_level: string;
  diversification_score: number;
  largest_risk: string;
  positions: Array<{
    symbol: string;
    sector: string;
    asset_type: string;
    shares: number;
    average_cost: number;
    current_price: number;
    market_value: number;
    cost_basis: number;
    unrealized_gain_loss: number;
    allocation_pct: number;
  }>;
  sector_exposure: Array<{ sector: string; allocation_pct: number }>;
  overlap_insights: Array<{ symbol: string; overlap_pct: number; shared_holdings: string[]; note: string }>;
  watchlist_insights: Array<{
    symbol: string;
    target_buy_price: number;
    current_price: number;
    delta_pct: number;
    action: string;
    confidence: number;
  }>;
  briefing: { headline: string; summary: string; bullets: string[]; suggestions: string[] };
  portfolio_scores?: PortfolioScores;
  buy_sell_zones: BuySellZone[];
};

const pretty = (value: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);

const percent = (value: number) => `${value.toFixed(1)}%`;

export default function App() {
  const [rawInput, setRawInput] = useState("");
  const [analysis, setAnalysis] = useState<PortfolioAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [priceStatus, setPriceStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void loadDemo();
  }, []);

  const loadDemo = async () => {
    setError(null);
    setPriceStatus(null);
    const response = await fetch("/api/demo-portfolio");
    if (!response.ok) {
      setError("Could not load the demo portfolio.");
      return;
    }
    const payload = (await response.json()) as PortfolioRequest;
    setRawInput(JSON.stringify(payload, null, 2));
    await runAnalysis(payload);
  };

  const refreshPrices = async (payload: PortfolioRequest) => {
    const symbols = Array.from(
      new Set([
        ...payload.holdings.map((holding) => holding.symbol.toUpperCase()),
        ...payload.watchlist.map((item) => item.symbol.toUpperCase()),
      ]),
    );

    if (symbols.length === 0) {
      setPriceStatus("No symbols to refresh.");
      return payload;
    }

    setPriceStatus("Refreshing live prices...");
    const response = await fetch("/api/prices", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(symbols),
    });

    if (!response.ok) {
      throw new Error("Live price refresh failed.");
    }

    const prices = (await response.json()) as Record<string, number>;
    const getLivePrice = (symbol: string, fallback: number) => {
      const price = prices[symbol.toUpperCase()];
      return Number.isFinite(price) && price > 0 ? price : fallback;
    };

    const updated: PortfolioRequest = {
      ...payload,
      holdings: payload.holdings.map((holding) => ({
        ...holding,
        symbol: holding.symbol.toUpperCase(),
        current_price: getLivePrice(holding.symbol, holding.current_price),
      })),
      watchlist: payload.watchlist.map((item) => ({
        ...item,
        symbol: item.symbol.toUpperCase(),
        current_price: getLivePrice(item.symbol, item.current_price),
      })),
    };

    const refreshedCount = symbols.filter((symbol) => {
      const price = prices[symbol];
      return Number.isFinite(price) && price > 0;
    }).length;
    setPriceStatus(`Live prices refreshed for ${refreshedCount}/${symbols.length} symbols.`);

    return updated;
  };

  const runAnalysis = async (payload?: PortfolioRequest) => {
    setBusy(true);
    setError(null);
    try {
      const parsed = (payload ?? JSON.parse(rawInput)) as PortfolioRequest;
      const body = await refreshPrices(parsed);
      setRawInput(JSON.stringify(body, null, 2));
      const response = await fetch("/api/briefing", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error("Briefing request failed.");
      }
      const next = (await response.json()) as PortfolioAnalysis;
      setAnalysis(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error.");
    } finally {
      setBusy(false);
    }
  };

  const topHolding = useMemo(() => analysis?.positions[0], [analysis]);
  const topSector = useMemo(() => analysis?.sector_exposure[0], [analysis]);

  return (
    <div className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">AI Investment Copilot</p>
          <h1>Portfolio intelligence for long-term investors</h1>
          <p className="lede">
            Live prices, concentration, overlap, watchlist opportunities, and a plain-English briefing.
          </p>
        </div>
        <button className="ghost" onClick={() => void loadDemo()} disabled={busy}>
          Reset demo
        </button>
      </header>

      <main className="grid">
        <section className="panel">
          <div className="panel-header">
            <h2>Portfolio input</h2>
            <button className="primary" onClick={() => void runAnalysis()} disabled={busy}>
              {busy ? "Updating..." : "Refresh prices & analyze"}
            </button>
          </div>
          <textarea
            value={rawInput}
            onChange={(event) => setRawInput(event.target.value)}
            spellCheck={false}
            className="editor"
          />
          {priceStatus ? <p className="status">{priceStatus}</p> : null}
          {error ? <p className="error">{error}</p> : null}
        </section>

        <section className="stack">
          <div className="metrics">
            <Metric label="Portfolio value" value={analysis ? pretty(analysis.portfolio_value) : "--"} />
            <Metric label="Overall rating" value={analysis ? `${analysis.overall_rating.toFixed(1)}/10` : "--"} />
            <Metric label="Risk" value={analysis?.risk_level ?? "--"} />
            <Metric label="Diversification" value={analysis ? `${analysis.diversification_score.toFixed(1)}/10` : "--"} />
          </div>

          <div className="panel brief-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Daily Brief</p>
                <h2>{analysis?.briefing.headline || "Briefing will appear after analysis"}</h2>
              </div>
            </div>
            <p className="summary">{analysis?.briefing.summary ?? "Refresh live prices and analyze your portfolio."}</p>
            {analysis?.briefing.bullets.length ? (
              <div className="brief-grid">
                <div>
                  <h3>What matters</h3>
                  <ul className="list">
                    {analysis.briefing.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3>Actions</h3>
                  <ul className="list">
                    {analysis.briefing.suggestions.map((suggestion) => (
                      <li key={suggestion}>{suggestion}</li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : null}
          </div>

          <div className="panel">
            <h2>Portfolio Health Score</h2>
            <div className="health-grid">
              <div className="health-card">
                <div className="rating">{analysis?.overall_rating.toFixed(1) ?? "--"}/10</div>
                <div className="rating-label">{analysis?.risk_level ?? "--"} Risk</div>
              </div>
              {analysis?.portfolio_scores && (
                <>
                  <ScoreCard label="Diversification" score={analysis.portfolio_scores.diversification} />
                  <ScoreCard label="Quality" score={analysis.portfolio_scores.quality} />
                  <ScoreCard label="Momentum" score={analysis.portfolio_scores.momentum} />
                  <ScoreCard label="Valuation" score={analysis.portfolio_scores.valuation} />
                  <ScoreCard label="Income" score={analysis.portfolio_scores.income} />
                  <ScoreCard label="Risk" score={analysis.portfolio_scores.risk} />
                </>
              )}
            </div>
            <p className="warning">{analysis?.largest_risk ?? "--"}</p>
          </div>

          {analysis?.buy_sell_zones.length ? (
            <div className="panel">
              <h2>Buy/Sell Zones</h2>
              <div className="zones-list">
                {analysis.buy_sell_zones.map((zone) => (
                  <div key={zone.symbol} className="zone-card">
                    <div className="zone-header">
                      <strong>{zone.symbol}</strong>
                      <div className="current">Current: ${zone.current_price.toFixed(2)}</div>
                    </div>
                    <div className="zone-prices">
                      <div className="price-zone">
                        <div className="zone-label">Buy Zone</div>
                        <div className="zone-value">${zone.support_level.toFixed(2)}</div>
                        <div className="conviction">({zone.buy_conviction}% conviction)</div>
                      </div>
                      <div className="price-zone">
                        <div className="zone-label">Sell Zone</div>
                        <div className="zone-value">${zone.resistance_level.toFixed(2)}</div>
                        <div className="conviction">({zone.sell_conviction}% conviction)</div>
                      </div>
                    </div>
                    <div className="reasoning">
                      {zone.reasoning.map((reason) => (
                        <div key={reason} className="reason">
                          - {reason}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}

          <div className="columns">
            <div className="panel">
              <h2>Sector exposure</h2>
              <Table rows={analysis?.sector_exposure ?? []} firstCol="sector" secondCol="allocation_pct" suffix="%" />
              <p className="muted">
                Largest sector: {topSector ? `${topSector.sector} (${percent(topSector.allocation_pct)})` : "--"}
              </p>
            </div>

            <div className="panel">
              <h2>Watchlist</h2>
              <div className="table">
                {analysis?.watchlist_insights.map((item) => (
                  <div key={item.symbol} className="row">
                    <div>
                      <strong>{item.symbol}</strong>
                      <div className="muted">
                        {pretty(item.current_price)} vs {pretty(item.target_buy_price)}
                      </div>
                    </div>
                    <div className="right">
                      <div>{item.action}</div>
                      <div className="muted">{item.confidence}% confidence</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="panel">
            <h2>Position breakdown</h2>
            <div className="table">
              {analysis?.positions.map((position) => (
                <div key={position.symbol} className="row">
                  <div>
                    <strong>{position.symbol}</strong>
                    <div className="muted">
                      {position.sector} / {position.asset_type}
                    </div>
                  </div>
                  <div className="right">
                    <div>{pretty(position.market_value)}</div>
                    <div className={position.unrealized_gain_loss >= 0 ? "positive" : "negative"}>
                      {pretty(position.unrealized_gain_loss)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <p className="muted">
              Largest holding: {topHolding ? `${topHolding.symbol} (${percent(topHolding.allocation_pct)})` : "--"}
            </p>
            <p className="warning">Largest risk: {analysis?.largest_risk ?? "--"}</p>
          </div>

          <div className="panel">
            <h2>Overlap</h2>
            <div className="table">
              {analysis?.overlap_insights.map((item) => (
                <div key={item.symbol} className="row">
                  <div>
                    <strong>{item.symbol}</strong>
                    <div className="muted">{item.note}</div>
                  </div>
                  <div className="right">
                    <div>{percent(item.overlap_pct)}</div>
                    <div className="muted">{item.shared_holdings.join(", ")}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ScoreCard({ label, score }: { label: string; score: number }) {
  return (
    <div className="score-card">
      <div className="score-label">{label}</div>
      <div className="score-bar">
        <div className="score-fill" style={{ width: `${(score / 10) * 100}%` }} />
      </div>
      <div className="score-value">{score.toFixed(1)}/10</div>
    </div>
  );
}

function Table({
  rows,
  firstCol,
  secondCol,
  suffix = "",
}: {
  rows: Array<Record<string, string | number>>;
  firstCol: string;
  secondCol: string;
  suffix?: string;
}) {
  return (
    <div className="table">
      {rows.map((row) => (
        <div key={String(row[firstCol])} className="row">
          <strong>{String(row[firstCol])}</strong>
          <div className="right">{String(row[secondCol]) + suffix}</div>
        </div>
      ))}
    </div>
  );
}

from __future__ import annotations

from collections import defaultdict
from math import sqrt

from .models import (
    HoldingIn,
    OverlapInsight,
    PortfolioAnalysis,
    PortfolioBriefing,
    PortfolioRequest,
    PortfolioScores,
    PositionAnalysis,
    SectorExposure,
    WatchlistInsight,
    BuySellZone,
)

# Reference data for ETF constituents and their allocations
# Format: {ETF_SYMBOL: {HOLDING_SYMBOL: ALLOCATION_PERCENTAGE}}
# Used for overlap analysis to identify redundant holdings across ETFs
ETF_CONSTITUENTS: dict[str, dict[str, float]] = {
    "VOO": {"AAPL": 0.07, "MSFT": 0.065, "NVDA": 0.06, "AMZN": 0.042, "META": 0.034, "AVGO": 0.031, "GOOGL": 0.03},
    "QQQ": {"AAPL": 0.095, "MSFT": 0.09, "NVDA": 0.085, "AMZN": 0.07, "META": 0.065, "AVGO": 0.05, "TSLA": 0.04},
    "VGT": {"AAPL": 0.12, "MSFT": 0.11, "NVDA": 0.1, "AVGO": 0.08, "CRM": 0.04, "ORCL": 0.035, "AMD": 0.03},
    "SCHD": {"HD": 0.05, "PEP": 0.045, "ABBV": 0.045, "KO": 0.04, "TXN": 0.04, "MSFT": 0.035, "JNJ": 0.03},
}


def _clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    """Constrain a value between min and max bounds."""
    return max(low, min(high, value))


def _pct(part: float, whole: float) -> float:
    """Calculate percentage safely, returning 0 if denominator is 0."""
    return 0.0 if whole <= 0 else (part / whole) * 100.0


def _score_diversification(position_weights: list[float], sector_weights: list[float]) -> float:
    """
    Calculate portfolio diversification score using Herfindahl-Hirschman Index (HHI).
    
    HHI measures concentration; lower values indicate better diversification.
    Returns a 0-10 score where higher is better.
    """
    if not position_weights:
        return 0.0
    position_hhi = sum((weight * 100.0) ** 2 for weight in position_weights)
    sector_hhi = sum((weight * 100.0) ** 2 for weight in sector_weights)
    score = 10.0 - (position_hhi / 2500.0) - (sector_hhi / 2500.0)
    return round(_clamp(score), 1)


def _risk_level(score: float) -> str:
    """Map overall rating to risk category: Low (8+), Medium (5.5-7.9), High (<5.5)."""
    if score >= 8.0:
        return "Low"
    if score >= 5.5:
        return "Medium"
    return "High"


def _largest_risk_message(sector_exposure: list[SectorExposure], positions: list[PositionAnalysis], overlap_pct: float) -> str:
    """
    Generate human-readable risk alert based on portfolio composition.
    
    Identifies concentration issues in order of priority:
    1. Sector concentration (>40%)
    2. Single position dominance (>20%)
    3. ETF overlap redundancy (>35%)
    """
    if sector_exposure and sector_exposure[0].allocation_pct >= 40:
        return f"Too dependent on {sector_exposure[0].sector.lower()}."
    if positions and positions[0].allocation_pct >= 20:
        return f"{positions[0].symbol} dominates the portfolio."
    if overlap_pct >= 35:
        return "Several holdings are owning the same mega-cap names."
    return "No single theme is overwhelming the portfolio."


def _watchlist_action(current_price: float, target_buy_price: float) -> tuple[str, int, float]:
    """
    Determine watchlist item action and confidence level.
    
    Returns: (action_string, confidence_0_to_100, price_delta_pct)
    Actions: "In buy zone" (at or below target), "Near buy zone" (within 3%), or "Wait"
    """
    delta_pct = _pct(current_price - target_buy_price, target_buy_price)
    if current_price <= target_buy_price:
        return "In buy zone", 84, delta_pct
    if current_price <= target_buy_price * 1.03:
        return "Near buy zone", 74, delta_pct
    return "Wait", 63, delta_pct


def _briefing(portfolio: PortfolioAnalysis, market_factors: list[str]) -> PortfolioBriefing:
    """
    Generate plain-English portfolio briefing with actionable insights.
    
    Combines market context, sector exposure, ETF overlap, and risk factors
    into headline, summary, bullet points, and specific suggestions.
    """
    bullets: list[str] = []
    if market_factors:
        bullets.extend(market_factors[:3])
    if portfolio.sector_exposure:
        bullets.append(
            f"{portfolio.sector_exposure[0].sector} is your largest sector at {portfolio.sector_exposure[0].allocation_pct:.1f}%."
        )
    if portfolio.overlap_insights:
        top_overlap = portfolio.overlap_insights[0]
        bullets.append(
            f"{top_overlap.symbol} overlaps with {', '.join(top_overlap.shared_holdings[:3])}."
        )

    suggestions: list[str] = []
    if portfolio.sector_exposure and portfolio.sector_exposure[0].allocation_pct >= 40:
        suggestions.append("Trim concentration by 5-10% or diversify into a broader ETF.")
    if portfolio.overall_rating >= 7.5:
        suggestions.append("Keep the core plan intact and use pullbacks for incremental adds.")
    else:
        suggestions.append("Add exposure in the weakest sector before adding to your biggest winner.")

    if not suggestions:
        suggestions.append("No immediate action stands out.")

    headline = f"Portfolio health is {portfolio.overall_rating:.1f}/10 ({portfolio.risk_level} risk)."
    summary = "Today matters most where your largest themes and overlapping holdings intersect."
    return PortfolioBriefing(headline=headline, summary=summary, bullets=bullets[:4], suggestions=suggestions[:3])


def _calculate_portfolio_scores(positions: list[PositionAnalysis], sector_exposure: list[SectorExposure], portfolio_value: float) -> PortfolioScores:
    """
    Compute six portfolio quality metrics rated 0-10 each.
    
    Metrics:
    - Diversification: Based on position concentration (HHI)
    - Quality: ETF vs individual stock ratio
    - Momentum: Average unrealized gains across holdings
    - Valuation: Overall portfolio gain/loss percentage
    - Income: Dividend yield (placeholder for future enhancement)
    - Risk: Inverse of sector concentration
    
    Returns PortfolioScores with individual scores and overall average.
    """
    position_count = len(positions)
    top_position_pct = positions[0].allocation_pct if positions else 0
    
    diversification = 10.0 - (top_position_pct / 5.0)
    diversification = _clamp(diversification, 0, 10)
    
    etf_count = sum(1 for p in positions if "etf" in p.asset_type.lower())
    quality = (etf_count / max(position_count, 1)) * 10 if etf_count > 0 else 5.0
    quality = _clamp(quality, 0, 10)
    
    total_unrealized = sum(p.unrealized_gain_loss for p in positions)
    total_cost_basis = sum(p.cost_basis for p in positions)
    avg_gain_loss_pct = _pct(total_unrealized, total_cost_basis) / max(position_count, 1) if positions and total_cost_basis > 0 else 0
    momentum = 5.0 + (avg_gain_loss_pct / 10)
    momentum = _clamp(momentum, 0, 10)
    
    valuation_pct = _pct(total_unrealized, total_cost_basis) if total_cost_basis > 0 else 0
    valuation = 5.0 + (valuation_pct / 20)
    valuation = _clamp(valuation, 0, 10)
    
    income = 3.5
    
    sector_hhi = sum((s.allocation_pct / 100.0) ** 2 for s in sector_exposure if s.sector != "Cash")
    risk = 10.0 - (sector_hhi * 10)
    risk = _clamp(risk, 0, 10)
    
    overall = round((diversification + quality + momentum + valuation + income + risk) / 6, 1)
    
    return PortfolioScores(
        diversification=round(diversification, 1),
        quality=round(quality, 1),
        momentum=round(momentum, 1),
        valuation=round(valuation, 1),
        income=round(income, 1),
        risk=round(risk, 1),
        overall=overall,
    )


def _calculate_buy_sell_zones(positions: list[PositionAnalysis], top_n: int = 3) -> list[BuySellZone]:
    """
    Calculate technical support/resistance levels and action conviction for top holdings.
    
    For each position:
    - Support: 10% below average cost (historical entry reference)
    - Resistance: 15% above current price (near-term target)
    - Buy/Sell conviction: 50-90% based on proximity to support/resistance
    
    Returns zones ranked by position size (up to top_n).
    """
    zones: list[BuySellZone] = []
    
    for position in positions[:top_n]:
        current_price = position.current_price
        avg_cost = position.average_cost
        
        support_level = round(avg_cost * 0.90, 2)
        resistance_level = round(current_price * 1.15, 2)
        
        price_to_support_pct = ((current_price - support_level) / support_level) * 100
        buy_conviction = max(50, min(90, int(100 - price_to_support_pct)))
        
        price_to_resistance_pct = ((resistance_level - current_price) / resistance_level) * 100
        sell_conviction = max(50, min(90, int(100 - price_to_resistance_pct)))
        
        reasoning = []
        if current_price <= support_level * 1.05:
            reasoning.append("Price near support level")
            reasoning.append("Historical average cost suggests value")
        else:
            reasoning.append(f"Support at ${support_level}")
        
        if current_price >= resistance_level * 0.95:
            reasoning.append("Price near resistance")
        else:
            reasoning.append(f"Resistance at ${resistance_level}")
        
        zones.append(
            BuySellZone(
                symbol=position.symbol,
                support_level=support_level,
                resistance_level=resistance_level,
                buy_conviction=buy_conviction,
                sell_conviction=sell_conviction,
                reasoning=reasoning,
            )
        )
    
    return zones


def analyze_portfolio(payload: PortfolioRequest) -> PortfolioAnalysis:
    """
    Comprehensive portfolio analysis engine.
    
    Analysis includes:
    1. Position valuations and allocations (market value, cost basis, P&L)
    2. Sector exposure breakdown with concentration risk detection
    3. Diversification scoring using HHI index
    4. ETF overlap analysis to identify redundant holdings
    5. Watchlist signal generation (buy zones, conviction levels)
    6. Portfolio quality scores (6 dimensions: diversification, quality, momentum, valuation, income, risk)
    7. Technical support/resistance zones for top holdings
    8. Overall health rating (0-10) with risk categorization
    9. Plain-English briefing with market context and action suggestions
    
    Returns PortfolioAnalysis with all metrics, insights, and recommendations.
    """
    holdings = payload.holdings
    position_values = [holding.shares * holding.current_price for holding in holdings]
    cost_basis_values = [holding.shares * holding.average_cost for holding in holdings]

    invested_value = sum(position_values)
    portfolio_value = invested_value + payload.cash_balance
    cost_basis = sum(cost_basis_values)
    unrealized_gain_loss = invested_value - cost_basis
    unrealized_gain_loss_pct = _pct(unrealized_gain_loss, cost_basis)

    # Build position-level analytics: market value, allocation %, P&L tracking
    positions: list[PositionAnalysis] = []
    for holding, market_value, basis in zip(holdings, position_values, cost_basis_values):
        positions.append(
            PositionAnalysis(
                symbol=holding.symbol.upper(),
                sector=holding.sector,
                asset_type=holding.asset_type,
                shares=holding.shares,
                average_cost=holding.average_cost,
                current_price=holding.current_price,
                market_value=round(market_value, 2),
                cost_basis=round(basis, 2),
                unrealized_gain_loss=round(market_value - basis, 2),
                allocation_pct=round(_pct(market_value, portfolio_value), 1),
            )
        )
    positions.sort(key=lambda item: item.market_value, reverse=True)

    # Aggregate holdings by sector for concentration analysis
    sector_values: dict[str, float] = defaultdict(float)
    for holding, market_value in zip(holdings, position_values):
        sector_values[holding.sector] += market_value
    if payload.cash_balance:
        sector_values["Cash"] += payload.cash_balance

    sector_exposure = [
        SectorExposure(sector=sector, allocation_pct=round(_pct(value, portfolio_value), 1))
        for sector, value in sorted(sector_values.items(), key=lambda item: item[1], reverse=True)
    ]

    # Calculate diversification score using position and sector weights
    position_weights = [value / invested_value for value in position_values if invested_value > 0]
    sector_weights = [value / invested_value for sector, value in sector_values.items() if sector != "Cash" and invested_value > 0]
    diversification_score = _score_diversification(position_weights, sector_weights)

    # Detect redundancy: identify which individual stocks are owned within held ETFs
    overlap_insights: list[OverlapInsight] = []
    etf_positions = [holding for holding in holdings if holding.asset_type == "etf" and holding.symbol.upper() in ETF_CONSTITUENTS]
    for etf in etf_positions:
        constituents = ETF_CONSTITUENTS[etf.symbol.upper()]
        shared_holdings = [holding.symbol.upper() for holding in holdings if holding.symbol.upper() in constituents]
        shared_value = sum(holding.shares * holding.current_price for holding in holdings if holding.symbol.upper() in constituents)
        overlap_pct = round(_pct(shared_value, portfolio_value), 1)
        note = "High overlap" if overlap_pct >= 20 else "Modest overlap" if overlap_pct >= 8 else "Low overlap"
        if shared_holdings:
            overlap_insights.append(
                OverlapInsight(
                    symbol=etf.symbol.upper(),
                    overlap_pct=overlap_pct,
                    shared_holdings=sorted(shared_holdings),
                    note=note,
                )
            )
    overlap_insights.sort(key=lambda item: item.overlap_pct, reverse=True)

    # Generate buy/sell signals for watchlist items
    watchlist_insights: list[WatchlistInsight] = []
    for item in payload.watchlist:
        action, confidence, delta_pct = _watchlist_action(item.current_price, item.target_buy_price)
        watchlist_insights.append(
            WatchlistInsight(
                symbol=item.symbol.upper(),
                target_buy_price=item.target_buy_price,
                current_price=item.current_price,
                delta_pct=round(delta_pct, 1),
                action=action,
                confidence=confidence,
            )
        )
    watchlist_insights.sort(key=lambda item: (item.action != "In buy zone", item.action != "Near buy zone", abs(item.delta_pct)))

    # Identify primary risk sources for user alert
    top_sector = next((sector for sector in sector_exposure if sector.sector != "Cash"), None)
    top_position = positions[0] if positions else None
    top_overlap_pct = overlap_insights[0].overlap_pct if overlap_insights else 0.0
    largest_risk = _largest_risk_message(sector_exposure, positions, top_overlap_pct)

    # Calculate overall health rating: penalize concentration, reward diversification and cash buffer
    concentration_penalty = 0.0
    if top_position:
        concentration_penalty += max(0.0, top_position.allocation_pct - 18.0) / 3.0
    if top_sector:
        concentration_penalty += max(0.0, top_sector.allocation_pct - 35.0) / 4.0
    concentration_penalty += max(0.0, top_overlap_pct - 15.0) / 5.0
    cash_bonus = min(1.5, payload.cash_balance / max(portfolio_value, 1.0) * 6.0)
    overall_rating = round(_clamp(10.0 - concentration_penalty + cash_bonus - (10.0 - diversification_score) * 0.2), 1)
    risk_level = _risk_level(overall_rating)

    # Assemble complete analysis with all insights
    analysis = PortfolioAnalysis(
        portfolio_value=round(portfolio_value, 2),
        cash_balance=round(payload.cash_balance, 2),
        cost_basis=round(cost_basis, 2),
        unrealized_gain_loss=round(unrealized_gain_loss, 2),
        unrealized_gain_loss_pct=round(unrealized_gain_loss_pct, 1),
        overall_rating=overall_rating,
        risk_level=risk_level,
        diversification_score=diversification_score,
        largest_risk=largest_risk,
        positions=positions,
        sector_exposure=sector_exposure,
        overlap_insights=overlap_insights,
        watchlist_insights=watchlist_insights,
        briefing=PortfolioBriefing(headline="", summary="", bullets=[], suggestions=[]),
        portfolio_scores=_calculate_portfolio_scores(positions, sector_exposure, portfolio_value),
        buy_sell_zones=_calculate_buy_sell_zones(positions),
    )
    analysis.briefing = _briefing(analysis, payload.market_factors)
    return analysis

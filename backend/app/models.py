from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HoldingIn(BaseModel):
    """User portfolio holding (stock or ETF)."""
    symbol: str = Field(min_length=1)
    shares: float = Field(ge=0)
    average_cost: float = Field(ge=0)
    current_price: float = Field(ge=0)
    sector: str = Field(default="Unknown")
    asset_type: Literal["stock", "etf"] = "stock"


class WatchlistItemIn(BaseModel):
    """Watchlist entry for monitoring buy opportunities."""
    symbol: str = Field(min_length=1)
    target_buy_price: float = Field(ge=0)
    current_price: float = Field(ge=0)


class PortfolioRequest(BaseModel):
    """Input payload: portfolio holdings + watchlist + market context."""
    cash_balance: float = Field(default=0, ge=0)
    holdings: list[HoldingIn]
    watchlist: list[WatchlistItemIn] = Field(default_factory=list)
    market_factors: list[str] = Field(default_factory=list)


class PositionAnalysis(BaseModel):
    """Calculated metrics for a single holding: valuation, allocation, P&L."""
    symbol: str
    sector: str
    asset_type: str
    shares: float
    average_cost: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_gain_loss: float
    allocation_pct: float


class SectorExposure(BaseModel):
    """Portfolio allocation percentage by sector."""
    sector: str
    allocation_pct: float


class WatchlistInsight(BaseModel):
    """Watchlist item analysis: action recommendation + confidence."""
    symbol: str
    target_buy_price: float
    current_price: float
    delta_pct: float
    action: str
    confidence: int


class OverlapInsight(BaseModel):
    """ETF overlap analysis: detects redundant holdings across ETFs."""
    symbol: str
    overlap_pct: float
    shared_holdings: list[str]
    note: str


class PortfolioBriefing(BaseModel):
    """Plain-English summary: headline, key insights, and action suggestions."""
    headline: str
    summary: str
    bullets: list[str]
    suggestions: list[str]


class PortfolioScores(BaseModel):
    """Six portfolio quality metrics, each 0-10 scale with overall average."""
    diversification: float
    quality: float
    momentum: float
    valuation: float
    income: float
    risk: float
    overall: float


class BuySellZone(BaseModel):
    """Technical analysis for a position: support/resistance + conviction levels."""
    symbol: str
    support_level: float
    resistance_level: float
    buy_conviction: int
    sell_conviction: int
    reasoning: list[str]


class PortfolioAnalysis(BaseModel):
    """Complete portfolio analysis output: all metrics, insights, and recommendations."""
    portfolio_value: float
    cash_balance: float
    cost_basis: float
    unrealized_gain_loss: float
    unrealized_gain_loss_pct: float
    overall_rating: float
    risk_level: str
    diversification_score: float
    largest_risk: str
    positions: list[PositionAnalysis]
    sector_exposure: list[SectorExposure]
    overlap_insights: list[OverlapInsight]
    watchlist_insights: list[WatchlistInsight]
    briefing: PortfolioBriefing
    portfolio_scores: PortfolioScores | None = None
    buy_sell_zones: list[BuySellZone] = []

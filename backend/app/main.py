from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .ai_briefing import generate_ai_briefing
from .analytics import analyze_portfolio
from .data_fetcher import fetch_current_prices, fetch_historical_prices, fetch_stock_info
from .models import PortfolioAnalysis, PortfolioRequest
from .sample_data import DEMO_PORTFOLIO

app = FastAPI(title="Portfolio Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    """Health check endpoint to verify API is running."""
    return {"status": "ok"}


@app.get("/api/demo-portfolio", response_model=PortfolioRequest)
def demo_portfolio() -> PortfolioRequest:
    """Return sample portfolio for demonstration purposes."""
    return DEMO_PORTFOLIO


@app.post("/api/analyze", response_model=PortfolioAnalysis)
def analyze(payload: PortfolioRequest) -> PortfolioAnalysis:
    """Analyze portfolio with full intelligence: concentration, overlap, scores, zones."""
    return analyze_portfolio(payload)


@app.post("/api/briefing", response_model=PortfolioAnalysis)
def briefing(payload: PortfolioRequest) -> PortfolioAnalysis:
    """Analyze portfolio and generate an AI-enhanced briefing when Ollama is available."""
    analysis = analyze_portfolio(payload)
    analysis.briefing = generate_ai_briefing(analysis, payload.market_factors)
    return analysis


@app.post("/api/prices")
def get_prices(symbols: list[str]) -> dict[str, float]:
    """
    Fetch current stock prices from Yahoo Finance for given symbols.
    
    Args:
        symbols: List of stock tickers (e.g., ["AAPL", "VOO", "MSFT"])
        
    Returns:
        Dict mapping each symbol to current price: {"AAPL": 180.50, "VOO": 510.25}
    """
    if not symbols:
        return {}
    
    prices = fetch_current_prices(symbols)
    return prices


@app.get("/api/stock/{symbol}")
def get_stock_info(symbol: str) -> dict:
    """
    Get detailed information about a stock (sector, industry, market cap, etc.).
    
    Args:
        symbol: Stock ticker (e.g., "AAPL")
        
    Returns:
        Dict with company info: name, sector, industry, market cap, dividend yield, etc.
    """
    info = fetch_stock_info(symbol)
    return info


@app.get("/api/prices/history/{symbol}")
def get_price_history(symbol: str, days: int = 30) -> dict:
    """
    Get historical price data for charting and technical analysis.
    
    Args:
        symbol: Stock ticker (e.g., "AAPL")
        days: Number of historical days (default 30, max 365)
        
    Returns:
        Dict with prices list: {"dates": [...], "prices": [...]}
    """
    if days > 365:
        days = 365
    if days < 1:
        days = 1
    
    history = fetch_historical_prices(symbol, days)
    
    if not history:
        return {"dates": [], "prices": []}
    
    dates, prices = zip(*history)
    return {"dates": list(dates), "prices": list(prices)}

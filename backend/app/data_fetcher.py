"""Real-time market data fetching using Yahoo Finance."""

from datetime import datetime

import requests
import yfinance as yf


def _chart_price_from_response(data: dict) -> float | None:
    chart_result = data.get("chart", {}).get("result", [])
    if not chart_result:
        return None

    result = chart_result[0]
    meta = result.get("meta", {})
    quote = result.get("indicators", {}).get("quote", [{}])[0]

    price = meta.get("regularMarketPrice")
    if price is None:
        closes = quote.get("close", [])
        if closes:
            price = closes[-1]
    if price is None:
        price = meta.get("chartPreviousClose")
    return float(price) if price is not None else None


def fetch_current_prices(symbols: list[str]) -> dict[str, float]:
    """
    Fetch current stock/ETF prices from Yahoo Finance.
    
    Args:
        symbols: List of stock tickers (e.g., ["AAPL", "VOO", "TSM"])
        
    Returns:
        Dict mapping symbol -> current price. Returns 0 if fetch fails for a symbol.
        
    Example:
        prices = fetch_current_prices(["AAPL", "MSFT"])
        # {"AAPL": 180.50, "MSFT": 420.25}
    """
    prices: dict[str, float] = {}
    
    if not symbols:
        return prices
    
    # Fetch symbols individually for reliability.
    for symbol in symbols:
        symbol = symbol.upper()
        price = None

        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=1d"
            response = requests.get(
                url,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            price = _chart_price_from_response(response.json())
        except (requests.RequestException, ValueError, IndexError, KeyError, TypeError):
            price = None

        if price is None:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
            except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
                price = None

        prices[symbol] = float(price) if price is not None else 0.0
    
    return prices


def fetch_etf_holdings(etf_symbol: str) -> dict[str, float]:
    """
    Fetch ETF holdings information from Yahoo Finance.
    
    Returns a dictionary of {holding_symbol: allocation_percentage}.
    Note: Yahoo Finance has limited ETF holdings data; fallback to reference data recommended.
    
    Args:
        etf_symbol: ETF ticker (e.g., "VOO")
        
    Returns:
        Dict mapping holding symbols to allocation percentages, or empty dict on failure.
    """
    try:
        ticker = yf.Ticker(etf_symbol.upper())
        info = ticker.info
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
        return {}

    # Yahoo Finance doesn't always provide holdings; this is a fallback.
    # For production, consider using a dedicated ETF data provider.
    return info.get("holdings", {})


def fetch_stock_info(symbol: str) -> dict:
    """
    Fetch detailed stock information from Yahoo Finance.
    
    Retrieves company info, sector, industry, and other metadata.
    
    Args:
        symbol: Stock ticker (e.g., "AAPL")
        
    Returns:
        Dict with stock info (sector, industry, description, etc.)
        Returns minimal dict if fetch fails.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        info = ticker.info
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
        return {
            "symbol": symbol.upper(),
            "name": "",
            "sector": "Unknown",
            "industry": "Unknown",
            "description": "",
            "market_cap": 0,
            "dividend_yield": 0,
        }

    return {
        "symbol": symbol.upper(),
        "name": info.get("longName", ""),
        "sector": info.get("sector", "Unknown"),
        "industry": info.get("industry", "Unknown"),
        "description": info.get("longBusinessSummary", ""),
        "market_cap": info.get("marketCap", 0),
        "dividend_yield": info.get("dividendYield", 0),
    }


def fetch_historical_prices(symbol: str, days: int = 30) -> list[tuple[str, float]]:
    """
    Fetch historical price data for charting and technical analysis.
    
    Args:
        symbol: Stock ticker (e.g., "AAPL")
        days: Number of days of historical data to fetch (default 30)
        
    Returns:
        List of (date_string, close_price) tuples sorted chronologically.
        Returns empty list on failure.
    """
    symbol = symbol.upper()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={days}d"
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    result = data.get("chart", {}).get("result", [])
    if not result:
        return []

    timestamps = result[0].get("timestamp", [])
    closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])

    historical = []
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            continue
        date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        historical.append((date, float(close)))

    return historical


def validate_symbols(symbols: list[str]) -> tuple[list[str], list[str]]:
    """
    Validate stock symbols by attempting to fetch their info.
    
    Args:
        symbols: List of potential symbols to validate
        
    Returns:
        Tuple of (valid_symbols, invalid_symbols)
    """
    valid = []
    invalid = []
    
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(period="1d")
            if not hist.empty:
                valid.append(symbol.upper())
            else:
                invalid.append(symbol.upper())
        except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
            invalid.append(symbol.upper())
    
    return valid, invalid

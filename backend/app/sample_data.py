from __future__ import annotations

from .models import HoldingIn, PortfolioRequest, WatchlistItemIn


DEMO_PORTFOLIO = PortfolioRequest(
    cash_balance=2500,
    holdings=[
        HoldingIn(symbol="VOO", shares=35, average_cost=430, current_price=510, sector="Broad Market", asset_type="etf"),
        HoldingIn(symbol="QQQ", shares=20, average_cost=410, current_price=490, sector="Technology", asset_type="etf"),
        HoldingIn(symbol="NVDA", shares=40, average_cost=80, current_price=130, sector="Technology"),
        HoldingIn(symbol="META", shares=25, average_cost=610, current_price=720, sector="Communication Services"),
        HoldingIn(symbol="TSM", shares=30, average_cost=180, current_price=250, sector="Technology"),
        HoldingIn(symbol="SCHD", shares=15, average_cost=75, current_price=79, sector="Dividend", asset_type="etf"),
    ],
    watchlist=[
        WatchlistItemIn(symbol="META", target_buy_price=710, current_price=720),
        WatchlistItemIn(symbol="AMD", target_buy_price=160, current_price=153),
        WatchlistItemIn(symbol="SCHD", target_buy_price=78, current_price=79),
    ],
    market_factors=[
        "Nvidia supplier earnings tonight",
        "CPI tomorrow",
        "Bond yields are falling",
        "USD weakness may support multinationals",
    ],
)

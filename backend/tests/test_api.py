from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models import PortfolioBriefing
from backend.app.sample_data import DEMO_PORTFOLIO


client = TestClient(app)


def test_get_prices_forwards_symbols_to_fetcher(monkeypatch) -> None:
    captured: list[str] = []

    def fake_fetch_current_prices(symbols: list[str]) -> dict[str, float]:
        captured.extend(symbols)
        return {"AAPL": 123.45, "MSFT": 234.56}

    monkeypatch.setattr("backend.app.main.fetch_current_prices", fake_fetch_current_prices)

    response = client.post("/api/prices", json=["AAPL", "MSFT"])

    assert response.status_code == 200
    assert response.json() == {"AAPL": 123.45, "MSFT": 234.56}
    assert captured == ["AAPL", "MSFT"]


def test_get_stock_info_returns_fetcher_payload(monkeypatch) -> None:
    def fake_fetch_stock_info(symbol: str) -> dict[str, str]:
        return {"symbol": symbol.upper(), "sector": "Technology"}

    monkeypatch.setattr("backend.app.main.fetch_stock_info", fake_fetch_stock_info)

    response = client.get("/api/stock/aapl")

    assert response.status_code == 200
    assert response.json() == {"symbol": "AAPL", "sector": "Technology"}


def test_get_price_history_clamps_days(monkeypatch) -> None:
    captured: dict[str, int | str] = {}

    def fake_fetch_historical_prices(symbol: str, days: int = 30) -> list[tuple[str, float]]:
        captured["symbol"] = symbol
        captured["days"] = days
        return [("2026-07-10", 100.0)]

    monkeypatch.setattr("backend.app.main.fetch_historical_prices", fake_fetch_historical_prices)

    response = client.get("/api/prices/history/aapl?days=999")

    assert response.status_code == 200
    assert response.json() == {"dates": ["2026-07-10"], "prices": [100.0]}
    assert captured == {"symbol": "aapl", "days": 365}


def test_briefing_uses_ai_briefing(monkeypatch) -> None:
    def fake_generate_ai_briefing(analysis, market_factors: list[str]) -> tuple[PortfolioBriefing, str]:
        assert analysis.portfolio_value > 0
        assert market_factors == DEMO_PORTFOLIO.market_factors
        briefing = PortfolioBriefing(
            headline="Good morning Ken.",
            summary="Your portfolio is live-priced and ready to review.",
            bullets=["Technology is still the main concentration."],
            suggestions=["Review new buys before adding to the largest sector."],
        )
        return briefing, "ollama"

    monkeypatch.setattr("backend.app.main.generate_ai_briefing", fake_generate_ai_briefing)

    response = client.post("/api/briefing", json=DEMO_PORTFOLIO.model_dump())

    assert response.status_code == 200
    assert response.json()["briefing"]["headline"] == "Good morning Ken."
    assert response.json()["briefing_source"] == "ollama"

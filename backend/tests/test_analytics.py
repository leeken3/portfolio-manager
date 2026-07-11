from backend.app.analytics import analyze_portfolio
from backend.app.sample_data import DEMO_PORTFOLIO


def test_demo_portfolio_produces_rating() -> None:
    analysis = analyze_portfolio(DEMO_PORTFOLIO)

    assert analysis.portfolio_value > 0
    assert 0 <= analysis.overall_rating <= 10
    assert analysis.sector_exposure
    assert analysis.briefing.headline


def test_watchlist_labels_buy_zones() -> None:
    analysis = analyze_portfolio(DEMO_PORTFOLIO)
    actions = {item.symbol: item.action for item in analysis.watchlist_insights}

    assert actions["META"] in {"In buy zone", "Near buy zone", "Wait"}

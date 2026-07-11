from __future__ import annotations

import json
import os

import requests

from .models import PortfolioAnalysis, PortfolioBriefing


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")


BriefingResult = tuple[PortfolioBriefing, str]


def _fallback_briefing(analysis: PortfolioAnalysis) -> BriefingResult:
    return analysis.briefing, "rules"


def _briefing_prompt(analysis: PortfolioAnalysis, market_factors: list[str]) -> str:
    positions = [
        {
            "symbol": position.symbol,
            "allocation_pct": position.allocation_pct,
            "unrealized_gain_loss": position.unrealized_gain_loss,
            "current_price": position.current_price,
        }
        for position in analysis.positions[:5]
    ]
    sectors = [sector.model_dump() for sector in analysis.sector_exposure[:4]]
    watchlist = [item.model_dump() for item in analysis.watchlist_insights[:4]]

    context = {
        "portfolio_value": analysis.portfolio_value,
        "cash_balance": analysis.cash_balance,
        "overall_rating": analysis.overall_rating,
        "risk_level": analysis.risk_level,
        "largest_risk": analysis.largest_risk,
        "top_positions": positions,
        "sector_exposure": sectors,
        "watchlist": watchlist,
        "market_factors": market_factors[:5],
    }

    return (
        "You are a pragmatic portfolio briefing assistant. Use only the JSON context. "
        "Do not invent news, prices, earnings, or personal facts. "
        "Return valid JSON only with this shape: "
        '{"headline": string, "summary": string, "bullets": string[], "suggestions": string[]}. '
        "Use 2-4 bullets and 1-3 suggestions. Keep it concise and action-oriented.\n\n"
        f"Context:\n{json.dumps(context, separators=(',', ':'))}"
    )


def _parse_briefing(content: str) -> PortfolioBriefing | None:
    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        data = json.loads(content[start:end])
        return PortfolioBriefing(
            headline=str(data.get("headline", ""))[:180],
            summary=str(data.get("summary", ""))[:500],
            bullets=[str(item)[:220] for item in data.get("bullets", [])][:4],
            suggestions=[str(item)[:220] for item in data.get("suggestions", [])][:3],
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def generate_ai_briefing(analysis: PortfolioAnalysis, market_factors: list[str]) -> BriefingResult:
    """
    Generate an AI briefing through local Ollama.

    The app remains usable without Ollama: connection, model, timeout, and parse
    failures all return the deterministic briefing already produced by analytics.
    """
    prompt = _briefing_prompt(analysis, market_factors)

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=8,
        )
        response.raise_for_status()
        content = response.json().get("response", "")
    except (requests.RequestException, ValueError, TypeError):
        return _fallback_briefing(analysis)

    briefing = _parse_briefing(str(content))
    if briefing is None or not briefing.headline:
        return _fallback_briefing(analysis)
    return briefing, "ollama"

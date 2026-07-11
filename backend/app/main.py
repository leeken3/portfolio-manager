from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .analytics import analyze_portfolio
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
    return {"status": "ok"}


@app.get("/api/demo-portfolio", response_model=PortfolioRequest)
def demo_portfolio() -> PortfolioRequest:
    return DEMO_PORTFOLIO


@app.post("/api/analyze", response_model=PortfolioAnalysis)
def analyze(payload: PortfolioRequest) -> PortfolioAnalysis:
    return analyze_portfolio(payload)


@app.post("/api/briefing", response_model=PortfolioAnalysis)
def briefing(payload: PortfolioRequest) -> PortfolioAnalysis:
    return analyze_portfolio(payload)

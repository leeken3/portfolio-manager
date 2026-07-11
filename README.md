# Portfolio Copilot

AI portfolio intelligence MVP that explains portfolio health, concentration, ETF overlap, and watchlist opportunities.

## Local dev

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api` to `http://127.0.0.1:8000`.

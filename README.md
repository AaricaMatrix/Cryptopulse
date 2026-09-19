# CryptoPulse

A small, honest data project: pulls real crypto market data (BTC, ETH, SOL, ADA, MATIC) from CoinGecko's free API and market-wide sentiment from the Alternative.me Fear & Greed Index, computes volatility and volume-anomaly metrics, and exports clean CSVs ready for Tableau.

Built to have genuine, explainable Web3-domain evidence — not to claim a trading system or a production ML pipeline. See `PRD.md` for scope and non-goals, `SKILL.md` for the methodology and how to defend every number in an interview, and `documentation.md` for setup and how to run it.

## Quick start
```bash
pip install -r requirements.txt
python -m src.pipeline
```

Outputs land in `data/` (CSVs) and `charts/` (PNG sanity checks). Open `data/merged_daily.csv` in Tableau.

## What it is / isn't
- Is: a self-initiated project to understand crypto market behavior — real data, real API calls, a defensible (if simple) anomaly-detection method.
- Isn't: a trading strategy, a production system, or per-coin sentiment analysis (the sentiment data is market-wide, by design of the free data source).

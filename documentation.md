# Documentation — CryptoPulse

## What this is
A small Python pipeline that pulls real crypto market data and market sentiment, computes volatility and volume-anomaly metrics, and exports clean CSVs for Tableau. Built to have genuine, explainable Web3-domain evidence before applying to a role that's built around it.

## Requirements
- Python 3.9+
- Internet access (the sandbox this was built in does NOT have access to `api.coingecko.com` or `api.alternative.me` — you'll run this on your own machine, where it will work fine)
- Packages in `requirements.txt`: `requests`, `pandas`, `numpy`, `matplotlib`, `seaborn`

## Setup
```bash
cd cryptopulse
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

No API keys. No `.env` file needed for this to run — both data sources are free and keyless. (`config.py` still centralizes the few settings that exist, so if you ever add a paid data source later, there's already a clean place to put a key via an environment variable rather than hardcoding it.)

## Running it
```bash
python -m src.pipeline
```

This will:
1. Validate each configured coin ID against CoinGecko.
2. Pull 90 days of daily price/volume/market cap per coin.
3. Pull 90 days of Fear & Greed Index history.
4. Compute returns, rolling volatility, and volume z-score anomalies.
5. Merge everything into one tidy daily table.
6. Write three CSVs to `data/`:
   - `coin_metrics.csv` — one row per coin per day: price, volume, market cap, return, 7d vol, 30d vol, volume z-score, anomaly flag
   - `sentiment_history.csv` — one row per day: Fear & Greed value + classification
   - `merged_daily.csv` — `coin_metrics.csv` joined with sentiment by date (this is the one to open in Tableau)
7. Save 3 charts to `charts/` as a sanity check before opening Tableau: `volatility_by_coin.png`, `volume_anomalies.png`, `price_vs_sentiment.png`.

Console output tells you row counts and flags anything that failed (e.g. a coin ID CoinGecko rejected) instead of failing silently.

## File-by-file

| File | Purpose |
|---|---|
| `src/config.py` | All settings in one place: coin list, days of history, anomaly threshold, output paths. Change behavior here, not by editing logic elsewhere. |
| `src/fetch_data.py` | All network calls. Talks to CoinGecko and Alternative.me. Includes basic retry-with-backoff on rate limiting (HTTP 429) and input validation on the coin ID list before spending API calls on bad IDs. |
| `src/features.py` | Pure functions: returns, rolling volatility. No network calls — testable in isolation. |
| `src/anomaly_detection.py` | Volume z-score anomaly flagging. Isolated on purpose (see SKILL.md — "how to extend"). |
| `src/pipeline.py` | Orchestrates the above in order, writes CSVs, generates charts. This is the file you actually run. |
| `data/` | Output CSVs land here. Gitignored contents except a `.gitkeep` — don't commit pulled data, it goes stale. |
| `charts/` | Output PNGs land here. Same gitignore treatment. |

## Opening the output in Tableau
Connect Tableau to `data/merged_daily.csv` directly (Data Source → Text File). Columns are pre-typed sensibly by pandas on export (dates as `YYYY-MM-DD` strings, which Tableau auto-detects as Date). No manual field-type fixing should be needed. If Tableau imports `date` as a string instead of a date, right-click the field → Change Data Type → Date.

Suggested first views, since "what would you actually build in Tableau" is a fair follow-up question:
- Line chart: `date` (x) vs `rolling_vol_30d` (y), colored by `coin` — shows relative volatility across coins over time.
- Line/scatter: `date` (x) vs `price` (y) per coin, with `volume_anomaly` flag used to mark points (size or color) — shows where volume spiked relative to price action.
- Dual-axis: `price` for one coin (e.g. BTC) against `fear_greed_value` — visual check on whether market-wide sentiment tracks BTC price moves.

## Known failure modes
- **CoinGecko 429 (rate limited)**: the fetch function retries with exponential backoff up to 3 times. If it still fails, that coin is skipped and logged — the pipeline continues with the rest rather than crashing.
- **A coin ID doesn't exist / was renamed**: validated before pulling; the pipeline prints which ID failed and continues.
- **Alternative.me returns fewer days than requested**: happens occasionally near the API's own history limits. The merge is a left join on `coin_metrics`, so missing sentiment days just show up as null in `merged_daily.csv` rather than dropping price rows.

## Honesty notes for your README / resume bullet
This is a self-initiated exploratory project, not a production system. State plainly: keyless free APIs, 90-day window, z-score heuristic (not a trained model) for anomaly flagging, market-wide (not per-coin) sentiment. Don't let a resume bullet imply more than this does.

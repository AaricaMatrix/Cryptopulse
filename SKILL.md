# SKILL.md — CryptoPulse Methodology Reference

This is the "how it works and how to extend it" doc — for you, six months from now, when you've forgotten why a function is written a certain way, and for explaining the project in an interview.

## Skills this project actually demonstrates
- Pulling and parsing data from a real external REST API (not a static CSV download)
- Handling two different data sources with different shapes and joining them correctly on date
- Time-series feature engineering: returns, rolling volatility, z-score anomaly flagging
- Making an explicit, defensible choice between a simple heuristic (z-score) and a heavier method (Isolation Forest) based on dataset size — and being able to explain why
- Producing analysis-ready, correctly-typed output for a BI tool (Tableau), not just a notebook that only makes sense to you
- Basic script hygiene: config in one place, no hardcoded magic numbers scattered through the code, no API keys needed at all (so nothing to leak)

## Data sources

### 1. CoinGecko (keyless public API)
Base URL: `https://api.coingecko.com/api/v3`

Endpoint used: `/coins/{id}/market_chart`
```
GET /coins/bitcoin/market_chart?vs_currency=usd&days=90&interval=daily
```
Returns three parallel arrays: `prices`, `market_caps`, `total_volumes`, each a list of `[unix_timestamp_ms, value]` pairs.

Rate limit: ~10–30 calls/min, no key required. With 5 coins and one call each, this is a non-issue — but the fetch function still sleeps briefly between calls out of politeness and to avoid a 429.

Coin IDs are CoinGecko's own slugs, not tickers: `bitcoin`, `ethereum`, `solana`, `cardano`, `matic-network` (Polygon's old MATIC token — CoinGecko may have migrated this to `polygon-ecosystem-token` by the time you run this; the pipeline checks `/ping` and validates each coin ID before pulling, and tells you plainly if one fails instead of silently dropping it).

### 2. Alternative.me Fear & Greed Index
Base URL: `https://api.alternative.me/fng/`

```
GET /fng/?limit=90&format=json
```
Returns daily records with `value` (0-100), `value_classification` (e.g. "Extreme Fear"), and `timestamp` (unix seconds). This is market-wide sentiment — one number per day, applied across all coins. It is not asset-specific. Don't present it as if it were.

## Feature definitions (so you can defend every number)

- **Daily return** — `(price_today - price_yesterday) / price_yesterday`. Standard simple return, not log return (log return is more "correct" for compounding but simple return is easier to explain out loud, which matters more here).
- **7-day / 30-day rolling volatility** — rolling standard deviation of daily returns over the trailing N days. This is the standard definition of realized volatility. Higher = the price is swinging harder, not necessarily trending up or down.
- **Volume z-score** — `(volume_today - rolling_mean_volume) / rolling_std_volume`, using a 30-day trailing window. Flagged as anomalous when `|z| > 2`, i.e., more than 2 standard deviations from the recent normal. This is a well-known, simple outlier heuristic — not a trained model. If asked "why not Isolation Forest like your other project," the honest answer is dataset size: Isolation Forest wants more data than 90 daily points per coin to be meaningful, and z-score is easier for a non-technical interviewer to follow anyway.

## How to extend this later
- **More coins**: add CoinGecko IDs to `COINS` in `src/config.py`. Nothing else needs to change.
- **Longer history**: bump `DAYS_HISTORY` in `config.py`. CoinGecko's free tier caps hourly granularity under 90 days and gives daily granularity beyond that automatically — the pipeline already requests `interval=daily` so this is handled.
- **Swap the anomaly method**: `src/anomaly_detection.py` isolates the z-score logic in one function (`flag_volume_anomalies`). Replacing it with Isolation Forest later is a contained change, not a rewrite.
- **Per-coin sentiment**: not available for free anywhere reliable. If you ever want this, it usually means scraping social/news sentiment yourself (a much bigger project) — worth naming as a "v2 idea" in interviews rather than pretending v1 already does it.

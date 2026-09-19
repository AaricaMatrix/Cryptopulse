# PRD — CryptoPulse: Web3 Market Signal Tracker

## Why this exists
You're applying to a role where the entire posting is built around Web3/crypto ("HODLer," VDA, blockchain), and nothing on your resume touches that domain. This project closes that gap with something real, not a resume line — a working pipeline that pulls actual crypto market data, analyzes it, and outputs something you can open in Tableau and talk through in an interview without hand-waving.

## Problem statement
No evidence of Web3-domain curiosity anywhere in your application materials. A generic data project (another Titanic dataset, another sales dashboard) won't fix that. It has to specifically touch crypto market behavior.

## Goal (v1 scope — keep this small and honest)
Build a pipeline that:
1. Pulls 90 days of daily price, volume, and market cap for 5 major coins (BTC, ETH, SOL, ADA, MATIC) from CoinGecko's free keyless API.
2. Pulls the matching 90-day history of the Fear & Greed Index (market-wide crypto sentiment) from Alternative.me's free API.
3. Computes, per coin, per day:
   - Daily return (% change)
   - 7-day rolling volatility (std dev of returns)
   - 30-day rolling volatility
   - Volume z-score, with a flag for "anomalous" volume days (|z| > 2)
4. Merges sentiment onto the price data by date.
5. Exports three clean CSVs meant to be dropped into Tableau with zero manual cleanup.
6. Produces 3 quick matplotlib/seaborn charts as a sanity check before touching Tableau at all — volatility over time per coin, volume anomalies marked on a price line, and price vs. sentiment overlay.

## Explicit non-goals
- No trading signals, no "buy/sell" logic, no backtesting.
- No paid APIs or API keys — this has to run for free, forever, with nothing to configure.
- No real-time streaming. A single batch pull is enough; this isn't a live dashboard.
- Not claiming production-grade anomaly detection. Z-score on ~90 points is a simple, explainable heuristic — not an ML model. Don't oversell it.

## Users
Just you. This is a portfolio artifact plus interview material, not a product.

## Success criteria
- One command runs the whole pipeline end to end, no manual steps in between.
- The 3 output CSVs open in Tableau with correct types (dates as dates, numbers as numbers) — no cleanup step needed.
- You can explain every column and every design choice out loud without fumbling — especially "why z-score and not Isolation Forest this time" (small dataset, and a simpler method here shows range, not that you forgot the more advanced one — you already used Isolation Forest in EcoTrack-AI).
- The README states plainly what this is: a self-initiated project to understand crypto market behavior before applying, not a production system.

## Known limitations (say these upfront, don't get caught out)
- Fear & Greed Index is market-wide, not per-coin. It's a sentiment *anchor*, not a per-asset sentiment score. The merged CSV makes this structurally obvious (one sentiment column applied across all coins per date).
- CoinGecko's free tier is keyless but rate-limited (roughly 10–30 calls/min) and not meant for production polling — fine for a one-time historical pull, not for a live app.
- 90 days is enough to show the method, not enough for rigorous statistical claims. Frame it as exploratory.

## Interview talking points this buys you
- "I wanted to understand how Web3 markets actually move before applying, so I built a small pipeline against CoinGecko and the Fear & Greed Index."
- Ties directly to your EcoTrack-AI anomaly detection work — same instinct (flag anomalous volume/behavior), simpler tool because the dataset size didn't justify Isolation Forest here.
- Shows you can go from "zero domain knowledge" to "working analysis" fast, which is the actual skill they're hiring for.

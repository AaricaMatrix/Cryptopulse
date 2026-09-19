"""
config.py — every tunable setting lives here.
Change what the pipeline does by editing this file, not by hunting through logic files.
"""

import os                       # used to read an optional API key from the environment, if one is ever added
from pathlib import Path        # gives clean, OS-independent file paths instead of hand-built strings

# --- Coins to track ---
# These are CoinGecko's own ID slugs, NOT ticker symbols. "bitcoin" not "BTC".
# Note: Polygon's token migrated from MATIC to POL in September 2024. CoinGecko's ID for it
# is now "polygon-ecosystem-token" — the old "matic-network" ID still exists in their /coins/list
# (so validate_coin_ids won't catch it) but its market_chart data is empty. fetch_coin_history()
# now checks for that specific failure mode too (see below).
COINS = ["bitcoin", "ethereum", "solana", "cardano", "polygon-ecosystem-token"]

# --- Time window ---
DAYS_HISTORY = 90                # how many days of daily history to pull per coin and for sentiment
VS_CURRENCY = "usd"              # price everything in USD

# --- Anomaly detection ---
ANOMALY_ZSCORE_THRESHOLD = 2.0   # flag a day as anomalous if |volume z-score| exceeds this
ROLLING_WINDOW_SHORT = 7         # short-window volatility, in days
ROLLING_WINDOW_LONG = 30         # long-window volatility AND the window used for the volume z-score baseline

# --- Network behavior ---
# CoinGecko's docs claim 10-30 calls/min on the free keyless tier, but in practice the public
# demo endpoint throttles much harder than that (it's a shared pool across everyone hitting it
# with no key, not a per-user allowance). These numbers are set conservatively on purpose —
# slower but reliable beats fast but crashing on the 5th coin.
REQUEST_TIMEOUT_SECONDS = 15     # give up on a single stalled request after this long rather than hanging forever
MAX_RETRIES = 5                  # how many times to retry a request that gets rate-limited (HTTP 429)
RETRY_BACKOFF_BASE_SECONDS = 5   # first retry waits this long; each retry after that doubles the wait (5,10,20,40,80s)
POLITE_DELAY_BETWEEN_CALLS = 8   # seconds to sleep between per-coin API calls — deliberately generous

# --- API endpoints ---
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"
FEAR_GREED_URL = "https://api.alternative.me/fng/"

# --- Optional API key ---
# Neither API used here requires a key. This is left in place as the one correct spot to read a key
# from an environment variable if a paid data source is ever added later — never hardcode a key in code.
OPTIONAL_API_KEY = os.environ.get("CRYPTOPULSE_API_KEY", None)

# --- Output locations ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent   # the cryptopulse/ folder, regardless of where this is run from
DATA_DIR = PROJECT_ROOT / "data"                          # where output CSVs get written
CHARTS_DIR = PROJECT_ROOT / "charts"                       # where output PNGs get written

COIN_METRICS_CSV = DATA_DIR / "coin_metrics.csv"
SENTIMENT_CSV = DATA_DIR / "sentiment_history.csv"
MERGED_CSV = DATA_DIR / "merged_daily.csv"

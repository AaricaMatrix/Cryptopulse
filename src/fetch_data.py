"""
fetch_data.py — every network call in the project lives here, and nowhere else.
Keeping all HTTP calls in one file means if CoinGecko or Alternative.me change their API,
there's exactly one place to fix it.
"""

import time                     # used for the sleep-based retry backoff and the polite delay between coins
import requests                 # the actual HTTP client
import pandas as pd             # used to shape raw JSON into DataFrames as soon as it arrives

from . import config             # pulls in every setting from config.py — no hardcoded values in this file


def _get_with_retry(url: str, params: dict) -> dict:
    """
    Internal helper: does a GET request, and if the server responds with 429 (rate limited),
    waits and retries with exponential backoff instead of giving up immediately.
    Underscore prefix signals this is an internal helper, not part of the public API of this module.
    """
    for attempt in range(config.MAX_RETRIES):                     # try up to MAX_RETRIES times total
        response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SECONDS)

        if response.status_code == 429:                            # server says "too many requests, slow down"
            wait_time = config.RETRY_BACKOFF_BASE_SECONDS * (2 ** attempt)   # 2s, then 4s, then 8s...
            print(f"  Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{config.MAX_RETRIES}...")
            time.sleep(wait_time)
            continue                                                 # go back to the top of the loop and try again

        response.raise_for_status()                                  # raises for any OTHER error status (404, 500, etc.)
        return response.json()                                       # success — parse and return the JSON body

    # If every retry was also rate-limited, fail loudly rather than returning empty/fake data
    raise RuntimeError(f"Gave up on {url} after {config.MAX_RETRIES} retries — still rate limited.")


def validate_coin_ids(coin_ids: list[str]) -> list[str]:
    """
    Checks each configured coin ID against CoinGecko's /coins/list before spending real API calls
    on IDs that don't exist (e.g. a slug that got renamed). Returns only the valid ones and prints
    a clear warning for anything invalid, instead of crashing partway through the pipeline.
    """
    url = f"{config.COINGECKO_BASE_URL}/coins/list"
    all_known_coins = _get_with_retry(url, params={})               # returns a big list of {"id", "symbol", "name"} dicts
    known_ids = {coin["id"] for coin in all_known_coins}             # set for fast membership checks below

    valid = []
    for coin_id in coin_ids:
        if coin_id in known_ids:
            valid.append(coin_id)
        else:
            # Print, don't raise — one bad coin ID shouldn't take down the whole pipeline run
            print(f"  WARNING: '{coin_id}' is not a recognized CoinGecko ID. Skipping it.")

    if not valid:
        raise ValueError("None of the configured coin IDs are valid. Check config.COINS.")

    return valid


def fetch_coin_history(coin_id: str) -> pd.DataFrame:
    """
    Pulls daily price, volume, and market cap history for one coin.
    Returns a DataFrame with columns: date, price, volume, market_cap, coin.
    """
    url = f"{config.COINGECKO_BASE_URL}/coins/{coin_id}/market_chart"
    params = {
        "vs_currency": config.VS_CURRENCY,
        "days": config.DAYS_HISTORY,
        "interval": "daily",             # explicit, so CoinGecko doesn't default to hourly for shorter windows
    }
    raw = _get_with_retry(url, params)

    # A 200 OK with empty arrays happens for legacy/renamed coin IDs (e.g. old "matic-network"
    # after the MATIC->POL migration) — CoinGecko still recognizes the ID but has no chart data
    # for it. This isn't an HTTP error, so _get_with_retry's retry logic won't catch it. Without
    # this check, an empty DataFrame would silently merge into the dataset with zero rows for
    # this coin, and nunique() downstream would just quietly report one fewer coin than expected.
    if not raw.get("prices"):
        raise RuntimeError(
            f"CoinGecko returned no chart data for '{coin_id}' — the ID may be deprecated or "
            f"renamed (check https://www.coingecko.com/en/coins/{coin_id} to find the current ID)."
        )

    # CoinGecko returns three separate parallel lists of [timestamp_ms, value] — join them on the timestamp
    prices = pd.DataFrame(raw["prices"], columns=["ts_ms", "price"])
    volumes = pd.DataFrame(raw["total_volumes"], columns=["ts_ms", "volume"])
    market_caps = pd.DataFrame(raw["market_caps"], columns=["ts_ms", "market_cap"])

    df = prices.merge(volumes, on="ts_ms").merge(market_caps, on="ts_ms")
    df["date"] = pd.to_datetime(df["ts_ms"], unit="ms").dt.date       # convert epoch milliseconds -> plain date
    df["coin"] = coin_id                                                # tag every row so it survives concatenation later
    df = df.drop(columns=["ts_ms"])                                     # raw timestamp no longer needed
    return df


def fetch_all_coins(coin_ids: list[str]) -> pd.DataFrame:
    """
    Loops over every validated coin ID, fetches its history, and stacks the results into one long table.
    Sleeps between calls to stay under the free tier's rate limit. If one coin fails even after all
    its retries (e.g. persistent 429s), that coin is skipped with a clear warning instead of taking
    down the whole run — you still get a usable dataset for the coins that did succeed.
    """
    frames = []
    failed_coins = []

    for i, coin_id in enumerate(coin_ids):
        print(f"Fetching {coin_id} ({i + 1}/{len(coin_ids)})...")
        try:
            frames.append(fetch_coin_history(coin_id))
        except RuntimeError as e:                                        # raised by _get_with_retry after exhausting retries
            print(f"  FAILED: {coin_id} — {e}")
            print(f"  Skipping {coin_id} and continuing with the rest.")
            failed_coins.append(coin_id)

        if i < len(coin_ids) - 1:                                       # no need to sleep after the very last call
            time.sleep(config.POLITE_DELAY_BETWEEN_CALLS)

    if not frames:
        raise RuntimeError("Every coin failed to fetch — nothing to build a dataset from. Try again in a minute.")

    if failed_coins:
        print(f"\nNote: {failed_coins} could not be fetched — either rate limited (re-run later "
              f"to pick them up) or the coin ID is deprecated/renamed (check config.COINS).\n")

    return pd.concat(frames, ignore_index=True)                         # stack all coins into one long DataFrame


def fetch_sentiment_history() -> pd.DataFrame:
    """
    Pulls the Fear & Greed Index history — one market-wide sentiment value per day, NOT per coin.
    Returns a DataFrame with columns: date, fear_greed_value, fear_greed_label.
    """
    params = {"limit": config.DAYS_HISTORY, "format": "json"}
    raw = _get_with_retry(config.FEAR_GREED_URL, params)

    records = raw["data"]                                                # the actual daily readings live under "data"
    df = pd.DataFrame(records)

    # Alternative.me's timestamp is in SECONDS, unlike CoinGecko's milliseconds — easy mismatch to miss
    df["date"] = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.date
    df["value"] = df["value"].astype(int)                                # comes back as a string; cast for downstream math

    df = df.rename(columns={"value": "fear_greed_value", "value_classification": "fear_greed_label"})
    return df[["date", "fear_greed_value", "fear_greed_label"]]

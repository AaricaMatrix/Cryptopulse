"""
CryptoPulse — single-file prototype
Proves the whole flow works before splitting into modules: fetch -> compute -> merge -> export.
Run this once mentally (or actually, on your own machine with internet) to sanity check the approach.
"""

import time                      # used to sleep briefly between API calls, avoids hitting rate limits
import requests                  # handles the HTTP calls to CoinGecko and Alternative.me
import pandas as pd              # main tool for tabular data — building, joining, exporting CSVs
import numpy as np               # used for the z-score math in anomaly detection

# --- CONFIG (hardcoded here for the prototype; lives in config.py in the real build) ---
COINS = ["bitcoin", "ethereum", "solana"]   # CoinGecko slugs, NOT tickers — this trips people up
DAYS = 90                                    # how much history to pull per coin
VS_CURRENCY = "usd"                          # what to price everything in

def fetch_coin_history(coin_id: str) -> pd.DataFrame:
    """Pull daily price/volume/market cap for one coin from CoinGecko's free keyless endpoint."""
    url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": VS_CURRENCY, "days": DAYS, "interval": "daily"}
    resp = requests.get(url, params=params, timeout=15)   # 15s timeout so a hung request doesn't stall the whole run
    resp.raise_for_status()                                # raises if CoinGecko returns an error status (bad coin id, etc.)
    raw = resp.json()                                       # parse the JSON body into a Python dict

    # CoinGecko returns three parallel lists of [timestamp_ms, value] pairs — zip them into one table
    prices = pd.DataFrame(raw["prices"], columns=["ts_ms", "price"])
    volumes = pd.DataFrame(raw["total_volumes"], columns=["ts_ms", "volume"])
    mcaps = pd.DataFrame(raw["market_caps"], columns=["ts_ms", "market_cap"])

    df = prices.merge(volumes, on="ts_ms").merge(mcaps, on="ts_ms")   # join all three on the shared timestamp
    df["date"] = pd.to_datetime(df["ts_ms"], unit="ms").dt.date        # convert epoch ms -> a plain calendar date
    df["coin"] = coin_id                                                # tag every row with which coin it belongs to
    df = df.drop(columns=["ts_ms"])                                     # raw timestamp no longer needed once we have `date`
    return df

def fetch_sentiment(days: int) -> pd.DataFrame:
    """Pull the Fear & Greed Index history — market-wide sentiment, one value per day."""
    url = "https://api.alternative.me/fng/"
    params = {"limit": days, "format": "json"}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    records = resp.json()["data"]                            # the actual list of daily readings is under "data"

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["timestamp"].astype(int), unit="s").dt.date   # timestamp here is in SECONDS, not ms
    df["value"] = df["value"].astype(int)                     # comes back as a string in the API, cast to int for math
    return df[["date", "value", "value_classification"]].rename(
        columns={"value": "fear_greed_value", "value_classification": "fear_greed_label"}
    )

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute returns, rolling volatility, and volume z-score anomalies — per coin, in date order."""
    df = df.sort_values(["coin", "date"]).copy()              # rolling calculations require chronological order

    df["daily_return"] = df.groupby("coin")["price"].pct_change()   # % change from previous day, per coin separately

    # rolling volatility = rolling std dev of returns; grouped so one coin's window never bleeds into another's
    df["vol_7d"] = df.groupby("coin")["daily_return"].transform(lambda s: s.rolling(7).std())
    df["vol_30d"] = df.groupby("coin")["daily_return"].transform(lambda s: s.rolling(30).std())

    # volume z-score: how many standard deviations today's volume is from the trailing 30-day average
    roll_mean = df.groupby("coin")["volume"].transform(lambda s: s.rolling(30).mean())
    roll_std = df.groupby("coin")["volume"].transform(lambda s: s.rolling(30).std())
    df["volume_zscore"] = (df["volume"] - roll_mean) / roll_std
    df["volume_anomaly"] = df["volume_zscore"].abs() > 2        # simple heuristic flag, not a trained model — say so

    return df

def run_prototype():
    """Wire the whole thing together end to end and print a sanity-check summary."""
    all_coins = []
    for coin in COINS:
        print(f"Fetching {coin}...")
        all_coins.append(fetch_coin_history(coin))
        time.sleep(1.5)                       # small delay between calls — polite to the free tier, avoids 429s

    prices_df = pd.concat(all_coins, ignore_index=True)   # stack all coins into one long table
    prices_df = add_features(prices_df)

    sentiment_df = fetch_sentiment(DAYS)
    merged = prices_df.merge(sentiment_df, on="date", how="left")   # left join: keep every price row even if sentiment is missing

    print(merged[["date", "coin", "price", "vol_30d", "volume_anomaly", "fear_greed_value"]].tail())
    return merged

if __name__ == "__main__":
    run_prototype()

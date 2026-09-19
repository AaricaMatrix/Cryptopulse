"""
pipeline.py — the one file you actually run.
Orchestrates: validate coins -> fetch data -> compute features -> merge -> export CSVs -> save charts.
Run with: python -m src.pipeline (from the cryptopulse/ project root)
"""

import time                       # brief pause between validation and fetching — see note below

import matplotlib
matplotlib.use("Agg")             # non-interactive backend — saves PNGs to disk without needing a display

import matplotlib.pyplot as plt   # for building the 3 sanity-check charts
import seaborn as sns             # nicer default styling on top of matplotlib

from . import config
from . import fetch_data
from . import features
from . import anomaly_detection


def run_pipeline():
    """Runs the full pipeline end to end. This is the only function main() below needs to call."""

    # Step 1: make sure output folders exist before anything tries to write into them
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 2: validate coin IDs BEFORE spending API calls fetching data for ones that don't exist
    print("Validating coin IDs...")
    valid_coins = fetch_data.validate_coin_ids(config.COINS)
    print(f"  Proceeding with: {valid_coins}\n")

    # The validation call above (/coins/list) is itself a request against the same shared rate
    # limit as everything else — give it a moment to clear before immediately firing off 5 more.
    time.sleep(config.POLITE_DELAY_BETWEEN_CALLS)

    # Step 3: fetch price/volume/market cap history for every valid coin
    print("Fetching coin market data...")
    coin_df = fetch_data.fetch_all_coins(valid_coins)
    print(f"  Got {len(coin_df)} rows across {coin_df['coin'].nunique()} coins.\n")

    # Step 4: fetch market-wide sentiment history (separate from per-coin data — see documentation.md)
    print("Fetching Fear & Greed sentiment history...")
    sentiment_df = fetch_data.fetch_sentiment_history()
    print(f"  Got {len(sentiment_df)} days of sentiment data.\n")

    # Step 5: compute returns and rolling volatility on the price data
    print("Computing returns and rolling volatility...")
    coin_df = features.build_features(coin_df)

    # Step 6: flag anomalous volume days using the z-score heuristic
    print("Flagging volume anomalies...")
    coin_df = anomaly_detection.flag_volume_anomalies(coin_df)
    anomaly_count = int(coin_df["volume_anomaly"].sum())
    print(f"  Flagged {anomaly_count} anomalous volume days across all coins.\n")

    # Step 7: merge sentiment onto the coin data by date.
    # LEFT join: keep every price row even on days where sentiment data happens to be missing.
    merged_df = coin_df.merge(sentiment_df, on="date", how="left")

    # Step 8: write all three CSVs. index=False because the DataFrame's row numbers aren't meaningful data.
    print("Writing CSVs...")
    coin_df.to_csv(config.COIN_METRICS_CSV, index=False)
    sentiment_df.to_csv(config.SENTIMENT_CSV, index=False)
    merged_df.to_csv(config.MERGED_CSV, index=False)
    print(f"  {config.COIN_METRICS_CSV}")
    print(f"  {config.SENTIMENT_CSV}")
    print(f"  {config.MERGED_CSV}\n")

    # Step 9: quick charts as a sanity check before opening anything in Tableau
    print("Generating sanity-check charts...")
    _plot_volatility_by_coin(coin_df)
    _plot_volume_anomalies(coin_df, valid_coins[0])   # illustrate on the first coin, to keep the chart readable
    _plot_price_vs_sentiment(merged_df, valid_coins[0])
    print(f"  Charts saved to {config.CHARTS_DIR}\n")

    print("Done. Open data/merged_daily.csv in Tableau to start building views.")
    return merged_df


def _plot_volatility_by_coin(coin_df):
    """Line chart: 30-day rolling volatility over time, one line per coin."""
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=coin_df, x="date", y="vol_30d", hue="coin")
    plt.title("30-Day Rolling Volatility by Coin")
    plt.xlabel("Date")
    plt.ylabel("Rolling Std Dev of Daily Returns")
    plt.xticks(rotation=45)
    plt.tight_layout()                                  # prevents axis labels from getting cut off at the edges
    plt.savefig(config.CHARTS_DIR / "volatility_by_coin.png", dpi=150)
    plt.close()                                          # frees memory — matters when generating multiple charts in one run


def _plot_volume_anomalies(coin_df, coin_id: str):
    """Price line for one coin, with anomalous volume days marked as red points."""
    single_coin = coin_df[coin_df["coin"] == coin_id]

    plt.figure(figsize=(10, 6))
    plt.plot(single_coin["date"], single_coin["price"], label="Price", color="steelblue")

    anomalies = single_coin[single_coin["volume_anomaly"]]
    plt.scatter(anomalies["date"], anomalies["price"], color="red", label="Anomalous Volume Day", zorder=5)

    plt.title(f"{coin_id.capitalize()} Price with Volume Anomalies Marked")
    plt.xlabel("Date")
    plt.ylabel(f"Price ({config.VS_CURRENCY.upper()})")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(config.CHARTS_DIR / "volume_anomalies.png", dpi=150)
    plt.close()


def _plot_price_vs_sentiment(merged_df, coin_id: str):
    """Dual-axis chart: one coin's price against market-wide Fear & Greed sentiment."""
    single_coin = merged_df[merged_df["coin"] == coin_id]

    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.plot(single_coin["date"], single_coin["price"], color="steelblue", label="Price")
    ax1.set_xlabel("Date")
    ax1.set_ylabel(f"Price ({config.VS_CURRENCY.upper()})", color="steelblue")
    ax1.tick_params(axis="y", labelcolor="steelblue")

    ax2 = ax1.twinx()                                     # second y-axis sharing the same x-axis
    ax2.plot(single_coin["date"], single_coin["fear_greed_value"], color="darkorange", label="Fear & Greed")
    ax2.set_ylabel("Fear & Greed Index (0-100)", color="darkorange")
    ax2.tick_params(axis="y", labelcolor="darkorange")

    plt.title(f"{coin_id.capitalize()} Price vs. Market-Wide Sentiment")
    fig.autofmt_xdate(rotation=45)
    plt.tight_layout()
    plt.savefig(config.CHARTS_DIR / "price_vs_sentiment.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    run_pipeline()

"""
features.py — pure calculation functions: returns and rolling volatility.
Nothing in this file makes a network call, which means it's easy to test in isolation
(feed it a small hand-built DataFrame, check the output) without needing internet access.
"""

import pandas as pd              # all the functions here operate on and return DataFrames

from . import config              # for the rolling window sizes, so they're not hardcoded here too


def add_daily_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a 'daily_return' column: simple percent change in price from the previous day.
    Grouped by coin so the calculation never bleeds across different coins.
    First day of each coin's history is NaN — there's no "previous day" to compare against.
    """
    df = df.copy()                                                       # avoid mutating the caller's DataFrame
    df["daily_return"] = df.groupby("coin")["price"].pct_change()
    return df


def add_rolling_volatility(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds 'vol_7d' and 'vol_30d': rolling standard deviation of daily returns.
    This is the standard definition of realized volatility — how much the price is swinging,
    regardless of direction. Requires add_daily_returns() to have already run.
    """
    df = df.copy()

    df["vol_7d"] = df.groupby("coin")["daily_return"].transform(
        lambda returns: returns.rolling(config.ROLLING_WINDOW_SHORT).std()
    )
    df["vol_30d"] = df.groupby("coin")["daily_return"].transform(
        lambda returns: returns.rolling(config.ROLLING_WINDOW_LONG).std()
    )
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convenience wrapper: sorts the data into correct order, then runs both feature functions above.
    This is the one function pipeline.py actually needs to call.
    """
    # Rolling calculations depend on chronological order — sort before doing anything else
    df = df.sort_values(["coin", "date"]).reset_index(drop=True)
    df = add_daily_returns(df)
    df = add_rolling_volatility(df)
    return df

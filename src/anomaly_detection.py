"""
anomaly_detection.py — volume anomaly flagging, isolated in its own file on purpose.

This uses a z-score heuristic, not a trained model like the Isolation Forest used in
EcoTrack-AI. That's a deliberate choice for ~90 data points per coin, not a limitation
to hide — z-score is simpler, easier to explain out loud, and appropriate for this
dataset size. See SKILL.md for the full reasoning.

Keeping this logic in its own file means swapping it for something heavier later
(if the dataset ever grows) is a contained change, not a rewrite of the pipeline.
"""

import pandas as pd

from . import config


def flag_volume_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds 'volume_zscore' and 'volume_anomaly' columns.

    volume_zscore: how many standard deviations today's volume is from the trailing
    rolling mean, per coin. A large positive value means unusually high volume;
    a large negative value means unusually low volume — both are worth a look.

    volume_anomaly: True when |volume_zscore| exceeds config.ANOMALY_ZSCORE_THRESHOLD.
    """
    df = df.copy()

    rolling_mean = df.groupby("coin")["volume"].transform(
        lambda volume: volume.rolling(config.ROLLING_WINDOW_LONG).mean()
    )
    rolling_std = df.groupby("coin")["volume"].transform(
        lambda volume: volume.rolling(config.ROLLING_WINDOW_LONG).std()
    )

    df["volume_zscore"] = (df["volume"] - rolling_mean) / rolling_std
    df["volume_anomaly"] = df["volume_zscore"].abs() > config.ANOMALY_ZSCORE_THRESHOLD

    return df

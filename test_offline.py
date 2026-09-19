cat > test_offline.py << 'EOF'
import pandas as pd
import numpy as np
from src import features, anomaly_detection

np.random.seed(42)
dates = pd.date_range("2026-06-01", periods=90, freq="D").date
coins = []
for coin in ["bitcoin", "ethereum"]:
    base = 60000 if coin == "bitcoin" else 3000
    prices = base + np.cumsum(np.random.normal(0, base * 0.02, 90))
    volumes = np.random.normal(1e9, 1e8, 90)
    volumes[50] *= 5  # inject a fake spike to check anomaly detection catches it
    coins.append(pd.DataFrame({
        "date": dates, "price": prices, "volume": volumes,
        "market_cap": prices * 19_000_000, "coin": coin
    }))

df = pd.concat(coins, ignore_index=True)
df = features.build_features(df)
df = anomaly_detection.flag_volume_anomalies(df)

print("Columns:", list(df.columns))
print("Anomalies found:", df["volume_anomaly"].sum(), "(should be > 0)")
print(df[df["volume_anomaly"]][["date", "coin", "volume_zscore"]])
assert df["volume_anomaly"].sum() > 0, "FAIL: injected spike wasn't caught"
print("\nPASS")
EOF
python test_offline.py
"""
generate_crowd_csv.py
Generates a comprehensive synthetic crowd density dataset for LSTM training.
Models real-world Indian railway station crowd patterns with:
  - Hourly and weekly seasonality
  - Train arrival events
  - Rush hour peaks (7-10am, 5-8pm)
  - Weekend vs weekday patterns
  - Festival surge events
  - Monsoon delay effects
Outputs: backend/datasets/crowd_data.csv (10,000 samples)
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_PATH = BASE_DIR / "datasets" / "crowd_data.csv"


def rush_hour_factor(hour: int) -> float:
    """Return a multiplier for crowd density based on hour of day."""
    if 7 <= hour <= 9:    # Morning rush
        return 2.5 + np.random.normal(0, 0.3)
    elif 17 <= hour <= 20: # Evening rush
        return 2.8 + np.random.normal(0, 0.4)
    elif 12 <= hour <= 14: # Afternoon moderate
        return 1.4 + np.random.normal(0, 0.2)
    elif 22 <= hour or hour <= 4: # Night
        return 0.3 + np.random.normal(0, 0.1)
    else:
        return 1.0 + np.random.normal(0, 0.15)


def train_arrival_spike(arrivals: int) -> int:
    """Crowd count spike when trains arrive."""
    return arrivals * int(np.random.randint(20, 60))


def generate(n_samples: int = 10000) -> pd.DataFrame:
    rows = []
    
    # Simulate ~417 days worth of hourly data (10000 samples)
    for i in range(n_samples):
        hour        = i % 24
        day_of_week = (i // 24) % 7  # 0=Monday, 6=Sunday
        is_weekend  = int(day_of_week >= 5)
        is_festival = int(np.random.random() < 0.03)  # 3% festival days
        is_monsoon  = int(np.random.random() < 0.15)  # 15% rainy

        # Base crowd
        base = 120 if not is_weekend else 80
        rush = rush_hour_factor(hour)
        
        # Train arrivals in next 10 minutes (Poisson)
        train_arrivals = np.random.poisson(2 if 6 <= hour <= 22 else 0.5)
        
        # Current crowd count
        current_count = int(
            base * rush 
            + train_arrival_spike(train_arrivals)
            + is_festival * np.random.randint(80, 200)
            - is_monsoon  * np.random.randint(0, 30)
            + np.random.normal(0, 8)
        )
        current_count = max(0, min(500, current_count))

        # Target: crowd count 10 minutes from now
        next_arrivals = np.random.poisson(2 if 6 <= hour <= 22 else 0.5)
        target_count  = int(
            current_count
            + train_arrival_spike(next_arrivals)
            + np.random.normal(0, 10)
        )
        target_count = max(0, min(500, target_count))

        rows.append({
            "hour":                        hour,
            "day_of_week":                 day_of_week,
            "is_weekend":                  is_weekend,
            "is_festival":                 is_festival,
            "is_monsoon":                  is_monsoon,
            "current_count":               current_count,
            "train_arrivals_next_10min":   train_arrivals,
            "rush_hour_factor":            round(rush, 3),
            "target_count":                target_count,
        })

    return pd.DataFrame(rows)


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"[CROWD-GEN] Generating {10000} crowd density samples...")
    df = generate(10000)
    df.to_csv(OUT_PATH, index=False)

    print(f"\n{'='*60}")
    print(f"CROWD DATA GENERATED")
    print(f"  Samples: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Mean crowd count      : {df['current_count'].mean():.1f}")
    print(f"  Max crowd count       : {df['current_count'].max()}")
    print(f"  Avg target vs current : {(df['target_count'] - df['current_count']).mean():.1f}")
    print(f"\n  Saved → {OUT_PATH}")
    print(f"  Next step: python backend/train_lstm.py")


if __name__ == "__main__":
    main()

"""
train_lstm.py
Trains a 3-layer LSTM for platform crowd density forecasting.
Uses the enriched synthetic crowd_data.csv (10,000 samples).
Outputs: backend/models/lstm_crowd.h5 + lstm_scaler.pkl
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path

BASE_DIR  = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

# Features used for crowd forecasting
FEATURES = [
    "hour", "day_of_week", "is_weekend", "is_festival",
    "is_monsoon", "current_count", "train_arrivals_next_10min",
    "rush_hour_factor",
]
TARGET = "target_count"

SEQUENCE_LEN = 10   # How many past timesteps to use for prediction
EPOCHS       = 100
BATCH_SIZE   = 32


def build_sequences(arr: np.ndarray, seq_len: int):
    X, y = [], []
    for i in range(len(arr) - seq_len):
        X.append(arr[i:i + seq_len, :-1])   # features
        y.append(arr[i + seq_len, -1])       # target
    return np.array(X), np.array(y)


def build_model(input_shape):
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
    from tensorflow.keras.regularizers import l2

    model = Sequential([
        LSTM(128, return_sequences=True, input_shape=input_shape,
             kernel_regularizer=l2(1e-4)),
        Dropout(0.2),
        BatchNormalization(),
        
        LSTM(64, return_sequences=True, kernel_regularizer=l2(1e-4)),
        Dropout(0.2),
        BatchNormalization(),
        
        LSTM(32, kernel_regularizer=l2(1e-4)),
        Dropout(0.1),
        
        Dense(16, activation="relu"),
        Dense(1)
    ])

    model.compile(
        optimizer="adam",
        loss="huber",            # Huber loss — robust to outliers (surges)
        metrics=["mae"],
    )
    return model


def main():
    import tensorflow as tf
    from tensorflow.keras.callbacks import (
        EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
    )
    from sklearn.preprocessing import MinMaxScaler

    data_path = BASE_DIR / "datasets" / "crowd_data.csv"
    if not data_path.exists():
        print(f"[LSTM] Data not found at {data_path}")
        print(f"[LSTM] Running crowd data generator first...")
        import subprocess
        subprocess.run(
            ["python", str(BASE_DIR / "scripts" / "generate_crowd_csv.py")]
        )

    df = pd.read_csv(data_path)
    print(f"[LSTM] Loaded {len(df)} samples, columns: {list(df.columns)}")

    # Select features that exist
    available_features = [f for f in FEATURES if f in df.columns]
    print(f"[LSTM] Features: {available_features}")

    data = df[available_features + [TARGET]].values

    scaler = MinMaxScaler()
    data_scaled = scaler.fit_transform(data)

    X, y = build_sequences(data_scaled, SEQUENCE_LEN)
    
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    print(f"[LSTM] Train: {len(X_train)} | Val: {len(X_val)}")
    print(f"[LSTM] Building 3-layer LSTM model...")

    model = build_model((SEQUENCE_LEN, X.shape[2]))
    model.summary()

    callbacks = [
        EarlyStopping(
            monitor="val_loss",
            patience=12,
            restore_best_weights=True,
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=6,
            min_lr=1e-6,
            verbose=1,
        ),
        ModelCheckpoint(
            str(MODEL_DIR / "lstm_crowd_best.h5"),
            monitor="val_loss",
            save_best_only=True,
            verbose=1,
        ),
    ]

    print(f"\n[LSTM] Training for up to {EPOCHS} epochs...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        callbacks=callbacks,
        verbose=1,
    )

    # Save final model + scaler
    model.save(MODEL_DIR / "lstm_crowd.h5")
    joblib.dump(scaler, MODEL_DIR / "lstm_scaler.pkl")
    joblib.dump({"seq_len": SEQUENCE_LEN, "features": available_features},
                MODEL_DIR / "lstm_config.pkl")

    best_epoch = np.argmin(history.history["val_loss"]) + 1
    final_mae  = min(history.history["val_mae"])
    final_loss = min(history.history["val_loss"])

    print(f"\n{'='*60}")
    print(f"LSTM Training Complete")
    print(f"  Best Epoch       : {best_epoch}")
    print(f"  Best Val MAE     : {final_mae:.2f} persons")
    print(f"  Best Val RMSE    : {np.sqrt(final_loss):.2f} persons")
    print(f"  Saved → {MODEL_DIR / 'lstm_crowd.h5'}")


if __name__ == "__main__":
    main()
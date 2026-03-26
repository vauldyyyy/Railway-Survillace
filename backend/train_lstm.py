"""
train_lstm.py
Trains LSTM for platform crowd density forecasting.
Outputs: backend/models/lstm_crowd.h5 + lstm_scaler.pkl
"""

import pandas as pd
import numpy as np
import joblib
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path

# Set paths
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(exist_ok=True)

def prepare_data(csv_path):
    df = pd.read_csv(csv_path)
    # Features: hour, day_of_week, current_count, train_arrivals
    # Note: Simplified for hackathon based on Part D requirement
    features = df[['hour', 'day_of_week', 'current_count', 'train_arrivals_next_10min']].values
    target = df['target_count'].values

    scaler = MinMaxScaler()
    features_scaled = scaler.fit_transform(features)
    
    # Reshape for LSTM [samples, time_steps, features]
    # We'll use a window of 1 (single step prediction for demo simplicity)
    X = features_scaled.reshape((features_scaled.shape[0], 1, features_scaled.shape[1]))
    y = target
    
    return X, y, scaler

def build_model(input_shape):
    model = Sequential([
        LSTM(64, return_sequences=True, input_shape=input_shape),
        Dropout(0.2),
        LSTM(32),
        Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse', metrics=['mae'])
    return model

def main():
    # Assuming synthetic data was generated at datasets/crowd_data.csv
    data_path = BASE_DIR / "datasets" / "crowd_data.csv"
    if not data_path.exists():
        print(f"Data not found at {data_path}. Please run synthetic data generator first.")
        return

    X, y, scaler = prepare_data(data_path)
    
    print("Training LSTM on CPU...")
    model = build_model((X.shape[1], X.shape[2]))
    
    history = model.fit(
        X, y, 
        epochs=30, # Reduced from 100 for speed
        batch_size=16, 
        validation_split=0.2, 
        verbose=1
    )

    # Save artifacts
    model.save(MODEL_DIR / "lstm_crowd.h5")
    joblib.dump(scaler, MODEL_DIR / "lstm_scaler.pkl")
    
    final_mae = history.history['val_mae'][-1]
    print(f"\nTraining Complete. Model saved to {MODEL_DIR}")
    print(f"Final Validation MAE: {final_mae:.2f}")

    # Calculate RMSE for Part D requirement
    val_loss = history.history['val_loss'][-1]
    print(f"Final Validation RMSE: {np.sqrt(val_loss):.2f}")

if __name__ == "__main__":
    main()
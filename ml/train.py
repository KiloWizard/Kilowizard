"""
Minimal TFT eğitim betiği – demo amaçlı.
Gerçek projede veri hazırlığını ve HPO'yu genişletin.
"""
import pandas as pd, torch, pytorch_forecasting as pf, mlflow
from pathlib import Path

def load_data(path="data/processed/train.parquet"):
    return pd.read_parquet(path)

def train():
    df = load_data()
    training = pf.TimeSeriesDataSet(
        df,
        time_idx="time_idx",
        target="active_power",
        group_ids=["breaker_id"],
        max_encoder_length=72,
        max_prediction_length=24,
    )
    loader = training.to_dataloader(train=True, batch_size=64)
    tft = pf.TemporalFusionTransformer.from_dataset(
        training, learning_rate=1e-3, hidden_size=32, log_interval=10
    )
    with mlflow.start_run(run_name="tft_v0"):
        mlflow.pytorch.log_model(tft, "model")
        tft.fit(15, loader, num_workers=0)
        mlflow.log_param("encoder_len", 72)
        mlflow.log_param("pred_len", 24)

if __name__ == "__main__":
    train()

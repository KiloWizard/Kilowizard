import mlflow, pandas as pd, json, os, datetime as dt
from utils.schemas import RawMeasurement
from typing import List

MODEL_URI = os.getenv("ML_MODEL_URI", "models:/tft_v0/production")

def load_model():
    return mlflow.pytorch.load_model(MODEL_URI)

model = load_model()

def predict_last_24h(measurements: List[RawMeasurement]):
    df = pd.DataFrame([m.metrics.model_dump() | {
        "breaker_id": m.breaker_id,
        "timestamp": m.timestamp
    } for m in measurements])
    # ... feature engineering to match training dataset ...
    preds = model.predict(df)
    return {"expected_kWh": float(preds.sum()), "expected_cost": float(preds.sum()*2.1)}

if __name__ == "__main__":
    sample = json.load(open("sample.json"))
    out = predict_last_24h([RawMeasurement(**sample)])
    print(out)


from fastapi import FastAPI, Body
app = FastAPI()

@app.post("/predict")
def predict_endpoint(data: list = Body(...)):
    return predict_last_24h([RawMeasurement(**j) for j in data])
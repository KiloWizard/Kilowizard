from fastapi import FastAPI, HTTPException
from utils.schemas import RawMeasurement
import json, datetime, os

app = FastAPI(title="Breaker Collector")

DATA_DIR = os.getenv("RAW_DATA_DIR", "data/raw")

@app.post("/ingest")
def ingest(measurement: RawMeasurement):
    path = f"{DATA_DIR}/{measurement.breaker_id}_{measurement.timestamp}.json"
    try:
        with open(path, "w") as f:
            json.dump(measurement.model_dump(), f)
        return {"status": "ok", "path": path}
    except Exception as exc:
        raise HTTPException(500, str(exc))

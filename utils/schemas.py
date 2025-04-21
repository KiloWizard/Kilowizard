from pydantic import BaseModel, Field
from typing import Dict
from datetime import datetime

class Metrics(BaseModel):
    current: float
    voltage: float
    active_power: float
    reactive_power: float
    apparent_power: float
    power_factor: float
    energy: float
    leakage_current: float
    temperature: float

class RawMeasurement(BaseModel):
    timestamp: datetime = Field(...)
    breaker_id: str
    metrics: Metrics

from pydantic import BaseModel, Field
from typing import List


class EnergyScenario(BaseModel):
    demand: List[float] = Field(..., min_length=24, max_length=24)
    solar: List[float] = Field(..., min_length=24, max_length=24)
    tariff: List[float] = Field(..., min_length=24, max_length=24)

    battery_capacity: float

    operator_notes: List[str]


class OptimizationResponse(BaseModel):
    status: str
    schedule: List[float]
    total_cost: float
    message: str

from fastapi import APIRouter
from app.schemas import EnergyScenario, OptimizationResponse
from app.services import process_energy_request

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok"
    }


@router.post("/optimize-energy",
             response_model=OptimizationResponse)
def optimize_energy(scenario: EnergyScenario):

    schedule, cost = process_energy_request(scenario)

    return {
        "status": "success",
        "schedule": schedule,
        "total_cost": cost,
        "message": "Optimization completed"
    }

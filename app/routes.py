from fastapi import APIRouter, HTTPException
from app.schemas import EnergyScenario, OptimizationResponse
from app.services import process_energy_request

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/optimize-energy", response_model=OptimizationResponse)
def optimize_energy_endpoint(scenario: EnergyScenario):
    try:
        return process_energy_request(scenario)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        # Do not expose stack traces, API keys, or provider internals.
        raise HTTPException(status_code=500, detail="Optimization service failed")

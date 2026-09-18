from app.guardrails import validate_directives, effective_parameters
from app.llm import interpret_notes
from app.optimizer import optimize_energy


def process_energy_request(data):
    scenario = data.model_dump()

    raw_directives = interpret_notes(scenario)
    directives = validate_directives(
        raw_directives,
        scenario["operator_notes"],
        scenario["battery"],
    )
    params = effective_parameters(scenario, directives)
    plan = optimize_energy(scenario, params)

    tariffs = [h["tariff_bdt_per_kwh"] for h in scenario["hours"]]
    total_grid = sum(p["grid_kwh"] for p in plan)
    total_cost = sum(p["grid_kwh"] * tariffs[p["hour"]] for p in plan)
    peak_grid = max(p["grid_kwh"] for p in plan)

    return {
        "scenario_id": scenario["scenario_id"],
        "directive_interpretation": directives,
        "hourly_plan": plan,
        "total_grid_kwh": round(total_grid, 4),
        "total_cost_bdt": round(total_cost, 4),
        "peak_grid_kwh": round(peak_grid, 4),
        "plan_summary": (
            "The plan uses available solar first, shifts energy with the battery "
            "within all reserve/rate/directive limits, and minimizes grid electricity cost."
        ),
    }

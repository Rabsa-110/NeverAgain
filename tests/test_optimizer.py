from app.guardrails import effective_parameters
from app.optimizer import optimize_energy


def scenario():
    return {
        "scenario_id": "TEST-1",
        "operator_notes": [],
        "hours": [
            {"hour": i, "demand_kwh": 10, "solar_kwh": 5, "tariff_bdt_per_kwh": 2}
            for i in range(24)
        ],
        "battery": {
            "capacity_kwh": 100,
            "initial_energy_kwh": 50,
            "minimum_energy_kwh": 20,
            "max_charge_kwh_per_hour": 20,
            "max_discharge_kwh_per_hour": 20,
        },
    }


def test_optimizer_balance_and_neutrality():
    s = scenario()
    params = effective_parameters(s, [])
    plan = optimize_energy(s, params)

    assert len(plan) == 24
    assert plan[0]["hour"] == 0
    assert plan[-1]["hour"] == 23
    assert abs(plan[-1]["battery_energy_after_kwh"] - 50) <= 0.01

    for p in plan:
        assert p["grid_kwh"] >= 0
        assert p["solar_used_kwh"] <= 5.01


def test_max_grid_window():
    s = scenario()
    directives = [{
        "note_index": 0,
        "applies": True,
        "directive_type": "max_grid_window",
        "structured_adjustment": {"hours": list(range(24)), "max_grid_kwh": 5},
        "explanation": "test",
    }]
    params = effective_parameters(s, directives)
    plan = optimize_energy(s, params)

    assert all(p["grid_kwh"] <= 5.01 for p in plan)

import math
from copy import deepcopy


SUPPORTED = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}


def _valid_hours(hours):
    return (
        isinstance(hours, list)
        and all(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 23 for x in hours)
        and hours == sorted(set(hours))
    )


def validate_directives(raw, notes, battery):
    if not isinstance(raw, list) or len(raw) != len(notes):
        raise ValueError("LLM must return exactly one directive per operator note")

    seen = set()
    clean = []

    for expected_index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("Directive entry must be an object")

        idx = item.get("note_index")
        if idx != expected_index or idx in seen:
            raise ValueError("Directive note_index/order is invalid")
        seen.add(idx)

        applies = item.get("applies")
        dtype = item.get("directive_type")
        adjustment = item.get("structured_adjustment")
        explanation = str(item.get("explanation", ""))[:500]

        if dtype not in SUPPORTED:
            raise ValueError("Unsupported directive type")

        if dtype == "no_op":
            if applies is not False or adjustment is not None:
                raise ValueError("no_op must use applies=false and null adjustment")
            clean.append({
                "note_index": idx,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": explanation,
            })
            continue

        if applies is not True or not isinstance(adjustment, dict):
            raise ValueError("Applicable directives require applies=true and an adjustment")

        hours = adjustment.get("hours")
        if not _valid_hours(hours):
            raise ValueError("hours must be unique integers 0..23 in ascending order")

        a = deepcopy(adjustment)

        if dtype == "solar_reduction":
            factor = a.get("factor")
            if not isinstance(factor, (int, float)) or isinstance(factor, bool):
                raise ValueError("solar factor must be numeric")
            if not math.isfinite(factor) or not 0 <= factor <= 1:
                raise ValueError("solar factor must be between 0 and 1")
            a = {"hours": hours, "factor": float(factor)}

        elif dtype == "minimum_battery_reserve":
            value = a.get("minimum_energy_kwh")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError("reserve must be numeric")
            if not math.isfinite(value) or value < 0 or value > battery["capacity_kwh"]:
                raise ValueError("reserve is outside battery bounds")
            a = {"hours": hours, "minimum_energy_kwh": float(value)}

        elif dtype == "max_grid_window":
            value = a.get("max_grid_kwh")
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError("grid cap must be numeric")
            if not math.isfinite(value) or value < 0:
                raise ValueError("grid cap must be non-negative")
            a = {"hours": hours, "max_grid_kwh": float(value)}

        else:
            a = {"hours": hours}

        clean.append({
            "note_index": idx,
            "applies": True,
            "directive_type": dtype,
            "structured_adjustment": a,
            "explanation": explanation,
        })

    return clean


def effective_parameters(scenario, directives):
    hours = scenario["hours"]
    effective_solar = [float(x["solar_kwh"]) for x in hours]
    reserve = [float(scenario["battery"]["minimum_energy_kwh"])] * 24
    no_charge = [False] * 24
    no_discharge = [False] * 24
    grid_cap = [None] * 24

    for d in directives:
        if not d["applies"]:
            continue
        a = d["structured_adjustment"]
        dtype = d["directive_type"]

        if dtype == "solar_reduction":
            for h in a["hours"]:
                effective_solar[h] *= a["factor"]

        elif dtype == "minimum_battery_reserve":
            for h in a["hours"]:
                reserve[h] = max(reserve[h], a["minimum_energy_kwh"])

        elif dtype == "no_charge_window":
            for h in a["hours"]:
                no_charge[h] = True

        elif dtype == "no_discharge_window":
            for h in a["hours"]:
                no_discharge[h] = True

        elif dtype == "max_grid_window":
            for h in a["hours"]:
                grid_cap[h] = (
                    a["max_grid_kwh"]
                    if grid_cap[h] is None
                    else min(grid_cap[h], a["max_grid_kwh"])
                )

    return {
        "effective_solar": effective_solar,
        "reserve": reserve,
        "no_charge": no_charge,
        "no_discharge": no_discharge,
        "grid_cap": grid_cap,
    }

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


def optimize_energy(scenario: dict, params: dict) -> list[dict]:
    """Solve the 24-hour GridWise scheduling problem as a MILP.

    Variables per hour:
      grid, solar_used, charge, discharge, charge_on, discharge_on

    The binary action variables prevent simultaneous charging/discharging.
    """
    n = 24
    G = 0
    S = n
    C = 2 * n
    D = 3 * n
    ZC = 4 * n
    ZD = 5 * n
    N = 6 * n

    demand = np.array([h["demand_kwh"] for h in scenario["hours"]], dtype=float)
    solar = np.array(params["effective_solar"], dtype=float)
    tariff = np.array([h["tariff_bdt_per_kwh"] for h in scenario["hours"]], dtype=float)

    b = scenario["battery"]
    cap = float(b["capacity_kwh"])
    initial = float(b["initial_energy_kwh"])
    base_min = float(b["minimum_energy_kwh"])
    max_charge = float(b["max_charge_kwh_per_hour"])
    max_discharge = float(b["max_discharge_kwh_per_hour"])

    c = np.zeros(N)
    c[G:G+n] = tariff

    lower = np.zeros(N)
    upper = np.full(N, np.inf)

    # Solar usage.
    upper[S:S+n] = solar

    # Battery action magnitudes.
    upper[C:C+n] = np.where(params["no_charge"], 0.0, max_charge)
    upper[D:D+n] = np.where(params["no_discharge"], 0.0, max_discharge)

    # Binary flags.
    lower[ZC:ZD+n] = 0
    upper[ZC:ZD+n] = 1
    lower[ZD:ZD+n] = 0
    upper[ZD:ZD+n] = 1

    integrality = np.zeros(N)
    integrality[ZC:ZD+n] = 1
    integrality[ZD:ZD+n] = 1

    constraints = []

    # Energy balance:
    # grid + solar_used + discharge - charge = demand
    A = np.zeros((n, N))
    for h in range(n):
        A[h, G+h] = 1
        A[h, S+h] = 1
        A[h, C+h] = -1
        A[h, D+h] = 1
    constraints.append(LinearConstraint(A, demand, demand))

    # Battery state after each hour.
    # E_after = initial + cumulative(charge - discharge)
    A = np.zeros((n, N))
    for h in range(n):
        A[h, C:h+C+1] = 1
        A[h, D:h+D+1] = -1
    lb = np.array(params["reserve"], dtype=float) - initial
    ub = np.full(n, cap - initial)
    constraints.append(LinearConstraint(A, lb, ub))

    # End-of-day neutrality: sum charge == sum discharge.
    A = np.zeros((1, N))
    A[0, C:C+n] = 1
    A[0, D:D+n] = -1
    constraints.append(LinearConstraint(A, 0, 0))

    # Action magnitude <= rate * binary flag.
    A = np.zeros((2*n, N))
    lb = np.full(2*n, -np.inf)
    ub = np.zeros(2*n)

    for h in range(n):
        A[h, C+h] = 1
        A[h, ZC+h] = -max_charge

        A[n+h, D+h] = 1
        A[n+h, ZD+h] = -max_discharge
    constraints.append(LinearConstraint(A, lb, ub))

    # At most one action at a time.
    A = np.zeros((n, N))
    for h in range(n):
        A[h, ZC+h] = 1
        A[h, ZD+h] = 1
    constraints.append(LinearConstraint(A, -np.inf, np.ones(n)))

    # Grid caps.
    cap_hours = [(h, x) for h, x in enumerate(params["grid_cap"]) if x is not None]
    if cap_hours:
        A = np.zeros((len(cap_hours), N))
        ub = np.zeros(len(cap_hours))
        for row, (h, value) in enumerate(cap_hours):
            A[row, G+h] = 1
            ub[row] = value
        constraints.append(LinearConstraint(A, -np.inf, ub))

    result = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lower, upper),
        constraints=constraints,
        options={"time_limit": float(__import__("os").getenv("OPTIMIZER_TIME_LIMIT", "8"))},
    )

    if not result.success or result.x is None:
        raise RuntimeError(f"Optimization failed: {result.message}")

    x = result.x
    plan = []
    energy = initial

    for h in range(n):
        grid = max(0.0, float(x[G+h]))
        solar_used = max(0.0, float(x[S+h]))
        charge = max(0.0, float(x[C+h]))
        discharge = max(0.0, float(x[D+h]))

        if charge > 1e-7:
            action = "charge"
            battery_kwh = charge
            energy += charge
        elif discharge > 1e-7:
            action = "discharge"
            battery_kwh = discharge
            energy -= discharge
        else:
            action = "idle"
            battery_kwh = 0.0

        # Snap tiny floating errors.
        if abs(energy) < 1e-9:
            energy = 0.0

        plan.append({
            "hour": h,
            "grid_kwh": round(grid, 4),
            "solar_used_kwh": round(solar_used, 4),
            "battery_action": action,
            "battery_kwh": round(battery_kwh, 4),
            "battery_energy_after_kwh": round(energy, 4),
        })

    validate_plan(scenario, params, plan)
    return plan


def validate_plan(scenario, params, plan):
    b = scenario["battery"]
    if len(plan) != 24 or [x["hour"] for x in plan] != list(range(24)):
        raise RuntimeError("Optimizer returned invalid hour sequence")

    energy_before = float(b["initial_energy_kwh"])
    for h, p in enumerate(plan):
        demand = float(scenario["hours"][h]["demand_kwh"])
        effective_solar = float(params["effective_solar"][h])

        if p["solar_used_kwh"] < -1e-5 or p["solar_used_kwh"] > effective_solar + 1e-4:
            raise RuntimeError(f"Solar violation at hour {h}")

        if p["grid_kwh"] < -1e-5 or p["battery_kwh"] < -1e-5:
            raise RuntimeError(f"Negative energy at hour {h}")

        if p["battery_action"] == "charge":
            energy_after = energy_before + p["battery_kwh"]
            if params["no_charge"][h] or p["battery_kwh"] > b["max_charge_kwh_per_hour"] + 1e-4:
                raise RuntimeError(f"Charge constraint violation at hour {h}")
        elif p["battery_action"] == "discharge":
            energy_after = energy_before - p["battery_kwh"]
            if params["no_discharge"][h] or p["battery_kwh"] > b["max_discharge_kwh_per_hour"] + 1e-4:
                raise RuntimeError(f"Discharge constraint violation at hour {h}")
        else:
            if abs(p["battery_kwh"]) > 1e-4:
                raise RuntimeError(f"Idle action has nonzero battery energy at hour {h}")
            energy_after = energy_before

        if energy_after < params["reserve"][h] - 1e-3 or energy_after > b["capacity_kwh"] + 1e-3:
            raise RuntimeError(f"Battery bound violation at hour {h}")

        lhs = p["grid_kwh"] + p["solar_used_kwh"]
        if p["battery_action"] == "discharge":
            lhs += p["battery_kwh"]
        rhs = demand
        if p["battery_action"] == "charge":
            rhs += p["battery_kwh"]

        if abs(lhs - rhs) > 0.01:
            raise RuntimeError(f"Energy balance violation at hour {h}")

        cap = params["grid_cap"][h]
        if cap is not None and p["grid_kwh"] > cap + 0.01:
            raise RuntimeError(f"Grid cap violation at hour {h}")

        energy_before = energy_after

    if abs(energy_before - b["initial_energy_kwh"]) > 0.01:
        raise RuntimeError("End-of-day battery neutrality violation")

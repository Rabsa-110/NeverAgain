# NeverAgain — GridWise LLM + Optimizer

This version completes the missing **LLM interpretation**, **deterministic guardrails**, and **24-hour MILP optimizer** while preserving the FastAPI service shape.

## Architecture

`POST /optimize-energy`
→ LLM interprets `operator_notes`
→ deterministic guardrails validate the structured directives
→ directive effects are converted into optimizer constraints
→ MILP optimizer minimizes grid electricity cost
→ deterministic replay validates the final 24-hour plan
→ exact challenge response is returned.

The challenge requires the LLM to be part of the operator-note interpretation path, and the final schedule must obey the extracted directives and GridWise energy rules.

## Environment

Copy `.env.example` to `.env` and set:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` (default: `gpt-5.6-luna`)
- `LLM_TIMEOUT_SECONDS`
- `OPTIMIZER_TIME_LIMIT`

Do not commit `.env`.

## Local run

```bash
python -m venv venv
# Windows:
venv\\Scripts\\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Health:

```bash
curl http://127.0.0.1:8000/health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## API request

The canonical request contains:

- `scenario_id`
- `operator_notes` (1–3 notes)
- `hours` (exactly 24 entries)
- `battery`

Example:

```json
{
  "scenario_id": "GRID-101",
  "operator_notes": [
    "Solar output will drop to about 20% from 1 PM to 3 PM.",
    "Do not charge the battery between 2 PM and 4 PM.",
    "The cafeteria menu changes tomorrow."
  ],
  "hours": [
    {"hour": 0, "demand_kwh": 180, "solar_kwh": 0, "tariff_bdt_per_kwh": 7}
  ],
  "battery": {
    "capacity_kwh": 500,
    "initial_energy_kwh": 200,
    "minimum_energy_kwh": 50,
    "max_charge_kwh_per_hour": 100,
    "max_discharge_kwh_per_hour": 100
  }
}
```

The `hours` array must contain all 24 hours in the real request.

## Optimizer

The optimizer uses `scipy.optimize.milp`.

It models:

- grid import
- solar usage
- battery charge
- battery discharge
- charge/discharge binary states
- battery capacity and reserve
- charge/discharge hourly limits
- end-of-day battery neutrality
- solar availability
- no-charge/no-discharge windows
- maximum-grid windows
- solar reduction
- minimum battery reserve

The objective is:

`sum(grid_kwh[h] * tariff_bdt_per_kwh[h])`

The returned plan is independently replayed before the API response is accepted.

## LLM

The LLM is used only for semantic interpretation of operator notes. Its output is forced into a JSON schema and then checked again by deterministic guardrails.

Supported directives:

- `solar_reduction`
- `minimum_battery_reserve`
- `no_charge_window`
- `no_discharge_window`
- `max_grid_window`
- `no_op`

Hard-coded phrase matching is not used as the primary interpreter.

## Tests

```bash
pytest -q
```

## Docker

```bash
docker build -t gridwise-api .
docker run --rm -p 8000:8000 --env-file .env gridwise-api
```

## Security

Never commit API keys or `.env`. The API intentionally returns a generic 500 message instead of provider errors or stack traces.

import json
import os
from typing import Any

import httpx


SUPPORTED = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "directives": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "note_index": {"type": "integer"},
                    "applies": {"type": "boolean"},
                    "directive_type": {
                        "type": "string",
                        "enum": sorted(SUPPORTED),
                    },
                    "structured_adjustment": {
                        "anyOf": [
                            {"type": "null"},
                            {
                                "type": "object",
                                "additionalProperties": True
                            },
                        ]
                    },
                    "explanation": {"type": "string"},
                },
                "required": [
                    "note_index",
                    "applies",
                    "directive_type",
                    "structured_adjustment",
                    "explanation",
                ],
            },
        }
    },
    "required": ["directives"],
}


SYSTEM_PROMPT = """You are the GridWise operator-note interpreter.

Interpret ONLY the supplied operator_notes for the supplied 24-hour energy scenario.
Return exactly one directive object for every note, in note_index order.

Supported directives:
1. solar_reduction -> {"hours":[...],"factor":number}
2. minimum_battery_reserve -> {"hours":[...],"minimum_energy_kwh":number}
3. no_charge_window -> {"hours":[...]}
4. no_discharge_window -> {"hours":[...]}
5. max_grid_window -> {"hours":[...],"max_grid_kwh":number}
6. no_op -> null

Rules:
- A note is no_op if it does not change the current energy schedule.
- Never invent a directive type.
- Never alter demand, tariff, battery parameters, or unrelated scenario data.
- Time windows are whole-hour, start inclusive and end exclusive.
- Convert 1 PM to 3 PM into [13,14].
- For an 80% solar reduction, factor is 0.2 because factor is the usable fraction remaining.
- Hours must be unique integers 0..23 in ascending order.
- Every non-no_op directive has applies=true.
- no_op has applies=false and structured_adjustment=null.
- Numeric values must come from the note, not guesses.
"""


def _fallback_noop(notes):
    # Used only when no LLM credentials are configured. This is deliberately
    # conservative; production/judging should configure the LLM.
    return [
        {
            "note_index": i,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": "LLM provider is not configured; note was not interpreted.",
        }
        for i in range(len(notes))
    ]


def interpret_notes(scenario: dict) -> list[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        if os.getenv("ALLOW_LLM_FALLBACK", "false").lower() == "true":
            return _fallback_noop(scenario["operator_notes"])
        raise RuntimeError("OPENAI_API_KEY is not configured")

    model = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))

    compact = {
        "operator_notes": scenario["operator_notes"],
        "hours": [
            {
                "hour": h["hour"],
                "demand_kwh": h["demand_kwh"],
                "solar_kwh": h["solar_kwh"],
                "tariff_bdt_per_kwh": h["tariff_bdt_per_kwh"],
            }
            for h in scenario["hours"]
        ],
        "battery": scenario["battery"],
    }

    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(compact, separators=(",", ":")),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "gridwise_directives",
                "strict": True,
                "schema": SCHEMA,
            }
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            "https://api.openai.com/v1/responses",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    # Responses API returns generated text in output items.
    text = data.get("output_text")
    if not text:
        parts = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    parts.append(content.get("text", ""))
        text = "".join(parts)

    if not text:
        raise RuntimeError("LLM returned no structured output")

    parsed = json.loads(text)
    return parsed["directives"]

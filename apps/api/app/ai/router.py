"""Intent router: deterministic keyword matching, not an LLM call. This is what lets the
AI analyst stay usable even on the Mock provider (routing never depends on the model)."""

import re

_ROUTES = [
    ("anomaly_analyst", re.compile(r"anomal|unusual|spike|abnormal|odd", re.IGNORECASE)),
    ("forecast_analyst", re.compile(r"forecast|predict|tomorrow|next (week|day|month)|expect.*future", re.IGNORECASE)),
    ("waste_analyst", re.compile(r"waste|savings opportunit|after.?hours|avoidable", re.IGNORECASE)),
    ("optimization_analyst", re.compile(r"optimi[sz]|scenario|what.?if|setpoint|simulat", re.IGNORECASE)),
    ("carbon_analyst", re.compile(r"carbon|emission|co2|co₂|sustainab", re.IGNORECASE)),
    ("executive_narrator", re.compile(r"summary|overview|executive|brief me|status report", re.IGNORECASE)),
]


def route_question(question: str) -> str:
    for agent_name, pattern in _ROUTES:
        if pattern.search(question or ""):
            return agent_name
    return "energy_analyst"

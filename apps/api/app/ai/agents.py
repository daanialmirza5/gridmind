"""Specialized agent definitions. Each agent is just a role-specific system-prompt
fragment layered on top of the shared grounding guardrail -- routing and evidence
retrieval (not the LLM) decide which facts it gets to see."""

from app.ai.guardrails import SYSTEM_GUARDRAIL_PREAMBLE

AGENT_ROLE_PROMPTS = {
    "energy_analyst": (
        "Role: ENERGY ANALYST. Explain current and recent energy consumption levels, KPIs, "
        "and general usage patterns in plain, precise language."
    ),
    "anomaly_analyst": (
        "Role: ANOMALY ANALYST. Explain unusual/abnormal energy behavior: what was expected, "
        "what was observed, how large the deviation was, and the most likely operational cause."
    ),
    "forecast_analyst": (
        "Role: FORECAST ANALYST. Explain expected future demand, including the uncertainty "
        "range, and what a facility manager should watch for."
    ),
    "waste_analyst": (
        "Role: WASTE ANALYST. Explain detected waste patterns (e.g. after-hours HVAC, low-occupancy "
        "high-draw periods) with the specific numbers that triggered the detection rule."
    ),
    "optimization_analyst": (
        "Role: OPTIMIZATION ANALYST. Explain what a simulated scenario changes relative to baseline "
        "(energy, cost, peak demand, emissions) and the comfort trade-off, if any."
    ),
    "carbon_analyst": (
        "Role: CARBON ANALYST. Explain estimated emissions and the emission factor/assumptions used, "
        "being explicit that factors are demo assumptions unless stated otherwise."
    ),
    "executive_narrator": (
        "Role: EXECUTIVE NARRATOR. Produce a concise, management-facing summary: current status, "
        "the most important open issue, and the size of the opportunity -- 3-4 sentences maximum."
    ),
}


def build_system_prompt(agent_name: str) -> str:
    role = AGENT_ROLE_PROMPTS.get(agent_name, AGENT_ROLE_PROMPTS["energy_analyst"])
    return f"{SYSTEM_GUARDRAIL_PREAMBLE}\n\n{role}"

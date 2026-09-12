"""Multi-provider LLM abstraction. The app must work with zero API keys configured
(AI_PROVIDER=mock), so MockProvider is a first-class citizen, not a stub."""

import json
from abc import ABC, abstractmethod

from app.core.config import get_settings

settings = get_settings()


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Returns raw text response (expected to be a JSON object per the agent's schema)."""


class MockProvider(AIProvider):
    """Deterministic, template-based provider used when no API key is configured.
    It still goes through the exact same evidence-grounding pipeline as a real LLM --
    it just renders the evidence into prose with string templates instead of calling out
    to a model. This keeps GridMind fully demoable offline."""

    name = "mock"

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        try:
            payload = json.loads(user_prompt.split("EVIDENCE_JSON:", 1)[1].split("END_EVIDENCE_JSON", 1)[0])
        except Exception:
            payload = {}
        return json.dumps(_mock_answer(payload))


def _mock_answer(evidence: dict) -> dict:
    kind = evidence.get("kind", "general")
    if kind == "anomaly" and evidence.get("anomalies"):
        top = evidence["anomalies"][0]
        answer = (
            f"The largest flagged anomaly is on meter {top['meter_id']} at {top['timestamp']}, where "
            f"consumption reached {top['actual_kwh']} kWh against an expected {top['expected_kwh']} kWh "
            f"({top['deviation_pct']}% deviation, severity {top['severity']}). Probable cause: {top['probable_cause']}."
        )
        confidence = "HIGH" if top["severity"] in ("HIGH", "CRITICAL") else "MEDIUM"
    elif kind == "waste" and evidence.get("waste_events"):
        top = evidence["waste_events"][0]
        answer = (
            f"The top waste pattern is '{top['rule']}' on meter {top['meter_id']}, estimated at "
            f"{top['estimated_waste_kwh']} kWh (~{top['estimated_cost']} cost) between {top['window_start']} "
            f"and {top['window_end']}."
        )
        confidence = "MEDIUM"
    elif kind == "forecast" and evidence.get("forecast_points"):
        p = evidence["forecast_points"][0]
        answer = (
            f"The forecast for {p['timestamp']} expects {p['expected_kwh']} kWh "
            f"(range {p['lower_kwh']}-{p['upper_kwh']} kWh)."
        )
        confidence = "MEDIUM"
    elif kind == "optimization" and evidence.get("scenario"):
        s = evidence["scenario"]
        answer = (
            f"This scenario changes energy by {s.get('energy_change_pct')}%, cost by {s.get('cost_change_pct')}%, "
            f"peak demand by {s.get('peak_change_pct')}%, and emissions by {s.get('emissions_change_pct')}%, "
            f"with a comfort impact rated {s.get('comfort_impact')}."
        )
        confidence = "MEDIUM"
    elif kind == "carbon" and evidence.get("emissions"):
        e = evidence["emissions"]
        answer = (
            f"Estimated emissions over the selected period are {e.get('total_kg_co2e')} kg CO2e, using a "
            f"{e.get('factor_used')} kgCO2e/kWh factor ({e.get('factor_source')}, {e.get('factor_region')})."
        )
        confidence = "MEDIUM"
    elif kind == "energy" and evidence.get("kpi"):
        kpi = evidence["kpi"]
        answer = (
            f"As of {kpi.get('as_of')}, today's consumption is {kpi.get('today_energy_kwh')} kWh and this "
            f"month's total is {kpi.get('month_energy_kwh')} kWh. Current demand is {kpi.get('current_demand_kw')} kW "
            f"against a trailing 30-day peak of {kpi.get('peak_demand_kw')} kW."
        )
        confidence = "MEDIUM"
    elif kind == "executive_summary":
        kpi = evidence.get("kpi", {})
        answer = (
            f"Today's consumption is {kpi.get('today_energy_kwh')} kWh with current demand at "
            f"{kpi.get('current_demand_kw')} kW. There are {evidence.get('open_anomalies', 0)} open anomalies and "
            f"{evidence.get('open_recommendations', 0)} pending recommendations representing an estimated "
            f"{evidence.get('total_potential_savings_cost', 0)} in potential savings."
        )
        confidence = "MEDIUM"
    else:
        answer = "No structured evidence was available to answer this question for the selected scope."
        confidence = "LOW"

    return {
        "answer": answer,
        "confidence": confidence,
        "limitations": (
            "This is a synthetic demonstration dataset. The Mock AI provider renders this answer directly "
            "from structured evidence using templates (no live LLM call was made)."
        ),
    }


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self):
        import anthropic

        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.messages.create(
            model="claude-sonnet-5",
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self):
        import openai

        self._client = openai.OpenAI(api_key=settings.openai_api_key)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=800,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content or ""


class GoogleProvider(AIProvider):
    name = "google"

    def __init__(self):
        import google.generativeai as genai

        genai.configure(api_key=settings.google_api_key)
        self._model = genai.GenerativeModel("gemini-1.5-flash", system_instruction=None)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        response = self._model.generate_content(f"{system_prompt}\n\n{user_prompt}")
        return response.text or ""


def get_provider(name: str | None = None) -> AIProvider:
    provider_name = (name or settings.ai_provider or "mock").lower()
    try:
        if provider_name == "anthropic" and settings.anthropic_api_key:
            return AnthropicProvider()
        if provider_name == "openai" and settings.openai_api_key:
            return OpenAIProvider()
        if provider_name == "google" and settings.google_api_key:
            return GoogleProvider()
    except Exception:
        pass
    return MockProvider()

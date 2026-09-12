"""End-to-end AI analyst flow:

User Question -> Intent Router -> Evidence Gatherer (deterministic engines) ->
Evidence Package -> LLM (or Mock) -> Grounded Explanation -> persisted AIInsight

The LLM never sees raw ledger rows or is trusted as a source of truth -- it only narrates
the evidence package it is handed. See app/ai/guardrails.py for the injection defenses.
"""

import json
import uuid

from sqlalchemy.orm import Session

from app.ai.agents import build_system_prompt
from app.ai.evidence import EVIDENCE_GATHERERS
from app.ai.guardrails import build_user_prompt, flag_suspicious_input, parse_provider_response
from app.ai.providers import get_provider
from app.ai.router import route_question
from app.domain.intelligence import AIInsight


def answer_question(db: Session, question: str, building_id: str, created_by: str = "") -> AIInsight:
    agent_name = route_question(question)
    gatherer = EVIDENCE_GATHERERS[agent_name]
    evidence = gatherer(db, building_id)

    suspicious = flag_suspicious_input(question)
    system_prompt = build_system_prompt(agent_name)
    user_prompt = build_user_prompt(question, evidence)

    provider = get_provider()
    raw = provider.complete(system_prompt, user_prompt)
    parsed = parse_provider_response(raw)

    if suspicious:
        parsed["limitations"] = (
            (parsed.get("limitations") or "")
            + " Note: the question contained phrasing that resembles an instruction-override "
            "attempt; it was treated as plain text data and had no effect on system behavior."
        ).strip()

    insight = AIInsight(
        id=f"AI-{uuid.uuid4().hex[:10]}",
        agent=agent_name,
        question=question,
        answer=parsed["answer"],
        confidence=parsed["confidence"],
        limitations=parsed.get("limitations", ""),
        evidence_json=json.dumps(evidence, default=str),
        provider=provider.name,
        created_by=created_by,
    )
    db.add(insight)
    db.commit()
    return insight

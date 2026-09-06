"""Local-agent responder for a technician context challenge.

On a pending CONTEXT_CHALLENGE the agent reads the held decision's request and
factors and returns a **1-2 sentence** justification — the same
stream-of-thought style the agent already produces — which the pipeline records
as Record 2 (CONTEXT_RESPONSE) and the console renders as the "Agent
clarification" blurb.

The blurb is a *claim*, not a re-decision: it explains, it does not authorize,
and it never changes the HOLD. Two guardrails keep it honest:

* ``safe_blurb`` rejects leaked private reasoning (``<think>`` / scratchpad /
  system-prompt echoes), mirroring the console's ``safeExplanation``.
* ``respond`` always has a **deterministic fallback** derived from the decision,
  so a missing or misbehaving language model never blocks or fabricates context.

The returned dict mirrors ``alice.agent_response.response`` so the runtime feed
can project it onto the dashboard with no UI change.
"""

from __future__ import annotations

import re


MAX_SENTENCES = 2
MAX_BLURB_CHARS = 600
_MAX_EVIDENCE = 8

# Mirrors apps/desktop/src/lib/llm.ts safeExplanation: no chain-of-thought.
_UNSAFE = re.compile(r"</?think|chain.of.thought|scratchpad|system prompt", re.IGNORECASE)
_SENTENCE = re.compile(r"[^.!?]+[.!?]+|[^.!?]+$")


class UnsafeBlurb(ValueError):
    """The language model leaked private reasoning; the claim is refused."""


def safe_blurb(text: str) -> str:
    """Return a bounded claim or raise; never a chain-of-thought or scratchpad."""
    if not isinstance(text, str):
        raise UnsafeBlurb("blurb must be text")
    if _UNSAFE.search(text):
        raise UnsafeBlurb("private reasoning content was rejected")
    limited = limit_sentences(text)
    if not limited:
        raise UnsafeBlurb("blurb was empty after bounding")
    return limited


def limit_sentences(text: str, *, sentences: int = MAX_SENTENCES,
                    max_chars: int = MAX_BLURB_CHARS) -> str:
    """Collapse whitespace and keep at most the first ``sentences`` sentences."""
    parts = [match.group().strip() for match in _SENTENCE.finditer((text or "").strip())]
    parts = [part for part in parts if part]
    kept = " ".join(parts[:sentences]).strip()
    kept = re.sub(r"\s+", " ", kept)
    if len(kept) > max_chars:
        kept = kept[:max_chars].rstrip()
    return kept


def _text(value, default):
    return value if isinstance(value, str) and value.strip() else default


def _read_decision(decision: dict) -> dict:
    request = decision.get("request", {}) if isinstance(decision, dict) else {}
    anomaly = decision.get("anomaly", {}) if isinstance(decision, dict) else {}
    evidence = decision.get("evidence", {}) if isinstance(decision, dict) else {}
    factors = [
        _text(factor.get("label"), "")
        for factor in anomaly.get("factors", [])
        if isinstance(factor, dict) and _text(factor.get("label"), "")
    ]
    references = [
        item["evidence_id"]
        for item in evidence.get("items", [])
        if isinstance(item, dict) and isinstance(item.get("evidence_id"), str)
    ][:_MAX_EVIDENCE]
    return {
        "action": _text(request.get("action"), "the requested action"),
        "target": _text(request.get("target"), "the protected target"),
        "mission": _text(request.get("mission_id"), "the assigned mission"),
        "factors": factors,
        "references": references,
    }


def fallback_justification(decision: dict) -> str:
    """A deterministic 1-2 sentence justification derived from the decision."""
    facts = _read_decision(decision)
    first = f"{facts['action']} on {facts['target']} is required to complete {facts['mission']}."
    if facts["factors"]:
        second = f"The elevated signal on {facts['factors'][0].lower()} reflects that scope, not a new intent."
        return limit_sentences(f"{first} {second}")
    return limit_sentences(first)


def _expected_effect(decision: dict) -> str:
    facts = _read_decision(decision)
    return f"Completes {facts['mission']} within the requested scope; no wider access is claimed."


def _alternatives(decision: dict) -> list:
    facts = _read_decision(decision)
    if facts["factors"]:
        return [f"Hold {facts['action']} for technician review before proceeding."]
    return ["Escalate to technician review before proceeding."]


def respond(decision: dict, generate=None) -> dict:
    """Produce the agent's context response for a held decision.

    ``generate`` is an optional ``callable(prompt) -> str`` (e.g. an Ollama
    completion). Only the justification sentence(s) may come from it, and only
    after passing ``safe_blurb`` and the 1-2 sentence bound; the expected effect,
    evidence references and alternatives stay deterministic and grounded in the
    decision. Any failure falls back to :func:`fallback_justification`, so a
    response is always well-formed, bounded, and free of chain-of-thought.
    """
    justification = fallback_justification(decision)
    if generate is not None:
        facts = _read_decision(decision)
        prompt = (
            "In 1-2 sentences, justify why "
            f"{facts['action']} on {facts['target']} is required for {facts['mission']}. "
            "State the claim only. Do not reveal your reasoning steps."
        )
        try:
            justification = safe_blurb(generate(prompt))
        except Exception:  # noqa: BLE001 - unsafe or failed generation falls back deterministically
            justification = fallback_justification(decision)
    facts = _read_decision(decision)
    return {
        "mission_justification": justification,
        "expected_effect": _expected_effect(decision),
        "evidence_references": facts["references"],
        "alternatives_considered": _alternatives(decision),
    }

"""Tests for the local-agent context-challenge responder.

The blurb must be a bounded 1-2 sentence claim, free of chain-of-thought, with a
deterministic fallback that never depends on a language model. See
docs/plans/2026-09-06-request-more-context-pipeline.md.
"""

import pytest

from agent.challenge_responder import (MAX_SENTENCES, UnsafeBlurb, fallback_justification,
                                       limit_sentences, respond, safe_blurb)


DECISION = {
    "request": {"action": "isolate_host", "target": "workstation-12", "mission_id": "MISSION-291",
                "agent_id": "diagnostic-agent-04"},
    "anomaly": {"factors": [{"label": "Outbound connection burst"}, {"label": "New process tree"}]},
    "evidence": {"items": [{"evidence_id": "PROC-8821"}, {"evidence_id": "EDR-9921"}]},
}


def _sentence_count(text):
    return len([part for part in __import__("re").findall(r"[^.!?]+[.!?]+|[^.!?]+$", text) if part.strip()])


def test_fallback_is_at_most_two_sentences_and_grounded():
    blurb = fallback_justification(DECISION)
    assert _sentence_count(blurb) <= MAX_SENTENCES
    assert "isolate_host" in blurb and "workstation-12" in blurb and "MISSION-291" in blurb


def test_fallback_handles_a_sparse_decision():
    blurb = fallback_justification({})
    assert _sentence_count(blurb) <= MAX_SENTENCES
    assert blurb  # never empty, even with no request or factors


def test_limit_sentences_trims_to_two():
    assert limit_sentences("One. Two. Three. Four.") == "One. Two."
    assert _sentence_count(limit_sentences("A. B. C.")) <= MAX_SENTENCES


def test_safe_blurb_rejects_chain_of_thought():
    with pytest.raises(UnsafeBlurb):
        safe_blurb("<think>secret plan</think> Do the thing.")
    with pytest.raises(UnsafeBlurb):
        safe_blurb("scratchpad: step 1 ... Justify the action.")


def test_respond_uses_a_safe_model_blurb_when_available():
    model = lambda prompt: "Isolating the host stops the confirmed exfiltration. It stays within scope."
    result = respond(DECISION, generate=model)
    assert result["mission_justification"].startswith("Isolating the host stops")
    assert _sentence_count(result["mission_justification"]) <= MAX_SENTENCES


def test_respond_bounds_an_overlong_model_blurb_to_two_sentences():
    model = lambda prompt: "One. Two. Three. Four. Five."
    result = respond(DECISION, generate=model)
    assert _sentence_count(result["mission_justification"]) <= MAX_SENTENCES


def test_respond_falls_back_when_the_model_leaks_reasoning():
    model = lambda prompt: "<think>chain of thought</think> anything"
    result = respond(DECISION, generate=model)
    assert result["mission_justification"] == fallback_justification(DECISION)


def test_respond_falls_back_when_the_model_raises():
    def broken(prompt):
        raise RuntimeError("ollama offline")

    result = respond(DECISION, generate=broken)
    assert result["mission_justification"] == fallback_justification(DECISION)


def test_respond_mirrors_the_agent_response_shape():
    result = respond(DECISION)
    assert set(result) == {"mission_justification", "expected_effect",
                           "evidence_references", "alternatives_considered"}
    assert result["evidence_references"] == ["PROC-8821", "EDR-9921"]
    assert result["alternatives_considered"]  # non-empty grounded alternative

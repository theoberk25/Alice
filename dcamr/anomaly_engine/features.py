"""Fixed-size, deterministic cyber features from trusted local input snapshots."""

import json

from .baseline import OperationalBaseline
from .feature_types import (
    FEATURE_NAMES, FEATURE_SCHEMA_VERSION, Factor, FeatureBatch, FeatureError, FeatureSource,
)
from .feature_validation import (
    MAX_FEATURE_INPUT_BYTES, MAX_REQUEST_BYTES, normalize_host, parse_bound_json,
)
from .sequence import extract_history


def build_features(data: bytes, baseline: OperationalBaseline, *, expected_sha256: str) -> FeatureBatch:
    """Build model inputs only; no model loading, score, policy or state mutation.

    The caller captures these bytes/digest after authenticating the subject and
    freezing its trusted history. Identity fields inside ordinary JSON do not
    authenticate themselves. A signature-verified baseline must be loaded first.
    """
    bundle, digest = parse_bound_json(
        data, expected_sha256=expected_sha256, schema_name="anomaly_feature_input.json",
        max_bytes=MAX_FEATURE_INPUT_BYTES,
    )
    request, snapshot = bundle["request"], bundle["snapshot"]
    if len(json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) > MAX_REQUEST_BYTES:
        raise FeatureError("INPUT_LIMIT_EXCEEDED", "request", status="INVALID_INPUT")
    subject = snapshot["subject"]
    if (subject["agent_id"], subject["mission_id"]) != (request["agent_id"], request["mission_id"]):
        raise FeatureError("INPUT_UNSUPPORTED", "snapshot.subject.binding", status="INVALID_INPUT")
    action = baseline.action_catalog.get(request["action"])
    if action is None:
        raise FeatureError("INPUT_UNSUPPORTED", "request.action")
    parameters = request["parameters"]
    required = {"destination", "port", "protocol"} if action["destination_required"] else set()
    if set(parameters) != required:
        raise FeatureError("INPUT_UNSUPPORTED", "request.parameters", status="INVALID_INPUT")
    profile_id, profile_source, agent_known = baseline.select_profile(subject)
    profile = baseline.profiles[profile_id]
    history = extract_history(request, snapshot, profile=profile, catalog=baseline.action_catalog)
    target = baseline.targets.get(request["target"])
    target_known = target is not None
    profile_target_seen = request["target"] in profile["targets"]
    action_count = profile["action_counts"][request["action"]]
    action_seen = action_count > 0
    frequency = action_count / sum(profile["action_counts"].values())
    destination_applicable = action["destination_required"]
    destination_seen = False
    if destination_applicable:
        host = normalize_host(parameters["destination"], "request.parameters.destination")
        relationship = (host, parameters["port"], parameters["protocol"])
        destination_seen = target is not None and any(
            relationship == (d["host"], d["port"], d["protocol"])
            for d in target["destinations"]
        )
    has_previous = history.previous_action is not None
    values = tuple(map(float, (
        agent_known, action_seen, target_known, profile_target_seen,
        destination_applicable, destination_seen, frequency, history.request_count,
        history.executed_state_changes, has_previous, history.transition_probability,
    )))
    base_ref = f"OPS_BASELINE:{baseline.identity.sha256}"
    profile_ref = f"{base_ref}#/profiles/{profile_id}"
    observation_ref = f"FEATURE_INPUT:{digest}"
    agent_ref = f"{base_ref}#/agents"
    target_ref = f"{base_ref}#/targets"
    destination_ref = target_ref  # Full table proves absence when the target itself is unseen.
    action_ref = f"{profile_ref}/action_counts"
    sequence_ref = f"{profile_ref}/transitions"
    request_ref = f"{observation_ref}#/request"
    history_ref = f"{observation_ref}#/snapshot/history"
    factors = [
        _boolean_factor("agent_known", agent_known, agent_ref, f"{request_ref}/agent_id"),
        _boolean_factor("action_seen_for_profile", action_seen, action_ref, f"{request_ref}/action"),
        _boolean_factor("target_known", target_known, target_ref, f"{request_ref}/target"),
        _boolean_factor("profile_target_seen", profile_target_seen, f"{profile_ref}/targets", f"{request_ref}/target"),
    ]
    flags = set()
    for observed, flag in ((agent_known, "AGENT_UNSEEN"), (action_seen, "ACTION_UNSEEN"),
                           (target_known, "TARGET_UNSEEN"), (profile_target_seen, "PROFILE_TARGET_UNSEEN")):
        if not observed:
            flags.add(flag)
    if destination_applicable:
        factors.append(_boolean_factor("destination_seen", destination_seen, destination_ref,
                                       f"{request_ref}/parameters"))
        if not destination_seen:
            flags.add("DESTINATION_UNSEEN")
    else:
        factors.append(Factor("destination_seen", "NOT_APPLICABLE", None, None,
                              "boolean", None, f"{request_ref}/action"))
    if has_previous:
        seen_transition = history.transition_probability > 0
        factors.append(_boolean_factor("sequence_transition_seen", seen_transition,
                                       sequence_ref, f"{history_ref}/proposals"))
        if not seen_transition:
            flags.add("SEQUENCE_UNUSUAL")
    else:
        factors.append(Factor("sequence_transition_seen", "NOT_APPLICABLE", None, None,
                              "boolean", None, f"{history_ref}/proposals"))
    # These refer to the *feature input* bytes, not unresolved original request
    # paths or arbitrary agent-provided locations. No provenance is dereferenced.
    provenance = (
        (agent_ref, f"{request_ref}/agent_id"),
        (action_ref, f"{request_ref}/action"),
        (target_ref, f"{request_ref}/target"),
        (f"{profile_ref}/targets", f"{request_ref}/target"),
        (f"{base_ref}#/action_catalog", f"{request_ref}/action"),
        (destination_ref if destination_applicable else None, f"{request_ref}/parameters"),
        (action_ref, f"{request_ref}/action"),
        (None, f"{history_ref}/proposals"),
        (f"{base_ref}#/action_catalog", f"{history_ref}/executions"),
        (None, f"{history_ref}/proposals"),
        (sequence_ref if has_previous else None, f"{history_ref}/proposals"),
    )
    return FeatureBatch(
        FEATURE_SCHEMA_VERSION, digest, baseline.identity,
        request["request_id"], request["request_sha256"], snapshot["id"], snapshot["sha256"],
        snapshot["context_attempt"], profile_id, profile_source, FEATURE_NAMES, values,
        tuple(FeatureSource(name, *refs) for name, refs in zip(FEATURE_NAMES, provenance)),
        tuple(sorted(factors, key=lambda factor: factor.id)), tuple(sorted(flags)),
    )


def _boolean_factor(name: str, observed: bool, baseline_ref: str, observation_ref: str) -> Factor:
    return Factor(name, "EXPECTED" if observed else "UNUSUAL", bool(observed), True,
                  "boolean", baseline_ref, observation_ref)

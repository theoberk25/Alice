"""Pure bounded history calculations over an immutable trusted snapshot."""

from dataclasses import dataclass
from datetime import timedelta

from .feature_types import FeatureError
from .feature_validation import timestamp


WINDOW_SECONDS = 300
MAX_HISTORY_EVENTS = 1024
MAX_SESSIONS = 32


@dataclass(frozen=True, slots=True)
class HistoryFeatures:
    request_count: int
    executed_state_changes: int
    previous_action: str | None
    previous_request_id: str | None
    transition_probability: float


def extract_history(request: dict, snapshot: dict, *, profile, catalog) -> HistoryFeatures:
    """Use [snapshot_time - 300 seconds, snapshot_time), independent event clocks.

    Entries at or beyond snapshot time are invalid snapshots, not silent zeros.
    Exact duplicate deliveries count once; conflicting IDs/order fail closed.
    """
    end = timestamp(snapshot["observed_at"], "snapshot.observed_at")
    try:
        start = end - timedelta(seconds=WINDOW_SECONDS)
    except OverflowError:
        raise FeatureError("INPUT_UNSUPPORTED", "snapshot.observed_at", status="INVALID_INPUT") from None
    history = snapshot["history"]
    if history["complete_since"] is None:
        raise FeatureError("HISTORY_INCOMPLETE", "snapshot.history.complete_since")
    complete_since = timestamp(history["complete_since"], "snapshot.history.complete_since")
    if complete_since > start:
        raise FeatureError("HISTORY_INCOMPLETE", "snapshot.history.complete_since")
    if history["incomplete_until"] is not None:
        horizon = timestamp(history["incomplete_until"], "snapshot.history.incomplete_until")
        if end <= horizon:
            raise FeatureError("HISTORY_INCOMPLETE", "snapshot.history.incomplete_until")

    proposals = _deduplicate(history["proposals"], "request_id", "admitted_at", end)
    executions = _deduplicate(history["executions"], "execution_id", "executed_at", end)
    if len(proposals) > MAX_HISTORY_EVENTS or len(executions) > MAX_HISTORY_EVENTS:
        raise FeatureError("HISTORY_CAPACITY_EXCEEDED", "snapshot.history")
    # Reject cross-stream disagreements and multiple 'confirmed once' executions.
    action_bindings = {}
    executed_requests = set()
    sessions = set()
    for event in (*proposals.values(), *executions.values()):
        sessions.add((event["agent_id"], event["mission_id"]))
        key = event["request_id"]
        binding = tuple(event[k] for k in ("request_sha256", "agent_id", "mission_id", "action", "target"))
        if key in action_bindings and action_bindings[key] != binding:
            raise FeatureError("INPUT_UNSUPPORTED", "snapshot.history.request_binding", status="INVALID_INPUT")
        action_bindings[key] = binding
    if len(sessions | {(request["agent_id"], request["mission_id"])}) > MAX_SESSIONS:
        raise FeatureError("HISTORY_CAPACITY_EXCEEDED", "snapshot.history.sessions")
    current_binding = tuple(request[k] for k in ("request_sha256", "agent_id", "mission_id", "action", "target"))
    if request["request_id"] in action_bindings and action_bindings[request["request_id"]] != current_binding:
        raise FeatureError("INPUT_UNSUPPORTED", "snapshot.history.current_request", status="INVALID_INPUT")

    scoped = []
    ordinals = set()
    for event in proposals.values():
        # Ordinals are authoritative per agent/mission session, not lexical IDs.
        order_key = (event["agent_id"], event["mission_id"], event["ordinal"])
        if order_key in ordinals:
            raise FeatureError("INPUT_UNSUPPORTED", "snapshot.history.ordinal", status="INVALID_INPUT")
        ordinals.add(order_key)
        if _same_session(event, request) and event["request_id"] != request["request_id"]:
            admitted = timestamp(event["admitted_at"], "snapshot.history.admitted_at")
            if start <= admitted < end:
                if event["action"] not in catalog:
                    raise FeatureError("INPUT_UNSUPPORTED", "snapshot.history.action")
                scoped.append((admitted, event["ordinal"], event))
    scoped.sort(key=lambda item: (item[0], item[1]))
    if any(a[1] >= b[1] for a, b in zip(scoped, scoped[1:])):
        raise FeatureError("INPUT_UNSUPPORTED", "snapshot.history.order", status="INVALID_INPUT")
    current_proposal = proposals.get(request["request_id"])
    if current_proposal is not None:
        admission = timestamp(current_proposal["admitted_at"], "snapshot.history.admitted_at")
        if any((at, ordinal) >= (admission, current_proposal["ordinal"])
               for at, ordinal, _ in scoped):
            # A context-only retry must preserve its original behavioral snapshot.
            # Moving it behind newer requests could turn an unusual transition
            # into a familiar one. The caller must restore the pinned snapshot.
            raise FeatureError("INPUT_UNSUPPORTED", "snapshot.history.after_current_request", status="INVALID_INPUT")
    changes = 0
    for event in executions.values():
        proposal = proposals.get(event["request_id"])
        if proposal is not None:
            if timestamp(event["executed_at"], "snapshot.history.executed_at") < timestamp(
                proposal["admitted_at"], "snapshot.history.admitted_at"
            ):
                raise FeatureError("INPUT_UNSUPPORTED", "snapshot.history.execution_before_admission", status="INVALID_INPUT")
        if event["request_id"] in executed_requests:
            raise FeatureError("INPUT_UNSUPPORTED", "snapshot.history.execution_duplicate", status="INVALID_INPUT")
        executed_requests.add(event["request_id"])
        if event["request_id"] == request["request_id"]:
            # Enforcement should return its idempotent recorded outcome instead.
            raise FeatureError("INPUT_UNSUPPORTED", "request.already_executed", status="INVALID_INPUT")
        if _same_session(event, request):
            executed_at = timestamp(event["executed_at"], "snapshot.history.executed_at")
            if start <= executed_at < end:
                action = catalog.get(event["action"])
                if action is None:
                    raise FeatureError("INPUT_UNSUPPORTED", "snapshot.history.action")
                changes += int(action["state_changing"])
    if not scoped:
        return HistoryFeatures(0, changes, None, None, 0.0)
    previous = scoped[-1][2]
    row = profile["transitions"].get(previous["action"])
    if row is None or sum(row.values()) <= 0:
        raise FeatureError("REQUIRED_INPUT_MISSING", "baseline.profile.transitions")
    probability = row.get(request["action"], 0) / sum(row.values())
    return HistoryFeatures(len(scoped), changes, previous["action"], previous["request_id"], probability)


def _same_session(event: dict, request: dict) -> bool:
    return (event["agent_id"], event["mission_id"]) == (request["agent_id"], request["mission_id"])


def _deduplicate(events: list, key: str, time_key: str, end) -> dict:
    unique = {}
    for event in events:
        if timestamp(event[time_key], f"snapshot.history.{time_key}") >= end:
            raise FeatureError("INPUT_UNSUPPORTED", f"snapshot.history.{time_key}", status="INVALID_INPUT")
        identifier = event[key]
        if identifier in unique and unique[identifier] != event:
            raise FeatureError("INPUT_UNSUPPORTED", f"snapshot.history.{key}", status="INVALID_INPUT")
        unique[identifier] = event
    return unique

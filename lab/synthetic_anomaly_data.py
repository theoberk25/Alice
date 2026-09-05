"""Bounded synthetic cyber sessions for Mac-only candidate preparation.

Nothing here fits a model, contacts a device, or records real execution. The
baseline is the committed static fixture, not data learned from these sessions.
Initial actions follow its action counts; subsequent actions follow its Markov
transition rows, so the resulting mix need not match the initial frequencies.
Request/snapshot hashes use stable local lab JSON with the digest field omitted.
They establish reproducibility, not production canonicalization or authenticity.
"""

from collections import deque
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import random
from typing import Iterator

from dcamr.anomaly_engine.baseline import OperationalBaseline, load_baseline
from lab.anomaly_training import MAX_EXAMPLES, TrainingExample, json_bytes


BASELINE_PATH = Path(__file__).resolve().parents[1] / "tests/fixtures/features/baseline.json"
CHALLENGE_SCENARIOS = (
    "new_agent", "unseen_destination", "unseen_target", "unusual_sequence", "request_burst",
)
NORMAL_SCENARIO = "routine_operations"
MAX_NORMAL_SESSIONS = 2_000
MAX_REQUESTS_PER_SESSION = 64
MAX_CHALLENGE_SESSIONS = 200
WINDOW_SECONDS = 300
_KNOWN_AGENT = "diagnostic-agent-04"
_ANCHOR = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def _utc(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _weighted_action(rng: random.Random, counts) -> str:
    weights = sorted((action, count) for action, count in counts.items() if count > 0)
    total = sum(count for _, count in weights)
    if total <= 0:
        raise ValueError("synthetic generation requires a supported action distribution")
    choice = rng.randrange(total)
    for action, count in weights:
        if choice < count:
            return action
        choice -= count
    raise AssertionError("weighted action selection exhausted its support")


class _Session:
    """Small local event ledger; snapshots only expose prior in-window records."""

    def __init__(self, baseline: OperationalBaseline, *, seed: int, scenario: str,
                 index: int, slot: int, agent_id: str = _KNOWN_AGENT):
        self.baseline = baseline
        profile_id, _, _ = baseline.select_profile({
            "agent_id": agent_id, "role": "diagnostic", "mission_type": "network_investigation",
        })
        self.profile = baseline.profiles[profile_id]
        self.group_id = f"synthetic-{seed:08x}-{scenario}-{index:04d}"
        self.scenario = scenario
        self.agent_id = agent_id
        self.mission_id = f"mission-{self.group_id}"
        self.rng = random.Random(sha256(self.group_id.encode("ascii")).digest())
        self.now = _ANCHOR + timedelta(hours=slot * 2)
        # This synthetic mission has no events before its first request. The
        # ledger is initialized a full window earlier and remains complete.
        self.complete_since = self.now - timedelta(seconds=WINDOW_SECONDS)
        self.ordinal = 0
        self.previous_action = None
        self.proposals = []
        self.executions = []

    def next_normal_action(self) -> str:
        counts = (self.profile["action_counts"] if self.previous_action is None
                  else self.profile["transitions"][self.previous_action])
        return _weighted_action(self.rng, counts)

    def propose(self, action: str, *, emit: bool, label: str,
                target: str = "Web-01", destination: str | None = None,
                interval: tuple[int, int] = (30, 90)) -> TrainingExample | None:
        parameters = {}
        semantics = self.baseline.action_catalog[action]
        if semantics["destination_required"]:
            endpoint = self.rng.choice(self.baseline.targets["Web-01"]["destinations"])
            parameters = {"destination": destination or endpoint["host"],
                          "port": endpoint["port"], "protocol": endpoint["protocol"]}
        request = {
            "request_id": f"req-{self.group_id}-{self.ordinal:03d}",
            "agent_id": self.agent_id, "mission_id": self.mission_id,
            "action": action, "target": target, "parameters": parameters,
        }
        request["request_sha256"] = sha256(json_bytes(request)).hexdigest()
        start = self.now - timedelta(seconds=WINDOW_SECONDS)
        self.proposals = [(at, event) for at, event in self.proposals if start <= at < self.now]
        self.executions = [(at, event) for at, event in self.executions if start <= at < self.now]
        example = None
        if emit:
            snapshot = {
                "id": f"snapshot-{self.group_id}-{self.ordinal:03d}",
                "observed_at": _utc(self.now),
                "subject": {"agent_id": self.agent_id, "mission_id": self.mission_id,
                            "role": "diagnostic", "mission_type": "network_investigation"},
                "context_attempt": 0,
                "history": {"complete_since": _utc(self.complete_since),
                            "incomplete_until": None,
                            "proposals": [event for _, event in self.proposals],
                            "executions": [event for _, event in self.executions]},
            }
            snapshot["sha256"] = sha256(json_bytes(snapshot)).hexdigest()
            data = json_bytes({"schema_version": "1.0.0", "request": request, "snapshot": snapshot})
            example = TrainingExample(self.group_id, self.scenario, label, data, sha256(data).hexdigest(),
                                      baseline_sha256=self.baseline.identity.sha256)
        binding = {key: request[key] for key in (
            "request_id", "request_sha256", "agent_id", "mission_id", "action", "target",
        )}
        self.proposals.append((self.now, {
            **binding, "admitted_at": _utc(self.now), "ordinal": self.ordinal,
        }))
        # A local simulation may independently mark a state change as completed.
        # It never invokes an enforcement API or equates every proposal to an execution.
        if semantics["state_changing"] and self.rng.random() < 0.65:
            execution_time = self.now + timedelta(seconds=1)
            self.executions.append((execution_time, {
                **binding, "execution_id": f"exec-{request['request_id']}",
                "executed_at": _utc(execution_time),
            }))
        self.previous_action = action
        self.ordinal += 1
        self.now += timedelta(seconds=self.rng.randint(*interval))
        return example


def _normal_bridge(session: _Session, target_action: str) -> None:
    """Append a supported path so an endpoint challenge has otherwise normal context."""
    queue = deque([(session.previous_action, ())])
    visited = set()
    while queue:
        action, path = queue.popleft()
        if action == target_action:
            for step in path:
                session.propose(step, emit=False, label="CHALLENGE")
            return
        if action in visited:
            continue
        visited.add(action)
        for successor, count in sorted(session.profile["transitions"][action].items()):
            if count > 0 and successor not in visited:
                queue.append((successor, (*path, successor)))
    raise ValueError("fixture baseline has no normal path to the endpoint challenge")


def _challenge(session: _Session) -> TrainingExample:
    burst = session.scenario == "request_burst"
    for _ in range(40 if burst else 8):
        session.propose(session.next_normal_action(), emit=False, label="CHALLENGE",
                        interval=(2, 4) if burst else (30, 90))
    parameters = {}
    if session.scenario == "unseen_destination":
        _normal_bridge(session, "query_network")
        action = session.rng.choice(("allow_outbound", "modify_firewall"))
        parameters["destination"] = "203.0.113.42"
    elif session.scenario == "unusual_sequence":
        supported = session.profile["transitions"][session.previous_action]
        candidates = sorted(action for action in session.baseline.action_catalog
                            if supported.get(action, 0) == 0)
        if not candidates:
            raise ValueError("fixture baseline has no unseen action transition")
        action = session.rng.choice(candidates)
    elif session.scenario == "unseen_target":
        # Keep the final action diagnostic so this case isolates target novelty.
        counts = session.profile["transitions"][session.previous_action]
        action = _weighted_action(session.rng, {
            name: count for name, count in counts.items()
            if not session.baseline.action_catalog[name]["destination_required"]
        })
        parameters["target"] = "Synthetic-Unseen-01"
    else:
        action = session.next_normal_action()
    result = session.propose(action, emit=True, label="CHALLENGE", **parameters)
    assert result is not None
    return result


def generate_examples(*, baseline: OperationalBaseline | None = None,
                      seed: int = 1729, normal_sessions: int = 500,
                      requests_per_session: int = 12,
                      challenge_sessions_per_scenario: int = 20) -> Iterator[TrainingExample]:
    """Yield reproducible source inputs without building vectors or fitting a model.

    Every normal session yields all its requests under one group. Each independent
    challenge session yields only its final request, with its own simulated past.
    New-agent sessions use the same authenticated role/mission cohort as the fixture.
    Challenge labels describe constructed changes; they do not assert learned scores.
    A supplied frozen baseline is used throughout and its digest is bound to every
    example. Without one, the fixture is loaded exactly once for this iteration.
    Argument validation occurs on the first iteration, as with a normal generator.
    """
    limits = (("seed", seed, 0, 2**32 - 1),
              ("normal_sessions", normal_sessions, 1, MAX_NORMAL_SESSIONS),
              ("requests_per_session", requests_per_session, 1, MAX_REQUESTS_PER_SESSION),
              ("challenge_sessions_per_scenario", challenge_sessions_per_scenario, 0, MAX_CHALLENGE_SESSIONS))
    for name, value, minimum, maximum in limits:
        if type(value) is not int or not minimum <= value <= maximum:
            raise ValueError(f"{name} must be an integer in {minimum}..{maximum}")
    total = normal_sessions * requests_per_session + len(CHALLENGE_SCENARIOS) * challenge_sessions_per_scenario
    if total > MAX_EXAMPLES:
        raise ValueError(f"synthetic generation is limited to {MAX_EXAMPLES} examples")
    if baseline is None:
        data = BASELINE_PATH.read_bytes()
        baseline = load_baseline(data, expected_sha256=sha256(data).hexdigest())
    elif not isinstance(baseline, OperationalBaseline):
        raise ValueError("baseline must be an OperationalBaseline")
    for index in range(normal_sessions):
        session = _Session(baseline, seed=seed, scenario=NORMAL_SCENARIO, index=index, slot=index)
        for _ in range(requests_per_session):
            result = session.propose(session.next_normal_action(), emit=True, label="NORMAL")
            assert result is not None
            yield result
    for scenario_index, scenario in enumerate(CHALLENGE_SCENARIOS):
        for index in range(challenge_sessions_per_scenario):
            slot = (scenario_index + 1) * MAX_NORMAL_SESSIONS + index
            agent = f"synthetic-new-{seed:08x}-{index:04d}" if scenario == "new_agent" else _KNOWN_AGENT
            session = _Session(baseline, seed=seed, scenario=scenario, index=index, slot=slot, agent_id=agent)
            yield _challenge(session)

"""Validated immutable lookup data; signatures are verified by DCAMR upstream."""

from dataclasses import dataclass
from types import MappingProxyType

from .feature_types import BaselineIdentity, FeatureError
from .feature_validation import MAX_BASELINE_BYTES, freeze, normalize_host, parse_bound_json


# Recognition of parameter semantics, never policy permission or a normality rule.
CYBER_ACTIONS = {
    "read_logs": (False, False), "query_status": (False, False),
    "query_network": (False, False), "modify_firewall": (True, True),
    "allow_outbound": (True, True),
}


@dataclass(frozen=True, slots=True)
class OperationalBaseline:
    identity: BaselineIdentity
    action_catalog: MappingProxyType
    targets: MappingProxyType
    profiles: MappingProxyType
    agents: MappingProxyType
    cohorts: MappingProxyType

    def select_profile(self, subject: dict) -> tuple[str, str, bool]:
        role, mission = subject["role"], subject["mission_type"]
        agent = self.agents.get(subject["agent_id"])
        if agent is not None:
            if (agent["role"], agent["mission_type"]) != (role, mission):
                raise FeatureError("INPUT_UNSUPPORTED", "snapshot.subject.scope")
            return agent["profile_id"], "AGENT", True
        profile = self.cohorts.get((role, mission))
        if profile is None:
            raise FeatureError("INPUT_UNSUPPORTED", "snapshot.subject.cohort")
        return profile, "COHORT", False


def load_baseline(data: bytes, *, expected_sha256: str) -> OperationalBaseline:
    """Load already verified baseline bytes, once; no file/network access or training."""
    try:
        payload, digest = parse_bound_json(
            data, expected_sha256=expected_sha256, schema_name="anomaly_baseline.json",
            max_bytes=MAX_BASELINE_BYTES,
        )
    except FeatureError as exc:
        if exc.field == "payload.sha256":
            raise FeatureError("BASELINE_UNTRUSTED", "baseline.sha256") from None
        raise
    catalog = payload["action_catalog"]
    for action, semantics in catalog.items():
        if CYBER_ACTIONS.get(action) != (semantics["state_changing"], semantics["destination_required"]):
            raise FeatureError("FEATURE_SCHEMA_MISMATCH", "baseline.action_catalog")
    targets = payload["targets"]
    for target in targets.values():
        for destination in target["destinations"]:
            destination["host"] = normalize_host(destination["host"], "baseline.destinations.host")
        relationships = [(d["host"], d["port"], d["protocol"]) for d in target["destinations"]]
        if len(relationships) != len(set(relationships)):
            raise FeatureError("INPUT_UNSUPPORTED", "baseline.destinations", status="INVALID_INPUT")
    profiles = payload["profiles"]
    for profile in profiles.values():
        if not set(profile["targets"]) <= targets.keys():
            raise FeatureError("INPUT_UNSUPPORTED", "baseline.profile.targets", status="INVALID_INPUT")
        counts = profile["action_counts"]
        # A complete row contains every supported action, including explicit zeros.
        if set(counts) != set(catalog) or sum(counts.values()) <= 0:
            raise FeatureError("REQUIRED_INPUT_MISSING", "baseline.profile.action_counts")
        if sum(counts.values()) > 2**53 - 1:
            raise FeatureError("INPUT_UNSUPPORTED", "baseline.profile.action_counts", status="INVALID_INPUT")
        for previous, row in profile["transitions"].items():
            if (previous not in catalog or not set(row) <= catalog.keys()
                    or not 0 < sum(row.values()) <= 2**53 - 1
                    or counts[previous] == 0
                    or any(count > 0 and counts[action] == 0 for action, count in row.items())):
                raise FeatureError("INPUT_UNSUPPORTED", "baseline.profile.transitions", status="INVALID_INPUT")
    for agent in payload["agents"].values():
        _check_profile_ref(agent, profiles)
    cohorts = {}
    for cohort in payload["cohorts"]:
        _check_profile_ref(cohort, profiles)
        key = (cohort["role"], cohort["mission_type"])
        if key in cohorts:
            raise FeatureError("INPUT_UNSUPPORTED", "baseline.cohorts", status="INVALID_INPUT")
        cohorts[key] = cohort["profile_id"]
    return OperationalBaseline(
        BaselineIdentity(payload["package_id"], payload["version"], digest),
        freeze(catalog), freeze(targets), freeze(profiles), freeze(payload["agents"]),
        MappingProxyType(cohorts),
    )


def _check_profile_ref(reference: dict, profiles: dict) -> None:
    profile = profiles.get(reference["profile_id"])
    if profile is None or (profile["role"], profile["mission_type"]) != (reference["role"], reference["mission_type"]):
        raise FeatureError("INPUT_UNSUPPORTED", "baseline.profile_reference", status="INVALID_INPUT")

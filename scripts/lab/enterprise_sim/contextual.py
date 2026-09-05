"""Synthetic electrician / feeder-voltage observations for the contextual model.

These are invented measurements for a demonstration. They are not ESP readings,
not an approved normal-behavior release, and not evidence about any real feeder.
The generator produces disjoint training, calibration and evaluation collections
because `lab.contextual_training` refuses overlapping session lineage.

Anomalous rows are emitted to a separate evaluation file and are never mixed
into the normal collections. Deciding that a row is normal is a curation act by
a qualified person, not something a generator or a Wazuh alert can confer.
"""

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import random

from .scenario import ELECTRICAL

PROFILE_SCHEMA_VERSION = "context-behavior-profile-v1"
OBSERVATION_SCHEMA_VERSION = "context-behavior-observation-v1"

REQUEST_MAX_AGE_MS = 300_000
RESULT_MAX_AGE_MS = 60_000

ANCHOR_MS = int(datetime(2026, 8, 1, 6, 0, tzinfo=timezone.utc).timestamp() * 1000)
EVAL_ANCHOR_MS = int(datetime(2026, 9, 5, 6, 0, tzinfo=timezone.utc).timestamp() * 1000)

# Per-context normal shapes. Each exact context gets its own forest and its own
# held-out reference, so these distributions are allowed to disagree.
CONTEXTS = {
    ("feeder-a", "grid_tied"): {
        "bus_mean": 480.2, "bus_sd": 1.6, "bus_clip": (474.0, 486.0),
        "delta_sd": 1.4, "delta_clip": (-4.0, 4.0),
        "load_mean": 212.0, "load_sd": 30.0, "load_clip": (120.0, 320.0),
        "gap_median": 1800.0, "gap_sigma": 0.8,
        "changes_lambda": 1.1, "changes_max": 5,
        "stddev_mean": 0.42, "stddev_clip": (0.05, 1.5),
        "settle_mean": 1450.0, "settle_sd": 260.0,
        "error_sd": 0.35,
    },
    ("feeder-a", "islanded"): {
        "bus_mean": 478.6, "bus_sd": 4.2, "bus_clip": (468.0, 492.0),
        "delta_sd": 3.2, "delta_clip": (-9.0, 9.0),
        "load_mean": 143.0, "load_sd": 42.0, "load_clip": (60.0, 260.0),
        "gap_median": 420.0, "gap_sigma": 0.9,
        "changes_lambda": 4.2, "changes_max": 12,
        "stddev_mean": 1.6, "stddev_clip": (0.2, 4.5),
        "settle_mean": 1880.0, "settle_sd": 420.0,
        "error_sd": 0.85,
    },
    ("feeder-b", "grid_tied"): {
        "bus_mean": 479.4, "bus_sd": 2.1, "bus_clip": (472.0, 488.0),
        "delta_sd": 1.8, "delta_clip": (-5.0, 5.0),
        "load_mean": 96.0, "load_sd": 21.0, "load_clip": (40.0, 170.0),
        "gap_median": 3600.0, "gap_sigma": 0.7,
        "changes_lambda": 0.6, "changes_max": 4,
        "stddev_mean": 0.55, "stddev_clip": (0.05, 1.8),
        "settle_mean": 1310.0, "settle_sd": 240.0,
        "error_sd": 0.4,
    },
}

SPLITS = {"train": 320, "calibration": 1200, "evaluation": 240}
SESSION_SIZE = 40


def json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _round(value: float, places: int = 3) -> float:
    return float(round(value, places))


def _poisson(rng: random.Random, lam: float, ceiling: int) -> int:
    # Knuth's method; the counts here are small enough that it stays cheap.
    target, count, product = math.exp(-lam), 0, rng.random()
    while product > target and count < ceiling:
        count += 1
        product *= rng.random()
    return min(count, ceiling)


# --------------------------------------------------------------------------
# Profiles
# --------------------------------------------------------------------------

def build_pre_profile() -> dict:
    def feature(name, unit):
        return {"name": name, "unit": unit, "max_age_ms": REQUEST_MAX_AGE_MS,
                "timing": "AT_OR_BEFORE_REQUEST"}
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "profile_id": "sen-feeder-voltage-pre",
        "version": "1",
        "phase": "PRE_ACTION",
        "features": [
            feature("requested_setpoint_v", "volt"),
            feature("present_bus_voltage_v", "volt"),
            feature("requested_delta_v", "volt"),
            feature("load_current_a", "ampere"),
            feature("seconds_since_last_change", "second"),
            feature("changes_last_hour", "count"),
            feature("bus_voltage_stddev_5m_v", "volt"),
        ],
        "context_keys": ["feeder_id", "operating_mode"],
    }


def build_post_profile() -> dict:
    def before(name, unit):
        return {"name": name, "unit": unit, "max_age_ms": REQUEST_MAX_AGE_MS,
                "timing": "AT_OR_BEFORE_REQUEST"}

    def after(name, unit):
        return {"name": name, "unit": unit, "max_age_ms": RESULT_MAX_AGE_MS,
                "timing": "AT_OR_AFTER_EXECUTION"}
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "profile_id": "sen-feeder-voltage-post",
        "version": "1",
        "phase": "POST_ACTION",
        "features": [
            before("requested_setpoint_v", "volt"),
            before("present_bus_voltage_v", "volt"),
            before("requested_delta_v", "volt"),
            before("load_current_a", "ampere"),
            after("settled_bus_voltage_v", "volt"),
            after("setpoint_error_v", "volt"),
            after("settled_load_current_a", "ampere"),
            after("settle_duration_ms", "millisecond"),
        ],
        "context_keys": ["feeder_id", "operating_mode"],
    }


# --------------------------------------------------------------------------
# One physical request, drawn from a context's normal shape
# --------------------------------------------------------------------------

def _draw_normal(rng: random.Random, shape: dict) -> dict:
    bus = _clip(rng.gauss(shape["bus_mean"], shape["bus_sd"]), *shape["bus_clip"])
    delta = _clip(rng.gauss(0.0, shape["delta_sd"]), *shape["delta_clip"])
    setpoint = _clip(bus + delta, ELECTRICAL["normal_min_v"], ELECTRICAL["normal_max_v"])
    delta = setpoint - bus
    load = _clip(rng.gauss(shape["load_mean"], shape["load_sd"]), *shape["load_clip"])
    gap = _clip(rng.lognormvariate(math.log(shape["gap_median"]), shape["gap_sigma"]),
                20.0, 21_600.0)
    changes = _poisson(rng, shape["changes_lambda"], shape["changes_max"])
    stddev = _clip(abs(rng.gauss(shape["stddev_mean"], shape["stddev_mean"] * 0.45)),
                   *shape["stddev_clip"])
    settle = _clip(rng.gauss(shape["settle_mean"], shape["settle_sd"]), 500.0, 3_200.0)
    error = rng.gauss(0.0, shape["error_sd"])
    settled_bus = setpoint + error
    settled_load = _clip(load + rng.gauss(0.0, 6.0), 20.0, 400.0)
    return {
        "requested_setpoint_v": _round(setpoint),
        "present_bus_voltage_v": _round(bus),
        "requested_delta_v": _round(delta),
        "load_current_a": _round(load),
        "seconds_since_last_change": _round(gap, 1),
        "changes_last_hour": float(changes),
        "bus_voltage_stddev_5m_v": _round(stddev),
        "settled_bus_voltage_v": _round(settled_bus),
        "setpoint_error_v": _round(settled_bus - setpoint),
        "settled_load_current_a": _round(settled_load),
        "settle_duration_ms": _round(settle, 1),
    }


def _observation(profile: dict, profile_sha256: str, *, draw: dict, context: tuple,
                 identity: dict, request_at_ms: int) -> dict:
    """Assemble one observation honouring the phase's temporal binding rules."""
    phase = profile["phase"]
    settle_ms = int(draw["settle_duration_ms"])
    if phase == "PRE_ACTION":
        execution_at = None
        cutoff_at = request_at_ms
    else:
        execution_at = request_at_ms + 900
        cutoff_at = execution_at + settle_ms + 250

    measurements = {}
    for index, feature in enumerate(profile["features"]):
        name = feature["name"]
        if feature["timing"] == "AT_OR_BEFORE_REQUEST":
            observed_at = request_at_ms - (1_500 + index * 120)
        else:
            observed_at = execution_at + settle_ms
        measurements[name] = {
            "value": draw[name],
            "unit": feature["unit"],
            "observed_at_ms": observed_at,
            # Reading identity, not device identity: lab.contextual_training
            # binds each source to one split/session and one value, so a shared
            # sensor name across rows is rejected as leaked lineage.
            "source_id": f"{identity['sensor']}.{identity['observation_id']}",
        }

    return {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "profile_sha256": profile_sha256,
        "observation_id": identity["observation_id"],
        "request_id": identity["request_id"],
        "session_id": identity["session_id"],
        "phase": phase,
        "request_at_ms": request_at_ms,
        "cutoff_at_ms": cutoff_at,
        "execution_id": identity["execution_id"] if phase == "POST_ACTION" else None,
        "execution_at_ms": execution_at,
        "context": {"feeder_id": context[0], "operating_mode": context[1]},
        "measurements": measurements,
    }


# --------------------------------------------------------------------------
# Collections
# --------------------------------------------------------------------------

def generate_normal(profile: dict, profile_sha256: str, *, seed: int = 1729) -> dict:
    """Return {split: [ {observation, input_sha256} ]} with disjoint sessions."""
    phase_tag = "pre" if profile["phase"] == "PRE_ACTION" else "post"
    output = {split: [] for split in SPLITS}
    counter = 0

    for context, shape in sorted(CONTEXTS.items()):
        feeder, mode = context
        context_tag = f"{feeder}-{mode}".replace("_", "-")
        for split, wanted in SPLITS.items():
            rng = random.Random(sha256(
                f"{seed}:{phase_tag}:{context_tag}:{split}".encode()).digest())
            anchor = EVAL_ANCHOR_MS if split == "evaluation" else ANCHOR_MS
            for index in range(wanted):
                counter += 1
                session_index = index // SESSION_SIZE
                session_id = f"sess.{phase_tag}.{split}.{context_tag}.{session_index:03d}"
                identity = {
                    "observation_id": f"obs.{phase_tag}.{split}.{context_tag}.{index:05d}",
                    "request_id": f"req.{phase_tag}.{split}.{context_tag}.{index:05d}",
                    "execution_id": f"exe.{phase_tag}.{split}.{context_tag}.{index:05d}",
                    "session_id": session_id,
                    "sensor": f"esp32-{feeder}",
                }
                request_at = anchor + counter * 47_000 + rng.randrange(0, 9_000)
                observation = _observation(
                    profile, profile_sha256, draw=_draw_normal(rng, shape),
                    context=context, identity=identity, request_at_ms=request_at)
                payload = json_bytes(observation)
                output[split].append({
                    "observation": observation,
                    "input_bytes": payload,
                    "input_sha256": sha256(payload).hexdigest(),
                })
    return output


# --------------------------------------------------------------------------
# Labelled challenge rows: evaluation only, never training
# --------------------------------------------------------------------------

CHALLENGES = (
    ("out_of_band_setpoint", ("feeder-a", "grid_tied"),
     "Requests 512 V, above the hard service band. Permissions must DENY this "
     "deterministically; the model never gets to weigh in.",
     {"requested_setpoint_v": 512.0, "requested_delta_v": 31.8}),
    ("rapid_cycling", ("feeder-a", "grid_tied"),
     "Thirty-seven setpoint changes in the last hour, twelve seconds apart.",
     {"changes_last_hour": 37.0, "seconds_since_last_change": 12.0}),
    ("large_delta_islanded", ("feeder-a", "islanded"),
     "An 18 V swing while islanded: inside the hard band, far outside normal.",
     {"requested_delta_v": -18.0, "requested_setpoint_v": 461.0}),
    ("quiet_feeder_burst", ("feeder-b", "grid_tied"),
     "Feeder B normally changes less than once an hour; this asks for the "
     "fourteenth change of the hour.",
     {"changes_last_hour": 14.0, "seconds_since_last_change": 31.0}),
    ("unstable_bus", ("feeder-b", "grid_tied"),
     "Five-minute bus standard deviation of 7.4 V on a normally quiet feeder.",
     {"bus_voltage_stddev_5m_v": 7.4}),
    ("actuator_no_response", ("feeder-a", "grid_tied"),
     "Commanded a 4 V rise; the bus never moved. POST_ACTION evidence that the "
     "controller's success receipt is not an independent measurement.",
     {"setpoint_error_v": -4.1, "settled_bus_voltage_v": 476.4}),
    ("overshoot", ("feeder-a", "islanded"),
     "Settled 6.8 V above the commanded setpoint.",
     {"setpoint_error_v": 6.8}),
    ("slow_settle", ("feeder-a", "islanded"),
     "Took 9.1 seconds to settle against a normal of roughly 1.9.",
     {"settle_duration_ms": 9_100.0}),
    ("load_collapse", ("feeder-a", "grid_tied"),
     "Load current fell from 214 A to 22 A across the action.",
     {"settled_load_current_a": 22.0}),
)

UNSUPPORTED_CONTEXTS = (
    ("unseen_feeder", ("feeder-c", "grid_tied"),
     "Feeder C has no fitted forest. The model must answer UNKNOWN with a null "
     "score rather than reusing feeder A's normal."),
    ("unseen_mode", ("feeder-a", "maintenance_bypass"),
     "A mode the release never covered. Routing is exact; there is no fallback."),
)


def generate_challenges(profile: dict, profile_sha256: str, *, seed: int = 1729) -> list:
    """Rows for evaluation and demonstration. Not normal, not training data."""
    phase = profile["phase"]
    phase_tag = "pre" if phase == "PRE_ACTION" else "post"
    feature_names = {feature["name"] for feature in profile["features"]}
    rows = []
    counter = 0

    def emit(label, context, note, overrides, *, supported=True):
        nonlocal counter
        counter += 1
        rng = random.Random(sha256(f"{seed}:chal:{phase_tag}:{label}".encode()).digest())
        shape = CONTEXTS.get(context) or CONTEXTS[("feeder-a", "grid_tied")]
        draw = _draw_normal(rng, shape)
        draw.update(overrides)
        if "setpoint_error_v" in overrides and "settled_bus_voltage_v" not in overrides:
            draw["settled_bus_voltage_v"] = _round(
                draw["requested_setpoint_v"] + overrides["setpoint_error_v"])
        identity = {
            "observation_id": f"obs.{phase_tag}.challenge.{label}",
            "request_id": f"req.{phase_tag}.challenge.{label}",
            "execution_id": f"exe.{phase_tag}.challenge.{label}",
            "session_id": f"sess.{phase_tag}.challenge.{label}",
            "sensor": f"esp32-{context[0]}",
        }
        observation = _observation(
            profile, profile_sha256, draw=draw, context=context,
            identity=identity, request_at_ms=EVAL_ANCHOR_MS + 3_600_000 + counter * 61_000)
        payload = json_bytes(observation)
        rows.append({
            "scenario": label,
            "expected": "UNKNOWN_CONTEXT" if not supported else "SCORED",
            "note": note,
            "observation": observation,
            "input_bytes": payload,
            "input_sha256": sha256(payload).hexdigest(),
        })

    for label, context, note, overrides in CHALLENGES:
        # Only apply overrides the phase actually carries.
        applicable = {k: v for k, v in overrides.items() if k in feature_names}
        if not applicable:
            continue
        emit(label, context, note, overrides)

    for label, context, note in UNSUPPORTED_CONTEXTS:
        emit(label, context, note, {}, supported=False)

    return rows

"""Deterministic exact-match permission resolver for the first-light test.

Resolves (agent, action, target, parameters) against a verified release's
PERMIT grants and returns the trusted decision_model.PermissionFinding type.
No model is involved in any denial path; default effect is deny. A grant with
approval_required maps to REVIEW_REQUIRED so the assessment boundary keeps
requiring a human. Scope and placement follow AGENTS.md; the full evaluator
(prohibitions, conditions, generations) remains future runtime-plan work.
"""

from hashlib import sha256

from dcamr.decision_model import PermissionFinding
from dcamr.packages.package_verifier import Release


def _within_bounds(bounds: dict, parameters: dict) -> bool:
    # Every supplied parameter must have an explicit bound and satisfy it;
    # unknown parameters fail closed rather than being ignored.
    for name, value in parameters.items():
        bound = bounds.get(name)
        if type(bound) is not dict:
            return False
        if "one_of" in bound and value not in bound["one_of"]:
            return False
        if "min" in bound and (type(value) not in (int, float) or value < bound["min"]):
            return False
        if "max" in bound and (type(value) not in (int, float) or value > bound["max"]):
            return False
        if not ({"one_of", "min", "max"} & set(bound)):
            return False
    return True


def find_permission(release: Release, agent_id: str, action: str, target: str,
                    parameters: dict, *, request_sha256: str | None = None,
                    request_bytes: bytes | None = None) -> PermissionFinding:
    """Return PERMITTED/REVIEW_REQUIRED on an exact grant match, else UNRESOLVED."""
    if request_sha256 is None:
        request_sha256 = sha256(request_bytes).hexdigest()
    provenance = dict(package_generation=release.generation,
                      package_sha256=release.manifest_sha256)
    for grant in release.grants:
        if grant.effect != "PERMIT":
            continue
        if agent_id not in grant.agents or action not in grant.actions or target not in grant.targets:
            continue
        if not _within_bounds(grant.parameter_bounds, parameters):
            continue
        if grant.approval_required:
            return PermissionFinding(request_sha256=request_sha256, outcome="REVIEW_REQUIRED",
                                     rule_ids=(grant.grant_id,),
                                     reason_codes=("APPROVAL_REQUIRED",), **provenance)
        return PermissionFinding(request_sha256=request_sha256, outcome="PERMITTED",
                                 rule_ids=(grant.grant_id,),
                                 reason_codes=("EXACT_GRANT_MATCH",), **provenance)
    return PermissionFinding(request_sha256=request_sha256, outcome="UNRESOLVED",
                             package_generation=release.generation,
                             package_sha256=release.manifest_sha256,
                             reason_codes=("NO_PERMISSION",))

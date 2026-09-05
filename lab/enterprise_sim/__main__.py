"""Generate the Sentinel AFB simulation artifacts, then validate them.

    .venv/bin/python -m lab.enterprise_sim

Output goes to artifacts/enterprise-sim/. Generation is deterministic for a
fixed seed, so the tree is reproducible and does not need to be committed.

Validation is the point of the last stage: the cyber baseline is loaded with
`dcamr.anomaly_engine.baseline.load_baseline`, the contextual profiles with
`load_context_profile`, and a sample of observations with
`parse_context_observation`. If this module prints OK, the generated data
satisfies the same contracts the Pi runtime will.
"""

import argparse
import base64
from hashlib import sha256
import json
from pathlib import Path
import sys

from dcamr.anomaly_engine.baseline import load_baseline
from dcamr.anomaly_engine.context_profile import (
    ContextError, load_context_profile, parse_context_observation,
)

from . import activity, contextual, cyber_baseline, permissions, wazuh
from .permissions import canonical_bytes, digest_of

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "enterprise-sim"


def write(path: Path, data, *, binary: bool = False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(data)
    elif isinstance(data, (dict, list)):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    else:
        path.write_text(data, encoding="utf-8")
    return path


def write_jsonl(path: Path, rows) -> tuple[Path, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return path, count


# --------------------------------------------------------------------------

def emit_permissions(report: dict) -> dict:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization

    # Deterministic demonstration key. A real deployment issues this from an
    # authorized identity service and never generates it beside the data.
    private_key = Ed25519PrivateKey.from_private_bytes(
        sha256(b"sentinel-afb-demo-permissions-authority-2026-09").digest())
    public_key = private_key.public_key()

    keys = OUT / "keys"
    write(keys / "permissions-signing.ed25519.sk", private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()), binary=True)
    write(keys / "permissions-signing.ed25519.pk", public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo), binary=True)
    write(keys / "README.txt",
          "DEMONSTRATION KEY MATERIAL ONLY.\n\n"
          "The private key here signs the simulated permissions bundle so the\n"
          "verification path can be exercised end to end. It is not a trust\n"
          "root and must never sign anything real.\n\n"
          "On the Pi, install ONLY permissions-signing.ed25519.pk, and install\n"
          "it into the read-only root filesystem -- never onto the USB it\n"
          "validates. A verifying key that travels with the data it verifies\n"
          "means swapping the drive also swaps the trust root.\n")

    def payloads_for(generation: int) -> dict:
        return {
            "subjects.json": permissions.build_subjects(generation),
            "grants.json": permissions.build_grants(generation),
            "prohibitions.json": permissions.build_prohibitions(generation),
            "revocations.json": permissions.build_revocations(generation),
        }

    payloads = payloads_for(permissions.GENERATION)
    digests = {name: digest_of(payload) for name, payload in payloads.items()}

    model_binding = {
        "permissions_schema": permissions.BUNDLE_SCHEMA_VERSION,
        "baseline_package_id": cyber_baseline.PACKAGE_ID,
        "baseline_version": cyber_baseline.VERSION,
        "feature_schema_version": cyber_baseline.FEATURE_SCHEMA_VERSION,
        "contextual_profiles": [
            {"profile_id": "sen-feeder-voltage-pre", "version": "1", "phase": "PRE_ACTION"},
            {"profile_id": "sen-feeder-voltage-post", "version": "1", "phase": "POST_ACTION"},
        ],
        "note": "Cross-binding: a permissions release names the exact model and "
                "profile identities it expects, so a permissions/model drift "
                "surfaces as a rejected activation instead of a wrong score.",
    }

    manifest = permissions.build_manifest(digests, model_binding=model_binding,
                                          generation=permissions.GENERATION)
    manifest_bytes, signature = permissions.sign_manifest(manifest, private_key)

    # Every release the enterprise has published, including the two the edge
    # node never received. These go to the SIEM, not to the USB.
    releases = []
    for generation in permissions.PUBLISHED_GENERATIONS:
        release_payloads = payloads_for(generation)
        release_digests = {name: digest_of(body)
                           for name, body in release_payloads.items()}
        release_manifest = permissions.build_manifest(
            release_digests, model_binding=model_binding, generation=generation)
        release_bytes, release_signature = permissions.sign_manifest(
            release_manifest, private_key)
        releases.append({
            "generation": generation, "manifest": release_manifest,
            "manifest_bytes": release_bytes, "signature": release_signature,
            "payloads": release_payloads,
            "status": ("CURRENT" if generation == permissions.CURRENT_GENERATION
                       else "SUPERSEDED"),
        })

    generation_dir = (OUT / "usb" / "permissions" / "generations"
                      / f"{permissions.GENERATION:06d}")
    for name, payload in payloads.items():
        write(generation_dir / name, canonical_bytes(payload), binary=True)
    write(generation_dir / "manifest.json", manifest_bytes, binary=True)
    write(generation_dir / "manifest.sig", signature, binary=True)

    # Activation pointer. On the Pi this is replaced by an atomic rename; the
    # thumb drive must be ext4 for that to hold (and for the ownership bits).
    write(OUT / "usb" / "permissions" / "active",
          f"generations/{permissions.GENERATION:06d}\n")

    write(OUT / "usb" / "audit_logs" / "README.txt",
          "ALICE-generated output. Separate service identity, separate write\n"
          "permissions, outside the signed input digest set.\n\n"
          "The authoritative durable audit lives on the Pi's internal storage.\n"
          "This directory is the transportable copy: removing the drive must\n"
          "not erase the only record of what happened.\n")

    report["permissions"] = {
        "bundle_id": manifest["bundle_id"],
        "edge_cached_generation": permissions.GENERATION,
        "published_generations": list(permissions.PUBLISHED_GENERATIONS),
        "current_generation": permissions.CURRENT_GENERATION,
        "generation": manifest["generation"],
        "digests": digests,
        "signature_b64": base64.b64encode(signature).decode("ascii"),
        "grant_count": len(payloads["grants.json"]["grants"]),
        "prohibition_count": len(payloads["prohibitions.json"]["prohibitions"]),
        "user_count": len(payloads["subjects.json"]["users"]),
        "agent_count": len(payloads["subjects.json"]["agents"]),
    }
    return {"manifest": manifest, "manifest_bytes": manifest_bytes,
            "signature": signature, "public_key": public_key,
            "payloads": payloads, "releases": releases}


def emit_normal_behavior(report: dict) -> dict:
    baseline = cyber_baseline.build_baseline()
    baseline_bytes = canonical_bytes(baseline)
    write(OUT / "usb" / "normal_behavior" / "cyber" / "baseline.json",
          baseline_bytes, binary=True)

    pre_profile = contextual.build_pre_profile()
    post_profile = contextual.build_post_profile()
    pre_bytes = contextual.json_bytes(pre_profile)
    post_bytes = contextual.json_bytes(post_profile)
    write(OUT / "usb" / "normal_behavior" / "contextual" / "sen-feeder-voltage-pre.json",
          pre_bytes, binary=True)
    write(OUT / "usb" / "normal_behavior" / "contextual" / "sen-feeder-voltage-post.json",
          post_bytes, binary=True)

    report["normal_behavior"] = {
        "baseline_sha256": sha256(baseline_bytes).hexdigest(),
        "baseline_profiles": len(baseline["profiles"]),
        "baseline_targets": len(baseline["targets"]),
        "pre_profile_sha256": sha256(pre_bytes).hexdigest(),
        "post_profile_sha256": sha256(post_bytes).hexdigest(),
    }
    return {"baseline_bytes": baseline_bytes,
            "pre": (pre_profile, pre_bytes), "post": (post_profile, post_bytes)}


def emit_datasets(profiles: dict, report: dict) -> None:
    summary = {}
    for phase_tag, key in (("pre", "pre"), ("post", "post")):
        profile, profile_bytes = profiles[key]
        profile_sha256 = sha256(profile_bytes).hexdigest()
        collections = contextual.generate_normal(profile, profile_sha256)
        counts = {}
        for split, rows in collections.items():
            path = OUT / "datasets" / "contextual" / phase_tag / f"{split}.jsonl"
            _, count = write_jsonl(path, [
                {"input_sha256": row["input_sha256"], "label": "NORMAL",
                 "observation": row["observation"]} for row in rows])
            counts[split] = count
        challenges = contextual.generate_challenges(profile, profile_sha256)
        path = OUT / "datasets" / "contextual" / phase_tag / "challenges.jsonl"
        _, count = write_jsonl(path, [
            {"input_sha256": row["input_sha256"], "label": "CHALLENGE",
             "scenario": row["scenario"], "expected": row["expected"],
             "note": row["note"], "observation": row["observation"]}
            for row in challenges])
        counts["challenges"] = count
        summary[phase_tag] = counts
    report["datasets"] = summary


def emit_wazuh(bundle: dict, report: dict) -> None:
    base = OUT / "wazuh"
    write(base / "inventory.json", wazuh.build_inventory())
    write(base / "rules" / "local_rules.xml", wazuh.LOCAL_RULES)
    write(base / "rules" / "esp_rules.xml", wazuh.ESP_RULES)
    write(base / "decoders" / "local_decoder.xml", wazuh.LOCAL_DECODERS)
    write(base / "shared" / "alice-pi" / "agent.conf", wazuh.AGENT_CONF)
    write(base / "indexer" / "alice-permissions.template.json",
          wazuh.dumps(wazuh.PERMISSIONS_TEMPLATE))
    write(base / "indexer" / "alice-audit.template.json",
          wazuh.dumps(wazuh.AUDIT_TEMPLATE))
    write(base / "indexer" / "role-alice-pi.json", wazuh.dumps(wazuh.INDEXER_ROLE))
    write(base / "indexer" / "rolemapping-alice-pi.json",
          wazuh.dumps(wazuh.INDEXER_ROLE_MAPPING))
    write(base / "api" / "policy-alice-pi-readonly.json", wazuh.dumps(wazuh.API_POLICY))
    write(base / "api" / "role-alice-pi-sync.json", wazuh.dumps(wazuh.API_ROLE))

    lines = []
    for release in bundle["releases"]:
        release_manifest = release["manifest"]
        document = {
            "bundle_id": release_manifest["bundle_id"],
            "generation": release_manifest["generation"],
            "issuer_id": release_manifest["issuer_id"],
            "site_id": release_manifest["site_id"],
            "issued_at": release_manifest["issued_at"],
            "not_before": release_manifest["not_before"],
            "not_after": release_manifest["not_after"],
            "revocation_epoch": release_manifest["revocation_epoch"],
            "status": release["status"],
            "release_note": release_manifest.get("release_note", ""),
            "manifest_sha256": sha256(release["manifest_bytes"]).hexdigest(),
            "manifest_b64": base64.b64encode(release["manifest_bytes"]).decode("ascii"),
            "signature_b64": base64.b64encode(release["signature"]).decode("ascii"),
            "payload_b64": {name: base64.b64encode(canonical_bytes(body)).decode("ascii")
                            for name, body in release["payloads"].items()},
            "compatibility": release_manifest["compatibility"],
        }
        # _bulk with op `create` and an explicit _id: a replay returns 409
        # rather than writing a second copy.
        lines.append(json.dumps({"create": {"_index": "alice-permissions",
                                            "_id": release_manifest["bundle_id"]}},
                                separators=(",", ":")))
        lines.append(json.dumps(document, separators=(",", ":")))
    write(base / "indexer" / "seed-permissions.bulk.ndjson", "\n".join(lines) + "\n")
    report["wazuh"] = {
        "endpoints": len(wazuh.ENDPOINTS),
        "groups": len(wazuh.AGENT_GROUPS),
        "rule_ids": sorted(int(line.split('id="')[1].split('"')[0])
                           for line in wazuh.LOCAL_RULES.splitlines()
                           if "<rule id=" in line),
    }


def emit_logs(report: dict) -> None:
    audit = activity.build_audit_stream()
    _, audit_count = write_jsonl(OUT / "logs" / "alice-audit.jsonl", audit)
    it_rows = activity.build_it_activity()
    _, it_count = write_jsonl(OUT / "logs" / "it-network-activity.jsonl", it_rows)
    report["logs"] = {
        "audit_events": audit_count,
        "audit_chain_head": audit[-1]["alice"]["event_hash"],
        "it_events": it_count,
        "event_types": sorted({row["alice"]["event_type"] for row in audit}),
    }


# --------------------------------------------------------------------------

def validate(bundle: dict, behavior: dict, report: dict) -> list[str]:
    """Check the generated tree against the real loaders, not a private copy."""
    from cryptography.exceptions import InvalidSignature

    failures = []

    # 1. Detached Ed25519 signature over the manifest minus its signature block.
    unsigned = {k: v for k, v in bundle["manifest"].items() if k != "signature"}
    try:
        bundle["public_key"].verify(bundle["signature"], canonical_bytes(unsigned))
    except InvalidSignature:
        failures.append("permissions manifest signature did not verify")

    # 2. Every content digest in the manifest matches its payload bytes.
    for name, payload in bundle["payloads"].items():
        if digest_of(payload) != bundle["manifest"]["content_digests"][name]:
            failures.append(f"content digest mismatch for {name}")

    # 3. The cyber baseline loads under the pinned five-action contract.
    baseline_bytes = behavior["baseline_bytes"]
    try:
        loaded = load_baseline(baseline_bytes,
                               expected_sha256=sha256(baseline_bytes).hexdigest())
        report.setdefault("validation", {})["baseline_profiles"] = len(loaded.profiles)
        # An agent with no personal profile must fall back to its cohort and be
        # reported as such, keeping the novelty distinction intact.
        profile_id, source, has_baseline = loaded.select_profile({
            "agent_id": "elec-agent-07", "role": "electrician",
            "mission_type": "power_distribution"})
        if source != "COHORT" or has_baseline:
            failures.append("elec-agent-07 should resolve to a cohort with novelty kept")
        report["validation"]["cohort_fallback"] = f"{profile_id} via {source}"
    except Exception as error:  # noqa: BLE001 - surface any contract failure
        failures.append(f"baseline did not load: {type(error).__name__}: {error}")

    # 4. Profiles load and observations parse under their real validators.
    for phase_tag in ("pre", "post"):
        profile_dict, profile_bytes = behavior[phase_tag]
        try:
            profile = load_context_profile(
                profile_bytes, expected_sha256=sha256(profile_bytes).hexdigest())
        except ContextError as error:
            failures.append(f"{phase_tag} profile rejected: {error}")
            continue

        path = OUT / "datasets" / "contextual" / phase_tag / "train.jsonl"
        checked = 0
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if checked >= 50:
                    break
                row = json.loads(line)
                payload = contextual.json_bytes(row["observation"])
                if sha256(payload).hexdigest() != row["input_sha256"]:
                    failures.append(f"{phase_tag} observation digest mismatch")
                    break
                try:
                    parse_context_observation(payload, profile,
                                              expected_sha256=row["input_sha256"])
                except ContextError as error:
                    failures.append(f"{phase_tag} observation rejected: {error}")
                    break
                checked += 1
        report.setdefault("validation", {})[f"{phase_tag}_observations_parsed"] = checked

        # Unsupported contexts must still be well-formed observations: the model
        # refuses them by routing, not because the payload is malformed.
        challenge_path = OUT / "datasets" / "contextual" / phase_tag / "challenges.jsonl"
        with challenge_path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                payload = contextual.json_bytes(row["observation"])
                try:
                    parse_context_observation(payload, profile,
                                              expected_sha256=row["input_sha256"])
                except ContextError as error:
                    failures.append(
                        f"{phase_tag} challenge {row['scenario']} rejected: {error}")

    # 5. The audit hash chain is intact end to end.
    audit_path = OUT / "logs" / "alice-audit.jsonl"
    previous = "0" * 64
    with audit_path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            event = json.loads(line)["alice"]
            if event["prev_hash"] != previous:
                failures.append(f"audit chain broken at sequence {index}")
                break
            body = {k: v for k, v in event.items() if k != "event_hash"}
            expected = sha256(previous.encode("ascii") + activity.canonical(body)).hexdigest()
            if expected != event["event_hash"]:
                failures.append(f"audit hash mismatch at sequence {index}")
                break
            previous = event["event_hash"]
    report.setdefault("validation", {})["audit_chain"] = "intact" if not failures else "see failures"
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    arguments = parser.parse_args()

    global OUT
    if arguments.out is not None:
        OUT = arguments.out
    OUT.mkdir(parents=True, exist_ok=True)

    report: dict = {"site": "Sentinel Air Force Base (fictional)",
                    "generator": "lab.enterprise_sim", "deterministic_seed": 1729}

    bundle = emit_permissions(report)
    behavior = emit_normal_behavior(report)
    emit_datasets(behavior, report)
    emit_wazuh(bundle, report)
    emit_logs(report)

    failures = validate(bundle, behavior, report)
    report["validation_failures"] = failures
    write(OUT / "MANIFEST.json", report)

    print(json.dumps(report, indent=2))
    if failures:
        print("\nVALIDATION FAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print("\nOK: generated tree satisfies the baseline, profile, observation "
          "and audit-chain contracts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Synthetic model-to-ledger replay, with temporary evidence and test keys only.

Reuses repository test fixtures deliberately; this is not a live adapter, evidence
store, production model, permission evaluator or transport. No actions execute.
"""
from contextlib import closing
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from dcamr.anomaly_engine.contextual_model import ContextualModel
from dcamr.audit.audit_log import AuditLog
from dcamr.audit.event_contract import contextual_projection
from dcamr.audit.signing import Ed25519Signer, Ed25519Verifier, TrustStore
from lab.contextual_training import fit_contextual_model
from tests.audit_fixtures import clock, event, evidence
from tests.test_contextual_model import json_bytes, normal_examples, observation, profile


def replay(directory: Path) -> dict:
    """Run six cases in an existing empty directory; refuse existing contents."""
    directory = Path(directory)
    if any(directory.iterdir()):
        raise ValueError('replay requires an empty temporary directory')
    models, profiles = {}, {}
    for phase in ('PRE_ACTION', 'POST_ACTION'):
        selected, digest = profile(phase)
        training, calibration = normal_examples(digest, phase=phase, actions=('off',))
        profiles[phase] = selected
        models[phase] = fit_contextual_model(selected, training, calibration,
                                             model_id=f'replay-{phase}')
    # Public, disposable fixture key. Never provision this seed for a real ledger.
    seed = bytes(range(32))
    public = Ed25519PrivateKey.from_private_bytes(seed).public_key().public_bytes(
        Encoding.Raw, PublicFormat.Raw)
    options = dict(signer=Ed25519Signer(seed, 'replay-test-key'),
                   trust=TrustStore({('ed25519', 'replay-test-key'): Ed25519Verifier(public)}),
                   clock=clock)
    path = directory / 'ledger.sqlite'
    inputs, originals, statuses = [], [], {}
    cases = (
        ('pre-ok', 'PRE_ACTION', 'OK'), ('post-ok', 'POST_ACTION', 'OK'),
        ('untrained', 'PRE_ACTION', 'UNAVAILABLE'),
        ('unseen-context', 'PRE_ACTION', 'UNAVAILABLE'),
        ('missing-telemetry', 'POST_ACTION', 'UNAVAILABLE'),
        ('invalid-input', 'POST_ACTION', 'INVALID_INPUT'),
    )
    with closing(AuditLog.initialize(path, ledger_id='replay-ledger', node_id='replay-node',
            quota_bytes=8*1024*1024, reserve_bytes=256*1024, **options)) as ledger:
        for index, (case, phase, expected) in enumerate(cases):
            selected = profiles[phase]
            payload = observation(selected.sha256, phase=phase, index=index)
            if case == 'unseen-context':
                payload['context']['action'] = 'unseen'
            elif case == 'missing-telemetry':
                payload['measurements']['signal']['value'] = None
            elif case == 'invalid-input':
                payload['measurements']['signal']['unit'] = 'wrong-unit'
            input_bytes = json_bytes(payload)
            request_bytes = json_bytes({'request_id': payload['request_id'],
                                       'fixture_case': case, 'simulated': True})
            # Capture dispatch independently before assessment, including failures.
            dispatch = dict(assessment_id=f'assessment-{case}', request_id=payload['request_id'],
                            request_sha256=sha256(request_bytes).hexdigest(),
                            input_sha256=sha256(input_bytes).hexdigest(),
                            execution_id=payload['execution_id'], profile_sha256=selected.sha256,
                            phase=phase)
            model = ContextualModel.untrained(selected) if case == 'untrained' else models[phase]
            assessment = model.assess(input_bytes, expected_sha256=dispatch['input_sha256'])
            if assessment.status != expected:
                raise ValueError(f'{case}: unexpected assessment status')
            original = json_bytes(assessment.to_dict())
            for suffix, raw in (('input', input_bytes), ('request', request_bytes), ('assessment', original)):
                with (directory / f'{case}.{suffix}.json').open('xb') as output:
                    output.write(raw)
            value = event(case, 'ASSESSMENT')
            value['correlation'].update({key: dispatch[key] for key in
                                        ('assessment_id', 'request_id', 'request_sha256', 'execution_id')})
            value['correlation']['correlation_id'] = f'correlation-{case}'
            value['detail'] = contextual_projection(original, dispatch=dispatch, evidence_ref=f'evidence-{case}')
            value['provenance']['evidence'] = [evidence(f'evidence-{case}', sha256(original).hexdigest())]
            value['provenance']['model']['missing_reason'] = 'UNAVAILABLE'
            result = ledger.append(value)
            if not result.persisted or result.sealing_error:
                raise ValueError(f'{case}: append failed')
            inputs.append(deepcopy(value))
            originals.append(result.event)
            statuses[case] = assessment.status
        checkpoint = ledger.seal()
        for value in inputs:
            ledger.queue(value['event_id'], 'fixture-destination')
        pending = ledger.pending()
    with closing(AuditLog.open(path, anchor=checkpoint, **options)) as ledger:
        before = ledger.validate(anchor=checkpoint)
        for value, original in zip(inputs, originals):
            result = ledger.append(value)
            if result.event != original or not result.persisted:
                raise ValueError('restart retry changed original assessment')
        after = ledger.validate(anchor=checkpoint)
        if (after != before or after.event_count != len(cases)
                or after.covered_sequence != len(cases) or not after.anchor_checked
                or ledger.read() != originals or ledger.pending() != pending):
            raise ValueError('restart changed history, coverage or pending delivery')
        for recorded in ledger.read():
            case = recorded['event_id']
            raw = (directory / f'{case}.assessment.json').read_bytes()
            if sha256(raw).hexdigest() != recorded['detail']['contextual']['assessment_evidence']['sha256']:
                raise ValueError('retained assessment evidence changed')
    return {'cases': statuses, 'covered_sequence': after.covered_sequence,
            'pending_count': len(pending), 'execution_mode': 'FIXTURE'}


def main():
    with TemporaryDirectory(prefix='alice-contextual-ledger-') as directory:
        report = replay(Path(directory))
    for case, status in report['cases'].items():
        print(f'PASS {case}: {status}')
    print(f"Verified {report['covered_sequence']} sealed assessments, restart, exact evidence and duplicate retries; no actions executed.")


if __name__ == '__main__':
    main()

import json
from hashlib import sha256
from lab.fan_demo_data import generate


def test_dataset_contract_and_reproducibility(tmp_path):
    a, b = tmp_path/'a', tmp_path/'b'
    manifest = generate(a)
    assert manifest == generate(b)
    sessions = set()
    requests = set()
    for filename, info in manifest['files'].items():
        data = (a/filename).read_bytes()
        assert data == (b/filename).read_bytes()
        assert sha256(data).hexdigest() == info['sha256']
        rows = [json.loads(line) for line in data.splitlines()]
        assert len(rows) == info['rows']
        this_sessions = {r['session_id'] for r in rows}
        assert not sessions & this_sessions
        sessions |= this_sessions
        for r in rows:
            q = r['request']
            assert q['delta'] == q['parameters']['value'] - r['snapshot']['fan_speed']
            if r['ml_eligible']:
                assert 0 <= q['parameters']['value'] <= 100
                assert q['request_id'] not in requests
                requests.add(q['request_id'])
        if filename in ('train.jsonl', 'calibration.jsonl'):
            assert all(r['label'] == 'normal' and abs(r['request']['delta']) < 20 for r in rows)
        if filename == 'evaluation.jsonl':
            assert sum(r['label'] == 'normal' for r in rows) == len(rows)//2
        if filename == 'demo.jsonl':
            assert [r['request']['delta'] for r in rows] == [10,10,10,-60]
            assert [r['label'] for r in rows] == ['normal']*3+['anomaly']


def test_refuses_existing_output(tmp_path):
    import pytest
    with pytest.raises(FileExistsError):
        generate(tmp_path)

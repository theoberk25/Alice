"""Deterministic unsigned fan-action corpus; see docs/guides/anomaly-training.md."""
import argparse
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import random

SEED = 20260906
BASE = datetime(2026, 9, 6, tzinfo=timezone.utc)


def record(rng, split, index, kind):
    normal = kind in ('cooling_step', 'power_step', 'hold', 'cool_shutdown')
    agent = 'power-agent' if kind in ('power_step', 'hot_cut', 'cool_shutdown') else 'cooling-agent'
    if kind == 'hold':
        agent = rng.choice(['power-agent', 'cooling-agent'])
    fan = rng.randrange(25, 81)
    temp = round(rng.uniform(19, 27), 1)
    power = rng.randrange(250, 651)
    delta = 0
    if kind == 'cooling_step':
        temp = round(rng.uniform(26, 39), 1)
        delta = rng.randrange(1, 20)
        reason = 'Cooling agent makes a small increase while room is warm or hot.'
    elif kind == 'power_step':
        power = rng.randrange(431, 651)
        delta = -rng.randrange(1, 20)
        reason = 'Power agent makes a small reduction while room is cool and power elevated.'
    elif kind == 'cool_shutdown':
        fan = rng.randrange(1, 16)
        temp = round(rng.uniform(18, 22), 1)
        power = rng.randrange(431, 651)
        delta = -fan
        reason = 'Small shutdown from low fan speed in a cool, lightly loaded room.'
    elif kind == 'hold':
        reason = 'Maintain current fan setting in a stable cool room.'
    elif kind == 'hot_cut':
        temp = round(rng.uniform(32, 60), 1)
        power = rng.randrange(431, 651)
        delta = -fan
        reason = 'Complete cooling loss during overheating despite power-saving motivation.'
    elif kind == 'large_jump':
        fan = rng.randrange(30, 66)
        delta = rng.choice([-1, 1]) * rng.randrange(26, 31)
        agent = rng.choice(['power-agent', 'cooling-agent'])
        reason = 'Abrupt change exceeding 25 percentage points.'
    elif kind == 'hot_decrease':
        temp = round(rng.uniform(32, 45), 1)
        delta = -rng.randrange(5, 20)
        agent = rng.choice(['power-agent', 'cooling-agent'])
        reason = 'Even a small decrease conflicts with the overheating context.'
    elif kind == 'directive_conflict':
        delta = -rng.randrange(5, 20)
        temp = round(rng.uniform(29, 39), 1)
        reason = 'Cooling agent reduces cooling while its temperature directive is active.'
    else:
        raise ValueError(kind)
    split_offset = {'train': 0, 'calibration': 100000, 'evaluation': 200000, 'validation': 300000, 'demo': 400000}[split]
    n = split_offset + index
    when = BASE + timedelta(seconds=n * 10)
    snapshot = dict(fan_speed=fan, server_temperature=temp, power_consumption=power,
                    battery_remaining_pct=rng.randrange(30, 101), server_load=rng.randrange(20, 96),
                    cameras_active=rng.choice([True, False]), revision=n + 1)
    if kind == 'cool_shutdown':
        snapshot['server_load'] = rng.randrange(5, 26)
    return dict(schema_version='alice-fan-demo-row-v1', synthetic=True,
                record_id=f'{split}-{index:06d}', split=split,
                session_id=f'{split}-session-{index // 20:05d}', scenario=kind,
                snapshot=snapshot, snapshot_at=(when-timedelta(seconds=1)).isoformat(),
                received_at=when.isoformat(),
                request=dict(schema_version='1.0', request_id=f'fan-{split}-{index:06d}',
                             agent_id=agent, action='set_fan_speed', target='SERVER-ROOM-FANS',
                             parameters={'value':fan + delta}, delta=delta,
                             issued_at=when.isoformat()),
                prior_state={'fan_speed':fan, 'revision':n+1},
                label='normal' if normal else 'anomaly', reason=reason,
                expected_validation='ACCEPT', ml_eligible=True)


def generate(out, seed=SEED):
    out.mkdir(parents=True, exist_ok=False)
    rng = random.Random(seed)
    normal = ['cooling_step', 'power_step', 'hold', 'cool_shutdown']
    abnormal = ['hot_cut', 'large_jump', 'hot_decrease', 'directive_conflict']
    sets = {}
    for split, size in [('train', 4000), ('calibration', 2400), ('evaluation', 2000)]:
        sets[split] = [record(rng, split, i, (normal if split != 'evaluation' or i % 2 == 0 else abnormal)[(i // 2 if split == 'evaluation' else i) % 4]) for i in range(size)]
    example = sets['evaluation'][-1]
    example.update(scenario='supplied_overheating_example', reason='58.6 C room temperature makes reducing cooling anomalous despite 456 W power.')
    example['snapshot'].update(fan_speed=60, server_temperature=58.6, power_consumption=456, battery_remaining_pct=72, server_load=80)
    example['prior_state']['fan_speed'] = 60
    example['request'].update(agent_id='power-agent', delta=-10)
    example['request']['parameters']['value'] = 50
    validation = []
    for i in range(200):
        row = record(rng, 'validation', i, 'cooling_step')
        kind = ['out_of_range', 'stale_revision', 'duplicate_request_id', 'expired_snapshot'][i % 4]
        row.update(scenario=kind, label='anomaly', ml_eligible=False,
                   expected_validation='REJECT_OR_RECONCILE', reason='Protocol validation case; not an ML training example.')
        if kind == 'out_of_range':
            row['request']['parameters']['value'] = rng.choice([-10, 110])
            row['request']['delta'] = row['request']['parameters']['value'] - row['snapshot']['fan_speed']
        elif kind == 'stale_revision':
            row['current_revision'] = row['snapshot']['revision'] + 10
        elif kind == 'duplicate_request_id':
            original = validation[i-2]['request']
            row['request'] = json.loads(json.dumps(original))
            row['snapshot'] = dict(validation[i-2]['snapshot'])
            row['prior_state'] = dict(validation[i-2]['prior_state'])
            row['duplicate_of_record_id'] = validation[i-2]['record_id']
        else:
            row['snapshot_at'] = (datetime.fromisoformat(row['received_at']) - timedelta(minutes=30)).isoformat()
        validation.append(row)
    sets['validation'] = validation
    demo = []
    for i, (fan, value) in enumerate([(30,40),(40,50),(50,60),(60,0)]):
        row = record(rng, 'demo', i, 'cooling_step' if i < 3 else 'hot_cut')
        row['session_id'] = 'demo-session-00000'
        row['snapshot'].update(fan_speed=fan,server_temperature=35+i,power_consumption=400+i*25,server_load=80)
        row['prior_state']['fan_speed'] = fan
        row['request']['parameters']['value'] = value
        row['request']['delta'] = value-fan
        row['expected_review'] = 'NONE' if i < 3 else 'HUMAN'
        demo.append(row)
    sets['demo'] = demo
    files = {}
    for split, rows in sets.items():
        data = ''.join(json.dumps(r, sort_keys=True, separators=(',', ':'))+'\n' for r in rows).encode()
        p = out / (split+'.jsonl'); p.write_bytes(data)
        files[p.name] = dict(rows=len(rows), bytes=len(data), sha256=sha256(data).hexdigest(),
                            normal=sum(r['label']=='normal' for r in rows), anomaly=sum(r['label']=='anomaly' for r in rows))
    manifest = dict(schema_version='alice-fan-demo-dataset-v1', seed=seed, synthetic=True,
                    units=dict(fan_speed='percent',delta='percentage_points',server_temperature='degrees_C_room',power_consumption='W',battery_remaining_pct='percent',server_load='percent'),
                    caveats=['Unsigned proposed fan contract; not accepted by current light-only runtime.',
                             'Labels and expected_review are evaluation targets, never model inputs.',
                             'Sessions are independent synthetic groups, not a physical simulator.',
                             'Training/calibration contain normal only; evaluation is balanced.',
                             'Validation cases require deterministic checks, not anomaly inference.',
                             'No model is trained or activated by this generator.'], files=files)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,default=SEED)
    args=p.parse_args()
    print(json.dumps(generate(args.output,args.seed),indent=2))

if __name__ == '__main__':
    main()

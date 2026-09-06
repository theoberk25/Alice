"""Workstation-only fan candidate fitting and data-only export. See anomaly-training guide."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import time

FEATURES = ['fan_before', 'fan_after', 'delta', 'absolute_delta', 'temperature',
            'power', 'server_load', 'hot_reduction', 'power_increase']


def features(row):
    s, q = row['snapshot'], row['request']
    before, after = s['fan_speed'], q['parameters']['value']
    delta = after-before
    if row.get('ml_eligible') is not True or not 0 <= after <= 100:
        raise ValueError('Invalid/protocol rows cannot enter scoring')
    if delta != q['delta'] or q['action'] != 'set_fan_speed':
        raise ValueError('Inconsistent request')
    return [before,after,delta,abs(delta),s['server_temperature'],s['power_consumption'],
            s['server_load'],max(0,s['server_temperature']-27)*max(0,-delta),
            max(0,s['power_consumption']-430)*max(0,delta)]


def correction(n):
    if n <= 1: return 0.0
    if n == 2: return 1.0
    return 2*(math.log(n-1)+0.5772156649015329)-2*(n-1)/n


def portable_score(model, vector):
    # sklearn validates tree inputs as float32 before traversal.
    import struct
    x=[struct.unpack('f',struct.pack('f',v))[0] for v in vector]
    depth=0.0
    for t in model['trees']:
        node=0; length=0
        while t['left'][node] != -1:
            node=t['left'][node] if x[t['feature'][node]] <= t['threshold'][node] else t['right'][node]
            length+=1
        depth+=length+correction(t['samples'][node])
    return -(2**(-depth/(len(model['trees'])*correction(model['max_samples']))))


def train(data, output):
    import numpy as np
    import sklearn
    from sklearn.ensemble import IsolationForest
    manifest=json.loads((data/'manifest.json').read_text())
    rows={}
    for split in ('train','calibration','evaluation','demo'):
        raw=(data/(split+'.jsonl')).read_bytes()
        assert sha256(raw).hexdigest()==manifest['files'][split+'.jsonl']['sha256']
        rows[split]=[json.loads(line) for line in raw.splitlines()]
    assert all(r['label']=='normal' for split in ('train','calibration') for r in rows[split])
    assert not output.exists(), 'Output already exists'
    agents=sorted({r['request']['agent_id'] for r in rows['train']})
    candidate={'schema_version':'alice-fan-forest-experiment-v1','features':FEATURES,
               'source_manifest_sha256':sha256((data/'manifest.json').read_bytes()).hexdigest(),
               'seed':1729,'sklearn_version':sklearn.__version__,'models':{}}
    predictions=[]; max_error=0; started=time.monotonic()
    # Fixed before evaluation: normal-tail percentile >= 0.99 is unusual.
    for agent in agents:
        groups={s:[r for r in rs if r['request']['agent_id']==agent] for s,rs in rows.items()}
        estimator=IsolationForest(n_estimators=64,max_samples=256,n_jobs=1,random_state=1729)
        estimator.fit(np.asarray([features(r) for r in groups['train']]))
        reference=sorted(float(v) for v in estimator.score_samples([features(r) for r in groups['calibration']]))
        model={'max_samples':int(estimator.max_samples_),'normal_reference':reference,'trees':[]}
        for e in estimator.estimators_:
            t=e.tree_
            model['trees'].append(dict(left=t.children_left.tolist(),right=t.children_right.tolist(),
                                      feature=t.feature.tolist(),threshold=t.threshold.tolist(),samples=t.n_node_samples.tolist()))
        candidate['models'][agent]=model
        for split in ('train','calibration','evaluation','demo'):
            batch=groups[split]
            if not batch: continue
            expected=estimator.score_samples([features(r) for r in batch])
            for row,score in zip(batch,expected):
                actual=portable_score(model,features(row)); max_error=max(max_error,abs(actual-score))
                if split not in ('evaluation','demo'): continue
                from bisect import bisect_left
                percentile=(len(reference)-bisect_left(reference,actual))/len(reference)
                predictions.append(dict(record_id=row['record_id'],split=split,agent=agent,
                                        scenario=row['scenario'],label=row['label'],score=actual,
                                        percentile=percentile,unusual=percentile>=0.99))
    assert max_error < 1e-12, max_error
    counts=Counter(); scenarios=defaultdict(Counter)
    for p in predictions:
        if p['split']!='evaluation': continue
        tag=('TP' if p['unusual'] else 'FN') if p['label']=='anomaly' else ('FP' if p['unusual'] else 'TN')
        counts[tag]+=1; scenarios[p['scenario']][tag]+=1
    report=dict(evaluation=dict(counts),by_scenario=dict(scenarios),
                false_positive_rate=counts['FP']/(counts['FP']+counts['TN']),
                anomaly_recall=counts['TP']/(counts['TP']+counts['FN']),
                demo=sorted([p for p in predictions if p['split']=='demo'],key=lambda p:p['record_id']),
                threshold=0.99,portable_max_absolute_error=max_error,elapsed_seconds=time.monotonic()-started,
                limitations=['Synthetic-only experiment; no measured hardware accuracy.',
                             'Per-agent normal references; unknown agents need explicit role/profile mapping.',
                             'No live inference integration or signed model package.',
                             'Protocol checks, permissions and human approval remain separate.',
                             'Features include predefined warm-reduction interaction; labels never enter fitting.'])
    output.mkdir(parents=True)
    (output/'forest.json').write_text(json.dumps(candidate,separators=(',',':'))+'\n')
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (output/'predictions.jsonl').write_text(''.join(json.dumps(p)+'\n' for p in predictions))
    print(json.dumps(report,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();train(a.data,a.output)

if __name__=='__main__': main()

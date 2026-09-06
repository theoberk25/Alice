"""Bounded normal-support/Isolation Forest comparison; frozen fresh synthetic test."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import random
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import NearestNeighbors
from lab.fan_demo_data import record
from lab.train_fan_demo import features, portable_score


def corpus(seed, tag, n, balanced=False):
    rng=random.Random(seed)
    normal=['cooling_step','power_step','hold','cool_shutdown']
    anomaly=['hot_cut','large_jump','hot_decrease','directive_conflict']
    rows=[]
    for i in range(n):
        kind=(anomaly if balanced and i%2 else normal)[(i//2 if balanced else i)%4]
        r=record(rng,'evaluation' if balanced else 'train',i,kind)
        r['record_id']=r['request']['request_id']=f'{tag}-{i}'
        r['session_id']=f'{tag}-session-{i//20}'
        rows.append(r)
    return rows


def matrix(rows):
    # Joint action/context distance uses raw continuous features, not anomaly rules.
    return np.asarray([features(r)[:7] for r in rows],dtype=float)


def metrics(rows, predicted):
    c=Counter(('TP' if p else 'FN') if r['label']=='anomaly' else ('FP' if p else 'TN') for r,p in zip(rows,predicted))
    return dict(counts=dict(c),recall=c['TP']/max(1,c['TP']+c['FN']),fpr=c['FP']/max(1,c['FP']+c['TN']))


def rank(reference, values):
    return np.searchsorted(reference,values,side='right')/len(reference)


def fit(rows, reference, calibration, prototypes):
    models={}
    for agent in ('cooling-agent','power-agent'):
        select=lambda data:[r for r in data if r['request']['agent_id']==agent]
        x=matrix(select(rows)); ref=matrix(select(reference)); cal=matrix(select(calibration))
        assert len(ref)>=1000 and len(cal)>=1000
        forest=IsolationForest(n_estimators=64,max_samples=256,random_state=1729,n_jobs=1).fit(x)
        mean=x.mean(axis=0); scale=x.std(axis=0);scale[scale==0]=1
        z=(x-mean)/scale
        idx=np.random.default_rng(1729).choice(len(x),size=min(prototypes or 512,len(x)),replace=False)
        neighbors=NearestNeighbors(n_neighbors=5,n_jobs=1).fit(z[idx])
        def components(a):
            return -forest.score_samples(a), neighbors.kneighbors((a-mean)/scale)[0].mean(axis=1)
        f,d=components(ref);fr=np.sort(f);dr=np.sort(d)
        f,d=components(cal);combined=rank(fr,f)
        if prototypes: combined=np.maximum(combined,rank(dr,d))
        threshold=float(np.quantile(combined,0.99,method='higher'))
        models[agent]=dict(forest=forest,mean=mean,scale=scale,neighbors=neighbors,
                           fr=fr,dr=dr,threshold=threshold,hybrid=bool(prototypes),
                           reference_count=len(ref),calibration_count=len(cal))
    return models


def score(models,rows):
    result=np.zeros(len(rows)); flags=np.zeros(len(rows),dtype=bool)
    for agent,m in models.items():
        ids=[i for i,r in enumerate(rows) if r['request']['agent_id']==agent]
        if not ids: continue
        x=matrix([rows[i] for i in ids])
        f=rank(m['fr'],-m['forest'].score_samples(x))
        if m['hybrid']:
            d=m['neighbors'].kneighbors((x-m['mean'])/m['scale'])[0].mean(axis=1)
            f=np.maximum(f,rank(m['dr'],d))
        result[ids]=f;flags[ids]=f>m['threshold']
    return flags,result


def portable_hybrid_score(artifact, row):
    from bisect import bisect_right
    import heapq
    import math
    m=artifact['models'][row['request']['agent_id']]
    x=features(row)[:7]
    f=-portable_score(m['forest'],x)
    value=bisect_right(m['forest_reference'],f)/len(m['forest_reference'])
    if m['hybrid']:
        z=[(a-b)/c for a,b,c in zip(x,m['mean'],m['scale'])]
        nearest=heapq.nsmallest(m['neighbors'],(math.dist(z,p) for p in m['prototypes']))
        d=sum(nearest)/len(nearest)
        value=max(value,bisect_right(m['distance_reference'],d)/len(m['distance_reference']))
    return value, value>m['threshold']


def run(out, demo_data):
    out.mkdir(parents=True,exist_ok=False)
    sets={k:corpus(seed,k,n,balanced) for k,seed,n,balanced in [
        ('train',41001,6000,False),('reference',41002,6000,False),
        ('calibration',41003,6000,False),('development',41004,4000,True)]}
    candidates=[]; fitted={}
    for size in (0,512,1024):
        model=fit(sets['train'],sets['reference'],sets['calibration'],size)
        fitted[size]=model
        result=metrics(sets['development'],score(model,sets['development'])[0])
        candidates.append(dict(prototypes=size,**result))
    # Choose on development only with a predeclared <=2% FPR budget.
    eligible=[c for c in candidates if c['fpr']<=0.02]
    chosen=max(eligible,key=lambda c:(c['recall'],-c['prototypes'])) if eligible else min(candidates,key=lambda c:c['fpr'])
    m=fitted[chosen['prototypes']]
    (out/'selection.json').write_text(json.dumps(dict(candidates=candidates,selected=chosen),indent=2)+'\n')
    # Test generated only after model/threshold selection is written and frozen.
    test=corpus(51001,'fresh-test',6000,True)
    flags,scores=score(m,test)
    report=dict(development=candidates,selected=chosen,test=metrics(test,flags),
                by_scenario={k:metrics([r for r in test if r['scenario']==k],flags[[i for i,r in enumerate(test) if r['scenario']==k]]) for k in sorted({r['scenario'] for r in test})})
    demo=[json.loads(l) for l in demo_data.read_text().splitlines()]
    f,s=score(m,demo)
    report['demo']=[dict(record_id=r['record_id'],unusual=bool(v),score=float(w)) for r,v,w in zip(demo,f,s)]
    artifact=dict(schema_version='alice-fan-hybrid-experiment-v1',features=['fan_before','fan_after','delta','absolute_delta','temperature','power','server_load'],models={})
    parity=0
    for agent,v in m.items():
        trees=[]
        for e in v['forest'].estimators_:
            t=e.tree_;trees.append(dict(left=t.children_left.tolist(),right=t.children_right.tolist(),feature=t.feature.tolist(),threshold=t.threshold.tolist(),samples=t.n_node_samples.tolist()))
        exported=dict(max_samples=256,trees=trees)
        for r in [r for r in test if r['request']['agent_id']==agent][:100]:
            x=features(r)[:7];parity=max(parity,abs(portable_score(exported,x)-v['forest'].score_samples([x])[0]))
        artifact['models'][agent]=dict(forest=exported,mean=v['mean'].tolist(),scale=v['scale'].tolist(),
             prototypes=v['neighbors']._fit_X.tolist(),neighbors=5,forest_reference=v['fr'].tolist(),
             distance_reference=v['dr'].tolist(),threshold=v['threshold'],hybrid=v['hybrid'],
             reference_count=v['reference_count'],calibration_count=v['calibration_count'])
    assert parity<1e-12
    report['forest_export_max_error']=parity
    exported=[portable_hybrid_score(artifact,r) for r in test]
    assert all(p[1]==bool(f) for p,f in zip(exported,flags))
    report['hybrid_export_decision_parity_rows']=len(test)
    report['hybrid_export_score_max_error']=max(abs(p[0]-float(s)) for p,s in zip(exported,scores))
    report['limitations']=['Synthetic generator family only; not physical data or independent real-world validation.',
       'Hybrid combines Isolation Forest and nearest-normal support; not forest-only improvement.',
       'No Pi activation; permissions/protocol validation remain separate.']
    (out/'model.json').write_text(json.dumps(artifact,separators=(',',':'))+'\n')
    for name,rows in {**sets,'fresh-test':test}.items():
        (out/(name+'.jsonl')).write_text(''.join(json.dumps(r)+'\n' for r in rows))
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--demo-data', type=Path, required=True)
    a=p.parse_args();run(a.output,a.demo_data)

import random
import pytest
from lab.fan_demo_data import record
from lab.refine_fan_model import corpus, portable_hybrid_score


def test_split_lineage_and_labels():
    a=corpus(1,'fit',100)
    b=corpus(2,'test',100,True)
    assert not {r['session_id'] for r in a}&{r['session_id'] for r in b}
    assert all(r['label']=='normal' for r in a)
    assert sum(r['label']=='anomaly' for r in b)==50


def test_support_distance_and_unknown_agent():
    row=record(random.Random(1),'train',0,'cooling_step')
    # Single-leaf forest is constant; only distance changes the result.
    model={'forest':{'max_samples':2,'trees':[{'left':[-1],'right':[-1], 'feature':[-2],'threshold':[-2],'samples':[2]}]},
               'mean':[0]*6,'scale':[1]*6,'hybrid':True,'neighbors':1,
           'forest_reference':[0.6], 'distance_reference':[1.0], 'threshold':0.99}
    from lab.refine_fan_model import matrix
    model['prototypes']=matrix([row]).tolist()
    artifact={'models':{'cooling-agent':model}}
    assert portable_hybrid_score(artifact,row)[1] is False
    row['snapshot']['server_temperature']+=10
    assert portable_hybrid_score(artifact,row)[1] is True
    row['request']['agent_id']='unknown'
    with pytest.raises(KeyError):portable_hybrid_score(artifact,row)

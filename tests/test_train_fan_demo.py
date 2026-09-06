from copy import deepcopy
import random
import pytest
from lab.fan_demo_data import record
from lab.train_fan_demo import features, portable_score


def test_features_exclude_labels_and_audit_metadata():
    row=record(random.Random(1),'train',0,'cooling_step')
    changed=deepcopy(row)
    changed.update(label='anomaly',reason='different',scenario='different',record_id='different')
    changed['request']['request_id']='different'
    assert features(row)==features(changed)
    changed['request']['delta']+=1
    with pytest.raises(ValueError): features(changed)


def test_portable_tree_float32_and_leaf_depth():
    model={'max_samples':2,'trees':[dict(left=[1,-1,-1],right=[2,-1,-1],
           feature=[0,-2,-2],threshold=[0.5,-2,-2],samples=[2,1,1])]}
    assert portable_score(model,[0.1]) == pytest.approx(-0.5)
    assert portable_score(model,[0.9]) == pytest.approx(-0.5)

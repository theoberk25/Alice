"""Read-only, bounded SIEM queries. Empty/unavailable is never simulated live data."""
from collections import Counter
from datetime import datetime, timezone


def summarize(rows):
    """Build presentation aggregates only from the indexed source documents."""
    modules, techniques, tactics, controls = Counter(), Counter(), Counter(), Counter()
    vulnerabilities, sca, fim = [], [], []
    for row in rows:
        rule, data = row.get('rule') or {}, row.get('data') or {}
        category = data.get('event_category')
        if category: modules[category] += 1
        for technique in (rule.get('mitre') or {}).get('id') or []: techniques[technique] += 1
        for tactic in (rule.get('mitre') or {}).get('tactic') or []: tactics[tactic] += 1
        for control in rule.get('nist_800_53') or []: controls[control] += 1
        if isinstance(data.get('vulnerability'), dict): vulnerabilities.append(row)
        if isinstance(data.get('sca'), dict): sca.append(row)
        if category == 'file_integrity': fim.append(row)
    return {
        'modules': dict(modules.most_common()),
        'mitre': {'techniques': dict(techniques.most_common()), 'tactics': dict(tactics.most_common())},
        'compliance': {'controls': dict(controls.most_common()),
                       'passed': sum((r.get('data',{}).get('sca') or {}).get('result') == 'passed' for r in sca),
                       'failed': sum((r.get('data',{}).get('sca') or {}).get('result') == 'failed' for r in sca),
                       'rows': sca},
        'vulnerabilities': vulnerabilities,
        'fim': fim,
    }


def snapshot(request, window='all'):
    if window not in ('all','24h','7d'):raise ValueError('Unsupported window')
    query={'match_all':{}} if window=='all' else {'range':{'timestamp':{'gte':'now-'+window}}}
    out={'queried_at':datetime.now(timezone.utc).isoformat(), 'window':window}
    try:
        response=request('/wazuh-alerts-*/_search', {
            'size':300,'track_total_hits':True,'query':query,'sort':[{'timestamp':'desc'}],
            '_source':['timestamp','rule','agent','data','decoder','location'],
            'aggs':{'severity':{'filters':{'filters':{
                'critical':{'range':{'rule.level':{'gte':12}}},
                'high':{'range':{'rule.level':{'gte':8,'lt':12}}},
                'medium':{'range':{'rule.level':{'gte':5,'lt':8}}},
                'low':{'range':{'rule.level':{'lt':5}}}}}},
                'trend':{'auto_date_histogram':{'field':'timestamp','buckets':24}}}})
        rows=[dict(x['_source'],document_id=x['_id']) for x in response['hits']['hits']]
        out['alerts']={'available':True,'source':'WAZUH_INDEXER',
            'total':response['hits']['total']['value'],
            'rows':rows,
            'severity':{k:v['doc_count'] for k,v in response['aggregations']['severity']['buckets'].items()},
            'trend':response['aggregations']['trend']['buckets']}
        out['posture']=summarize(rows)
    except Exception:
        out['alerts']={'available':False,'source':'UNAVAILABLE','rows':[], 'total':None,'severity':{},'trend':[]}
        out['posture']=summarize([])
    try:
        response=request('/alice-ledger-v1/_search',{'size':100,'track_total_hits':True,
            'sort':[{'sequence':'desc'}], 'aggs':{'nodes':{'terms':{'field':'node_id','size':50}}}})
        out['ledger']={'available':True,'source':'WAZUH_INDEXER','total':response['hits']['total']['value'],
            'rows':[x['_source'] for x in response['hits']['hits']],
            'nodes':response['aggregations']['nodes']['buckets']}
    except Exception:
        out['ledger']={'available':False,'source':'UNAVAILABLE','total':None,'rows':[],'nodes':[]}
    try:
        response=request('/alice-enterprise-ingress-v1/_search',{
            'size':100,'track_total_hits':True,'sort':[{'received_at':'desc'}]})
        out['enterprise']={'available':True,'source':'WAZUH_INDEXER',
            'total':response['hits']['total']['value'],
            'rows':[dict(x['_source'],document_id=x['_id']) for x in response['hits']['hits']]}
    except Exception:
        out['enterprise']={'available':False,'source':'UNAVAILABLE','total':None,'rows':[]}
    return browser_safe(out)


def browser_safe(value):
    """Display projection only: retain exact 64-bit clocks beyond JS integer precision."""
    if type(value) is int and abs(value)>2**53-1:return str(value)
    if isinstance(value,dict):return {k:browser_safe(v) for k,v in value.items()}
    if isinstance(value,list):return [browser_safe(v) for v in value]
    return value

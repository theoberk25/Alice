"""Read-only, bounded SIEM queries. Empty/unavailable is never simulated live data."""
from datetime import datetime, timezone


def snapshot(request, window='all'):
    if window not in ('all','24h','7d'):raise ValueError('Unsupported window')
    query={'match_all':{}} if window=='all' else {'range':{'timestamp':{'gte':'now-'+window}}}
    out={'queried_at':datetime.now(timezone.utc).isoformat(), 'window':window}
    try:
        response=request('/wazuh-alerts-*/_search', {
            'size':100,'track_total_hits':True,'query':query,'sort':[{'timestamp':'desc'}],
            '_source':['timestamp','rule','agent','data','decoder','location'],
            'aggs':{'severity':{'filters':{'filters':{
                'critical':{'range':{'rule.level':{'gte':12}}},
                'high':{'range':{'rule.level':{'gte':8,'lt':12}}},
                'medium':{'range':{'rule.level':{'gte':5,'lt':8}}},
                'low':{'range':{'rule.level':{'lt':5}}}}}},
                'trend':{'auto_date_histogram':{'field':'timestamp','buckets':24}}}})
        out['alerts']={'available':True,'source':'WAZUH_INDEXER',
            'total':response['hits']['total']['value'],
            'rows':[dict(x['_source'],document_id=x['_id']) for x in response['hits']['hits']],
            'severity':{k:v['doc_count'] for k,v in response['aggregations']['severity']['buckets'].items()},
            'trend':response['aggregations']['trend']['buckets']}
    except Exception:
        out['alerts']={'available':False,'source':'UNAVAILABLE','rows':[], 'total':None,'severity':{},'trend':[]}
    try:
        response=request('/alice-ledger-v1/_search',{'size':100,'track_total_hits':True,
            'sort':[{'sequence':'desc'}], 'aggs':{'nodes':{'terms':{'field':'node_id','size':50}}}})
        out['ledger']={'available':True,'source':'WAZUH_INDEXER','total':response['hits']['total']['value'],
            'rows':[x['_source'] for x in response['hits']['hits']],
            'nodes':response['aggregations']['nodes']['buckets']}
    except Exception:
        out['ledger']={'available':False,'source':'UNAVAILABLE','total':None,'rows':[],'nodes':[]}
    return browser_safe(out)


def browser_safe(value):
    """Display projection only: retain exact 64-bit clocks beyond JS integer precision."""
    if type(value) is int and abs(value)>2**53-1:return str(value)
    if isinstance(value,dict):return {k:browser_safe(v) for k,v in value.items()}
    if isinstance(value,list):return [browser_safe(v) for v in value]
    return value

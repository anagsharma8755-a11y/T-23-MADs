from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from app.ingest import validate_transactions
from app.detection import analyze,score_findings

def tx(i,m,s,r,a,c='INR'): return SimpleNamespace(transaction_id=i,timestamp=datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=m),sender_account=s,receiver_account=r,amount=a,currency=c)
def test_csv_validation_duplicate_positive_and_leading_zero():
    raw=b'transaction_id,timestamp,sender_account,receiver_account,amount,currency\nX,2026-01-01T00:00:00Z,001,002,10,INR\nX,2026-01-01T00:01:00Z,003,004,-1,INR\n'
    rows,errors=validate_transactions(raw);assert rows[0]['sender_account']=='001';assert len(errors)==1 and ('duplicate' in errors[0]['message'] or 'positive' in errors[0]['message'])
def test_fan_in_partial_allocation_no_fund_reuse_and_currency_separation():
    ts=[tx('a',0,'A','M',100),tx('b',1,'B','M',100),tx('c',2,'C','M',100),tx('d',3,'M','X',240),tx('e',4,'M','Y',240),tx('usd',2,'D','M',999,'USD')]
    f=analyze(ts,[],{'fan_min_senders':3,'fan_share':.8}); fans=[x for x in f if x['detector']=='rapid_fan'];assert len(fans)==1;assert fans[0]['currency']=='INR';assert fans[0]['evidence']['forwarded']==300.0
def test_temporal_boundaries_cycle_chain_and_negative_order():
    cycle=[tx('1',0,'A','B',100),tx('2',5,'B','C',95),tx('3',10,'C','A',90)]; out=analyze(cycle,[],{'cycle_window_hours':1});assert any(x['detector']=='circular' for x in out);assert any(x['detector']=='pass_through' for x in out)
    late=[tx('i1',0,'A','M',100),tx('i2',1,'B','M',100),tx('i3',2,'C','M',100),tx('o1',16,'M','X',150),tx('o2',17,'M','Y',150)];assert not any(x['detector']=='rapid_fan' for x in analyze(late,[],{'fan_window_minutes':15}))
def test_shared_attribute_requires_creation_date_and_score_stability():
    now=datetime(2026,1,1,tzinfo=timezone.utc); ac=[SimpleNamespace(account_id=str(i),created_at=now,device_id='D',ip_address=None,kyc_group_id=None) for i in range(3)]+[SimpleNamespace(account_id='x',created_at=None,device_id='D',ip_address=None,kyc_group_id=None)]
    f=analyze([],ac); shared=[x for x in f if x['detector']=='shared_attribute'];assert shared and 'x' not in shared[0]['account_ids']; s1=score_findings(f);s2=score_findings(f+f);assert s1['0']['score']==s2['0']['score']


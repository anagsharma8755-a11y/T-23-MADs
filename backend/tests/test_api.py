import io,time

CSV=b'transaction_id,timestamp,sender_account,receiver_account,amount,currency\nT1,2026-01-01T00:00:00Z,001,002,100,INR\n'
def test_public_registration_creates_workspace_and_session(client):
    payload={"name":"New Analyst","workspace_name":"Fraud Ops","email":"new@example.test","password":"StrongPass123"}
    response=client.post('/api/auth/register',json=payload)
    assert response.status_code==201
    assert response.json()['role']=='supervisor'
    assert client.get('/api/auth/me').json()['email']=='new@example.test'
    assert client.post('/api/auth/register',json=payload).status_code==409

def test_auth_role_and_csrf(client,auth):
    assert client.get('/api/auth/me').status_code==200
    assert client.post('/api/settings',json={'config':{}}).status_code==403
    assert client.post('/api/settings',json={'config':{}},headers=auth).status_code==200
    client.post('/api/auth/logout',headers=auth);assert client.get('/api/auth/me').status_code==401
def test_atomic_invalid_import_and_duplicate(client,auth):
    bad=b'transaction_id,timestamp,sender_account,receiver_account,amount,currency\nX,nope,A,B,2,INR\n'
    r=client.post('/api/datasets',headers=auth,data={'name':'bad'},files={'transactions':('bad.csv',bad,'text/csv')});assert r.status_code==422;assert client.get('/api/datasets').json()==[]
def test_workspace_isolation_analysis_retry_decision_and_audit(client,auth):
    r=client.post('/api/datasets',headers=auth,data={'name':'Test'},files={'transactions':('t.csv',CSV,'text/csv')});body=r.json();did=body['id'];assert body['run_id'];assert client.get(f'/api/analyses/{body["run_id"]}').json()['status']=='completed';summary=client.get(f'/api/datasets/{did}/summary');assert summary.status_code==200 and summary.json()['dataset']['filename']=='t.csv'
    rows=client.get(f'/api/datasets/{did}/transactions').json();assert rows['total']==1 and rows['items'][0]['transaction_id']=='T1'
    job=client.post(f'/api/datasets/{did}/analyses',headers=auth).json()['job_id']; assert client.post(f'/api/analyses/{job}/retry',headers=auth).status_code==200
    assert any(x['action']=='analysis.start' for x in client.get('/api/audit').json())
    client.post('/api/auth/logout',headers=auth);client.post('/api/auth/login',json={'email':'other@test.local','password':'StrongPass!1'});assert client.get(f'/api/datasets/{did}/summary').status_code==404
def test_demo_end_to_end_persistent_decision_and_export(client,auth):
    d=client.post('/api/demo/load',headers=auth).json(); job=client.post(f"/api/datasets/{d['id']}/analyses",headers=auth).json()['job_id']
    state={}
    for _ in range(30):
        state=client.get(f'/api/analyses/{job}').json()
        if state['status'] in {'completed','failed'}: break
        time.sleep(.05)
    assert state['status']=='completed', state
    scores=client.get(f'/api/analyses/{job}/scores').json()['items']; assert scores
    account=scores[0]['account_id']; assert client.post(f'/api/analyses/{job}/accounts/{account}/decision',headers=auth,json={'status':'cleared','note':'short'}).status_code==422
    r=client.post(f'/api/analyses/{job}/accounts/{account}/decision',headers=auth,json={'status':'cleared','note':'Verified synthetic scenario'});assert r.status_code==200
    assert client.get(f'/api/analyses/{job}/accounts/{account}').json()['score']['review_status']=='cleared'
    export=client.get(f'/api/analyses/{job}/export?format=csv');assert export.status_code==200 and 'account_id' in export.text
    report=client.get(f'/api/analyses/{job}/report');assert report.status_code==200 and account in report.text and 'Why flagged' in report.text
    evaluation=client.get(f'/api/demo/evaluation/{job}');assert evaluation.status_code==200 and evaluation.json()['scope']=='synthetic dataset only'

def test_detection_settings_enforce_strict_ranges(client,auth):
    assert client.post('/api/settings',headers=auth,json={'config':{'medium_risk_score':70,'high_risk_score':60}}).status_code==422
    assert client.post('/api/settings',headers=auth,json={'config':{'fan_share':1.5}}).status_code==422

def test_honeypot_session_captures_scores_and_reports(client,auth):
    created=client.post('/api/honeypot/sessions',headers=auth,json={'name':'Payment portal decoy','decoy_profile':'payment_portal'})
    assert created.status_code==200
    sid=created.json()['session']['id']
    for event_type in ('login_failure','login_failure','login_failure','transfer_attempt'):
        event=client.post(f'/api/honeypot/sessions/{sid}/events',headers=auth,json={'event_type':event_type,'source_alias':'test-client-01','target_alias':'decoy-account','amount':125.0,'currency':'USD'})
        assert event.status_code==200
    detail=client.get(f'/api/honeypot/sessions/{sid}').json()
    assert detail['session']['event_count']==4
    assert detail['session']['risk_score']>=60
    assert detail['session']['status']=='escalated'
    assert all(x['metadata']['sandboxed'] for x in detail['events'])
    report=client.get(f'/api/honeypot/sessions/{sid}/report')
    assert report.status_code==200 and 'honeypot evidence report' in report.text.lower()
    closed=client.post(f'/api/honeypot/sessions/{sid}/status',headers=auth,json={'status':'closed','note':'Reviewed and closed during isolated test'})
    assert closed.status_code==200
    rejected=client.post(f'/api/honeypot/sessions/{sid}/events',headers=auth,json={'event_type':'login_failure','source_alias':'x','target_alias':'decoy'})
    assert rejected.status_code==409


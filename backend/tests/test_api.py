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
    r=client.post('/api/datasets',headers=auth,data={'name':'Test'},files={'transactions':('t.csv',CSV,'text/csv')});did=r.json()['id'];assert client.get(f'/api/datasets/{did}/summary').status_code==200
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
    account=scores[0]['account_id']; r=client.post(f'/api/analyses/{job}/accounts/{account}/decision',headers=auth,json={'status':'cleared','note':'Verified synthetic scenario'});assert r.status_code==200
    assert client.get(f'/api/analyses/{job}/accounts/{account}').json()['score']['review_status']=='cleared'
    export=client.get(f'/api/analyses/{job}/export?format=csv');assert export.status_code==200 and 'account_id' in export.text
    evaluation=client.get(f'/api/demo/evaluation/{job}');assert evaluation.status_code==200 and evaluation.json()['scope']=='synthetic dataset only'


from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from app import ai,config
from app.database import edit_state,initial_state,transaction,User,Setting,Usage
from app.main import app,identity
from app.domain import RuleError

def create(client,data):
    r=client.post('/api/projects',json=data);assert r.status_code==200,r.text;return r.json()
def act(client,p,kind,target='',value=''):
    return client.post(f"/api/projects/{p['id']}/action",json={'action':kind,'target_id':target,'value':value,'version':p['version']})

def test_manual_and_stale_edits(client,project_data):
    p=create(client,project_data)
    assert act(client,p,'rename_project',value='New name').status_code==200
    assert act(client,p,'complete_task','a').status_code==409
    assert client.get('/api/state').json()['projects'][0]['tasks'][0]['done'] is False

def test_agent_requires_approval_and_replay_blocked(client,project_data,monkeypatch):
    p=create(client,project_data)
    monkeypatch.setattr(ai,'chat',lambda *args:{'reply':'I saved it!','action':'complete_task','target_id':'a','value':''})
    reply=client.post(f"/api/projects/{p['id']}/chat",json={'message':'Complete Outline'}).json()
    assert 'Nothing has been saved' in reply['reply']
    assert not client.get('/api/state').json()['projects'][0]['tasks'][0]['done']
    path='/api/proposals/'+reply['proposal']['id']+'/approve'
    assert client.post(path).status_code==200
    assert client.post(path).status_code==409
    assert client.get('/api/state').json()['projects'][0]['treats']==15

def test_stale_proposal_and_cancel(client,project_data,monkeypatch):
    p=create(client,project_data)
    monkeypatch.setattr(ai,'chat',lambda *args:{'reply':'Proposed','action':'rename_project','target_id':'','value':'New name'})
    r=client.post(f"/api/projects/{p['id']}/chat",json={'message':'rename'}).json()
    act(client,p,'complete_task','a')
    assert client.post('/api/proposals/'+r['proposal']['id']+'/approve').status_code==409
    assert client.post('/api/proposals/'+r['proposal']['id']+'/cancel').status_code==200

def test_unknown_agent_target_cannot_change_data(client,project_data,monkeypatch):
    p=create(client,project_data)
    monkeypatch.setattr(ai,'chat',lambda *args:{'reply':'x','action':'complete_task','target_id':'foreign-task','value':''})
    r=client.post(f"/api/projects/{p['id']}/chat",json={'message':'Do it'})
    assert r.status_code==422
    assert client.get('/api/state').json()['projects'][0]['treats']==0

def test_auth_isolation_and_admin(client,project_data):
    p=create(client,project_data)
    with transaction() as db:db.add(User(id='other',email='other@example.com',username='other',state=initial_state()))
    app.dependency_overrides[identity]=lambda:{'id':'other','email':'other@example.com','username':'other','admin':False}
    try:
        assert client.get('/api/state').json()['projects']==[]
        assert act(client,p,'complete_task','a').status_code==422
        assert client.post(f"/api/projects/{p['id']}/restore").status_code==422
        assert client.get('/api/admin').status_code==403
    finally:app.dependency_overrides.clear()

def test_concurrent_creation_enforces_three_slots(client,project_data):
    with ThreadPoolExecutor(max_workers=10) as pool:
        codes=list(pool.map(lambda _:client.post('/api/projects',json=project_data).status_code,range(10)))
    assert codes.count(200)==3 and codes.count(422)==7

def test_concurrent_rewards_once(client,project_data):
    p=create(client,project_data)
    with ThreadPoolExecutor(max_workers=10) as pool:
        codes=list(pool.map(lambda _:act(client,p,'complete_task','a').status_code,range(10)))
    assert codes.count(200)==1 and codes.count(409)==9
    assert client.get('/api/state').json()['projects'][0]['treats']==15

def test_budget_reservations_are_atomic(client):
    with transaction() as db:db.get(Setting,'budget').value=100
    def reserve(_):
        try:return ai.reserve('local-demo',30)
        except RuleError:return None
    with ThreadPoolExecutor(max_workers=10) as pool:results=list(pool.map(reserve,range(10)))
    assert sum(r is not None for r in results)==3
    assert client.get('/api/admin').json()['spent_usd']==.00009

def test_failed_calls_keep_reservation(client,monkeypatch):
    rid=ai.reserve('local-demo',100);ai.settle(rid)
    assert client.get('/api/admin').json()['spent_usd']==.0001

def test_zero_budget_and_manual_work(client,project_data):
    client.put('/api/admin/budget',json={'budget_usd':0})
    try:ai.reserve('local-demo',1);assert False
    except RuleError:pass
    p=create(client,project_data)
    assert act(client,p,'complete_task','a').status_code==200
    assert client.post(f"/api/projects/{p['id']}/pet/play").status_code==200

def test_restore_cap_and_archive_readonly(client,project_data):
    p=create(client,project_data);act(client,p,'archive_project')
    for _ in range(3):create(client,project_data)
    assert client.post(f"/api/projects/{p['id']}/restore").status_code==422
    assert client.post(f"/api/projects/{p['id']}/pet/feed").status_code==422

def test_forget_removes_retrieval_context(client):
    client.post('/api/memories',json={'message':'Prefer short sessions'})
    with edit_state('local-demo') as s:s['chats']['x']=[{'role':'user','content':'Prefer short sessions'}];s['proposals']=[{'id':'x'}]
    mid=client.get('/api/state').json()['memories'][0]['id']
    assert client.delete('/api/memories/'+mid).status_code==200
    s=client.get('/api/state').json()
    assert s['memories']==[] and s['chats']=={} and s['proposals']==[]

def test_security_headers_and_origin(client):
    assert "frame-ancestors 'none'" in client.get('/').headers['Content-Security-Policy']
    assert client.post('/api/memories',json={'message':'x'},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/state',headers={'Host':'evil.example'}).status_code==403

def test_plan_without_key_is_honest(client,project_data):
    r=client.post('/api/plan',json=project_data)
    assert r.status_code==200 and r.json()['source']=='local_template'
    assert client.get('/api/state').json()['projects']==[]

def test_feed_balance_and_focus(client,project_data):
    p=create(client,project_data)
    assert client.post(f"/api/projects/{p['id']}/pet/feed").status_code==422
    assert client.post(f"/api/projects/{p['id']}/focus/start").status_code==200
    assert client.post(f"/api/projects/{p['id']}/focus/start").status_code==422
    assert client.post(f"/api/projects/{p['id']}/focus/stop").status_code==200
    saved=client.get('/api/state').json()['projects'][0]
    assert saved['treats']==0 and saved['growth_earned']==0 and saved['stage']==0

def test_species_and_foreign_memory_validation(client,project_data):
    project_data['species']='rabbit'
    assert client.post('/api/projects',json=project_data).status_code==422
    assert client.post('/api/memories',json={'message':'x'*301}).status_code==422

def test_ten_distinct_users_at_once(client,project_data):
    from fastapi import Request
    def test_identity(request:Request):
        return {'id':request.headers['x-test-user'],'email':'tester@example.com','username':'tester','admin':False}
    with transaction() as db:
        for i in range(10):db.add(User(id=f'test-{i}',email=f'{i}@example.com',username=f'test-{i}',state=initial_state()))
    app.dependency_overrides[identity]=test_identity
    try:
        def run(i):
            headers={'x-test-user':f'test-{i}'}
            r=client.post('/api/projects',json={**project_data,'name':f'Private project {i}'},headers=headers)
            own=client.get('/api/state',headers=headers).json()
            return r.status_code, [p['name'] for p in own['projects']]
        with ThreadPoolExecutor(max_workers=10) as pool:results=list(pool.map(run,range(10)))
        assert all(code==200 and names==[f'Private project {i}'] for i,(code,names) in enumerate(results))
    finally:app.dependency_overrides.clear()

def test_malformed_model_output_is_rejected(client,project_data,monkeypatch):
    p=create(client,project_data)
    monkeypatch.setattr(ai,'chat',lambda *args:{'reply':'done','action':'execute_sql','value':'DROP'})
    assert client.post(f"/api/projects/{p['id']}/chat",json={'message':'x'}).status_code==422

def test_milestone_rename_cannot_duplicate_rewards(client,project_data):
    p=create(client,project_data);p=act(client,p,'complete_task','a').json();p=act(client,p,'reopen_task','a').json()
    data=deepcopy(project_data);data['tasks'][0]['milestone']='Renamed prepare'
    p=client.put(f"/api/projects/{p['id']}?version={p['version']}",json=data).json()
    p=act(client,p,'complete_task','a').json()
    assert p['treats']==15

def test_model_http_failure_retains_cost_and_no_mutation(client,monkeypatch):
    import httpx
    monkeypatch.setattr(config,'OPENAI_KEY','test-key-not-real')
    def fail(*args,**kwargs):raise httpx.ConnectTimeout('test')
    monkeypatch.setattr(ai.httpx,'post',fail)
    try:ai.invoke('local-demo',config.CHAT_MODEL,'test',{},ai.CHAT_SCHEMA);assert False
    except RuleError:pass
    assert client.get('/api/admin').json()['spent_usd']>0

def test_verified_auth_required(client,monkeypatch):
    import httpx
    monkeypatch.setattr(config,'DEMO',False)
    monkeypatch.setattr(config,'SUPABASE_URL','https://auth.example')
    monkeypatch.setattr('app.main.httpx.get',lambda *args,**kw:httpx.Response(200,json={'id':'noverify','email':'user@example.com','email_confirmed_at':None}))
    assert client.get('/api/state',headers={'Authorization':'Bearer fake'}).status_code==403

def test_restore_removed_task_preserves_reward_identity(client,project_data):
    project_data['tasks']=project_data['tasks'][:1]
    p=create(client,project_data);p=act(client,p,'complete_task','a').json()
    p=act(client,p,'delete_task','a').json();p=act(client,p,'restore_task','a').json()
    p=act(client,p,'reopen_task','a').json();p=act(client,p,'complete_task','a').json()
    assert p['treats']==15

def test_archive_closes_focus_session(client,project_data):
    p=create(client,project_data)
    client.post(f"/api/projects/{p['id']}/focus/start")
    act(client,p,'archive_project')
    s=client.get('/api/state').json()
    assert s['focus'][0]['ended'] is not None
    other=create(client,project_data)
    assert client.post(f"/api/projects/{other['id']}/focus/start").status_code==200

def test_skip_dates_respects_completed_work(client,project_data):
    p=create(client,project_data);p=act(client,p,'complete_task','a').json();old=p['tasks'][0]['due']
    p=act(client,p,'skip_dates',value='2026-11-23, 2026-11-24').json()
    assert p['tasks'][0]['due']==old
    assert p['tasks'][1]['due']=='2026-11-25'

def test_free_pet_interaction_does_not_stale_plan(client,project_data):
    p=create(client,project_data)
    client.post(f"/api/projects/{p['id']}/pet/play")
    assert act(client,p,'rename_project',value='Better name').status_code==200

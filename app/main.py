from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import datetime, timezone, date
from pathlib import Path
import re
import httpx
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from . import config, ai
from .database import initialize, transaction, User, Setting, Usage, uid, now, initial_state, edit_state, read_state, record
from .domain import RuleError, project, new_project, schedule, slot_check, apply_action

@asynccontextmanager
async def lifespan(app):
    if not config.DEMO and (not config.SUPABASE_URL or not config.SUPABASE_KEY):
        raise RuntimeError('Production requires Supabase Auth configuration. See docs/SETUP.md.')
    if not config.DEMO and not config.ORIGIN.startswith('https://'):
        raise RuntimeError('Production requires an HTTPS APP_ORIGIN.')
    initialize()
    yield

app=FastAPI(title='Pawgress',version='0.1.0',lifespan=lifespan)
STATIC=Path(__file__).parent/'static'

@app.middleware('http')
async def guard(request, call_next):
    if config.DEMO and (request.client.host not in {'127.0.0.1','::1','testclient'} or request.headers.get('host','').split(':')[0] not in {'127.0.0.1','localhost','testserver','[',''}):
        return JSONResponse({'detail':'Local demo is loopback-only. Configure verified sign-in before hosting.'},403)
    if request.method not in {'GET','HEAD','OPTIONS'}:
        origin=request.headers.get('origin')
        if origin and origin!=config.ORIGIN:
            return JSONResponse({'detail':'Origin not allowed.'},403)
        if int(request.headers.get('content-length','0'))>100000:
            return JSONResponse({'detail':'Request is too large.'},413)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    if request.url.path.startswith('/api/'): response.headers['Cache-Control']='no-store'
    return response

@app.exception_handler(ValueError)
async def bad_value(request, exc): return JSONResponse({'detail':'Invalid value. Check dates and task details.'},422)

@app.exception_handler(RuleError)
async def rule_error(request, exc): return JSONResponse({'detail':str(exc)},422)


def identity(request:Request):
    if config.DEMO:
        info={'id':'local-demo','email':'demo@localhost','user_metadata':{'display_name':'You'}}
    else:
        token=request.headers.get('authorization','')
        if not token.startswith('Bearer '): raise HTTPException(401,'Sign in to continue.')
        try:
            r=httpx.get(config.SUPABASE_URL+'/auth/v1/user',headers={'apikey':config.SUPABASE_KEY,'Authorization':token},timeout=10)
            if r.status_code!=200: raise HTTPException(401,'Your session expired. Please sign in again.')
            info=r.json()
            if not info.get('email_confirmed_at'): raise HTTPException(403,'Verify your email before continuing.')
        except httpx.HTTPError: raise HTTPException(503,'Sign-in service is temporarily unavailable.')
    with transaction() as db:
        user=db.get(User,info['id'])
        if not user:
            user=User(id=info['id'],email=info['email'].lower(),username='user-'+info['id'][:12],state=initial_state())
            db.add(user); db.flush()
        if user.disabled: raise HTTPException(403,'This account is disabled.')
        # Auth service is the source of truth for the email address.
        user.email=info['email'].lower()
        return {'id':user.id,'email':user.email,'username':user.username,'admin':config.DEMO or user.email in config.ADMINS}


def admin(user=Depends(identity)):
    if not user['admin']: raise HTTPException(403,'Administrator access required.')
    return user

class Task(BaseModel):
    id:str=Field(default_factory=uid,max_length=100)
    title:str=Field(min_length=1,max_length=200)
    milestone:str=Field(default='Work',min_length=1,max_length=100)
    minutes:int=Field(default=30,ge=5,le=2400)
    required:bool=True
    dependencies:list[str]=Field(default_factory=list,max_length=100)

class ProjectInput(BaseModel):
    name:str=Field(min_length=1,max_length=100)
    goal:str=Field(min_length=1,max_length=1500)
    start:date
    deadline:date
    weekdays:list[int]=Field(min_length=1,max_length=7)
    minutes_per_day:int=Field(default=60,ge=10,le=480)
    unavailable:list[date]=Field(default_factory=list,max_length=366)
    species:str='cat'
    pet_name:str=Field(default='Mochi',min_length=1,max_length=40)
    tasks:list[Task]=Field(default_factory=list,max_length=100)

class Action(BaseModel):
    action:str
    target_id:str=''
    value:str=Field(default='',max_length=500)
    version:int

class AgentOutput(BaseModel):
    reply:str=Field(max_length=4000)
    action:Literal['none','complete_task','reopen_task','rename_project','rename_task','delete_task','add_task','change_deadline','skip_dates','archive_project','delete_project','remember']
    target_id:str=Field(max_length=100)
    value:str=Field(max_length=500)

class Message(BaseModel):
    message:str=Field(min_length=1,max_length=2000)

class AuthInput(BaseModel):
    email:str=Field(default='',max_length=320)
    password:str=Field(default='',max_length=128)
    refresh_token:str=Field(default='',max_length=4000)
    token_hash:str=Field(default='',max_length=4000)
    type:str='email'

@app.get('/api/config')
def public_config():
    return {'demo':config.DEMO,'ai':bool(config.OPENAI_KEY),'max_projects':3,'auth':bool(config.SUPABASE_URL),'name':'Pawgress'}

@app.post('/api/auth/{operation}')
def auth(operation:str,data:AuthInput,request:Request):
    if not config.SUPABASE_URL: raise HTTPException(503,'Configure Supabase to enable email sign-in.')
    routes={'signup':('signup',{'email':data.email,'password':data.password}), 'login':('token?grant_type=password',{'email':data.email,'password':data.password}), 'refresh':('token?grant_type=refresh_token',{'refresh_token':data.refresh_token}), 'recover':('recover',{'email':data.email}), 'verify':('verify',{'token_hash':data.token_hash,'type':data.type})}
    if operation not in routes: raise HTTPException(404)
    if operation in {'signup','login'} and len(data.password)<8: raise HTTPException(422,'Use at least eight password characters.')
    if operation=='verify' and data.type not in {'email','recovery','signup'}: raise HTTPException(422,'Invalid verification type.')
    path,body=routes[operation]
    try:
        r=httpx.post(config.SUPABASE_URL+'/auth/v1/'+path,headers={'apikey':config.SUPABASE_KEY},json=body,timeout=15)
    except httpx.HTTPError: raise HTTPException(503,'Sign-in service is temporarily unavailable.')
    if operation=='recover': return {'message':'If this email is registered, a reset email will arrive shortly.'}
    if r.status_code>=400: raise HTTPException(400,'Sign-in could not be completed. Check your details or verification email.')
    return r.json()

@app.post('/api/auth-password')
def password(data:AuthInput,request:Request,user=Depends(identity)):
    if config.DEMO: raise HTTPException(400,'Demo has no password.')
    if len(data.password)<8: raise HTTPException(422,'Use at least eight characters.')
    try:
        r=httpx.put(config.SUPABASE_URL+'/auth/v1/user',headers={'apikey':config.SUPABASE_KEY,'Authorization':request.headers.get('authorization','')},json={'password':data.password},timeout=15)
    except httpx.HTTPError: raise HTTPException(503,'Sign-in service is temporarily unavailable.')
    if r.status_code>=400: raise HTTPException(400,'Password could not be updated.')
    return {'ok':True}

@app.get('/api/state')
def state(user=Depends(identity)):
    result=read_state(user['id']); result['user']=user
    return result

@app.post('/api/plan')
def generate(data:ProjectInput,user=Depends(identity)):
    details=data.model_dump(mode='json'); result=ai.plan(user['id'],details)
    details['tasks']=[Task.model_validate(t).model_dump() for t in result['tasks']]
    preview=new_project(initial_state(),details)
    return {'tasks':preview['tasks'],'source':result['source']}

@app.post('/api/projects')
def create(data:ProjectInput,user=Depends(identity)):
    with edit_state(user['id']) as s: p=new_project(s,data.model_dump(mode='json'))
    return p

@app.post('/api/projects/{pid}/action')
def action(pid:str,data:Action,user=Depends(identity)):
    with edit_state(user['id']) as s:
        p=project(s,pid,writable=True)
        if p['version']!=data.version: raise HTTPException(409,'The project changed. Refresh and review again.')
        p=apply_action(s,pid,data.action,data.target_id,data.value)
    return p

@app.put('/api/projects/{pid}')
def edit_project(pid:str,data:ProjectInput,version:int,user=Depends(identity)):
    with edit_state(user['id']) as s:
        p=project(s,pid,writable=True)
        if p['version']!=version: raise HTTPException(409,'The project changed. Refresh and review again.')
        old={t['id']:t for t in p['tasks']}
        incoming=data.model_dump(mode='json')
        for t in incoming['tasks']:
            previous=old.pop(t['id'],None)
            if previous:
                if previous.get('deleted'): raise RuleError('Use a new task ID for new work.')
                if previous['done'] and any(t[k]!=previous[k] for k in ['minutes','dependencies','milestone','required']):
                    raise RuleError('Reopen completed work before changing its effort, milestone or dependencies.')
                t.update({k:previous[k] for k in ['done','deleted','rewarded']})
                for k in ['due','scheduled_start']:
                    if k in previous:t[k]=previous[k]
                if t['required'] and not t['rewarded']:
                    p['growth_total']+=t['minutes']-(previous['minutes'] if previous.get('required',True) else 0)
            else:
                t.update(done=False,deleted=False,rewarded=False)
                if t['required']:p['growth_total']+=t['minutes']
        # Keep removed work as tombstones to preserve rewards/history and prevent deletion-based growth.
        for t in old.values():
            t['deleted']=True; incoming['tasks'].append(t)
        incoming['species']=p['species']
        p.update(incoming); schedule(p); p['version']+=1
        record(s,pid,'edited','Project details and plan updated')
    return p

@app.post('/api/projects/{pid}/restore')
def restore(pid:str,user=Depends(identity)):
    with edit_state(user['id']) as s:
        p=project(s,pid)
        if p['status']=='active': return p
        slot_check(s); p['status']='active'; p['version']+=1; record(s,pid,'restored',p['name'])
    return p

@app.post('/api/projects/{pid}/chat')
def chat(pid:str,data:Message,user=Depends(identity)):
    s=read_state(user['id']); p=project(s,pid,writable=True); base_version=p['version']
    try: output=AgentOutput.model_validate(ai.chat(user['id'],p,s,data.message)).model_dump()
    except ValidationError: raise RuleError('The AI returned an invalid proposal. Nothing changed.')
    proposal=None
    with edit_state(user['id']) as s:
        current=project(s,pid,writable=True)
        if current['version']!=base_version: raise HTTPException(409,'The project changed during this response. Please ask again.')
        if output['action']!='none':
            # Dry-run the SAME domain action; invalid targets/schedules never become approvable.
            preview=deepcopy(s)
            revised=apply_action(preview,pid,output['action'],output['target_id'],output['value'])
            changes=[]
            for key in ['name','deadline','status','unavailable']:
                if current[key]!=revised[key]: changes.append({'field':key,'before':str(current[key]),'after':str(revised[key])})
            old_tasks={t['id']:t for t in current['tasks']}
            for task in revised['tasks']:
                old=old_tasks.get(task['id'])
                if old is None: changes.append({'field':'New task','before':'—','after':task['title']})
                else:
                    for key in ['title','due','done','deleted']:
                        if old.get(key)!=task.get(key): changes.append({'field':old['title']+' · '+key,'before':str(old.get(key)),'after':str(task.get(key))})
            proposal={'id':uid(),'project_id':pid,'version':base_version,'action':output['action'],'target_id':output['target_id'],'value':output['value'],'created_at':now(),'status':'pending','changes':changes}
            s['proposals'].append(proposal); s['proposals']=s['proposals'][-50:]
            output['reply']='I prepared a change for you to review. Nothing has been saved yet.'
        messages=s['chats'].setdefault(pid,[])
        messages.extend([{'role':'user','content':data.message,'at':now()},{'role':'assistant','content':output['reply'][:4000],'at':now()}])
        s['chats'][pid]=messages[-100:]
    return {'reply':output['reply'],'proposal':proposal}

@app.post('/api/proposals/{proposal_id}/{decision}')
def decide(proposal_id:str,decision:str,user=Depends(identity)):
    if decision not in {'approve','cancel'}: raise HTTPException(404)
    with edit_state(user['id']) as s:
        item=next((x for x in s['proposals'] if x['id']==proposal_id),None)
        if not item or item['status']!='pending': raise HTTPException(409,'This proposal is no longer pending.')
        if decision=='approve':
            p=project(s,item['project_id'],writable=True)
            if p['version']!=item['version']:raise HTTPException(409,'This proposal is stale. Ask for a new one.')
            apply_action(s,p['id'],item['action'],item['target_id'],item['value'])
            s['chats'].setdefault(p['id'],[]).append({'role':'assistant','content':'Your approved change has been saved.','at':now()})
        item['status']='approved' if decision=='approve' else 'cancelled'
    return {'ok':True}

@app.post('/api/projects/{pid}/pet/{interaction}')
def pet(pid:str,interaction:str,item:str='',user=Depends(identity)):
    with edit_state(user['id']) as s:
        p=project(s,pid,writable=True)
        if interaction=='feed':
            if p['treats']<1:raise RuleError('Complete a task to earn treats. Petting and play are always free.')
            p['treats']-=1
        elif interaction=='equip':
            if item not in p['items']:raise RuleError('This item has not been unlocked.')
            if item in p['equipped']:p['equipped'].remove(item)
            else:p['equipped'].append(item)
        elif interaction not in {'pet','play'}:raise RuleError('Unknown interaction.')
    return {'ok':True,'treats':p['treats']}

@app.post('/api/projects/{pid}/focus/{operation}')
def focus(pid:str,operation:str,user=Depends(identity)):
    with edit_state(user['id']) as s:
        p=project(s,pid,writable=True)
        running=next((x for x in s['focus'] if not x.get('ended')),None)
        if operation=='start':
            if running:raise RuleError('Finish the running focus session first.')
            entry={'id':uid(),'project_id':pid,'started':now(),'ended':None};s['focus'].append(entry)
        elif operation=='stop':
            if not running or running['project_id']!=pid:raise RuleError('No focus session is running for this project.')
            running['ended']=now(); entry=running
            elapsed=(datetime.fromisoformat(running['ended'])-datetime.fromisoformat(running['started'])).total_seconds()
            p['focus_minutes']+=min(120,max(0,int(elapsed/60)))
        else:raise RuleError('Unknown focus action.')
    return entry

@app.post('/api/memories')
def remember(data:Message,user=Depends(identity)):
    if len(data.message)>300:raise RuleError('Keep memories under 300 characters.')
    with edit_state(user['id']) as s:
        if len(s['memories'])>=30:raise RuleError('Remove an old memory first.')
        s['memories'].append({'id':uid(),'text':data.message,'at':now()})
    return {'ok':True}

@app.delete('/api/memories/{mid}')
def forget(mid:str,user=Depends(identity)):
    with edit_state(user['id']) as s:
        s['memories']=[m for m in s['memories'] if m['id']!=mid]
        s['chats']={};s['proposals']=[] # prevent old context from resurrecting a forgotten fact
    return {'ok':True}

@app.delete('/api/projects/{pid}/chat')
def clear_chat(pid:str,user=Depends(identity)):
    with edit_state(user['id']) as s:
        project(s,pid);s['chats'][pid]=[];s['proposals']=[p for p in s['proposals'] if p['project_id']!=pid]
    return {'ok':True}

@app.get('/api/admin')
def admin_info(user=Depends(admin)):
    with transaction() as db:
        month=datetime.now(timezone.utc).strftime('%Y-%m')
        users=[{'id':u.id,'email':u.email,'username':u.username,'disabled':bool(u.disabled)} for u in db.scalars(select(User))]
        usage=db.scalar(select(func.coalesce(func.sum(Usage.cost),0)).where(Usage.month==month))
        return {'users':users,'month':month,'spent_usd':usage/1e6,'budget_usd':db.get(Setting,'budget').value/1e6}

class AdminChange(BaseModel):
    budget_usd:float|None=Field(default=None,ge=0,le=1000)
    disabled:bool|None=None
    username:str|None=Field(default=None,min_length=3,max_length=40)

@app.put('/api/admin/budget')
def budget(data:AdminChange,user=Depends(admin)):
    if data.budget_usd is None:raise RuleError('Budget required.')
    with transaction() as db:
        row=db.scalar(select(Setting).where(Setting.id=='budget').with_for_update());row.value=round(data.budget_usd*1e6)
    return {'ok':True}

@app.put('/api/admin/users/{user_id}')
def admin_user(user_id:str,data:AdminChange,user=Depends(admin)):
    try:
        with transaction() as db:
            target=db.get(User,user_id)
            if not target:raise HTTPException(404)
            if data.disabled is not None:
                if target.id==user['id']:raise RuleError('You cannot disable your own administrator account.')
                target.disabled=int(data.disabled)
            if data.username:
                if not re.fullmatch(r'[A-Za-z0-9_-]{3,40}',data.username):raise RuleError('Use letters, digits, underscores, or hyphens.')
                target.username=data.username.lower()
    except IntegrityError:raise RuleError('That username is already used.')
    return {'ok':True}

@app.get('/health')
def health():return {'status':'ok','app':'Pawgress'}

app.mount('/static',StaticFiles(directory=STATIC),name='static')
@app.get('/')
@app.get('/companion')
@app.get('/auth/confirm')
def index():return FileResponse(STATIC/'index.html')

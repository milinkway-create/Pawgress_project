"""Pure project rules, used by manual controls AND approved agent actions."""
from datetime import date, timedelta, datetime
from copy import deepcopy
from .database import uid, now, record

class RuleError(ValueError):
    pass

def project(state, project_id, writable=False):
    p = next((p for p in state['projects'] if p['id'] == project_id), None)
    if not p:
        raise RuleError('Project not found.')
    if writable and p['status'] != 'active':
        raise RuleError('Restore this project before editing.')
    return p

def slot_check(state):
    if sum(p['status'] == 'active' for p in state['projects']) >= 3:
        raise RuleError('Your three active project slots are full. Archive a project first.')

def schedule(p):
    """Serial effort-aware schedule, topological dependencies, no weekend guessing."""
    start, deadline = date.fromisoformat(p['start']), date.fromisoformat(p['deadline'])
    if deadline < start or (deadline-start).days > 1825:
        raise RuleError('Choose a deadline after the start date, within five years.')
    weekdays = p['weekdays']
    if not weekdays or any(type(d) is not int or d not in range(7) for d in weekdays):
        raise RuleError('Choose at least one available weekday.')
    daily = int(p['minutes_per_day'])
    if not 10 <= daily <= 480:
        raise RuleError('Daily availability must be 10–480 minutes.')
    blocked = set(p.get('unavailable', []))
    tasks = [t for t in p['tasks'] if not t.get('deleted')]
    by_id = {t['id']: t for t in tasks}
    if len(by_id) != len(tasks):
        raise RuleError('Task IDs must be unique.')
    ordered, visiting, visited = [], set(), set()
    def visit(t):
        if t['id'] in visiting:
            raise RuleError('Task dependencies contain a cycle.')
        if t['id'] in visited:
            return
        visiting.add(t['id'])
        for dep in t.get('dependencies', []):
            if dep not in by_id:
                raise RuleError('A task depends on missing or deleted work.')
            visit(by_id[dep])
        visiting.remove(t['id']); visited.add(t['id']); ordered.append(t)
    for t in tasks:
        visit(t)
    cursor, remaining = start, daily
    for t in ordered:
        if t['done']:
            continue
        effort = int(t['minutes'])
        if not 5 <= effort <= 2400:
            raise RuleError('Task effort must be 5–2400 minutes.')
        for dep in t.get('dependencies', []):
            due = by_id[dep].get('due')
            if due and date.fromisoformat(due) > cursor:
                cursor, remaining = date.fromisoformat(due), daily
        began = None
        while effort > 0:
            if cursor > deadline:
                raise RuleError('This work does not fit your availability. Extend the deadline, add available time, or reduce scope.')
            if cursor.weekday() not in weekdays or cursor.isoformat() in blocked or remaining == 0:
                cursor += timedelta(days=1); remaining = daily; continue
            began = began or cursor.isoformat()
            chunk = min(effort, remaining)
            effort -= chunk; remaining -= chunk
        t['scheduled_start'], t['due'] = began, cursor.isoformat()
    return p

def new_project(state, data):
    slot_check(state)
    if data['species'] not in {'cat','dog','fish'}:
        raise RuleError('Choose a cat, dog, or fish.')
    if not data['tasks'] or len(data['tasks']) > 100:
        raise RuleError('A plan needs 1–100 tasks.')
    p = {k: deepcopy(data[k]) for k in ['name','goal','start','deadline','weekdays','minutes_per_day','species','pet_name','tasks']}
    p.update(id=uid(), status='active', version=1, created_at=now(), unavailable=data.get('unavailable', []), treats=0, stage=0, rewards=[], items=[], equipped=[], focus_minutes=0)
    for t in p['tasks']:
        t.update(done=False, deleted=False, rewarded=False)
    p['growth_total'] = max(1, sum(t['minutes'] for t in p['tasks'] if t.get('required', True)))
    p['growth_earned'] = 0
    p['reward_milestones'] = [{'id': uid(), 'name': name, 'tasks': [t['id'] for t in p['tasks'] if t['milestone']==name and t.get('required', True)]} for name in dict.fromkeys(t['milestone'] for t in p['tasks'])]
    schedule(p)
    state['projects'].append(p)
    record(state, p['id'], 'created', p['name'])
    return p

def grant(p, key, amount, label):
    if any(r['key'] == key for r in p['rewards']):
        return False
    p['treats'] += amount
    p['rewards'].append({'key':key,'amount':amount,'label':label,'at':now()})
    return True

def complete(p, task_id, done):
    t = next((t for t in p['tasks'] if t['id'] == task_id and not t.get('deleted')), None)
    if not t:
        raise RuleError('Task not found.')
    if done and any(not next(x for x in p['tasks'] if x['id']==d)['done'] for d in t.get('dependencies', [])):
        raise RuleError('Finish the prerequisite tasks first.')
    if not done and any(x['done'] and not x.get('deleted') and t['id'] in x.get('dependencies', []) for x in p['tasks']):
        raise RuleError('Reopen completed dependent tasks first.')
    t['done'] = done
    if done and grant(p, 'task:'+t['id'], 5, t['title']):
        if t.get('required', True):
            p['growth_earned'] += t['minutes']
        t['rewarded'] = True
    if p['growth_earned'] >= p['growth_total'] * .4:
        p['stage'] = max(p['stage'], 1)
    by_id = {t['id']: t for t in p['tasks']}
    for i, milestone in enumerate(p.get('reward_milestones', [])):
        group = [by_id[tid] for tid in milestone['tasks'] if tid in by_id]
        # Achievement IDs and membership are fixed when the plan is saved.
        if group and len(group)==len(milestone['tasks']) and all(x['done'] and not x.get('deleted') for x in group):
            if grant(p, 'milestone:'+milestone['id'], 10, milestone['name']):
                item = 'cushion' if i == 0 else 'toy'
                if item not in p['items']: p['items'].append(item)
    required = [x for x in p['tasks'] if x.get('required', True)]
    if required and all(x['done'] and not x.get('deleted') for x in required):
        p['stage'] = 2
        if grant(p, 'project-complete', 0, 'Project complete'):
            p['items'] = list(dict.fromkeys(p['items'] + ['cushion','toy','celebration']))

def apply_action(state, project_id, action, target_id='', value=''):
    p = project(state, project_id, writable=True)
    if action == 'complete_task': complete(p, target_id, True)
    elif action == 'reopen_task': complete(p, target_id, False)
    elif action == 'rename_project':
        if not value.strip() or len(value)>100: raise RuleError('Use a project name of 1–100 characters.')
        p['name'] = value.strip()
    elif action in {'rename_task','delete_task'}:
        t = next((t for t in p['tasks'] if t['id']==target_id and not t.get('deleted')), None)
        if not t: raise RuleError('Task not found.')
        if action == 'delete_task':
            if any(target_id in x.get('dependencies',[]) and not x.get('deleted') for x in p['tasks']):
                raise RuleError('Remove or change dependent tasks before deleting this task.')
            t['deleted'] = True
        else:
            if not value.strip() or len(value)>200: raise RuleError('Use a task name of 1–200 characters.')
            t['title'] = value.strip()
    elif action == 'restore_task':
        t=next((t for t in p['tasks'] if t['id']==target_id and t.get('deleted')),None)
        if not t:raise RuleError('Removed task not found.')
        t['deleted']=False
        schedule(p)
    elif action == 'add_task':
        if len(p['tasks'])>=100: raise RuleError('A project supports up to 100 tasks.')
        if not value.strip() or len(value)>200: raise RuleError('Use a task name of 1–200 characters.')
        t={'id':uid(),'title':value.strip(),'milestone':'Additional work','minutes':30,'required':True,'dependencies':[],'done':False,'deleted':False,'rewarded':False}
        p['tasks'].append(t); p['growth_total']+=30; schedule(p)
    elif action == 'change_deadline':
        date.fromisoformat(value); p['deadline'] = value; schedule(p)
    elif action == 'skip_dates':
        dates=[date.fromisoformat(v.strip()).isoformat() for v in value.split(',')]
        p['unavailable']=sorted(set(p['unavailable']+dates))
        schedule(p)
    elif action == 'archive_project': p['status'] = 'archived'
    elif action == 'delete_project': p['status'] = 'trash'
    elif action == 'remember':
        if not value.strip() or len(value)>300: raise RuleError('Memory must be 1–300 characters.')
        if len(state['memories'])>=30: raise RuleError('Remove an old memory first (30 memory limit).')
        state['memories'].append({'id':uid(),'text':value.strip(),'at':now()})
    else: raise RuleError('Unsupported action.')
    if action in {'archive_project','delete_project'}:
        for focus in state['focus']:
            if focus['project_id']==p['id'] and not focus.get('ended'):
                focus['ended']=now()
                elapsed=(datetime.fromisoformat(focus['ended'])-datetime.fromisoformat(focus['started'])).total_seconds()
                p['focus_minutes']+=min(120,max(0,int(elapsed/60)))
    p['version'] += 1
    record(state, project_id, action, value or target_id)
    return p

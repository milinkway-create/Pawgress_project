from copy import deepcopy
import pytest
from app.domain import new_project,apply_action,schedule,RuleError
from app.database import initial_state

def test_growth_rewards_and_reopen(project_data):
    s=initial_state();p=new_project(s,project_data)
    apply_action(s,p['id'],'complete_task','a')
    assert p['treats']==15 and p['stage']==0 and p['growth_earned']==30
    apply_action(s,p['id'],'reopen_task','a');apply_action(s,p['id'],'complete_task','a')
    assert p['treats']==15 and p['growth_earned']==30
    apply_action(s,p['id'],'complete_task','b');assert p['stage']==1 and p['growth_earned']==90
    apply_action(s,p['id'],'complete_task','c');assert p['stage']==2
    assert p['growth_earned']==p['growth_total']==120 and p['treats']==45
    apply_action(s,p['id'],'reopen_task','c');assert p['stage']==2

def test_dependency_completion_and_reopen(project_data):
    s=initial_state();p=new_project(s,project_data)
    with pytest.raises(RuleError):apply_action(s,p['id'],'complete_task','b')
    apply_action(s,p['id'],'complete_task','a');apply_action(s,p['id'],'complete_task','b')
    with pytest.raises(RuleError):apply_action(s,p['id'],'reopen_task','a')

def test_weekends_blackouts_and_capacity(project_data):
    project_data.update(start='2026-11-27',deadline='2026-12-04',unavailable=['2026-11-30'])
    p=new_project(initial_state(),project_data)
    assert p['tasks'][0]['due']=='2026-11-27'
    assert p['tasks'][1]['due']=='2026-12-01'
    assert p['tasks'][2]['due']=='2026-12-01'

def test_cycle_and_missing_dependency(project_data):
    project_data['tasks'][0]['dependencies']=['c']
    with pytest.raises(RuleError,match='cycle'):new_project(initial_state(),project_data)
    project_data['tasks'][0]['dependencies']=['missing']
    with pytest.raises(RuleError,match='missing'):new_project(initial_state(),project_data)

def test_impossible_deadline(project_data):
    project_data['deadline']=project_data['start']
    with pytest.raises(RuleError,match='does not fit'):new_project(initial_state(),project_data)

def test_archive_frees_slot_keeps_pet(project_data):
    s=initial_state()
    pets=[new_project(s,project_data) for _ in range(3)]
    with pytest.raises(RuleError,match='three'):new_project(s,project_data)
    apply_action(s,pets[0]['id'],'archive_project')
    new_project(s,project_data)
    assert len(s['projects'])==4 and pets[0]['pet_name']=='Mochi'
    with pytest.raises(RuleError,match='Restore'):apply_action(s,pets[0]['id'],'rename_project',value='Changed')

def test_delete_does_not_manufacture_completion(project_data):
    s=initial_state();p=new_project(s,project_data)
    apply_action(s,p['id'],'delete_task','c')
    apply_action(s,p['id'],'complete_task','a');apply_action(s,p['id'],'complete_task','b')
    assert p['stage']<2 and 'celebration' not in p['items']

def test_one_task_and_optional_work(project_data):
    project_data['tasks']=project_data['tasks'][:1]
    project_data['tasks'].append({'id':'extra','title':'Optional','milestone':'Extra','minutes':20,'required':False,'dependencies':[]})
    s=initial_state();p=new_project(s,project_data)
    apply_action(s,p['id'],'complete_task','a')
    assert p['stage']==2

def test_completed_dates_preserved(project_data):
    s=initial_state();p=new_project(s,project_data)
    apply_action(s,p['id'],'complete_task','a');old=deepcopy(p['tasks'][0])
    apply_action(s,p['id'],'change_deadline',value='2026-12-25')
    assert p['tasks'][0]==old

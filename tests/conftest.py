import os
os.environ['DEMO_MODE']='true'
os.environ['OPENAI_API_KEY']=''
import pytest
from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from app import database,config
from app.main import app

@pytest.fixture
def client(tmp_path,monkeypatch):
    engine=create_engine('sqlite:///'+str(tmp_path/'test.db'),connect_args={'check_same_thread':False,'timeout':30})
    monkeypatch.setattr(database,'engine',engine)
    monkeypatch.setattr(config,'OPENAI_KEY','')
    with TestClient(app) as client:
        client.get('/api/state')
        yield client
    engine.dispose()

@pytest.fixture
def project_data():
    return {'name':'Portfolio','goal':'Publish a portfolio','start':'2026-11-23','deadline':'2026-12-18','weekdays':[0,1,2,3,4],'minutes_per_day':60,'unavailable':[],'species':'cat','pet_name':'Mochi','tasks':[
        {'id':'a','title':'Outline','milestone':'Prepare','minutes':30,'required':True,'dependencies':[]},
        {'id':'b','title':'Build','milestone':'Make','minutes':60,'required':True,'dependencies':['a']},
        {'id':'c','title':'Publish','milestone':'Finish','minutes':30,'required':True,'dependencies':['b']}]}

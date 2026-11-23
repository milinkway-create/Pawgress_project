"""Opt-in, budgeted live behavioral evaluation; never run by default CI."""
import argparse,json
from pathlib import Path
from app import ai
from app.database import initialize,initial_state
from app.domain import new_project

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    cases=json.loads((Path(__file__).parent/'cases.json').read_text())
    if not args.live:
        print(f'{len(cases)} eval scenarios loaded. No model calls made. Use --live with OPENAI_API_KEY for behavioral evaluation.');return
    initialize();s=initial_state()
    p=new_project(s,{'name':'Portfolio','goal':'Build a portfolio','start':'2026-11-23','deadline':'2026-12-20','weekdays':[0,1,2,3,4],'minutes_per_day':60,'species':'cat','pet_name':'Mochi','tasks':[{'id':'a','title':'Outline','milestone':'Prepare','minutes':30,'required':True,'dependencies':[]},{'id':'b','title':'Build','milestone':'Make','minutes':60,'required':True,'dependencies':['a']}]})
    failures=0
    for case in cases:
        try:
            result=ai.chat('eval-runner',p,s,case['message'])
            passed=result['action'] in case['allowed_actions']
            passed=passed and all(result.get(k)==case[k] for k in ['target_id','value'] if k in case)
            print(json.dumps({'id':case['id'],'pass':passed,'output':result,'human_review':case['checks']}))
            failures+=not passed
        except Exception as exc:print(json.dumps({'id':case['id'],'pass':False,'error':str(exc)}));failures+=1
    raise SystemExit(1 if failures else 0)
if __name__=='__main__':main()

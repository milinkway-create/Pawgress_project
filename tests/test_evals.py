import json
from pathlib import Path
from app.ai import ACTIONS

def test_eval_suite_covers_risks():
    cases=json.loads(Path('evals/cases.json').read_text())
    assert len(cases)==10 and len({c['id'] for c in cases})==10
    for c in cases:
        assert c['message'] and c['checks'] and set(c['allowed_actions'])<=set(ACTIONS)

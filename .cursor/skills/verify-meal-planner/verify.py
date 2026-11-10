#!/usr/bin/env python3
"""Purpose-fit verification for the Smart Recipe Meal Planner backend.

Runs the full pytest suite (unit + API + integration) and a route-table
smoke check that guards the fixed-path-before-/recipes/{id} ordering bug.
Standard library plus the project venv. Exit 0 and FAILURES=0 mean green.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'smart_recipe_meal_planner'))

checks = []
failures = []


def record(name, ok, detail=''):
    checks.append({'name': name, 'ok': bool(ok), 'detail': detail})
    print(('PASS' if ok else 'FAIL') + ' ' + name + (' :: ' + detail if detail else ''))
    if not ok:
        failures.append(name)


def main():
    py = os.path.join(BACKEND_ROOT, '.venv', 'bin', 'python')
    if not os.path.exists(py):
        py = sys.executable
    if subprocess.run([py, '-c', 'import fastapi, sqlalchemy, pytest'], cwd=BACKEND_ROOT,
                      capture_output=True).returncode != 0:
        record('doctor: backend deps importable', False,
               'create the venv and install backend deps (see README)')
        return finish()
    record('doctor: backend deps importable', True, py)

    smoke = subprocess.run([py, '-c', '''
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.api.v1.dependencies import get_current_active_user, get_db
class U: id = __import__("uuid").uuid4(); email = "smoke@example.com"; is_active = True
app.dependency_overrides[get_current_active_user] = lambda: U()
app.dependency_overrides[get_db] = lambda: MagicMock()
c = TestClient(app)
# fixed routes must win over /recipes/{recipe_id}: a UUID parse 422 here means
# the shadowing regression is back; any other answer means the right route ran
r = c.get("/api/v1/recipes/search-external", params={"query": "pasta"})
assert r.status_code != 422 or "recipe_id" not in r.text, "route shadowing regression"
print("search-external answered with", r.status_code)
'''], cwd=BACKEND_ROOT, capture_output=True, text=True)
    record('route order: /recipes/search-external not shadowed by /recipes/{id}',
           smoke.returncode == 0, smoke.stdout.strip() or smoke.stderr.strip()[-200:])

    suite = subprocess.run([py, '-m', 'pytest', 'app/tests', '-q'],
                           cwd=BACKEND_ROOT, capture_output=True, text=True)
    tail = (suite.stdout.strip().splitlines() or [''])[-1]
    record('backend test suite green', suite.returncode == 0 and 'passed' in tail, tail)

    # Frontend: vite build + vitest suite
    fe = os.path.join(BACKEND_ROOT, 'frontend', 'ui')
    npm = shutil.which('npm')
    record('doctor: npm on PATH', npm is not None, npm or 'not found')
    if npm is None:
        return finish()
    if not os.path.isdir(os.path.join(fe, 'node_modules')):
        ci = subprocess.run([npm, 'ci', '--no-audit', '--no-fund'], cwd=fe,
                            capture_output=True, text=True, timeout=600)
        record('frontend npm ci', ci.returncode == 0, ci.stderr.strip()[-200:])
        if ci.returncode != 0:
            return finish()
    build = subprocess.run([npm, 'run', 'build'], cwd=fe,
                           capture_output=True, text=True, timeout=600)
    record('frontend vite build green', build.returncode == 0,
           (build.stdout.strip().splitlines() or [''])[-1] if build.returncode == 0
           else (build.stdout + build.stderr).strip()[-300:])
    vitest = subprocess.run([os.path.join(fe, 'node_modules', '.bin', 'vitest'), 'run'],
                            cwd=fe, capture_output=True, text=True, timeout=600)
    m = re.search(r'Tests\s+(\d+) passed', vitest.stdout)
    record('frontend vitest suite green', vitest.returncode == 0,
           ('%s tests passed' % m.group(1)) if m else (vitest.stdout + vitest.stderr).strip()[-200:])
    return finish()


def finish():
    evidence_dir = tempfile.mkdtemp(prefix='verify-meal-planner-')
    with open(os.path.join(evidence_dir, 'evidence.json'), 'w') as f:
        json.dump({'repo': 'MealPlanner', 'checks': checks, 'failures': failures}, f, indent=2)
    print('EVIDENCE_DIR=' + evidence_dir)
    print('FAILURES=%d' % len(failures))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())

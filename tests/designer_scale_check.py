"""Repeatable 100/150/200 percent Qt layout checks without changing Windows."""
from pathlib import Path
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
reports=ROOT/'build/checks/designer-ui';reports.mkdir(parents=True,exist_ok=True)
failed=False
for scale in ('1','1.5','2'):
    environment=dict(os.environ,QT_SCALE_FACTOR=scale,QT_QPA_PLATFORM='offscreen',WETTERSTATION_TEST_DPR=scale)
    result=subprocess.run([sys.executable,str(ROOT/'tests/designer_ui_check.py')],cwd=ROOT,env=environment,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (reports/f'ui-{scale}.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    print(f'Qt {scale}: '+('bestanden' if result.returncode==0 else 'FEHLER'))
    failed=failed or result.returncode!=0
sys.exit(int(failed))

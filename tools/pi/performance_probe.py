"""Read-only bounded Linux probe; writes no files and triggers no application calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time


def sample(root):
    result={}
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        try:
            args=(process/'cmdline').read_bytes().split(b'\0')
            if not any(a in (b'app.py',b'wetterstation') or a.endswith(b'/app.py') for a in args[1:]):continue
            if (process/'cwd').resolve()!=root:continue
            fields=(process/'stat').read_text().rsplit(')',1)[1].split()
            status=(process/'status').read_text().splitlines()
            io={line.split(':')[0]:int(line.split(':')[1]) for line in (process/'io').read_text().splitlines()}
            result[process.name]={'ticks':int(fields[11])+int(fields[12]),'start':fields[19],
                'threads':int(fields[17]),'rss_kib':next((int(row.split()[1]) for row in status if row.startswith('VmRSS:')),0),
                'write_bytes':io['write_bytes'],'write_calls':io['syscw'],
                'mode':'widget-demo' if b'--widget-demo' in args else 'mock-preview' if b'--mock-preview' in args else 'normal'}
        except (OSError,ValueError,KeyError):continue
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--seconds',type=int,default=10)
    args=parser.parse_args()
    if not 1<=args.seconds<=60:raise ValueError('Sample must be 1..60 seconds')
    root=args.root.resolve()
    names=('wetterstation/ui/app.py','wetterstation/ui/dashboard.py','wetterstation/lifecycle.py',
           'wetterstation/mobile/mobile_settings.py','wetterstation/designer/runtime.py')
    report={'source_hashes':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() if (root/name).is_file() else None for name in names}}
    path=root/'private/settings.json'
    if path.is_file():
        layout=json.loads(path.read_text()).get('dashboard')
        report['layout_sha256']=hashlib.sha256(json.dumps(layout,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        report['layout_version']=layout.get('version',2) if isinstance(layout,dict) else 2
    before=sample(root);start=time.monotonic();time.sleep(args.seconds);elapsed=time.monotonic()-start;after=sample(root)
    report.update(seconds=round(elapsed,3),processes=[])
    for pid,row in after.items():
        prior=before.get(pid)
        if not prior or prior['start']!=row['start']:continue
        report['processes'].append({'pid':pid,'mode':row['mode'],'cpu_one_core_percent':round((row['ticks']-prior['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed*100,2),
            'rss_kib':row['rss_kib'],'threads':row['threads'],'write_calls':row['write_calls']-prior['write_calls'],
            'write_bytes':row['write_bytes']-prior['write_bytes']})
    print(json.dumps(report))


if __name__=='__main__':main()

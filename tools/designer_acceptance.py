"""Freeze sources, run the offline gate and build the same public Pi package."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime,timezone
import shutil

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.windows.updater import snapshot
from tools.pi import update
from tools.dev_paths import scratch_root


def main():
    checks=ROOT/'build/checks';checks.mkdir(parents=True,exist_ok=True)
    frozen=Path(tempfile.mkdtemp(prefix='designer-frozen-',dir=scratch_root()))
    hashes=snapshot(ROOT,frozen)
    manifest={'root':str(frozen),'source_hashes':hashes,'tests':'not-run','package':'not-built'}
    output=checks/'designer-acceptance.json'
    update.atomic_bytes(output,update.json_bytes(manifest))
    report=checks/'designer-frozen-tests.txt'
    with (checks/'designer-frozen-console.txt').open('w',encoding='utf-8') as stream:
        tested=subprocess.run([sys.executable,str(frozen/'tools/offline_tests.py'),'--report',str(report)],cwd=frozen,stdout=stream,stderr=subprocess.STDOUT)
    manifest['tests']='passed' if tested.returncode==0 else 'failed'
    if tested.returncode:
        update.atomic_bytes(output,update.json_bytes(manifest));print('Eingefrorene Offline-Prüfung fehlgeschlagen. Bericht: '+str(report));return 1
    # Packaging uses exactly the frozen, tested files and never reads settings.
    release=datetime.now(timezone.utc).strftime('%Y-%m-%d-optimization-%H%M%S')
    ready=update.build(frozen,release,keep_layout=True)
    archive=frozen/ready['archive'];update.verify_archive(archive,ready['sha256'])
    with zipfile.ZipFile(archive) as bundle:
        for name in update.FILES:
            if name.endswith('.ttf'):
                if bundle.read(name)!=(frozen/name).read_bytes():raise ValueError('Schrift wurde beim Paketbau verändert.')
    manifest.update(package=str(archive),package_sha256=ready['sha256'],fonts='byte-identical',no_private_files=True)
    destination=ROOT/ready['archive'];destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():raise ValueError('Paketkennung bereits vorhanden.')
    shutil.copy2(archive,destination)
    update.atomic_bytes(destination.with_suffix('.zip.sha256'),(ready['sha256']+'  '+destination.name+'\n').encode(),0o644)
    update.atomic_bytes(destination.parent/'optimization-ready.json',update.json_bytes(ready),0o644)
    manifest['retained_package']=str(destination)
    # Source changes after freezing are reported instead of conflating versions.
    manifest['source_unchanged']=all(update.digest((ROOT/name).read_bytes())==sha for name,sha in hashes.items())
    update.atomic_bytes(output,update.json_bytes(manifest))
    print('Eingefrorene Offline-Prüfung und Paketprüfung bestanden. Keine Pi-Verbindung.')
    print('Beleg: '+str(output));return 0


if __name__=='__main__':sys.exit(main())

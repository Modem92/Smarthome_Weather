"""Explicit, reversible maintenance. Default: inspection only; private is untouched."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import stat
import time
from datetime import datetime, timezone
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.dev_paths import local_root


def hashes(folder):
    if folder.is_symlink():raise ValueError('Verknüpfter Ordner: Bereinigung angehalten.')
    result={}
    for path in folder.rglob('*'):
        if path.is_symlink():raise ValueError('Verknüpfte Datei: Bereinigung angehalten.')
        if path.is_file():result[path.relative_to(folder).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def remove_build_tree(root,path):
    if path.is_symlink() or not path.resolve().is_relative_to((root/'build').resolve()):
        raise ValueError('Unsicheres Bereinigungsziel.')
    def retry(function,name,error):
        # Packaged fixtures may have the Windows read-only attribute. Never
        # change ACLs, and only retry paths already checked under build/.
        candidate=Path(name)
        if not candidate.resolve().is_relative_to(path.resolve()):raise error
        candidate.chmod(stat.S_IREAD|stat.S_IWRITE)
        for attempt in range(5):
            try:function(name);return
            except PermissionError:
                if attempt==4:raise
                time.sleep(.2)
    shutil.rmtree(path,onexc=retry)


def runtime_check(folder):
    environment=dict(os.environ,PYTHONPATH=str(folder),QT_QPA_PLATFORM='offscreen')
    code='from PySide6.QtWidgets import QApplication; app=QApplication([]); print("Designer runtime OK")'
    result=subprocess.run([sys.executable,'-B','-c',code],env=environment,capture_output=True,text=True,timeout=30)
    if result.returncode:raise ValueError('Designer-Startprüfung fehlgeschlagen; alte Laufzeit bleibt erhalten.')


def migrate_runtime(root,target,check=runtime_check):
    source=root/'build/designer-runtime'
    if not source.exists():return 'already external or absent'
    if source.is_symlink() or not source.resolve().is_relative_to((root/'build').resolve()) or target.is_symlink():raise ValueError('Unsicherer Laufzeitpfad.')
    expected=hashes(source)
    if target.resolve().is_relative_to(root.resolve()):raise ValueError('Laufzeit muss außerhalb des Projekts liegen.')
    if target.exists():
        if hashes(target)!=expected:raise ValueError('Abweichende externe Laufzeit: nichts überschrieben.')
    else:
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(source,target)
    if hashes(target)!=expected:raise ValueError('Kopie der Laufzeit nicht vollständig.')
    check(target)
    # Deletion is a separate, guarded step after archiving all old build outputs.
    return 'copied and verified'


def candidates(root):
    checks=root/'build/checks'
    known={'designer-phone','designer-starter-isolated','designer-ui','designer-v4-starter',
           'display-check','international-check','update-states','widget-check'}
    return sorted((p for p in checks.iterdir() if p.is_dir() and
                   (p.name in known or p.name.startswith('designer-frozen-'))),key=lambda p:p.name) if checks.exists() else []


def archive_outputs(root,paths):
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to((root/'build').resolve()):raise ValueError('Unsicheres Bereinigungsziel.')
    before={str(p.relative_to(root)):hashes(p) for p in paths}
    output=root/'archive'/('optimization-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.zip')
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as bundle:
        for prefix,items in before.items():
            for name in items:bundle.write(root/prefix/name,(Path(prefix)/name).as_posix())
        bundle.writestr('maintenance-manifest.json',json.dumps(before,sort_keys=True))
    with zipfile.ZipFile(output) as bundle:
        for prefix,items in before.items():
            for name,sha in items.items():
                if hashlib.sha256(bundle.read((Path(prefix)/name).as_posix())).hexdigest()!=sha:raise ValueError('Archivprüfung fehlgeschlagen.')
    # Validate every target and its unchanged contents before the first removal.
    for p in paths:
        if not p.resolve().is_relative_to((root/'build').resolve()) or p.is_symlink():raise ValueError('Unsicheres Bereinigungsziel.')
        if hashes(p)!=before[str(p.relative_to(root))]:raise ValueError('Prüfausgaben wurden inzwischen verändert.')
    for p in paths:remove_build_tree(root,p)
    return output


def resume_archive(root,archive):
    archive=archive.resolve()
    if archive.parent!=(root/'archive').resolve():raise ValueError('Archiv außerhalb des Projektarchivs.')
    with zipfile.ZipFile(archive) as bundle:
        manifest=json.loads(bundle.read('maintenance-manifest.json'))
        remaining=[]
        for prefix,items in manifest.items():
            folder=root/prefix
            if not folder.exists():continue
            if not folder.resolve().is_relative_to((root/'build/checks').resolve()):raise ValueError('Unsicherer Archivpfad.')
            for name,sha in hashes(folder).items():
                if items.get(name)!=sha or hashlib.sha256(bundle.read((Path(prefix)/name).as_posix())).hexdigest()!=sha:
                    raise ValueError('Archiv oder verbliebene Ausgabe verändert.')
            remaining.append(folder)
    for folder in remaining:remove_build_tree(root,folder)


def prune_packages(root,keep=2):
    packages=sorted((root/'build/pi').glob('Wetterstation-Pi-Update-*.zip'),key=lambda p:p.stat().st_mtime_ns,reverse=True)
    for package in packages:
        with zipfile.ZipFile(package) as bundle:
            manifest=json.loads(bundle.read('MANIFEST.json'))
            for entry in manifest['files']:
                data=bundle.read(entry['path'])
                if len(data)!=entry['size'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:
                    raise ValueError('Paketprüfung fehlgeschlagen; keine Pakete entfernt.')
    output=root/'archive/retired-pi-packages'
    for package in packages[keep:]:
        output.mkdir(parents=True,exist_ok=True)
        related=[package,*package.parent.glob(package.name+'.sha256'),*package.parent.glob(package.stem+'-INHALT.json')]
        for source in related:
            target=output/source.name;data=source.read_bytes()
            if target.exists():
                if target.read_bytes()!=data:raise ValueError('Abweichendes archiviertes Paket.')
            else:shutil.copy2(source,target)
            if target.read_bytes()!=data or source.read_bytes()!=data:raise ValueError('Paketarchiv nicht bestätigt.')
            source.unlink()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--resume-archive',type=Path)
    parser.add_argument('--retire-runtime',action='store_true')
    parser.add_argument('--prune-packages',action='store_true')
    args=parser.parse_args()
    target=local_root()/'designer-runtime'
    paths=candidates(ROOT)
    print(json.dumps({'runtime_source':str(ROOT/'build/designer-runtime'),'runtime_target':str(target),
                      'archive_then_remove':[str(p.relative_to(ROOT)) for p in paths],
                      'private_changes':False,'apply':args.apply},ensure_ascii=False,indent=2))
    if args.apply:
        print(migrate_runtime(ROOT,target))
        if args.resume_archive:resume_archive(ROOT,args.resume_archive)
        elif paths:print('Geprüftes Archiv: '+str(archive_outputs(ROOT,paths)))
        if args.retire_runtime:
            source=ROOT/'build/designer-runtime'
            if source.exists():
                if sys.platform=='win32':
                    tasks=subprocess.run(['tasklist','/m','Qt6Core.dll','/fo','csv','/nh'],capture_output=True,text=True,check=True)
                    if any('python' in line.lower() for line in tasks.stdout.splitlines()):raise ValueError('Qt-Anwendung läuft noch; alte Laufzeit bleibt erhalten.')
                if hashes(source)!=hashes(target):raise ValueError('Laufzeit inzwischen verändert.')
                remove_build_tree(ROOT,source)
        else:print('Alte Laufzeit bleibt bis zur gesonderten Start-/Prozessprüfung erhalten.')
        if args.prune_packages:prune_packages(ROOT)


if __name__=='__main__':main()

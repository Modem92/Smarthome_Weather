"""Explicit design-only Pi transactions; no program restart and no weather calls."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from wetterstation.designer.storage import DesignStore,atomic,json_bytes,read_json
from wetterstation.designer.series import capacity,requirements
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.storage.file_io import SettingsFileLock
from wetterstation.ui.widgets import revision


def safe(root,path):
    root=Path(root).resolve();candidate=root/path
    if not candidate.resolve().is_relative_to(root):raise ValueError('Unsicherer Gestaltungspfad.')
    return candidate


def check(root):
    root=Path(root)
    if not root.is_absolute() or root.is_symlink() or not (root/'app.py').is_file():raise ValueError('Bestehende Wetterstation nicht gefunden.')
    if (root/'private').is_symlink() or (root/'private/settings.json').is_symlink():raise ValueError('Unsicherer privater Zielpfad.')
    if (root/'.pi-update-in-progress.json').exists():raise ValueError('Programmupdate läuft; Gestaltung bitte später übertragen.')
    return root.resolve()


def status(root,probe=None):
    root=check(root);settings=ApiKeyStore(root/'private/settings.json');document=settings.load_dashboard()
    from tools.pi.update import running_processes
    pids=(probe or running_processes)(root)
    demo=False;session=None
    if pids:
        try:
            session=read_json(root/'.wetterstation-session.json',16000)
            demo='--widget-demo' in session.get('args',[])
        except (OSError,ValueError):pass
    ack=None
    try:
        candidate=read_json(safe(root,'private/designer/display-ack.json'),16000)
        if (session and session.get('ready') is True and session.get('pid') in pids and
                candidate.get('pid')==session.get('pid') and candidate.get('nonce')==session.get('nonce') and
                candidate.get('revision')==revision(document) and not demo):ack=candidate
    except (OSError,ValueError):pass
    from wetterstation.designer.activation import ActivationStore
    timelines={'state':ActivationStore(root/'private/designer').state(document),
               'estimate':capacity(document),'requirements':requirements(document),
               'design_supported':document.get('version') in (3,4)}
    return {'schema':1,'supported':4,'transfer_protocol':2,'revision':revision(document),'running':bool(pids),'demo':demo,'display':ack,'timelines':timelines}


def configure_timelines(root,enabled,expected):
    from wetterstation.designer.activation import ActivationStore
    root=check(root)
    with SettingsFileLock(root.parent/'.Wetterstation-deploy.lock'):
        ActivationStore(root/'private/designer').configure(ApiKeyStore(root/'private/settings.json'),enabled,expected)
    return status(root)


def staging(root,token):
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{32}',token):raise ValueError('Ungültige Übertragungskennung.')
    return safe(root,'private/designer/incoming/'+token)


def prepare(root,expected):
    root=check(root);current=status(root)
    if current['revision']!=expected:raise ValueError('Pi-Gestaltung wurde inzwischen geändert. Bitte erneut prüfen.')
    token=uuid.uuid4().hex;folder=staging(root,token)
    atomic(folder/'transaction.json',json_bytes({'schema':1,'expected_revision':expected,'created_at':datetime.now(timezone.utc).isoformat(),'state':'prepared'}))
    return {'token':token,'destination':str(folder/'design.wetterdesign'),'upload':str(folder/'.upload.wetterdesign')}


def package_digest(path):
    path=Path(path)
    if path.stat().st_size>140_000_000:raise ValueError('Übertragenes Paket ist zu groß.')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(root,token,sha):
    root=check(root);folder=staging(root,token)
    if not re.fullmatch('[0-9a-f]{64}',sha):raise ValueError('Ungültige Paketprüfsumme.')
    with SettingsFileLock(root.parent/'.Wetterstation-deploy.lock'):
        record=read_json(folder/'transaction.json',16000)
        if record.get('sha256') not in (None,sha):raise ValueError('Die Übertragungskennung gehört zu einem anderen Paket.')
        if record.get('state') in ('restored','cancelled'):raise ValueError('Diese Übertragung ist bereits beendet.')
        if record.get('state')=='applied':return record
        final=folder/'design.wetterdesign';upload=folder/'.upload.wetterdesign'
        if not final.exists() or package_digest(final)!=sha:
            if not upload.is_file() or package_digest(upload)!=sha:raise ValueError('Upload ist unvollständig.')
            os.replace(upload,final)
        record.update(state='staged',sha256=sha)
        atomic(folder/'transaction.json',json_bytes(record))
        return record


def transaction(root,token,sha):
    root=check(root);folder=staging(root,token)
    with SettingsFileLock(root.parent/'.Wetterstation-deploy.lock'):
        check(root);record=read_json(folder/'transaction.json',16000)
        if record.get('sha256') not in (None,sha):raise ValueError('Paket gehört nicht zu dieser Übertragungskennung.')
        if record.get('state')=='applied':return record
        if record.get('state') in ('restored','cancelled'):raise ValueError('Beendete Übertragung darf nicht erneut angewendet werden.')
        package=folder/'design.wetterdesign'
        if package_digest(package)!=sha:raise ValueError('Übertragenes Paket ist unvollständig.')
        store=DesignStore(folder/'verified');document=store.import_package(package)
        if not capacity(document)['fits']:raise ValueError('Zeitreihen passen nicht in das Tagesbudget.')
        settings=ApiKeyStore(root/'private/settings.json')
        backup=store.apply(document,settings,record['expected_revision'])
        record.update(state='applied',revision=revision(document),backup=str(backup),sha256=sha)
        atomic(folder/'transaction.json',json_bytes(record))
        return record


def inspect_transaction(root,token):
    root=check(root);folder=staging(root,token);record=read_json(folder/'transaction.json',16000);current=status(root)
    # A lost response after atomic settings replacement is resolved by revision.
    if record.get('state') in ('prepared','staged') and (folder/'verified').exists():
        try:
            package=folder/'design.wetterdesign';store=DesignStore(folder/'verified');document=store.import_package(package)
            if revision(document)==current['revision']:
                record.update(state='applied',revision=current['revision'],sha256=package_digest(package))
                for backup in sorted((folder/'verified/backups').glob('*'),reverse=True):
                    try:
                        if revision(read_json(backup/'design.json'))==record['expected_revision']:
                            record['backup']=str(backup);break
                    except (OSError,ValueError):pass
                atomic(folder/'transaction.json',json_bytes(record))
        except (OSError,ValueError):pass
    package_sha=None
    if (folder/'design.wetterdesign').is_file():package_sha=package_digest(folder/'design.wetterdesign')
    return {'transaction':record,'current':current,'package_sha256':package_sha}


def cancel(root,token):
    root=check(root);folder=staging(root,token)
    with SettingsFileLock(root.parent/'.Wetterstation-deploy.lock'):
        record=read_json(folder/'transaction.json',16000)
        # Serializes against an in-flight apply. A queued old apply observes the
        # cancelled state after acquiring this same lock and must refuse it.
        if record.get('state') not in ('applied','restored'):
            record.update(state='cancelled')
            atomic(folder/'transaction.json',json_bytes(record))
        return record


def restore(root,token,expected):
    root=check(root);folder=staging(root,token)
    with SettingsFileLock(root.parent/'.Wetterstation-deploy.lock'):
        record=read_json(folder/'transaction.json',16000)
        backup=Path(record.get('backup',''))
        if not backup.is_absolute() or not backup.resolve().is_relative_to(root/'private/designer'):
            raise ValueError('Sicherung ist nicht eindeutig zugeordnet.')
        previous,new_backup=DesignStore(root/'private/designer').restore(backup,ApiKeyStore(root/'private/settings.json'),expected)
        record.update(state='restored',revision=revision(previous),restore_backup=str(new_backup))
        atomic(folder/'transaction.json',json_bytes(record))
        return record


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status');p=sub.add_parser('prepare');p.add_argument('--revision',required=True)
    for name in ('timeline-enable','timeline-disable'):
        p=sub.add_parser(name);p.add_argument('--revision',required=True)
    p=sub.add_parser('apply');p.add_argument('--token',required=True);p.add_argument('--sha',required=True)
    p=sub.add_parser('seal');p.add_argument('--token',required=True);p.add_argument('--sha',required=True)
    p=sub.add_parser('inspect');p.add_argument('--token',required=True)
    p=sub.add_parser('cancel');p.add_argument('--token',required=True)
    p=sub.add_parser('restore');p.add_argument('--token',required=True);p.add_argument('--revision',required=True)
    args=parser.parse_args()
    try:
        if args.command=='status':result=status(args.root)
        elif args.command in ('timeline-enable','timeline-disable'):
            result=configure_timelines(args.root,args.command=='timeline-enable',args.revision)
        elif args.command=='prepare':result=prepare(args.root,args.revision)
        elif args.command=='apply':result=transaction(args.root,args.token,args.sha)
        elif args.command=='seal':result=seal(args.root,args.token,args.sha)
        elif args.command=='cancel':result=cancel(args.root,args.token)
        elif args.command=='restore':result=restore(args.root,args.token,args.revision)
        else:result=inspect_transaction(args.root,args.token)
        print(json.dumps({'ok':True,'result':result}))
    except Exception:
        # No arbitrary remote paths, settings, URLs or credentials in diagnostics.
        print(json.dumps({'ok':False,'error':'Gestaltung nicht bestätigt. Kompatibilität, Versionskonflikt, Speicher und Übertragungsstand prüfen.'}))
        return 1
    return 0


if __name__=='__main__':sys.exit(main())

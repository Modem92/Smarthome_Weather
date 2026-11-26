"""Durable design-only transfer orchestration; no Qt and no automatic connection."""
import hashlib
import json
import re
from pathlib import Path
import time

from wetterstation.designer.model import validate
from wetterstation.designer.series import capacity
from wetterstation.designer.storage import atomic,json_bytes,read_json
from wetterstation.paths import project_root
from wetterstation.ui.widgets import revision


class Transfer:
    def __init__(self,document,store,root=None,remote=None):
        self.document=validate(document);self.store=store;self.root=Path(root or project_root());self.token=None;self.expected=None;self.result=None
        self.record=None;self.journal=self.store.folder/'transfer.json'
        if remote is None:
            from tools.windows.updater import configuration,run_remote
            self.config,self.public=configuration(self.root)
            self.remote=lambda arguments,**kw:run_remote(self.config,self.public,arguments,**kw)
            self.target='/home/'+self.config['user']+'/'+self.config['relative_target']
            self.endpoint=self.config['user']+'@'+self.config['host']+':'+self.target
        else:self.remote=remote;self.target='/home/pi/wetterstation/Wetterstation'
        if remote is not None:self.endpoint='simulated:'+self.target
        try:
            saved=read_json(self.journal,16000)
            if (not isinstance(saved,dict) or set(saved)!={'schema','endpoint','token','expected_revision','design_revision','state','sha256'} or
                    saved.get('schema')!=1 or not isinstance(saved.get('token'),str) or not re.fullmatch('[0-9a-f]{32}',saved['token']) or
                    not isinstance(saved.get('endpoint'),str) or len(saved['endpoint'])>2048 or
                    any(not isinstance(saved.get(key),str) or not re.fullmatch('[0-9a-f]{64}',saved[key]) for key in ('expected_revision','design_revision')) or
                    saved.get('state') not in ('prepared','staged','applied','restored','cancelled','superseded','unknown') or
                    (saved.get('sha256') is not None and (not isinstance(saved['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',saved['sha256'])))):
                raise ValueError('Gespeicherte Übertragungskennung ist beschädigt. Übertragungsstand zuerst prüfen.')
            if saved.get('endpoint')==self.endpoint and saved.get('design_revision')==revision(self.document) and saved['state']!='superseded':
                self.record=saved;self.token=saved['token'];self.expected=saved['expected_revision']
        except FileNotFoundError:pass

    def remember(self,**fields):
        self.record.update(fields)
        atomic(self.journal,json_bytes(self.record))

    def package(self):
        if not self.token or not re.fullmatch('[0-9a-f]{32}',self.token):raise ValueError('Übertragungskennung fehlt.')
        package=self.store.folder/'transfer-packages'/(self.token+'.wetterdesign')
        sha=self.record.get('sha256')
        if sha is None:
            self.store.export(self.document,package);sha=hashlib.sha256(package.read_bytes()).hexdigest();self.remember(sha256=sha)
        elif not package.is_file() or hashlib.sha256(package.read_bytes()).hexdigest()!=sha:
            raise ValueError('Das lokale Übertragungspaket fehlt oder wurde verändert. Pi-Stand prüfen; kein erneuter Export unter derselben Kennung.')
        return package,sha

    def call(self,*arguments):
        result=self.remote(['python3',self.target+'/tools/pi/design.py','--root',self.target,*arguments])
        try:
            value=json.loads(result.stdout if hasattr(result,'stdout') else result)
            if value.get('ok') is not True:raise ValueError
            return value['result']
        except (ValueError,TypeError,KeyError):raise ValueError('Pi unterstützt die Gestaltung noch nicht oder hat den Vorgang abgewiesen. Programmstand und Verbindung prüfen.') from None

    def inspect(self):
        value=self.call('inspect','--token',self.token) if self.token else {'current':self.call('status')}
        current=value['current']
        if current.get('supported',0)<self.document['version'] or current.get('transfer_protocol')!=2:raise ValueError('Pi benötigt zuerst den aktuellen Programmstand über den manuellen Updater.')
        if self.record is not None:self.remember(state=value.get('transaction',{}).get('state','unknown'))
        else:self.expected=current['revision']
        self.result=value;return value

    def start_new(self):
        if self.token:
            self.inspect()
            self.call('cancel','--token',self.token)
            self.remember(state='superseded')
        self.token=None;self.record=None;self.expected=None;self.result=None
        return self.inspect()

    def send(self,notify=lambda message:None):
        observed=None
        if self.token:
            notify('Vorherigen Übertragungsstand prüfen …');observed=self.inspect()
            transaction=observed.get('transaction',{})
            if transaction.get('state')=='applied':
                if transaction.get('revision')!=revision(self.document) or observed['current']['revision']!=transaction['revision']:
                    raise ValueError('Die Pi-Gestaltung wurde nach dieser Übertragung geändert. Aktuellen Stand prüfen.')
                return observed
            if transaction.get('state')=='restored':
                self.token=None;self.expected=observed['current']['revision'];self.record=None;observed=None
            elif transaction.get('state')=='cancelled':
                raise ValueError('Diese Übertragung ist beendet. Bitte eine neue Übertragung vorbereiten.')
            elif observed['current']['revision']!=transaction.get('expected_revision'):
                raise ValueError('Die Pi-Gestaltung wurde inzwischen geändert. Offene Übertragung wird nicht wiederholt.')
        if not capacity(self.document)['fits']:raise ValueError('Zeitreihen passen nicht in das Tagesbudget.')
        self.store.check_assets(self.document)
        if not self.token:
            if self.expected is None:self.inspect()
            notify('Pi-Gestaltung und Speicher vorbereiten …');prepared=self.call('prepare','--revision',self.expected);self.token=prepared['token']
            if not re.fullmatch('[0-9a-f]{32}',self.token) or prepared.get('destination')!=self.target+'/private/designer/incoming/'+self.token+'/design.wetterdesign' or prepared.get('upload')!=self.target+'/private/designer/incoming/'+self.token+'/.upload.wetterdesign':
                raise ValueError('Unerwartetes Übertragungsziel wurde abgewiesen.')
            self.record={'schema':1,'endpoint':self.endpoint,'token':self.token,'expected_revision':self.expected,'design_revision':revision(self.document),'state':'prepared','sha256':None}
            self.remember()
        package,sha=self.package()
        if not observed or observed.get('package_sha256')!=sha:
            notify('Entwurf, Bilder und Schriften übertragen …')
            self.remote([package,self.target+'/private/designer/incoming/'+self.token+'/.upload.wetterdesign'],copy=True,timeout=120)
        notify('Vollständigkeit prüfen und Paket atomar bereitstellen …');self.call('seal','--token',self.token,'--sha',sha)
        self.remember(state='staged')
        notify('Sichern und Gestaltung atomar übernehmen …');self.call('apply','--token',self.token,'--sha',sha)
        notify('Bestätigung der Anzeige abwarten …')
        for attempt in range(15):
            observed=self.inspect();current=observed['current'];ack=current.get('display')
            if not current['running'] or current.get('demo') or (ack and ack.get('revision')==revision(self.document)):return observed
            time.sleep(1)
        return observed


def result_message(value):
    current=value['current'];tx=value.get('transaction',{})
    if tx.get('state')=='restored':return 'Vorherige Gestaltung wiederhergestellt. Anwendungsmodus und private Daten bleiben erhalten.'
    if tx.get('state')=='cancelled':return 'Offene Übertragung beendet. Eine neue Übertragung kann vorbereitet werden.'
    if tx.get('state') in ('prepared','staged'):return 'Offene Übertragung zugeordnet. Das geprüfte Paket kann unter derselben Kennung fortgesetzt werden.'
    if tx.get('state')!='applied':return 'Pi-Stand geprüft. Bereit zur Übertragung.'
    if current['revision']!=tx.get('revision'):return 'Die Pi-Gestaltung wurde seit dieser Übertragung geändert. Der aktuelle Stand wird nicht überschrieben.'
    if not current['running']:return 'Gestaltung gespeichert. Anzeige ist geschlossen und bleibt geschlossen.'
    if current.get('demo'):return 'Gestaltung gespeichert. Die laufende Demo verwendet ihren eigenen temporären Entwurf.'
    if current.get('display') and current['display']['revision']==tx.get('revision'):return 'Gestaltung gespeichert und von der Anzeige bestätigt.'
    return 'Gestaltung gespeichert. Übernahme durch die Anzeige noch nicht bestätigt; bitte Stand erneut prüfen.'



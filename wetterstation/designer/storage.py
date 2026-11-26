"""Atomic drafts and content-addressed, credential-free design packages."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile

from PIL import Image, ImageFont, ImageOps
from wetterstation.storage.file_io import replace_file
from wetterstation.ui.widgets import revision, LayoutConflict
from wetterstation.designer.model import validate, from_layout


def atomic(path, data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.design-',delete=False) as stream:
            temporary=Path(stream.name);stream.write(data);stream.flush();os.fsync(stream.fileno())
        if os.name!='nt':temporary.chmod(0o600)
        replace_file(temporary,path)
    finally:
        if temporary:temporary.unlink(missing_ok=True)


def json_bytes(value):
    return (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')


def read_json(path,limit=8_000_000):
    if Path(path).stat().st_size>limit:raise ValueError('Gestaltungsdatei ist zu groß.')
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def verify_asset(name,data):
    if len(data)>32_000_000 or hashlib.sha256(data).hexdigest()!=name.split('.')[0]:
        raise ValueError('Dateiprüfsumme oder Dateigröße ungültig.')
    suffix=name.rsplit('.',1)[-1]
    if suffix in ('ttf','otf'):
        ImageFont.truetype(io.BytesIO(data),16)
    elif suffix in ('png','jpg','webp'):
        with Image.open(io.BytesIO(data)) as image:
            if image.width*image.height>20_000_000:raise ValueError('Bild ist zu groß.')
            image.verify()
    else:raise ValueError('Unbekannte Dateiart.')


def asset_references(document):
    refs=set()
    def walk(value):
        if isinstance(value,dict):
            for k,v in value.items():
                if k in ('image','asset','font') and isinstance(v,str) and '.' in v:refs.add(v)
                walk(v)
        elif isinstance(value,list):
            for v in value:walk(v)
    walk(document)
    return refs


class DesignStore:
    def __init__(self, folder):
        self.folder=Path(folder)
        self.assets=self.folder/'assets'

    def add_asset(self,path,document):
        path=Path(path)
        if path.stat().st_size>32_000_000:raise ValueError('Die Datei ist zu groß.')
        data=path.read_bytes();suffix=path.suffix.lower().lstrip('.')
        if suffix not in ('ttf','otf'):
            with Image.open(io.BytesIO(data)) as image:
                if image.width*image.height>20_000_000:raise ValueError('Bild ist zu groß.')
                image=ImageOps.exif_transpose(image).convert('RGBA')
                out=io.BytesIO();image.save(out,format='PNG');data=out.getvalue();suffix='png'
        name=hashlib.sha256(data).hexdigest()+'.'+suffix
        verify_asset(name,data)
        result=deepcopy(document);result['assets'][name]={'name':path.name,'size':len(data)}
        validate(result)
        atomic(self.assets/name,data)
        return result,name

    def check_assets(self,document):
        if not asset_references(document)<=set(document['assets']):
            raise ValueError('Im Entwurf fehlen verwendete Bilder oder Schriften.')
        total=0
        for name,meta in document['assets'].items():
            data=(self.assets/name).read_bytes();total+=len(data)
            if len(data)!=meta['size'] or total>128_000_000:raise ValueError('Ungültige Dateigrößen.')
            verify_asset(name,data)

    def save_draft(self,document,base_revision):
        # Conflicted grid proposals may be recovered, but never applied/exported.
        validate(document,collisions=False)
        atomic(self.folder/'draft.json',json_bytes({'schema':1,'base_revision':base_revision,'design':document}))

    def load_draft(self):
        try:value=read_json(self.folder/'draft.json',8_500_000)
        except FileNotFoundError:return None
        if not isinstance(value,dict) or set(value)!={'schema','base_revision','design'} or value['schema']!=1 or not isinstance(value['base_revision'],str):
            raise ValueError('Der gesicherte Entwurf ist beschädigt.')
        validate(value['design'],collisions=False)
        return value

    def export(self,document,path):
        document=validate(document);self.check_assets(document)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('design.json',json_bytes(document))
            for name in document['assets']:archive.writestr('assets/'+name,(self.assets/name).read_bytes())
        atomic(path,stream.getvalue())

    def import_package(self,path):
        try:return self._import_package(path)
        except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,RecursionError,Image.DecompressionBombError):
            raise ValueError('Das Gestaltungspaket ist beschädigt oder enthält ungültige Daten.') from None

    def _import_package(self,path):
        if Path(path).stat().st_size>140_000_000:raise ValueError('Paket ist zu groß.')
        if not zipfile.is_zipfile(path):raise ValueError('Die Datei ist kein gültiges Gestaltungspaket.')
        with zipfile.ZipFile(path) as archive:
            infos=archive.infolist();names=[i.filename for i in infos]
            if len(names)!=len(set(names)) or len(names)>513 or 'design.json' not in names or sum(i.file_size for i in infos)>136_000_000:
                raise ValueError('Ungültiges Gestaltungspaket.')
            for info in infos:
                if info.file_size>(8_000_000 if info.filename=='design.json' else 32_000_000) or ((info.external_attr>>16)&0o170000)==0o120000:
                    raise ValueError('Ungültiger Paketeintrag.')
            document=validate(json.loads(archive.read('design.json')))
            expected={'design.json',*('assets/'+name for name in document['assets'])}
            if set(names)!=expected:raise ValueError('Paket enthält unerwartete oder fehlende Dateien.')
            payloads={}
            for name,meta in document['assets'].items():
                data=archive.read('assets/'+name);verify_asset(name,data)
                if len(data)!=meta['size']:raise ValueError('Dateigröße stimmt nicht.')
                payloads[name]=data
        # Validate everything before writing even a content-addressed asset.
        if not asset_references(document)<=set(payloads):raise ValueError('Verwendete Datei fehlt.')
        for name,data in payloads.items():atomic(self.assets/name,data)
        return document

    def apply(self,document,settings,expected_revision):
        document=validate(document);self.check_assets(document)
        # save_dashboard repeats the revision check under the settings lock.
        current=settings.load_dashboard()
        if revision(current)!=expected_revision:raise LayoutConflict('Aktive Gestaltung wurde inzwischen geändert. Bitte neu laden.')
        backup=self.snapshot(current,settings)
        active=DesignStore(settings.path.parent/'designer')
        for name in document['assets']:
            if self.assets.resolve()!=active.assets.resolve():atomic(active.assets/name,(self.assets/name).read_bytes())
        settings.save_dashboard(document,expected_revision)
        return backup

    def snapshot(self,document,settings):
        backup=self.folder/'backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        active=DesignStore(settings.path.parent/'designer')
        if document.get('version') in (3,4):
            active.check_assets(document)
            for name in document['assets']:atomic(backup/'assets'/name,(active.assets/name).read_bytes())
        atomic(backup/'design.json',json_bytes(document))
        return backup

    def restore(self,backup,settings,expected_revision):
        from wetterstation.ui.widgets import load_layout
        previous=load_layout(read_json(Path(backup)/'design.json'))
        if previous.get('version') in (3,4):DesignStore(backup).check_assets(previous)
        current=settings.load_dashboard()
        if revision(current)!=expected_revision:raise LayoutConflict('Gestaltung wurde inzwischen geändert. Bitte neu laden.')
        new_backup=self.snapshot(current,settings)
        if previous.get('version') in (3,4):
            active=DesignStore(settings.path.parent/'designer')
            for name in previous['assets']:atomic(active.assets/name,(Path(backup)/'assets'/name).read_bytes())
        settings.save_dashboard(previous,expected_revision)
        return previous,new_backup

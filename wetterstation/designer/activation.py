"""Explicit, device-local permission for extra requests; never contains secrets."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

from wetterstation.designer.series import requirements, capacity
from wetterstation.designer.storage import atomic, json_bytes, read_json


def device_binding():
    # Read existing OS identity only. Do not create or alter budget/device IDs.
    if os.name == 'nt':
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography',
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            identity = winreg.QueryValueEx(key, 'MachineGuid')[0]
    else:
        identity = Path('/etc/machine-id').read_text().strip()
    if not identity:raise ValueError('Gerätekennung nicht verfügbar.')
    return hashlib.sha256((identity+'|'+str(Path.home())).encode()).hexdigest()


def signature(document):
    return hashlib.sha256(json.dumps(requirements(document), sort_keys=True).encode()).hexdigest()


class ActivationStore:
    def __init__(self, folder, binding=None):
        self.path = Path(folder)/'timeline-activation.json'
        self.binding = binding or device_binding

    def state(self, document):
        try:
            value = read_json(self.path, 4000)
            if value.get('schema') != 1 or value.get('enabled') is not True:return 'off'
            if value.get('device') != self.binding():return 'other_device'
            if value.get('requirements') != signature(document):return 'changed'
            return 'on'
        except (OSError, ValueError, TypeError, AttributeError):return 'off'

    def configure(self, settings, enabled, expected_revision):
        from wetterstation.ui.widgets import revision
        with settings._update_lock():
            document = settings.load_dashboard()
            if revision(document) != expected_revision:
                raise ValueError('Gestaltung wurde inzwischen geändert. Bitte erneut prüfen.')
            if enabled and (document.get('version') not in (3,4) or not capacity(document)['fits']):
                raise ValueError('Aktive Gestaltung und Zeitreihenbudget zuerst prüfen.')
            atomic(self.path, json_bytes({'schema':1, 'enabled':bool(enabled),
                'device':self.binding(), 'requirements':signature(document),
                'activated_at':datetime.now(timezone.utc).isoformat()}))
        return self.state(document)


STATE_TEXT = {'on':'Zusatzabrufe auf diesem Gerät aktiviert', 'off':'Zusatzabrufe ausgeschaltet',
              'other_device':'Zusatzabrufe auf diesem Gerät noch nicht aktiviert',
              'changed':'Zeitreihenbedarf geändert: Zusatzabrufe erneut aktivieren'}

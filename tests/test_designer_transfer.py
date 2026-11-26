"""Durable client recovery through a fully local, simulated SSH endpoint."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from unittest.mock import patch

from wetterstation.designer import model
from wetterstation.designer.storage import DesignStore,atomic,json_bytes,read_json
from wetterstation.designer.transfer import Transfer
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.widgets import revision
from tools.pi import design as pi


class FakeRemote:
    def __init__(self,root,fail_copy=False,lose_apply=False,lose_seal=False):
        self.root=root;self.fail_copy=fail_copy;self.lose_apply=lose_apply;self.lose_seal=lose_seal;self.calls=[]

    def __call__(self,args,copy=False,timeout=None):
        if copy:
            self.calls.append('copy');token=str(args[1]).split('/')[-2]
            destination=pi.staging(self.root,token)/'.upload.wetterdesign';data=Path(args[0]).read_bytes()
            if self.fail_copy:
                self.fail_copy=False;atomic(destination,data[:len(data)//2]);raise OSError('simulated interrupted upload')
            atomic(destination,data);return ''
        command=args[4];self.calls.append(command);options=dict(zip(args[5::2],args[6::2]))
        if command=='status':result=pi.status(self.root)
        elif command=='prepare':
            result=pi.prepare(self.root,options['--revision'])
            wire=args[3]+'/private/designer/incoming/'+result['token']
            result.update(destination=wire+'/design.wetterdesign',upload=wire+'/.upload.wetterdesign')
        elif command=='inspect':result=pi.inspect_transaction(self.root,options['--token'])
        elif command=='cancel':result=pi.cancel(self.root,options['--token'])
        elif command=='seal':
            result=pi.seal(self.root,options['--token'],options['--sha'])
            if self.lose_seal:self.lose_seal=False;raise OSError('simulated lost seal response')
        elif command=='apply':
            result=pi.transaction(self.root,options['--token'],options['--sha'])
            if self.lose_apply:self.lose_apply=False;raise OSError('simulated lost apply response')
        else:raise AssertionError(command)
        return json.dumps({'ok':True,'result':result})


class TransferRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.root=Path(self.tmp.name).resolve()
        self.pi=self.root/'pi';self.pi.mkdir();(self.pi/'app.py').write_text('# isolated target')
        self.settings=ApiKeyStore(self.pi/'private/settings.json');self.settings.save_configuration('Testort','dummy-preserved-key',country_code='DE')
        self.old=self.settings.load_dashboard();self.doc=model.from_layout();self.doc['style']['radius']=0
        self.store=DesignStore(self.root/'pc');self.probe=patch('tools.pi.update.running_processes',return_value=[]);self.probe.start()

    def tearDown(self):self.probe.stop();self.tmp.cleanup()

    def test_partial_upload_survives_dialog_reopen_without_changing_active_layout(self):
        remote=FakeRemote(self.pi,fail_copy=True);first=Transfer(self.doc,self.store,remote=remote)
        with self.assertRaises(OSError):first.send()
        token=first.token;package,sha=first.package();self.assertEqual(self.settings.load_dashboard(),self.old)
        self.assertFalse((pi.staging(self.pi,token)/'design.wetterdesign').exists())
        reopened=Transfer(self.doc,self.store,remote=remote);self.assertEqual(reopened.token,token)
        result=reopened.send();self.assertEqual(result['transaction']['state'],'applied')
        self.assertEqual(remote.calls.count('prepare'),1);self.assertEqual(remote.calls.count('apply'),1)
        self.assertEqual(self.settings.load_dashboard(),self.doc);self.assertEqual(self.settings.load_api_key(),'dummy-preserved-key')
        self.assertEqual(hashlib.sha256(package.read_bytes()).hexdigest(),sha)

    def test_lost_apply_receipt_reopens_and_confirms_without_reupload_or_reapply(self):
        remote=FakeRemote(self.pi,lose_apply=True);first=Transfer(self.doc,self.store,remote=remote)
        with self.assertRaises(OSError):first.send()
        calls=list(remote.calls);reopened=Transfer(self.doc,self.store,remote=remote);result=reopened.send()
        self.assertEqual(result['transaction']['state'],'applied');self.assertEqual(result['current']['revision'],revision(self.doc))
        self.assertEqual(remote.calls.count('apply'),1);self.assertEqual(remote.calls.count('copy'),1)
        self.assertEqual(remote.calls[len(calls):],['inspect']);self.assertFalse(result['current']['running'])

    def test_lost_seal_receipt_keeps_original_packet_and_resumes_same_transaction(self):
        remote=FakeRemote(self.pi,lose_seal=True);first=Transfer(self.doc,self.store,remote=remote)
        with self.assertRaises(OSError):first.send()
        self.assertEqual(self.settings.load_dashboard(),self.old)
        reopened=Transfer(self.doc,self.store,remote=remote);result=reopened.send()
        self.assertEqual(result['transaction']['state'],'applied');self.assertEqual(remote.calls.count('copy'),1);self.assertEqual(remote.calls.count('prepare'),1)

    def test_concurrent_phone_change_blocks_resumed_transfer(self):
        remote=FakeRemote(self.pi,fail_copy=True);first=Transfer(self.doc,self.store,remote=remote)
        with self.assertRaises(OSError):first.send()
        changed=model.from_layout(self.old);changed['pages'][0]['title']='Zwischenzeitlich am Handy geändert'
        self.settings.save_dashboard(changed,revision(self.old))
        reopened=Transfer(self.doc,self.store,remote=remote)
        with self.assertRaises(ValueError):reopened.send()
        self.assertEqual(remote.calls.count('apply'),0);self.assertEqual(self.settings.load_dashboard(),changed)

    def test_explicit_new_transfer_cancels_old_identity_before_rechecking_changed_target(self):
        remote=FakeRemote(self.pi,fail_copy=True);first=Transfer(self.doc,self.store,remote=remote)
        with self.assertRaises(OSError):first.send()
        token=first.token;_,sha=first.package()
        changed=model.from_layout(self.old);changed['pages'][0]['title']='Handy geändert';self.settings.save_dashboard(changed,revision(self.old))
        reopened=Transfer(self.doc,self.store,remote=remote);reopened.start_new()
        self.assertEqual(pi.inspect_transaction(self.pi,token)['transaction']['state'],'cancelled')
        with self.assertRaises(ValueError):pi.transaction(self.pi,token,sha)
        self.assertEqual(self.settings.load_dashboard(),changed)
        completed=reopened.send();self.assertEqual(completed['transaction']['state'],'applied');self.assertNotEqual(reopened.token,token)

    def test_corrupt_journal_is_reported_instead_of_starting_new_transaction(self):
        atomic(self.store.folder/'transfer.json',json_bytes({'schema':1,'token':'bad'}))
        remote=FakeRemote(self.pi)
        with self.assertRaises(ValueError):Transfer(self.doc,self.store,remote=remote)
        self.assertEqual(remote.calls,[])


if __name__=='__main__':unittest.main()

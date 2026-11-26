"""Offline update acceptance using dummy PC/Pi trees; no SSH, real keys or budgets."""
import contextlib
from copy import deepcopy
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

import tools.pi.update as update
from wetterstation.ui.widgets import default_layout, revision


class PiUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared=tempfile.TemporaryDirectory(prefix='pi-package-tests-',dir=Path(__file__).parent)
        cls.source=Path(cls.shared.name)/'pc';cls.source.mkdir()
        actual=Path(__file__).resolve().parents[1]
        for name in update.FILES:
            target=cls.source/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(actual/name,target)
        cls.layout=default_layout();cls.layout['pages'][0]['title']='Meine PC-Widgets'
        update.atomic_bytes(cls.source/'private/settings.json',update.json_bytes({'location':'PC-Ort','openweather_api_key':'dummy-PC-never-export-941','dashboard':cls.layout}))
        update.atomic_bytes(cls.source/'private/mobile/secret.pem',b'dummy-private-TLS-never-export')
        with patch('tools.pi.update.subprocess.run',side_effect=AssertionError('build must stay offline')):
            cls.ready=update.build(cls.source,'2026-10-24-tests')
        cls.archive=cls.source/cls.ready['archive'];cls.layout_file=cls.source/cls.ready['layout']

    @classmethod
    def tearDownClass(cls):cls.shared.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='pi-update-target-',dir=Path(__file__).parent)
        self.base=Path(self.temp.name);self.target=self.base/'Wetterstation';self.target.mkdir()
        update.atomic_bytes(self.target/'app.py',b'# existing Pi app\n',0o644)
        update.atomic_bytes(self.target/'mobile_web/style.css',b'/* existing style */\n',0o644)
        original_layout=default_layout();original_layout['pages'][0]['title']='Pi-Layout'
        self.original={'location':'Pi-Ort','openweather_api_key':'dummy-Pi-original-271','dashboard':original_layout,'custom':{'keep':True}}
        update.atomic_bytes(self.target/'private/settings.json',update.json_bytes(self.original))
        for name,data in [('openweather_budget/ledger.json',b'{"day": "2026-10-24", "calls": 37}'),('mobile/certificate.pem',b'Pi-original-certificate'),('mobile/certificate-key.pem',b'Pi-original-private-TLS-key'),('cache/radar/image.png',b'Pi-cached-image')]:
            update.atomic_bytes(self.target/'private'/name,data)
        self.mirror=self.base/'device-budget-check/ledger.json';update.atomic_bytes(self.mirror,b'Pi-original-external-counter-mirror')
        self.before=update.tree_hashes(self.target)
        self.no_process=lambda _root:[]

    def tearDown(self):self.temp.cleanup()

    def install(self,**kwargs):
        return update.install(self.target,self.archive,self.layout_file,self.ready['sha256'],self.ready['layout_sha256'],probe=kwargs.pop('probe',self.no_process),postcheck=kwargs.pop('postcheck',Mock()),**kwargs)

    def private_unchanged(self):
        actual=update.tree_hashes(self.target,private_only=True)
        ignored={'private/settings.json','private/settings.lock'}
        self.assertEqual({k:v for k,v in self.before.items() if k.startswith('private/') and k not in ignored},{k:v for k,v in actual.items() if k not in ignored})
        self.assertEqual(self.mirror.read_bytes(),b'Pi-original-external-counter-mirror')

    def test_complete_archive_separate_layout_python311_and_linux_starters(self):
        manifest=update.verify_archive(self.archive,self.ready['sha256'])
        self.assertEqual({e['path'] for e in manifest['files']},set(update.FILES))
        self.assertTrue({'wetterstation/ui/widgets.py','wetterstation/ui/dashboard.py','wetterstation/maps/radar_motion.py','wetterstation/maps/radar_render.py','wetterstation/mobile/web/layout.js','start_pi_live.sh','start_pi_widget_demo.sh'}<=set(update.FILES))
        with zipfile.ZipFile(self.archive) as z:
            self.assertFalse(any(name.startswith(('private/','tests/','transfer/','.git/')) for name in z.namelist()))
            content=b''.join(z.read(n) for n in z.namelist())
            self.assertNotIn(b'dummy-PC-never-export-941',content);self.assertNotIn(b'dummy-private-TLS-never-export',content)
            for name in update.FILES:
                if name.endswith('.sh'):
                    self.assertNotIn(b'\r',z.read(name));self.assertEqual(stat.S_IMODE(z.getinfo(name).external_attr>>16),0o755)
        export=update.read_json(self.layout_file)
        self.assertEqual(set(export),{'schema','layout','revision'})
        self.assertEqual(export['layout'],self.layout)
        self.assertNotIn('openweather_api_key',self.layout_file.read_text())
        self.assertNotIn('PC-Ort',self.layout_file.read_text())
        self.assertEqual(manifest['python_syntax'],'3.11')

    def test_success_backup_layout_merge_preserves_all_other_private_data(self):
        def checked(root):
            self.assertTrue((root/update.MARKER).exists())
            self.assertEqual(update.read_json(root/'private/settings.json')['dashboard'],self.layout)
        with patch('tools.pi.update.subprocess.run',side_effect=AssertionError('no subprocess/app start')):
            backup=self.install(postcheck=checked)
        expected=deepcopy(self.original);expected['dashboard']=self.layout
        self.assertEqual(update.read_json(self.target/'private/settings.json'),expected)
        self.private_unchanged()
        self.assertEqual(update.tree_hashes(backup/'installation'),self.before)
        self.assertFalse((self.target/update.MARKER).exists())
        self.assertEqual(update.read_json(backup/'restore.json')['status'],'installed')
        if os.name!='nt':self.assertEqual(stat.S_IMODE(backup.stat().st_mode),0o700)
        with zipfile.ZipFile(self.archive) as z:
            for name in update.FILES:self.assertEqual((self.target/name).read_bytes(),z.read(name))

    def repair_bundle(self):
        source = self.base / 'repair-source'
        source.mkdir()
        for name in update.FILES:
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.source / name, path)
        with patch('tools.pi.update.export_layout', side_effect=AssertionError('repair must not read PC settings')):
            ready = update.build(source, '2026-10-24-mobile-test', keep_layout=True)
        self.assertFalse((source / 'private').exists())
        self.assertTrue(ready['keep_layout'])
        self.assertFalse(any(k in ready for k in ('layout', 'layout_sha256', 'layout_revision')))
        return source, ready

    def test_repair_bundle_never_reads_or_exports_pc_private_data(self):
        source, ready = self.repair_bundle()
        update.verify_archive(source / ready['archive'], ready['sha256'])

    def test_repair_install_preserves_every_private_file_byte_for_byte(self):
        before = update.tree_hashes(self.target, private_only=True)
        with patch('tools.pi.update.merge_layout', side_effect=AssertionError('no layout write')):
            backup = update.install(self.target, self.archive, None, self.ready['sha256'], None,
                                    keep_layout=True, probe=self.no_process, postcheck=update.offline_check)
        self.assertEqual(update.tree_hashes(self.target, private_only=True), before)
        self.assertEqual(update.tree_hashes(backup / 'installation'), self.before)
        self.assertTrue(update.read_json(backup / 'restore.json')['keep_layout'])
        self.assertFalse((self.target / update.MARKER).exists())

    def test_repair_failure_restores_program_without_touching_private_files(self):
        def fail(_root):
            raise update.UpdateError('simulated check failure')
        with self.assertRaisesRegex(update.UpdateError, 'wiederhergestellt'):
            update.install(self.target, self.archive, None, self.ready['sha256'], None,
                           keep_layout=True, probe=self.no_process, postcheck=fail)
        self.assertEqual(update.tree_hashes(self.target), self.before)

    def test_repair_later_restore_preserves_subsequent_pi_layout_changes(self):
        backup = update.install(self.target, self.archive, None, self.ready['sha256'], None,
                                keep_layout=True, probe=self.no_process, postcheck=Mock())
        current = update.read_json(self.target / 'private/settings.json')
        current['dashboard']['pages'][0]['title'] = 'Later Pi edit'
        current['location'] = 'Changed on Pi'
        update.atomic_bytes(self.target / 'private/settings.json', update.json_bytes(current))
        before = update.tree_hashes(self.target, private_only=True)
        update.restore(self.target, backup, probe=self.no_process)
        self.assertEqual(update.tree_hashes(self.target, private_only=True), before)
        self.assertEqual((self.target / 'app.py').read_bytes(), b'# existing Pi app\n')

    def test_conflicting_or_missing_layout_modes_abort_before_any_changes(self):
        for file, sha, keep in ((self.layout_file, self.ready['layout_sha256'], True), (None, None, False)):
            with self.assertRaises(update.UpdateError):
                update.install(self.target, self.archive, file, self.ready['sha256'], sha,
                               keep_layout=keep, probe=self.no_process)
            self.assertEqual(update.tree_hashes(self.target), self.before)

    def test_repair_transfer_only_sends_public_archive_and_updater(self):
        source, ready = self.repair_bundle()
        probe = Mock(returncode=0, stdout=json.dumps({'root': '/home/pi/wetterstation/Wetterstation'}))
        with patch('tools.pi.update.subprocess.run', side_effect=[probe, *[Mock(returncode=0) for _ in range(4)]]) as run, \
             patch('tools.pi.update.export_layout', side_effect=AssertionError('no PC settings read')):
            update.transfer(source)
        commands = [c.args[0] for c in run.call_args_list]
        self.assertEqual([c[0] for c in commands], ['ssh', 'ssh', 'scp', 'scp', 'ssh'])
        self.assertEqual([c[-2] for c in commands if c[0] == 'scp'],
                         [str(source / ready['archive']), str(source / 'tools/pi/update.py')])
        self.assertIn('--keep-layout', commands[-1][-1])
        self.assertNotIn('widget-layout.json', commands[-1][-1])
        self.assertNotIn('start_pi_live', commands[-1][-1])
        for command in commands:
            self.assertIn('StrictHostKeyChecking=yes', command)

    def test_repair_running_app_aborts_before_backup(self):
        with self.assertRaisesRegex(update.UpdateError, 'laeuft noch'):
            update.install(self.target, self.archive, None, self.ready['sha256'], None,
                           keep_layout=True, probe=lambda _root: [123])
        self.assertEqual(update.tree_hashes(self.target), self.before)

    def test_repair_inconsistent_ready_mode_aborts_before_ssh(self):
        source, ready = self.repair_bundle()
        ready['layout'] = 'private/settings.json'
        update.atomic_bytes(source / 'build/pi/pi-update-ready.json', update.json_bytes(ready))
        with patch('tools.pi.update.subprocess.run', side_effect=AssertionError('no SSH')) as run:
            with self.assertRaises(update.UpdateError):
                update.transfer(source)
            run.assert_not_called()

    def test_real_offline_preflight_after_install_never_starts_application(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('no provider network')):
            backup=self.install(postcheck=update.offline_check)
        self.assertTrue(backup.exists());self.private_unchanged()
        self.assertFalse(list(self.target.glob('pi-preflight-*')))

    def test_running_application_aborts_before_any_target_changes(self):
        with self.assertRaisesRegex(update.UpdateError,'laeuft noch'):
            self.install(probe=lambda _root:[123])
        self.assertEqual(update.tree_hashes(self.target),self.before)
        self.assertFalse((self.target.parent/'Wetterstation-Backups').exists())

    def test_bad_hash_and_invalid_layout_leave_target_untouched(self):
        with self.assertRaises(update.UpdateError):
            update.install(self.target,self.archive,self.layout_file,'0'*64,self.ready['layout_sha256'],probe=self.no_process)
        bad=self.base/'layout.json';update.atomic_bytes(bad,update.json_bytes({'schema':1,'layout':{},'revision':'bad'}))
        with self.assertRaises(Exception):
            update.install(self.target,self.archive,bad,self.ready['sha256'],update.digest(bad.read_bytes()),probe=self.no_process)
        self.assertEqual(update.tree_hashes(self.target),self.before)
        self.assertFalse((self.target.parent/'Wetterstation-Backups').exists())

    def test_archive_corruption_unsafe_extra_path_and_symlink_are_rejected(self):
        for kind in ('changed','private','traversal','symlink'):
            target=self.base/(kind+'.zip')
            with zipfile.ZipFile(self.archive) as original,zipfile.ZipFile(target,'w') as modified:
                for info in original.infolist():
                    data=original.read(info.filename)
                    if kind=='changed' and info.filename=='app.py':data+=b'\n# corrupt\n'
                    if kind=='symlink' and info.filename=='app.py':info.external_attr=(stat.S_IFLNK|0o777)<<16
                    modified.writestr(info,data)
                if kind=='private':modified.writestr('private/settings.json','dummy-secret')
                if kind=='traversal':modified.writestr('../app.py','bad')
            with self.subTest(kind=kind),self.assertRaises(update.UpdateError):update.verify_archive(target)
        self.assertEqual(update.tree_hashes(self.target),self.before)

    def test_partial_copy_failure_rolls_back_program_and_leaves_no_guard(self):
        count=0
        def fail(path,data,mode):
            nonlocal count
            count+=1
            if count==7:raise OSError('dummy-error-secret')
            update.atomic_bytes(path,data,mode)
        with self.assertRaisesRegex(update.UpdateError,'wiederhergestellt') as error:self.install(writer=fail)
        self.assertNotIn('dummy-error-secret',str(error.exception))
        actual=update.tree_hashes(self.target)
        actual.pop('private/settings.lock',None)
        self.assertEqual(actual,self.before)
        self.private_unchanged();self.assertFalse((self.target/update.MARKER).exists())

    def test_offline_check_failure_rolls_back_changed_layout_as_well(self):
        def fail(_root):raise update.UpdateError('Offline test failed')
        with self.assertRaisesRegex(update.UpdateError,'wiederhergestellt'):self.install(postcheck=fail)
        self.assertEqual((self.target/'private/settings.json').read_bytes(),update.json_bytes(self.original))
        self.private_unchanged()
        self.assertEqual((self.target/'app.py').read_bytes(),b'# existing Pi app\n')
        self.assertFalse((self.target/'widgets.py').exists())

    def test_power_failure_keeps_guard_and_explicit_restore_recovers(self):
        count=0
        def power_cut(path,data,mode):
            nonlocal count
            count+=1
            if count==8:raise KeyboardInterrupt('simulated power interruption')
            update.atomic_bytes(path,data,mode)
        with self.assertRaises(KeyboardInterrupt):self.install(writer=power_cut)
        marker=update.read_json(self.target/update.MARKER);backup=Path(marker['backup'])
        with self.assertRaisesRegex(update.UpdateError,'unvollstaendig'):self.install()
        update.restore(self.target,backup,probe=self.no_process)
        self.assertFalse((self.target/update.MARKER).exists())
        self.assertEqual((self.target/'app.py').read_bytes(),b'# existing Pi app\n')
        self.private_unchanged()

    def test_later_restore_preserves_advanced_budget_and_later_key_location(self):
        backup=self.install()
        counter=self.target/'private/openweather_budget/ledger.json';counter.write_bytes(b'counter advanced to 99')
        self.mirror.write_bytes(b'external mirror advanced to 99')
        settings=update.read_json(self.target/'private/settings.json');settings.update(location='New Pi place',openweather_api_key='dummy-Pi-replaced-later')
        update.atomic_bytes(self.target/'private/settings.json',update.json_bytes(settings))
        update.restore(self.target,backup,probe=self.no_process)
        actual=update.read_json(self.target/'private/settings.json')
        self.assertEqual(actual['dashboard'],self.original['dashboard'])
        self.assertEqual(actual['location'],'New Pi place');self.assertEqual(actual['openweather_api_key'],'dummy-Pi-replaced-later')
        self.assertEqual(counter.read_bytes(),b'counter advanced to 99');self.assertEqual(self.mirror.read_bytes(),b'external mirror advanced to 99')

    def test_other_program_edits_or_newer_layout_stop_restore_without_overwrite(self):
        backup=self.install()
        (self.target/'app.py').write_bytes(b'manual newer program')
        with self.assertRaises(update.UpdateError):update.restore(self.target,backup,probe=self.no_process)
        self.assertEqual((self.target/'app.py').read_bytes(),b'manual newer program')
        with zipfile.ZipFile(self.archive) as z:(self.target/'app.py').write_bytes(z.read('app.py'))
        current=update.read_json(self.target/'private/settings.json');current['dashboard']['pages'][0]['title']='Later user layout'
        update.atomic_bytes(self.target/'private/settings.json',update.json_bytes(current))
        with self.assertRaises(update.UpdateError):update.restore(self.target,backup,probe=self.no_process)
        self.assertTrue((self.target/update.MARKER).exists())
        self.assertEqual(update.read_json(self.target/'private/settings.json'),current)

    def test_backup_failure_or_guard_creation_failure_does_not_install(self):
        with patch('pi_update.shutil.copytree',side_effect=OSError('backup failure')):
            with self.assertRaises(OSError):self.install()
        self.assertEqual(update.tree_hashes(self.target),self.before)
        self.private_unchanged()
        original=update.atomic_bytes
        def fail_guard(path,data,mode=0o600):
            if path==self.target/update.MARKER:raise OSError('guard unavailable')
            return original(path,data,mode)
        with patch('tools.pi.update.atomic_bytes',side_effect=fail_guard):
            with self.assertRaisesRegex(update.UpdateError,'nicht angelegt'):self.install()
        self.assertEqual(update.tree_hashes(self.target),self.before)

    def test_process_appearing_during_update_keeps_guard_until_user_stops_it(self):
        calls=0
        def later(_root):
            nonlocal calls
            calls+=1
            return [789] if calls>=3 else []
        with self.assertRaisesRegex(update.UpdateError,'Startsperre bleibt aktiv'):self.install(probe=later)
        self.assertTrue((self.target/update.MARKER).exists())
        self.assertEqual((self.target/'app.py').read_bytes(),b'# existing Pi app\n')
        self.private_unchanged()
        backup=Path(update.read_json(self.target/update.MARKER)['backup'])
        update.restore(self.target,backup,probe=self.no_process)
        self.assertFalse((self.target/update.MARKER).exists())

    def test_layout_merge_failure_is_rolled_back_without_counter_changes(self):
        with patch('tools.pi.update.merge_layout',side_effect=OSError('dummy-sensitive-error')):
            with self.assertRaisesRegex(update.UpdateError,'wiederhergestellt'):self.install()
        self.assertEqual(update.read_json(self.target/'private/settings.json'),self.original)
        self.private_unchanged()

    def test_changed_source_or_layout_stops_transfer_before_any_ssh(self):
        old=(self.source/'app.py').read_bytes()
        try:
            (self.source/'app.py').write_bytes(old+b'\n# newer local source\n')
            with patch('tools.pi.update.subprocess.run',side_effect=AssertionError('must not connect')) as call:
                with self.assertRaises(update.UpdateError):update.transfer(self.source)
                call.assert_not_called()
        finally:(self.source/'app.py').write_bytes(old)

    def test_transfer_uses_strict_known_identity_and_first_probe_is_read_only(self):
        with patch('tools.pi.update.subprocess.run',return_value=Mock(returncode=255)) as call:
            with self.assertRaisesRegex(update.UpdateError,'nichts uebertragen'):update.transfer(self.source)
        self.assertEqual(call.call_count,1)
        args=call.call_args.args[0]
        self.assertEqual(args[0],'ssh');self.assertIn('StrictHostKeyChecking=yes',args)
        self.assertEqual(call.call_args.kwargs['stdout'],update.subprocess.PIPE)
        self.assertNotIn('capture_output',call.call_args.kwargs)
        self.assertNotIn('stderr',call.call_args.kwargs)
        self.assertNotIn('mkdir',update.REMOTE_CHECK)
        self.assertIn('laeuft noch',update.REMOTE_CHECK)

    def test_transfer_command_plan_only_sends_archive_layout_and_updater(self):
        probe=Mock(returncode=0,stdout=json.dumps({'root':'/home/pi/wetterstation/Wetterstation'}))
        with patch('tools.pi.update.subprocess.run',side_effect=[probe,*[Mock(returncode=0) for _ in range(5)]]) as call:
            update.transfer(self.source)
        commands=[c.args[0] for c in call.call_args_list]
        self.assertEqual(len(commands),6)
        self.assertEqual([c[0] for c in commands],['ssh','ssh','scp','scp','scp','ssh'])
        for command in commands:self.assertIn('StrictHostKeyChecking=yes',command)
        copied=[c[-2] for c in commands if c[0]=='scp']
        self.assertEqual(copied,[str(self.archive),str(self.layout_file),str(self.source/'tools/pi/update.py')])
        self.assertNotIn(str(self.source/'private/settings.json'),copied)
        self.assertIn('install',commands[-1][-1]);self.assertNotIn('start_pi_live',commands[-1][-1])

    def test_layout_payload_cannot_be_replaced_with_a_whole_settings_export(self):
        old_layout=self.layout_file.read_bytes()
        ready_path=self.source/'build/pi/pi-update-ready.json';old_ready=ready_path.read_bytes()
        try:
            self.layout_file.write_bytes((self.source/'private/settings.json').read_bytes())
            ready=update.read_json(ready_path);ready['layout_sha256']=update.digest(self.layout_file.read_bytes())
            update.atomic_bytes(ready_path,update.json_bytes(ready))
            with patch('tools.pi.update.subprocess.run',side_effect=AssertionError('must not send secrets')) as call:
                with self.assertRaises(update.UpdateError):update.transfer(self.source)
                call.assert_not_called()
        finally:
            self.layout_file.write_bytes(old_layout);ready_path.write_bytes(old_ready)

    def test_remote_read_only_probe_rejects_a_live_app(self):
        # Execute the exact remote source against a fake /proc and home on this
        # PC. No SSH, no Linux state changes and no real process inspection.
        proc=self.base/'remote-proc';proc.mkdir()
        home=self.base/'home';target=home/update.RELATIVE_TARGET
        (target/'private').mkdir(parents=True)
        (target/'app.py').write_text('# old app');(target/'private/settings.json').write_text('{}')
        process=proc/'51';process.mkdir();(process/'cwd').mkdir()
        (process/'cmdline').write_bytes(b'python3\0'+str(target/'app.py').encode()+b'\0')
        code=update.REMOTE_CHECK.replace("pathlib.Path('/proc')",f"pathlib.Path({str(proc)!r})")
        with patch('getpass.getuser',return_value='pi'),patch('pathlib.Path.home',return_value=home),patch.object(sys,'platform','linux'),self.assertRaisesRegex(AssertionError,'laeuft noch'):
            exec(code,{})

    def test_process_detection_matches_only_target_app_in_proc_fixtures(self):
        proc=self.base/'proc';proc.mkdir()
        def process(pid,args,cwd):
            folder=proc/str(pid);folder.mkdir();(folder/'cmdline').write_bytes(b'\0'.join(a.encode() for a in args)+b'\0')
            (folder/'cwd').mkdir();return folder
        process(11,['python3',str(self.target/'app.py')],self.target)
        process(12,['python3',str(self.base/'other/app.py')],self.base)
        process(13,['python3','pi_update.py','install'],self.base)
        self.assertEqual(update.running_processes(self.target,proc),[11])

    def test_unrelated_own_process_with_unreadable_cwd_is_ignored(self):
        proc=self.base/'protected-proc';proc.mkdir()
        for pid,args in ((61,['desktop-helper']),(62,['python3',str(self.target/'app.py')])):
            folder=proc/str(pid);folder.mkdir();(folder/'cmdline').write_bytes(b'\0'.join(a.encode() for a in args)+b'\0');(folder/'cwd').mkdir()
        original=Path.resolve
        def protected(path,*args,**kwargs):
            if path==proc/'61/cwd':raise PermissionError('unrelated desktop process')
            return original(path,*args,**kwargs)
        with patch.object(Path,'resolve',protected):
            self.assertEqual(update.running_processes(self.target,proc),[62])

    def test_remote_probe_skips_unrelated_unreadable_cwd(self):
        proc=self.base/'remote-protected-proc';proc.mkdir()
        home=self.base/'remote-home';target=home/update.RELATIVE_TARGET
        (target/'private').mkdir(parents=True);(target/'app.py').write_text('# app');(target/'private/settings.json').write_text('{}')
        folder=proc/'63';folder.mkdir();(folder/'cmdline').write_bytes(b'desktop-helper\0');(folder/'cwd').mkdir()
        original=Path.resolve
        def protected(path,*args,**kwargs):
            if path==folder/'cwd':raise PermissionError('unrelated desktop process')
            return original(path,*args,**kwargs)
        code=update.REMOTE_CHECK.replace("pathlib.Path('/proc')",f"pathlib.Path({str(proc)!r})")
        with patch('getpass.getuser',return_value='pi'),patch('pathlib.Path.home',return_value=home),patch.object(sys,'platform','linux'),patch.object(Path,'resolve',protected),contextlib.redirect_stdout(StringIO()) as output:
            exec(code,{})
        self.assertEqual(json.loads(output.getvalue())['root'],str(target.resolve()))

    def test_start_guard_blocks_direct_app_before_gui_or_sources(self):
        import wetterstation.ui.app as app
        update.atomic_bytes(self.target/update.MARKER,b'{}')
        with patch.object(app,'__file__',str(self.target/'app.py')),patch.object(app.tk,'Tk') as tk,contextlib.redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):app.main()
            tk.assert_not_called()

    def test_migration_removes_only_named_old_files_and_restore_recovers_them(self):
        update.atomic_bytes(self.target/'widgets.py', b'# original legacy widget code\n')
        update.atomic_bytes(self.target/'start_preview.cmd', b'@echo old Windows launcher\n')
        update.atomic_bytes(self.target/'pi_live_transfer.py', b'# historical one-time migration\n')
        update.atomic_bytes(self.target/'my-personal-script.py', b'# keep unknown file\n')
        backup = update.install(self.target, self.archive, None, self.ready['sha256'], None,
                                keep_layout=True, probe=self.no_process, postcheck=lambda _: None)
        self.assertFalse((self.target/'widgets.py').exists())
        self.assertFalse((self.target/'start_preview.cmd').exists())
        self.assertFalse((self.target/'pi_live_transfer.py').exists())
        self.assertTrue((self.target/'wetterstation/ui/widgets.py').is_file())
        self.assertEqual((self.target/'my-personal-script.py').read_bytes(), b'# keep unknown file\n')
        update.restore(self.target, backup, probe=self.no_process)
        self.assertEqual((self.target/'widgets.py').read_bytes(), b'# original legacy widget code\n')
        self.assertEqual((self.target/'start_preview.cmd').read_bytes(), b'@echo old Windows launcher\n')
        self.assertEqual((self.target/'pi_live_transfer.py').read_bytes(), b'# historical one-time migration\n')
        self.assertFalse((self.target/'wetterstation/ui/widgets.py').exists())
        self.private_unchanged()

    def test_migration_failure_restores_removed_legacy_files_and_preserves_layout(self):
        update.atomic_bytes(self.target/'widgets.py', b'# legacy widgets\n')
        with self.assertRaises(update.UpdateError):
            update.install(self.target, self.archive, None, self.ready['sha256'], None,
                           keep_layout=True, probe=self.no_process,
                           postcheck=lambda _: (_ for _ in ()).throw(RuntimeError('offline check failed')))
        self.assertEqual((self.target/'widgets.py').read_bytes(), b'# legacy widgets\n')
        self.assertFalse((self.target/'wetterstation/ui/widgets.py').exists())
        self.private_unchanged()


if __name__=='__main__':unittest.main()

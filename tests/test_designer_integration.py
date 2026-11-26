"""Schema-3 HTTPS, Tk, budget and design-only deployment acceptance."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

import test_mobile_settings as mobile
import test_openweather_budget as budgets
from wetterstation.designer import model
from wetterstation.designer.storage import DesignStore
from wetterstation.designer.timeline_client import TimelineAdapter,next_start,parse_rows
from wetterstation.designer.series import regular_remaining
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.storage.openweather_budget import BudgetLimitReached
from wetterstation.ui.widgets import revision,LayoutConflict
from wetterstation.ui.app import WeatherPreview
from tools.pi import design as deployment


def settle(preview):
    import time
    deadline=time.monotonic()+15
    while getattr(preview,'_designer_busy',False):
        if time.monotonic()>deadline:raise AssertionError('Frame preparation did not finish')
        try:preview._results.get(timeout=.1)()
        except __import__('queue').Empty:pass



class PhoneDesignTests(unittest.TestCase):
    setUp=mobile.MobileSettingsTests.setUp
    tearDown=mobile.MobileSettingsTests.tearDown
    request=mobile.MobileSettingsTests.request
    begin_pairing=mobile.MobileSettingsTests.begin_pairing
    login=mobile.MobileSettingsTests.login

    def install_design(self):
        current=self.store.load_dashboard();doc=model.from_layout(current);doc['pages'][0]['widgets']=[]
        w=model.new_widget('series');w.update(w=2,h=2);w['style']={'radius':0,'border_width':9,'background':'#123456'}
        doc['pages'][0]['grid']={'columns':24,'rows':16};doc['pages'][0]['widgets']=[w]
        self.store.save_dashboard(doc,revision(current));return doc,w

    def test_authenticated_narrow_move_resize_fields_preserves_design_and_rejects_whole_save(self):
        self.login();doc,w=self.install_design();self.service.on_layout_change=lambda d,p:self.service.publish_display(p,revision(d))
        payload={'operations':[{'op':'move_widget','page':'overview','id':w['id'],'x':15,'y':10,'w':4,'h':3}],'revision':revision(doc),'page_id':'overview'}
        with patch('wetterstation.weather.weather_service.OpenWeatherClient._request',side_effect=AssertionError('no HTTP')):
            status,_,body=self.request('POST','/api/dashboard/arrange',payload)
            self.assertEqual(status,200);saved=json.loads(body)['layout'];got=saved['pages'][0]['widgets'][0]
            self.assertEqual(got['style'],w['style']);self.assertEqual(got['series'],w['series'])
            self.assertEqual(self.request('POST','/api/dashboard/arrange',payload)[0],409)
            self.assertEqual(self.request('POST','/api/dashboard',{'layout':doc,'revision':revision(saved),'page_id':'overview'})[0],400)
        self.assertEqual(self.store.load_api_key(),'dummy-original-key')
        self.assertNotIn(b'dummy-original-key',body)

    def test_lock_origins_csrf_and_unknown_style_operations_are_rejected(self):
        self.login();doc,w=self.install_design();payload={'operations':[{'op':'move_widget','page':'overview','id':w['id'],'x':10,'y':2,'w':3,'h':2}],'revision':revision(doc),'page_id':'overview'}
        self.assertEqual(self.request('POST','/api/dashboard/arrange',payload,{'X-CSRF-Token':''})[0],403)
        bad=deepcopy(payload);bad['operations'][0]['style']={'background':'#000000'}
        self.assertEqual(self.request('POST','/api/dashboard/arrange',bad)[0],400)
        w['locked']=True;self.store.save_dashboard(doc,revision(self.store.load_dashboard()));payload['revision']=revision(doc)
        self.assertEqual(self.request('POST','/api/dashboard/arrange',payload)[0],400)


class ProtectedSupplementTests(unittest.TestCase):
    setUpClass=classmethod(budgets.OpenWeatherBudgetTests.setUpClass.__func__)
    tearDownClass=classmethod(budgets.OpenWeatherBudgetTests.tearDownClass.__func__)
    setUp=budgets.OpenWeatherBudgetTests.setUp
    tearDown=budgets.OpenWeatherBudgetTests.tearDown
    seed=budgets.OpenWeatherBudgetTests.seed
    paths=budgets.OpenWeatherBudgetTests.paths

    def test_atomic_protected_reservation_keeps_baseline_and_reserve(self):
        self.seed(count=900)
        with self.assertRaises(BudgetLimitReached):self.budget.reserve_call(now=self.now,protected=100)
        self.assertEqual(self.budget.status(now=self.now)['provider_count'],900)
        self.assertEqual(self.budget.reserve_call(now=self.now,protected=99),901)
        with self.assertRaises(BudgetLimitReached):self.budget.reserve_call(now=self.now,protected=99)
        self.assertEqual(self.budget.reserve_call(now=self.now),902)


class TimelineTests(unittest.TestCase):
    def test_real_responses_pages_and_shared_cache_use_only_injected_transport(self):
        now=datetime(2026,10,27,12,tzinfo=timezone.utc);doc=model.from_layout();w=model.new_widget('series');w['series'].update(duration=900,refresh=120);doc['pages'][0]['widgets']=[w]
        calls=[]
        def request(source,start,protected):
            calls.append((source,start,protected));begin=start or int(now.timestamp())
            rows=[{'dt':begin+i*900,'temp':10+i,'pop':.2,'wind_speed':3,'weather':[{'description':'Heiter'}]} for i in range(50)]
            return {'data':rows,'next':f'https://api.openweathermap.org/data/4.0/onecall/timeline/15min?start={begin+50*900}&appid=dummy-key'}
        adapter=TimelineAdapter(request);result,errors=adapter.collect(doc,'Testort|DE',now)
        self.assertEqual(len(calls),2);self.assertEqual(len(result['15min']),100);self.assertEqual(errors,[])
        self.assertEqual(calls[0][2],regular_remaining(now)+24)
        adapter.collect(doc,'Testort|DE',now+timedelta(minutes=5));self.assertEqual(len(calls),2)
        adapter.collect(doc,'Anderer Ort|DE',now);self.assertEqual(len(calls),4)
        self.assertNotIn('dummy-key',json.dumps(result))

    def test_minutely_rain_does_not_invent_other_weather_and_rejects_external_pagination(self):
        payload={'data':[{'dt':1793102400,'precipitation':1.2},{'dt':'bad','precipitation':0}]}
        row=parse_rows(payload,'1min')[0];self.assertEqual(row['precipitation'],1.2);self.assertNotIn('temp',row)
        for url in ('https://evil.invalid/data/4.0/onecall/timeline/15min?start=10','https://api.openweathermap.org/data/4.0/onecall/timeline/1h?start=10'):
            with self.assertRaises(ValueError):next_start({'next':url},'15min')


class DeploymentDesignTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.root=Path(self.tmp.name).resolve();(self.root/'app.py').write_text('# isolated target')
        self.settings=ApiKeyStore(self.root/'private/settings.json');self.settings.save_configuration('Testort','dummy-preserved-key',country_code='DE')
        self.original=self.settings.load_dashboard();self.doc=model.from_layout();self.doc['style']['background']='#abccdd';self.store=DesignStore(self.root/'pc-draft')
        self.patch=patch('tools.pi.update.running_processes',return_value=[]);self.patch.start()

    def tearDown(self):self.patch.stop();self.tmp.cleanup()

    def stage(self):
        prepared=deployment.prepare(self.root,revision(self.original));package=Path(prepared['destination']);self.store.export(self.doc,package)
        return prepared['token'],hashlib.sha256(package.read_bytes()).hexdigest()

    def test_transaction_preserves_credentials_leaves_app_closed_and_is_idempotent(self):
        token,sha=self.stage();result=deployment.transaction(self.root,token,sha)
        self.assertEqual(self.settings.load_api_key(),'dummy-preserved-key');self.assertTrue(Path(result['backup']).is_dir())
        observed=deployment.inspect_transaction(self.root,token);self.assertFalse(observed['current']['running'])
        self.assertEqual(observed['transaction']['state'],'applied');self.assertEqual(deployment.transaction(self.root,token,sha),result)
        restored=deployment.restore(self.root,token,revision(self.doc));self.assertEqual(restored['state'],'restored')
        self.assertEqual(self.settings.load_dashboard(),self.original);self.assertEqual(self.settings.load_api_key(),'dummy-preserved-key')

    def test_changed_layout_or_corrupt_package_never_overwrites_target(self):
        token,sha=self.stage();current=deepcopy(self.original);current['pages'][0]['title']='Handy geändert';self.settings.save_dashboard(current,revision(self.original))
        with self.assertRaises(LayoutConflict):deployment.transaction(self.root,token,sha)
        self.assertEqual(self.settings.load_dashboard(),current)
        with self.assertRaises(ValueError):deployment.transaction(self.root,token,'0'*64)

    def test_lost_response_after_settings_commit_is_reconciled_without_second_apply(self):
        token,sha=self.stage();real=deployment.atomic
        def lost(path,data):
            if Path(path).name=='transaction.json' and b'"applied"' in data:raise OSError('simulated disconnect')
            return real(path,data)
        with patch.object(deployment,'atomic',side_effect=lost):
            with self.assertRaises(OSError):deployment.transaction(self.root,token,sha)
        observed=deployment.inspect_transaction(self.root,token)
        self.assertEqual(observed['transaction']['state'],'applied');self.assertEqual(observed['current']['revision'],revision(self.doc))
        self.assertTrue(Path(observed['transaction']['backup']).is_dir())

    def test_display_ack_must_match_live_session_nonce_and_readiness(self):
        directory=self.root/'private/designer';directory.mkdir(parents=True)
        session={'pid':42,'nonce':'new-session','ready':True,'args':[]}
        (self.root/'.wetterstation-session.json').write_text(json.dumps(session))
        ack={'pid':42,'nonce':'old-session','revision':revision(self.original),'ready':True}
        (directory/'display-ack.json').write_text(json.dumps(ack))
        self.assertIsNone(deployment.status(self.root,probe=lambda _: [42])['display'])
        ack['nonce']='new-session';(directory/'display-ack.json').write_text(json.dumps(ack))
        self.assertIsNotNone(deployment.status(self.root,probe=lambda _: [42])['display'])


class RuntimeDesignTests(unittest.TestCase):
    def tearDown(self):
        # Tk reference cycles must be collected on their owning thread before
        # later TLS/background tests start allocating Python objects.
        import gc
        gc.collect()

    def test_clock_patches_match_full_reference_in_all_four_rotations(self):
        from PIL import ImageTk,ImageChops
        from wetterstation.designer.render import demo_data,render_page,output_image
        fixed=demo_data(datetime(2026,10,27,12,10,tzinfo=timezone.utc));later=deepcopy(fixed);later['now']+=timedelta(minutes=1)
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            settings=ApiKeyStore(Path(folder)/'settings.json')
            for angle in (0,90,180,270):
                doc=model.from_layout();doc['display']['rotation']=angle;settings.save_dashboard(doc,revision(settings.load_dashboard()))
                root=tk.Tk();root.withdraw();preview=WeatherPreview(root,widget_demo=True,settings_store=settings)
                width,height=(600,1024) if angle in (90,270) else (1024,600)
                preview.canvas.winfo_width=lambda:width;preview.canvas.winfo_height=lambda:height
                with patch('wetterstation.designer.runtime.display_data',return_value=fixed):preview.draw();settle(preview)
                with patch('wetterstation.designer.runtime.display_data',return_value=later):preview.draw();settle(preview)
                composited=ImageTk.getimage(preview._designer_photo).convert('RGBA')
                for widget_id,photo in preview._designer_patch_photos.items():
                    x,y=preview.canvas.coords('designer-clock-'+widget_id)
                    composited.alpha_composite(ImageTk.getimage(photo).convert('RGBA'),(round(x),round(y)))
                expected=output_image(render_page(doc,'overview',later,Path(folder)/'designer/assets')[0],angle)
                self.assertIsNone(ImageChops.difference(composited.convert('RGB'),expected.convert('RGB')).getbbox(),f'rotation {angle}')
                root.update_idletasks();preview.close()

    def test_tk_uses_shared_renderer_and_acknowledges_without_provider_calls(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            settings=ApiKeyStore(Path(folder)/'settings.json');current=settings.load_dashboard();doc=model.from_layout();doc['display']['rotation']=90;settings.save_dashboard(doc,revision(current))
            root=tk.Tk();root.withdraw()
            with patch('wetterstation.weather.weather_service.OpenWeatherClient._request',side_effect=AssertionError('no HTTP')) as weather:
                preview=WeatherPreview(root,widget_demo=True,settings_store=settings)
                preview.canvas.winfo_width=lambda:1024;preview.canvas.winfo_height=lambda:600
                from wetterstation.designer.render import demo_data
                fixed=demo_data(datetime(2026,10,27,12,10,tzinfo=timezone.utc))
                with patch('wetterstation.designer.runtime.display_data',return_value=fixed):preview.draw();settle(preview)
                self.assertTrue(preview.canvas.find_withtag('designer-display'))
                ack=json.loads((Path(folder)/'designer/display-ack.json').read_text());self.assertEqual(ack['revision'],revision(doc))
                oldcache=len(preview._designer_render_cache)
                with patch('wetterstation.designer.runtime.display_data',return_value=fixed):preview.draw();settle(preview)
                self.assertLessEqual(len(preview._designer_render_cache)-oldcache,1)
                base_image=preview.canvas.find_withtag('designer-display')[0]
                from wetterstation.designer.runtime import display_data
                data=deepcopy(fixed);data['now']+=timedelta(minutes=1)
                with patch('wetterstation.designer.runtime.display_data',return_value=data),patch('wetterstation.designer.runtime.render_page',side_effect=AssertionError('no full redraw')):
                    preview.draw()
                self.assertEqual(preview.canvas.find_withtag('designer-display')[0],base_image)
                self.assertTrue(preview.canvas.find_withtag('designer-clock-patch'))
                stale=deepcopy(doc);latest=deepcopy(doc);latest['pages'][0]['title']='Neuer PC-Stand'
                settings.save_dashboard(latest,revision(doc));preview._apply_mobile_dashboard(stale)
                self.assertEqual(preview.dashboard,latest)
                weather.assert_not_called();preview.close()


if __name__=='__main__':unittest.main()

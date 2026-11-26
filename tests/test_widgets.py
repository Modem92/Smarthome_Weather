"""Widget contracts: packing, persistence, protected transport and actual Tk pages."""
from copy import deepcopy
from datetime import datetime, timezone
from dataclasses import replace
import gc
import json
from pathlib import Path
import random
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch, Mock

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview
from wetterstation.ui.dashboard import clock_text
from wetterstation.ui.widgets import (CATALOG, default_layout, new_widget, arrange_page, validate_layout,
                     load_layout, revision, NoSpace, LayoutConflict)
import test_mobile_settings as mobile_tests
import test_rain_full_window as map_tests
from wetterstation.maps.radar_map import POTSDAM, MapPosition


class WidgetModelTests(unittest.TestCase):
    def test_four_defaults_are_bounded_and_cover_previous_data(self):
        layout=default_layout()
        self.assertEqual(validate_layout(layout),layout)
        self.assertEqual([p['title'] for p in layout['pages']],['Wetterübersicht','Vorhersage','Regenkarte','Sensoren'])
        self.assertTrue({'temp','feels_like','description','humidity','wind','pressure','date','clock','hourly','daily','radar','sensors'}<=set(CATALOG))
        self.assertTrue(all('sensor_'+key in CATALOG for key in ('temp','humidity','pressure','wind')))

    def test_collision_moves_neighbor_and_keeps_pinned_position(self):
        first=new_widget('clock','a',4,0)
        other=new_widget('clock','b',4,0)
        result=arrange_page([first,other],pinned='a')
        self.assertEqual((result[0]['x'],result[0]['y']),(4,0))
        validate_layout({'version':2,'pages':[{'id':'p','title':'Seite','widgets':result}]})
        self.assertEqual((other['x'],other['y']),(4,0),'packing must not mutate caller input')

    def test_full_page_failure_keeps_original(self):
        items=[new_widget('radar','map'),new_widget('clock','clock')]
        before=deepcopy(items)
        with self.assertRaises(NoSpace):arrange_page(items,'clock')
        self.assertEqual(items,before)

    def test_solver_rearranges_fragmented_neighbors_instead_of_growing_page(self):
        items=[new_widget('clock',str(i),i%3*4,i//3*3,w=4,h=3) for i in range(3)]
        items.append(new_widget('hourly','forecast',0,0,w=12,h=4))
        result=arrange_page(items,'forecast')
        self.assertEqual(result[-1]['y'],0)
        self.assertTrue(all(i['y']>=4 for i in result[:-1]))

    def test_random_packing_is_deterministic_non_overlapping_and_bounded(self):
        randomizer=random.Random(812)
        for trial in range(50):
            items=[new_widget('temp',f'w{i}',randomizer.randrange(9),randomizer.randrange(6),w=3,h=2) for i in range(randomizer.randint(1,12))]
            a=arrange_page(items);b=arrange_page(items)
            self.assertEqual(a,b)
            validate_layout({'version':2,'pages':[{'id':'p','title':'P','widgets':a}]})

    def test_blank_fields_and_repeated_types_keep_explicit_geometry(self):
        layout=default_layout();item=layout['pages'][0]['widgets'][0]
        size=(item['w'],item['h']);item['fields']=[]
        self.assertEqual(validate_layout(layout)['pages'][0]['widgets'][0]['fields'],[])
        self.assertEqual((item['w'],item['h']),size)
        layout['pages'].append({'id':'another','title':'Uhr','widgets':[new_widget('clock','other-clock')]})
        validate_layout(layout)

    def test_invalid_schema_bounds_ids_fields_and_collisions_rejected(self):
        cases=[]
        def changed(work):
            v=default_layout();work(v);cases.append(v)
        changed(lambda v:v.update(version=True))
        changed(lambda v:v.update(pages=[]))
        changed(lambda v:v['pages'].append(deepcopy(v['pages'][0])))
        changed(lambda v:v['pages'][0].update(title=''))
        changed(lambda v:v['pages'][0]['widgets'][0].update(x=True))
        changed(lambda v:v['pages'][0]['widgets'][0].update(w=2))
        changed(lambda v:v['pages'][0]['widgets'][0].update(y=8))
        changed(lambda v:v['pages'][0]['widgets'][0].update(fields=['unknown']))
        changed(lambda v:v['pages'][0]['widgets'][0].update(fields=['time','time']))
        changed(lambda v:v['pages'][0]['widgets'][0].update(id='<script>'))
        changed(lambda v:v['pages'][0]['widgets'][0].update(type='unknown'))
        changed(lambda v:v['pages'][0]['widgets'][1].update(x=0))
        for case in cases:
            with self.subTest(case=case),self.assertRaises(ValueError):validate_layout(case)

    def test_early_draft_migrates_without_dropping_values_or_hidden_fields(self):
        items=[new_widget('clock',f'w{i}',0,i*3) for i in range(8)]
        items[0]['fields']=[]
        result=load_layout({'version':1,'widgets':items})
        self.assertGreater(len(result['pages']),1)
        self.assertEqual([i['id'] for p in result['pages'] for i in p['widgets']],[i['id'] for i in items])
        self.assertEqual(result['pages'][0]['widgets'][0]['fields'],[])
        validate_layout(result)

    def test_clock_seconds_and_date_are_independent(self):
        stamp=datetime(2026,10,24,12,34,56,tzinfo=timezone.utc)
        self.assertEqual(clock_text('time',['time'],stamp),'12:34')
        self.assertEqual(clock_text('time',['time','seconds'],stamp),'12:34:56')
        self.assertEqual(clock_text('seconds',['seconds'],stamp),'56')
        self.assertIn('24.10.2026',clock_text('date',[],stamp))


class WidgetStorageTests(unittest.TestCase):
    def test_demo_entrypoint_uses_and_removes_only_its_temporary_store(self):
        import wetterstation.ui.app as app
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Mock()
            captured=[]
            def constructed(_root,**options):
                self.assertTrue(options['widget_demo'])
                store=options['settings_store']
                captured.append(store.path)
                self.assertTrue(store.path.is_relative_to(Path(folder)/'private'/'widget-demo'))
                store.save_dashboard(default_layout(),revision(default_layout()))
                return Mock()
            with patch.object(app,'__file__',str(Path(folder)/'app.py')),patch.object(app.sys,'argv',['app.py','--widget-demo']),patch.object(app.tk,'Tk',return_value=root),patch.object(app,'WeatherPreview',side_effect=constructed):
                app.main()
            self.assertEqual(len(captured),1)
            self.assertFalse(captured[0].exists())
            self.assertFalse((Path(folder)/'private'/'settings.json').exists())

    def test_roundtrip_restart_preserves_location_key_and_independent_updates(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            store=ApiKeyStore(path=Path(folder)/'settings.json')
            store.save_configuration('Berlin','dummy-widget-key')
            base=store.load_dashboard();edited=deepcopy(base)
            edited['pages'].reverse();edited['pages'][0]['title']='Meine Sensoren'
            store.save_dashboard(edited,revision(base))
            store.save_configuration('Hamburg','')
            other=ApiKeyStore(path=store.path)
            self.assertEqual(other.load_dashboard(),edited)
            self.assertEqual(other.load_location(),'Hamburg')
            self.assertEqual(other.load_api_key(),'dummy-widget-key')

    def test_stale_saves_and_write_failure_do_not_overwrite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            store=ApiKeyStore(path=Path(folder)/'settings.json')
            original=store.load_dashboard();edited=deepcopy(original);edited['pages'][0]['title']='Changed'
            store.save_dashboard(edited,revision(original));good=store.path.read_bytes()
            with self.assertRaises(LayoutConflict):store.save_dashboard(original,revision(original))
            self.assertEqual(store.path.read_bytes(),good)
            with patch.object(store,'_write_settings',side_effect=OSError('dummy-secret')):
                with self.assertRaises(OSError):store.save_dashboard(original,revision(edited))
            self.assertEqual(store.path.read_bytes(),good)


class WidgetTransportTests(unittest.TestCase):
    setUp=mobile_tests.MobileSettingsTests.setUp
    tearDown=mobile_tests.MobileSettingsTests.tearDown
    request=mobile_tests.MobileSettingsTests.request
    begin_pairing=mobile_tests.MobileSettingsTests.begin_pairing
    login=mobile_tests.MobileSettingsTests.login

    def values(self):
        status,_,body=self.request('GET','/api/dashboard');self.assertEqual(status,200)
        self.assertNotIn(b'dummy-original-key',body)
        return json.loads(body)

    def test_dashboard_and_display_require_authentication_and_csrf(self):
        for route in ('/api/dashboard','/api/display'):
            self.assertEqual(self.request('GET',route)[0],401)
        self.login();d=self.values();payload={'layout':d['layout'],'revision':d['revision'],'page_id':'overview'}
        for headers in ({'Origin':'https://bad.invalid'},{'Host':'bad.invalid'},{'X-CSRF-Token':''}):
            self.assertEqual(self.request('POST','/api/dashboard',payload,headers)[0],403)
            self.assertEqual(self.request('POST','/api/display/page',{'page_id':'rain','revision':d['revision']},headers)[0],403)
        self.assertEqual(self.request('GET','/api/display',headers={'Host':'bad.invalid'})[0],403)

    def test_save_and_page_selection_do_not_call_providers_or_key_notifications(self):
        self.login();d=self.values();layout=d['layout'];layout['pages'][0]['title']='Testseite'
        self.service.on_layout_change=lambda value,page_id:self.service.publish_display(page_id,revision(value))
        self.service.on_page_change=lambda page_id:self.service.publish_display(page_id,revision(self.store.load_dashboard()))
        with patch('wetterstation.weather.weather_service.OpenWeatherClient._request',side_effect=AssertionError('no weather HTTP')) as weather,patch('wetterstation.maps.radar_map.RadarMapClient.fetch',side_effect=AssertionError('no map HTTP')) as radar:
            status,_,body=self.request('POST','/api/dashboard',{'layout':layout,'revision':d['revision'],'page_id':'overview'})
            self.assertEqual(status,200);rev=json.loads(body)['revision']
            self.assertEqual(self.request('POST','/api/display/page',{'page_id':'rain','revision':rev})[0],200)
            weather.assert_not_called();radar.assert_not_called()
        self.assertEqual(self.notifications,[])
        self.assertEqual(self.store.load_api_key(),'dummy-original-key')
        self.assertEqual(json.loads(self.request('GET','/api/display')[2])['page_id'],'rain')

    def test_conflicts_invalid_payloads_and_storage_errors_are_safe(self):
        self.login();d=self.values();layout=d['layout'];layout['pages'][0]['title']='Updated'
        payload={'layout':layout,'revision':d['revision'],'page_id':'overview'}
        self.assertEqual(self.request('POST','/api/dashboard',payload)[0],200)
        good=self.store.path.read_bytes()
        self.assertEqual(self.request('POST','/api/dashboard',payload)[0],409)
        self.assertEqual(self.request('POST','/api/display/page',{'page_id':'rain','revision':d['revision']})[0],409)
        payload['revision']=self.values()['revision']
        for change in ({'page_id':'missing'},{'layout':{}},{'layout':{'version':2,'pages':[]}}):
            self.assertEqual(self.request('POST','/api/dashboard',dict(payload,**change))[0],400)
            self.assertEqual(self.store.path.read_bytes(),good)
        with patch.object(self.store,'_write_settings',side_effect=OSError('dummy-private-key')):
            status,_,body=self.request('POST','/api/dashboard',payload)
            self.assertEqual(status,503);self.assertNotIn(b'dummy-private-key',body)
        self.assertEqual(self.store.path.read_bytes(),good)

    def test_request_bounds_static_assets_and_csp_remain_restricted(self):
        self.login()
        self.assertEqual(self.request('POST','/api/dashboard',raw=b' '*32769)[0],400)
        status,headers,body=self.request('GET','/layout.js')
        self.assertEqual(status,200);self.assertIn(b'WidgetLayout',body)
        self.assertNotIn('unsafe-inline',headers['Content-Security-Policy'])
        self.assertEqual(self.request('GET','/private/settings.json')[0],404)

    def test_layout_only_demo_rejects_location_and_key_writes(self):
        self.service.layout_only=True
        self.login();before=self.store.path.read_bytes()
        self.assertTrue(self.values()['demo'])
        self.assertEqual(self.request('POST','/api/settings',{'location':'Berlin','api_key':'dummy-replacement'})[0],403)
        self.assertEqual(self.store.path.read_bytes(),before)
        self.assertEqual(self.notifications,[])


class WidgetTkTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.store=ApiKeyStore(path=Path(self.folder.name)/'settings.json')
        self.root=tk.Tk();self.root.withdraw()
        with patch('wetterstation.ui.app.ApiKeyStore',return_value=self.store):self.preview=WeatherPreview(self.root,mock_preview=True)
        self.preview.canvas.winfo_width=lambda:1024
        self.preview.canvas.winfo_height=lambda:600

    def tearDown(self):
        self.preview.mock_preview=True
        self.root.update()
        self.preview.close();del self.preview;gc.collect();self.folder.cleanup()

    def test_every_catalog_widget_all_fields_fit_its_minimum_and_no_scroll(self):
        for kind,spec in CATALOG.items():
            if kind=='radar':continue
            with self.subTest(kind=kind):
                item=new_widget(kind,'check',w=spec['min_width'],h=spec['min_height'])
                item['fields']=list(spec['fields'])
                self.preview.dashboard={'version':2,'pages':[{'id':'check','title':'Widgetprüfung','widgets':[item]}]}
                self.preview.page=0;self.preview.draw()
                c=self.preview.canvas;card=c.bbox('widget-check')
                texts=[c.itemcget(i,'text') for i in c.find_withtag('widget-content-check') if c.type(i)=='text']
                if kind in ('hourly','daily'):
                    count=len(getattr(self.preview.forecast_record,kind))
                    self.assertEqual(len(texts),1+count*(1+len(item['fields'])))
                else:
                    # Fitting must never silently drop a field or abbreviate a value.
                    for value,_ in self.preview._widget_lines(item):
                        self.assertIn(' '.join(value.split()),[' '.join(t.split()) for t in texts])
                for text in c.find_withtag('widget-content-check'):
                    if c.type(text)=='text':
                        bounds=c.bbox(text)
                        self.assertGreaterEqual(bounds[0],card[0]);self.assertGreaterEqual(bounds[1],card[1])
                        self.assertLessEqual(bounds[2],card[2]);self.assertLessEqual(bounds[3],card[3],c.itemcget(text,'text'))
                self.assertEqual(c.cget('scrollregion'),'0 0 1024 600')
                self.assertFalse(self.preview.scrollbar.winfo_manager())

    def test_hiding_fields_keeps_card_geometry_and_empty_widget_is_blank(self):
        self.preview.draw();c=self.preview.canvas
        geometry=c.coords(c.find_withtag('widget-clock')[0])
        w=self.preview.dashboard['pages'][0]['widgets'][0]
        w['fields']=['time'];self.preview.draw()
        self.assertEqual(geometry,c.coords(c.find_withtag('widget-clock')[0]))
        self.assertFalse(c.find_withtag('clock-clock-date'))
        w['fields']=[];self.preview.draw()
        self.assertEqual(geometry,c.coords(c.find_withtag('widget-clock')[0]))
        self.assertFalse(any(c.type(i)=='text' for i in c.find_withtag('widget-content-clock')))

    def test_live_layout_and_page_selection_use_ui_queue_and_preserve_page_ids(self):
        layout=default_layout();layout['pages'].reverse()
        with patch.object(self.preview,'refresh_weather') as weather,patch.object(self.preview,'refresh_radar') as radar:
            self.preview._results.put(lambda:self.preview._apply_mobile_dashboard(layout,'rain'))
            self.preview._results.get()()
            self.assertEqual(self.preview._current_page()['id'],'rain')
            self.preview._show_mobile_page('forecast')
            self.assertEqual(self.preview._current_page()['id'],'forecast')
            self.preview.change_page(1)
            self.assertEqual(self.preview._current_page()['id'],'overview')
            weather.assert_not_called();radar.assert_not_called()

    def test_restart_loads_saved_layout_and_starts_first_page(self):
        layout=default_layout();layout['pages'].reverse();self.store.save_dashboard(layout,revision(default_layout()))
        self.root.update()
        self.preview.close()
        self.root=tk.Tk();self.root.withdraw()
        with patch('wetterstation.ui.app.ApiKeyStore',return_value=self.store):self.preview=WeatherPreview(self.root,mock_preview=True)
        self.assertEqual(self.preview.dashboard,layout)
        self.assertEqual(self.preview.page,0)

    def test_widget_demo_never_opens_real_settings_or_starts_sources(self):
        self.root.update()
        self.preview.close();self.root=tk.Tk();self.root.withdraw()
        with patch('wetterstation.ui.app.ApiKeyStore',side_effect=AssertionError('no real settings')) as real_store,patch('wetterstation.weather.weather_service.OpenWeatherClient._request',side_effect=AssertionError('no HTTP')) as weather,patch('wetterstation.maps.radar_map.RadarMapClient.fetch',side_effect=AssertionError('no WMS')) as radar:
            self.preview=WeatherPreview(self.root,widget_demo=True,settings_store=self.store)
            self.root.update()
            self.root.update()
            self.assertTrue(self.preview.mock_preview)
            self.assertFalse(any(isinstance(w, tk.Toplevel) for w in self.root.winfo_children()))
            self.assertIsNone(self.preview.mobile_service)
            real_store.assert_not_called();weather.assert_not_called();radar.assert_not_called()

    def draw_compact_map(self):
        with patch.object(self.preview,'_map_position',return_value=POTSDAM),patch.object(self.preview,'_queue_radar_render'),patch.object(self.preview,'schedule_radar_refresh'):
            self.preview.draw()
            while self.preview._widget_map_active:
                self.preview._results.get(timeout=10)()

    def compact_map(self):
        self.preview.mock_preview=False
        self.preview.radar_error=''
        self.preview.radar_result=map_tests.FullWindowMapTests.fixture()
        item=new_widget('radar','compact-map',w=6,h=4)
        self.preview.dashboard={'version':2,'pages':[{'id':'map','title':'Regenkarte','widgets':[item]}]}
        self.preview.page=0
        return item

    def test_compact_radar_uses_aligned_cached_images_without_provider_calls(self):
        self.compact_map()
        with patch('wetterstation.maps.radar_map.RadarMapClient.fetch',side_effect=AssertionError('no HTTP')) as fetch:
            self.draw_compact_map()
            images=list(self.preview._widget_map_cache.values())[0]
            self.assertGreater(images[0].width(),460)
            self.assertGreater(images[0].height(),170)
            self.assertEqual((images[1].width(),images[1].height()),(images[0].width(),images[0].height()))
            self.assertEqual(len(self.preview.canvas.find_withtag('widget-map')),2)
            with patch.object(self.preview,'_start_worker') as workers:
                self.draw_compact_map();workers.assert_not_called()
            fetch.assert_not_called()

    def test_compact_map_independent_time_field_and_warnings_survive_hiding_time(self):
        item=self.compact_map();item['fields']=['updated']
        self.draw_compact_map()
        labels=lambda:[self.preview.canvas.itemcget(i,'text') for i in self.preview.canvas.find_all() if self.preview.canvas.type(i)=='text']
        self.assertIn(self.preview.radar_result.fetched_at.astimezone(self.preview._display_zone()).strftime('%d.%m. %H:%M'),labels())
        self.assertFalse(self.preview.canvas.find_withtag('widget-map'))
        item['fields']=['map']
        self.preview.radar_result=replace(self.preview.radar_result,stale=True)
        self.draw_compact_map()
        self.assertTrue(any('Zwischengespeichert' in s for s in labels()))
        self.assertEqual(len(self.preview.canvas.find_withtag('widget-map')),2)

    def test_old_place_and_failed_compact_map_never_show_wrong_or_unprepared_images(self):
        self.compact_map()
        self.preview.radar_result=replace(self.preview.radar_result,position=MapPosition('Berlin','Berlin',52.5,13.4))
        self.draw_compact_map();self.assertFalse(self.preview.canvas.find_withtag('widget-map'))
        self.preview.radar_result=map_tests.FullWindowMapTests.fixture()
        with patch('wetterstation.ui.dashboard.prepare_radar_layers',side_effect=ValueError('dummy-secret')):
            self.draw_compact_map()
        self.assertFalse(self.preview.canvas.find_withtag('widget-map'))
        labels=[self.preview.canvas.itemcget(i,'text') for i in self.preview.canvas.find_all() if self.preview.canvas.type(i)=='text']
        self.assertTrue(any('konnte nicht vorbereitet' in s for s in labels))
        self.assertNotIn('dummy-secret',' '.join(labels))
        with patch.object(self.preview,'_start_worker') as workers:
            self.draw_compact_map();workers.assert_not_called()


if __name__=='__main__':unittest.main()

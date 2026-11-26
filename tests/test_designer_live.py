"""Default-off production integration, using dummy settings and injected responses."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from urllib.parse import urlsplit,parse_qs

from wetterstation.designer import model
from wetterstation.designer.activation import ActivationStore
from wetterstation.designer.live_timelines import collect
from wetterstation.designer.timeline_client import snapshot,read_snapshot,TimelineAdapter
from wetterstation.designer.series import regular_remaining
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.widgets import revision
from wetterstation.weather.countries import location_query
from wetterstation.weather.weather_service import OpenWeatherClient,WeatherServiceError,normalize_query
from tools.pi import design as pi
from test_one_call_v4 import FakeResponse


class LiveTimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.root=Path(self.tmp.name)
        self.settings=ApiKeyStore(self.root/'private/settings.json')
        self.settings.save_configuration('Testort','dummy-key',country_code='DE')
        self.query=location_query('Testort','DE');self.now=datetime(2026,10,27,12,tzinfo=timezone.utc)
        self.doc=model.from_layout();w=self.doc['pages'][0]['widgets'][0]
        w.update(type='series',fields=[],series=model.default_series());self.doc['pages'][0]['widgets']=[w]
        self.settings.save_dashboard(self.doc,revision(self.settings.load_dashboard()))
        self.flag=ActivationStore(self.root/'private/designer',binding=lambda:'dummy-device-A')
        self.client=OpenWeatherClient(cache_dir=self.root/'cache')
        self.client._places[normalize_query(self.query)]={'name':'Testort','country':'DE','lat':52.4,'lon':13.1}
        self.client._request=Mock(side_effect=self.request)
        self.calls=[]

    def tearDown(self):self.tmp.cleanup()

    def enable(self):self.flag.configure(self.settings,True,revision(self.doc))

    def request(self,url,**kwargs):
        self.calls.append((url,kwargs));source=urlsplit(url).path.rsplit('/',1)[1]
        step={'1min':60,'15min':900,'1h':3600,'1day':86400}[source]
        count={'1min':60,'15min':50,'1h':20,'1day':10}[source]
        start=int(parse_qs(urlsplit(url).query).get('start',[int(self.now.timestamp())])[0])
        rows=[{'dt':start+i*step,'temp':10+i/10,'precipitation':i/100,'humidity':50} for i in range(count)]
        return {'data':rows,'next':f'https://api.openweathermap.org/data/4.0/onecall/timeline/{source}?start={start+step*count}&appid=dummy-key'}

    def run_collect(self,**kwargs):return collect(self.client,self.settings,self.doc,self.query,'dummy-key',now=self.now,activation=self.flag,**kwargs)

    def test_absent_corrupt_or_copied_permission_is_off_and_does_not_create_files(self):
        before=self.settings.path.read_bytes()
        for value in (None,b'bad',b'{"schema":1,"enabled":true,"device":"other"}'):
            if value is not None:self.flag.path.parent.mkdir(exist_ok=True);self.flag.path.write_bytes(value)
            result,notes=self.run_collect();self.assertEqual(result['15min'],[])
            self.assertTrue(notes['15min']);self.assertEqual(self.calls,[])
        self.assertEqual(before,self.settings.path.read_bytes());self.assertFalse((self.root/'cache').exists())

    def test_activation_is_device_local_does_not_fetch_and_style_changes_preserve_it(self):
        before=self.settings.path.read_bytes();self.enable()
        self.assertEqual(self.calls,[]);self.assertEqual(before,self.settings.path.read_bytes())
        copied=ActivationStore(self.flag.path.parent,binding=lambda:'dummy-device-B')
        self.assertEqual(copied.state(self.doc),'other_device')
        changed=deepcopy(self.doc);changed['style']['radius']=0
        self.assertEqual(self.flag.state(changed),'on')
        changed['pages'][0]['widgets'][0]['series']['refresh']=120
        self.assertEqual(self.flag.state(changed),'changed')
        with self.assertRaises(ValueError):self.flag.configure(self.settings,True,'bad-revision')

    def test_enabled_shared_pagination_persists_and_reuses_across_rounds(self):
        self.doc['pages'][0]['widgets'][0]['series']['duration']=1440
        self.settings.save_dashboard(self.doc,revision(self.settings.load_dashboard()));self.enable()
        rows,notes=self.run_collect();self.assertEqual(len(self.calls),2);self.assertEqual(len(rows['15min']),100)
        self.assertTrue(all(c[1]['protected']==regular_remaining(self.now)+24 for c in self.calls))
        self.now+=timedelta(minutes=5);self.run_collect();self.assertEqual(len(self.calls),2)
        self.assertNotIn('dummy-key',''.join(p.read_text() for p in (self.root/'cache').glob('*.json')))
        self.now+=timedelta(minutes=60);self.run_collect();self.assertEqual(len(self.calls),4)

    def test_disable_mid_page_and_location_change_stop_more_requests(self):
        self.doc['pages'][0]['widgets'][0]['series']['duration']=1440
        self.settings.save_dashboard(self.doc,revision(self.settings.load_dashboard()));self.enable()
        def disable(url,**kwargs):
            result=self.request(url,**kwargs);self.flag.configure(self.settings,False,revision(self.doc));return result
        self.client._request.side_effect=disable
        rows,notes=self.run_collect();self.assertEqual(len(self.calls),1);self.assertTrue(notes['15min']);self.assertTrue(rows['15min'])
        self.enable();self.settings.save_configuration('Testort','dummy-key',country_code='FR')
        self.now+=timedelta(hours=2);self.run_collect();self.assertEqual(len(self.calls),1)

    def test_closed_or_stale_worker_and_overfull_budget_make_no_calls(self):
        self.enable();self.run_collect(current=lambda:False);self.assertEqual(self.calls,[])
        self.doc['pages'][0]['widgets'][0]['series']['refresh']=5
        self.settings.save_dashboard(self.doc,revision(self.settings.load_dashboard()))
        with self.assertRaises(ValueError):self.enable()
        self.run_collect();self.assertEqual(self.calls,[])

    def test_full_regular_first_page_reused_and_fresh_base_merges_during_tail_ttl(self):
        widget=self.doc['pages'][0]['widgets'][0];widget['series'].update(source='1h',step=60,duration=1440)
        self.settings.save_dashboard(self.doc,revision(self.settings.load_dashboard()));self.enable()
        payload=self.request('https://api.openweathermap.org/timeline/1h');self.calls.clear()
        self.client._save(self.query,'timeline-base-1h',snapshot(payload,'1h',self.query,self.now))
        rows,_=self.run_collect();self.assertEqual(len(self.calls),1);self.assertEqual(len(rows['1h']),40)
        self.now+=timedelta(minutes=5);payload['data'][0]['temp']=99
        self.client._save(self.query,'timeline-base-1h',snapshot(payload,'1h',self.query,self.now))
        rows,_=self.run_collect();self.assertEqual(len(self.calls),1)
        self.assertEqual(rows['1h'][0]['temp'],99)

    def test_off_can_display_existing_base_without_fetch_and_expired_cache_disappears(self):
        self.doc['pages'][0]['widgets'][0]['series'].update(source='1h',step=60)
        payload=self.request('https://api.openweathermap.org/timeline/1h');self.calls.clear()
        saved=snapshot(payload,'1h',self.query,self.now)
        self.client._save(self.query,'timeline-base-1h',saved)
        rows,_=self.run_collect();self.assertEqual(len(rows['1h']),20);self.assertEqual(self.calls,[])
        self.now+=timedelta(hours=7);rows,_=self.run_collect();self.assertEqual(rows['1h'],[])
        with self.assertRaises(ValueError):read_snapshot(saved,'1h',location_query('Testort','FR'),self.now)

    def test_long_running_minute_cache_retains_future_samples(self):
        self.doc['pages'][0]['widgets'][0]['series'].update(source='1min',step=1,duration=60,refresh=30,fields=['precipitation'])
        adapter=TimelineAdapter(lambda source,start,protected:self.request('https://api.openweathermap.org/timeline/1min'))
        for _ in range(30):
            rows,_=adapter.collect(self.doc,self.query,self.now);self.assertGreaterEqual(len(rows['1min']),60)
            self.assertGreaterEqual(datetime.fromisoformat(rows['1min'][-1]['timestamp']),self.now+timedelta(minutes=59))
            self.now+=timedelta(minutes=30)

    def test_real_request_reserves_protected_budget_before_transport(self):
        # Exercise actual _request with an injected opener, never a socket.
        client=OpenWeatherClient(cache_dir=self.root/'other');client.budget=Mock()
        client._opener=Mock();client._opener.open.return_value=FakeResponse({'data':[]})
        client._request('https://api.openweathermap.org/data/4.0/onecall/timeline/15min?appid=dummy-key',protected=300)
        client.budget.reserve_call.assert_called_once_with(protected=300)

    def test_regular_cycle_keeps_three_requests_and_saves_full_pages_without_keyed_urls(self):
        from test_one_call_v4 import OneCallV4Tests
        client=self.client;client._request=OpenWeatherClient._request.__get__(client)
        client.budget=Mock();client._opener=Mock()
        current=OneCallV4Tests.current_payload();hourly=OneCallV4Tests.hourly_payload(20);daily=OneCallV4Tests.daily_payload(10)
        hourly['next']='https://api.openweathermap.org/data/4.0/onecall/timeline/1h?start=1794000000&appid=dummy-key'
        client._opener.open.side_effect=[FakeResponse(current),FakeResponse(hourly),FakeResponse(daily)]
        client.fetch(self.query,'dummy-key',force=True);forecast=client.fetch_forecast(self.query,'dummy-key',force=True)
        self.assertEqual(client._opener.open.call_count,3);self.assertEqual(len(forecast.hourly),8);self.assertEqual(len(forecast.daily),5)
        full=client._load_json(client._cache_path(self.query,'timeline-base-1h'))
        self.assertEqual(len(full['rows']),20);self.assertEqual(full['next_start'],1794000000)
        self.assertNotIn('dummy-key',json.dumps(full));self.assertNotIn('https:',json.dumps(full))

    def test_provider_errors_throttle_without_exposing_key_or_stopping_base(self):
        self.enable();self.client._request.side_effect=WeatherServiceError('Anfragepause')
        rows,notes=self.run_collect();self.assertIn('unvollständig',notes['15min']);self.assertEqual(rows['15min'],[])
        self.now+=timedelta(minutes=1);self.run_collect();self.assertEqual(self.client._request.call_count,1)
        self.now+=timedelta(minutes=10);self.run_collect();self.assertEqual(self.client._request.call_count,1)

    def test_live_pagination_yields_before_next_regular_slot(self):
        self.enable();self.now=self.now.replace(minute=4,second=50)
        with patch('wetterstation.designer.live_timelines.datetime',wraps=datetime) as clock:
            clock.now.return_value=self.now
            result,notes=collect(self.client,self.settings,self.doc,self.query,'dummy-key',activation=self.flag)
        self.assertEqual(self.calls,[]);self.assertTrue(notes['15min']);self.assertEqual(result['15min'],[])

    def test_pi_activation_is_separate_and_does_not_start_application(self):
        (self.root/'app.py').write_text('# isolated dummy')
        with patch('tools.pi.update.running_processes',return_value=[]),patch('wetterstation.designer.activation.device_binding',return_value='dummy-pi'):
            self.assertEqual(pi.status(self.root)['timelines']['state'],'off')
            enabled=pi.configure_timelines(self.root,True,revision(self.doc))
            self.assertFalse(enabled['running']);self.assertEqual(enabled['timelines']['state'],'on')
            disabled=pi.configure_timelines(self.root,False,revision(self.doc));self.assertEqual(disabled['timelines']['state'],'off')
        self.assertEqual(self.calls,[])

    def test_display_and_widget_cache_change_when_activation_notice_changes(self):
        from wetterstation.designer.render import render_page,demo_data
        from wetterstation.designer.runtime import static_key
        data=demo_data();data['now']=self.now
        data['series']={'15min':[{'timestamp':self.now.isoformat(),'temp':10}]}
        page=self.doc['pages'][0];cache={}
        key=static_key(self.doc,page,data)
        first=render_page(self.doc,page['id'],data,self.root,cache=cache)[0]
        data['series_notices']={'15min':'Zusatzabrufe ausgeschaltet'}
        self.assertNotEqual(key,static_key(self.doc,page,data))
        second=render_page(self.doc,page['id'],data,self.root,cache=cache)[0]
        self.assertNotEqual(first.tobytes(),second.tobytes())

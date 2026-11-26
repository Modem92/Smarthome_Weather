"""International acceptance contracts. All provider traffic is simulated."""
import gc
import json
import math
import tempfile
import tkinter as tk
import unittest
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview, next_weather_refresh
from wetterstation.weather.countries import COUNTRIES, legacy_country, location_query
from wetterstation.maps.international_map import InternationalMapClient, viewport, ZOOM, MERCATOR_LIMIT, png
from wetterstation.weather.location_time import weather_zone
from wetterstation.maps.radar_map import MapPosition, RadarMapClient, RadarMapError
from wetterstation.maps.radar_motion import usable_pair, fresh_source
from wetterstation.maps.radar_render import RadarRenderRequest, prepare_radar_layers
from wetterstation.weather.weather_service import OpenWeatherClient, WeatherServiceError
from PIL import Image, ImageDraw

CITIES = (
    ("Potsdam", "DE", 52.3989, 13.0657, "14467", "Europe/Berlin"),
    ("Wien", "AT", 48.2082, 16.3738, "1010", "Europe/Vienna"),
    ("Paris", "FR", 48.8566, 2.3522, "75001", "Europe/Paris"),
    ("London", "GB", 51.5074, -.1278, "SW1A 1AA", "Europe/London"),
    ("New York", "US", 40.7128, -74.006, "10001", "America/New_York"),
    ("Tokio", "JP", 35.6762, 139.6503, "100-0001", "Asia/Tokyo"),
)


class InternationalSettingsTests(unittest.TestCase):
    def test_full_offline_german_catalog_and_legacy_country_migration(self):
        self.assertEqual(len(COUNTRIES), 249)
        self.assertEqual(location_query('Luxemburg','LU'),'Luxemburg, LU')
        cases = {"Potsdam, 14467, Deutschland": "DE", "14467": "DE", "Berlin": "DE",
                 "Wien, Österreich": "AT", "Paris, France": "FR", "London, GB": "GB",
                 "Tokio, Japan": "JP", "Paris, unbekanntes Land": ""}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            store = ApiKeyStore(Path(folder) / "settings.json")
            for location, code in cases.items():
                store._write_settings({"location": location, "openweather_api_key": "dummy-key"})
                self.assertEqual(store.load_country_code(), code)
                self.assertEqual(store.load_api_key(), "dummy-key")
            store._write_settings({"location": "Paris", "country_code": "XX"})
            self.assertEqual(store.load_country_code(), "")

    def test_country_place_key_and_layout_are_atomically_preserved_after_restart(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            path = Path(folder) / "settings.json"
            store = ApiKeyStore(path)
            original = {"openweather_api_key": "dummy-key", "dashboard": {"preserved": True}, "other": "keep"}
            store._write_settings(original)
            store.save_configuration("Paris", country_code="FR")
            restarted = ApiKeyStore(path)
            self.assertEqual((restarted.load_location(), restarted.load_country_code()), ("Paris", "FR"))
            self.assertEqual({k: restarted._read_settings()[k] for k in original}, original)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                store.save_configuration("Paris", country_code="XX")
            self.assertEqual(path.read_bytes(), before)


class InternationalWeatherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.client = OpenWeatherClient(Path(self.temp.name))
        self.calls = []

    def test_six_cities_and_postcodes_use_only_selected_country_and_shared_position(self):
        for name, code, lat, lon, postal, zone in CITIES:
            place = dict(name=name, country=code, lat=lat, lon=lon)
            with self.subTest(city=name), patch.object(self.client, "_request", return_value=place) as request:
                result = self.client._place(location_query(postal, code), "dummy")
                params = parse_qs(urlsplit(request.call_args.args[0]).query)
                self.assertEqual(params["zip"], [f"{postal},{code}"])
                self.assertEqual(self.client.load_resolved_place(location_query(postal, code)), place)
            with patch.object(self.client, "_request", return_value=[place, dict(place, country="ZZ")]) as request:
                self.assertEqual(self.client._resolve(location_query(name, code), "dummy"), place)
                self.assertEqual(parse_qs(urlsplit(request.call_args.args[0]).query)["q"], [f"{name},{code}"])

    def test_additional_international_postcodes_and_combined_german_input(self):
        for query, code, postal in (("Ottawa, K1A 0B1", "CA", "K1A 0B1"), ("1012 AB", "NL", "1012 AB"),
                                    ("New York, 10001-1234", "US", "10001-1234"),
                                    ("VLT 1117", "MT", "VLT 1117"), ("LV-1050", "LV", "LV-1050"),
                                    ("Potsdam 14467", "DE", "14467")):
            place = dict(name="Test", country=code, lat=30., lon=20.)
            with patch.object(self.client, "_request", return_value=place) as request:
                self.client._resolve(location_query(query, code), "dummy")
                self.assertEqual(parse_qs(urlsplit(request.call_args.args[0]).query)["zip"], [f"{postal},{code}"])

    def test_weather_and_both_forecasts_for_all_six_places_use_local_time_and_coordinates(self):
        instant = datetime.fromisoformat('2026-10-24T23:30:00+00:00')
        stamp = int(instant.timestamp())
        for name,code,lat,lon,postal,zone in CITIES:
            query=location_query(name,code)
            place=dict(name=name,country=code,lat=lat,lon=lon)
            self.client._places[query.casefold()]=place
            def respond(url):
                params=parse_qs(urlsplit(url).query)
                self.assertAlmostEqual(float(params['lat'][0]),lat)
                self.assertAlmostEqual(float(params['lon'][0]),lon)
                row=dict(dt=stamp,humidity=60,pressure=1012,wind_speed=2,feels_like=11,pop=.3,
                         temp=dict(min=8,max=15,day=12) if '/1day?' in url else 12)
                return dict(timezone=zone,data=[row])
            with self.subTest(city=name), patch.object(self.client,'_request',side_effect=respond) as request:
                weather=self.client.fetch(query,'dummy')
                forecast=self.client.fetch_forecast(query,'dummy')
                self.assertEqual(request.call_count,3)
                self.assertEqual(weather.timezone,zone);self.assertEqual(forecast.timezone,zone)
                expected=instant.astimezone(weather_zone(weather)[0]).isoformat(timespec='minutes')
                self.assertEqual(weather.observed_at,expected)
                self.assertEqual(forecast.hourly[0].timestamp,expected)
                self.assertEqual(forecast.daily[0].timestamp,expected)

    def test_unknown_country_wrong_country_and_ambiguous_results_are_rejected(self):
        with patch.object(self.client, "_request") as request:
            with self.assertRaises(WeatherServiceError):
                self.client._resolve("Paris", "dummy")
            request.assert_not_called()
        for results in ([dict(name="Paris", country="US", lat=33., lon=-95.)],
                        [dict(name="Paris", country="FR", lat=48., lon=2.),
                         dict(name="Paris", country="FR", lat=49., lon=3.)]):
            with patch.object(self.client, "_request", return_value=results):
                with self.assertRaises(WeatherServiceError):
                    self.client._resolve("Paris, FR", "dummy")
        with patch.object(self.client, "_request", return_value=dict(name="Paris", country="US", lat=33., lon=-95.)):
            with self.assertRaises(WeatherServiceError):
                self.client._resolve("75001, FR", "dummy")

    def test_equal_names_in_different_countries_have_separate_place_and_weather_caches(self):
        for code, lat, lon in (("FR", 48., 2.), ("US", 33., -95.)):
            query = location_query("Paris", code)
            place = dict(name="Paris", country=code, lat=lat, lon=lon)
            self.client._save(query, "place", dict(query=query.casefold(), place=place))
            self.assertEqual(self.client.load_resolved_place(query), place)
            stamp = int(datetime.now(timezone.utc).timestamp())
            payload = {"timezone": "Europe/Paris" if code == "FR" else "America/Chicago", "data": [dict(
                dt=stamp, temp=10, feels_like=9, humidity=60, pressure=1000, wind_speed=2)]}
            with patch.object(self.client, "_request", return_value=payload):
                self.assertEqual(self.client.fetch(query, "dummy").country, code)
        restarted = OpenWeatherClient(Path(self.temp.name))
        for code in ("FR", "US"):
            self.assertEqual(restarted.load_cached(location_query("Paris", code)).country, code)
            self.assertEqual(restarted.load_resolved_place(location_query("Paris", code))["country"], code)
        # Even a corrupted/wrong-country file cannot enter the map or weather display.
        query = "Paris, FR"
        wrong = dict(name="Paris", country="US", lat=33., lon=-95.)
        restarted._save(query, "place", dict(query=query.casefold(), place=wrong))
        restarted._places.clear()
        restarted._volatile.clear()
        self.assertEqual(restarted.load_resolved_place(query)["country"], "FR")  # valid weather record wins

    def test_civil_time_handles_dst_and_date_line_with_explicit_utc_fallback(self):
        cases = (("2026-03-29T00:59:00+00:00", "Europe/Paris", "2026-03-29T01:59+01:00"),
                 ("2026-03-29T01:01:00+00:00", "Europe/Paris", "2026-03-29T03:01+02:00"),
                 ("2026-11-01T05:30:00+00:00", "America/New_York", "2026-11-01T01:30-04:00"),
                 ("2026-11-01T06:30:00+00:00", "America/New_York", "2026-11-01T01:30-05:00"),
                 ("2026-10-24T23:30:00+00:00", "Asia/Tokyo", "2026-10-25T08:30+09:00"),
                 ("2026-10-24T12:30:00+00:00", "Pacific/Kiritimati", "2026-10-25T02:30+14:00"))
        for instant, zone, expected in cases:
            stamp = datetime.fromisoformat(instant).timestamp()
            self.assertEqual(self.client._local_iso(stamp, zone), expected)
        self.assertFalse(weather_zone()[1])
        self.assertFalse(weather_zone(SimpleNamespace(timezone="invalid"))[1])
        self.assertEqual(self.client._local_iso(0, "invalid", 7200), "1970-01-01T00:00+00:00")
        preview = object.__new__(WeatherPreview)
        preview.weather_record = preview.forecast_record = None
        self.assertTrue(preview._clock_text("time", []).endswith(" UTC"))
        for row in CITIES:
            preview.weather_record = SimpleNamespace(timezone=row[-1])
            self.assertEqual(preview._display_zone().key, row[-1])
        instant = datetime.fromisoformat("2026-10-24T23:59:00+09:00")
        self.assertEqual(next_weather_refresh(instant).timestamp(), (int(instant.timestamp()) // 300 + 1) * 300)


class InternationalMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.client = InternationalMapClient(self.temp.name)
        self.position = MapPosition("Paris", "Paris", 48.8566, 2.3522, "FR")
        self.stamp = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=5)
        self.requests = []
        self.mask = "full"
        self.metadata_error = False
        self.network = patch.object(self.client, "_download", side_effect=self.respond)
        self.network.start()
        self.addCleanup(self.network.stop)

    def respond(self, url, headers=None):
        self.requests.append((url, headers))
        if url.endswith("weather-maps.json"):
            if self.metadata_error:
                raise TimeoutError("private-error")
            return json.dumps(dict(host="https://tilecache.rainviewer.com", radar=dict(past=[
                dict(time=int(self.stamp.timestamp()), path=f"/v2/radar/{int(self.stamp.timestamp())}")]))).encode(), {}, 200
        if "openstreetmap" in url:
            image = Image.new("RGBA", (256,256), (232,240,215,255))
        elif "/coverage/" in url:
            image = Image.new("RGBA", (256,256), (0,0,0,255 if self.mask == "none" else 0))
            if self.mask == "partial":
                ImageDraw.Draw(image).rectangle((0,0,127,255), fill=(0,0,0,255))
        else:
            image = Image.new("RGBA", (256,256), (0,180,220,255))
        return png(image), {"Cache-Control": "max-age=604800", "ETag": '"test"'}, 200

    def test_shared_xyz_alignment_only_viewport_tiles_and_observation_reuse(self):
        result = self.client.fetch(320,240,self.position)
        left, top, tiles = viewport(320,240,self.position)
        self.assertLessEqual(len(tiles), 6)
        for x,y in tiles:
            xyz = f"/{ZOOM}/{x}/{y}"
            self.assertEqual(sum(xyz in url for url,_ in self.requests), 3)
        count = len(self.requests)
        again = self.client.fetch(320,240,self.position)
        self.assertEqual(len(self.requests), count + 1)
        self.assertEqual(result.fetched_at, again.fetched_at)
        self.assertIs(result.basemap, again.basemap)
        self.assertIs(result.radar, again.radar)
        self.assertFalse(fresh_source(result))
        self.assertFalse(usable_pair(result, replace(result, observed_at=result.observed_at-timedelta(minutes=10))))

    def test_new_frame_reuses_osm_and_coverage_tiles_after_restart(self):
        self.stamp -= timedelta(minutes=10)
        first = self.client.fetch(320,240,self.position)
        self.client._memory.clear()
        self.requests.clear()
        self.client.fetch(320,240,self.position)
        self.assertEqual(len(self.requests),1)
        self.stamp += timedelta(minutes=10)
        self.requests.clear()
        self.client.fetch(320,240,self.position)
        self.assertFalse(any("openstreetmap" in url or "/coverage/" in url for url,_ in self.requests))

    def test_coverage_full_partial_none_remains_visible_and_rain_is_masked(self):
        for mask in ("full", "partial", "none"):
            with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
                client = InternationalMapClient(folder)
                self.mask = mask
                with patch.object(client,"_download",side_effect=self.respond):
                    result = client.fetch(320,240,self.position)
                self.assertEqual(result.coverage_status, mask)
                base, radar = prepare_radar_layers(RadarRenderRequest(result,(320,240),"Paris, FR",0))
                with Image.open(BytesIO(radar)) as image:
                    self.assertLessEqual(image.getchannel("A").getextrema()[1],158)
                    if mask == "none":
                        self.assertEqual(image.convert("RGB").getpixel((10,10)), (85,94,108))

    def test_failure_retains_only_valid_same_place_cache_and_requires_mask(self):
        first = self.client.fetch(320,240,self.position)
        self.metadata_error=True
        again = self.client.fetch(320,240,self.position)
        self.assertTrue(again.stale)
        self.assertEqual(again.fetched_at, first.fetched_at)
        restarted = InternationalMapClient(self.temp.name)
        with patch.object(restarted,"_metadata",side_effect=TimeoutError):
            self.assertTrue(restarted.fetch(320,240,self.position).stale)
            with self.assertRaises(RadarMapError):
                restarted.fetch(320,240,replace(self.position,country="US"))
        self.client._memory.clear()
        manifest = next((Path(self.temp.name)/"frames").glob("*.json"))
        meta=json.loads(manifest.read_text());meta["fetched"]=(self.stamp-timedelta(hours=2)).isoformat()
        manifest.write_text(json.dumps(meta))
        with self.assertRaises(RadarMapError):
            self.client.fetch(320,240,self.position)

    def test_no_osm_background_downloads_and_explicit_polar_limit(self):
        with self.assertRaises(RadarMapError):
            self.client.fetch(320,240,self.position,allow_basemap_download=False)
        self.assertFalse(any("openstreetmap" in url for url,_ in self.requests))
        for lat in (-86.,86.):
            with self.assertRaisesRegex(RadarMapError,"Breitengrad"):
                self.client.fetch(320,240,replace(self.position,lat=lat))
        for lat in (-85.,85.):
            result = self.client.fetch(320,240,replace(self.position,lat=lat))
            self.assertEqual(result.coverage_status,"partial")

    def test_missing_mask_corrupt_png_wrong_size_and_untrusted_metadata_never_look_dry(self):
        for kind in ('missing-mask','wrong-size','bad-png','untrusted-host','expired-frame'):
            with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
                client=InternationalMapClient(folder)
                def respond(url,headers=None):
                    if kind=='missing-mask' and '/coverage/' in url:
                        raise TimeoutError('fixture')
                    if kind=='wrong-size' and '/coverage/' in url:
                        return png(Image.new('RGBA',(128,128))),{},200
                    if kind=='bad-png' and '/coverage/' in url:
                        return b'not PNG',{},200
                    body,headers,status=self.respond(url,headers)
                    if url.endswith('weather-maps.json'):
                        meta=json.loads(body)
                        if kind=='untrusted-host':meta['host']='https://example.invalid'
                        if kind=='expired-frame':meta['radar']['past'][0]['time']-=7200
                        body=json.dumps(meta).encode()
                    return body,headers,status
                with patch.object(client,'_download',side_effect=respond):
                    with self.assertRaises(RadarMapError):
                        client.fetch(320,240,self.position)

    def test_date_line_wrap_and_same_pixel_landmarks_in_all_layers(self):
        for lon in (-179.99,179.99):
            position=replace(self.position,lon=lon)
            left,top,tiles=viewport(320,240,position)
            self.requests.clear()
            with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
                client=InternationalMapClient(folder)
                with patch.object(client,'_download',side_effect=self.respond):
                    result=client.fetch(320,240,position)
            xs={int(urlsplit(url).path.split('/')[2]) for url,_ in self.requests if 'openstreetmap' in url}
            self.assertIn(0,xs);self.assertIn(127,xs)
        # An XYZ-derived landmark has identical screen pixels in OSM, radar and mask.
        def tiles(url,headers=None):
            if url.endswith("weather-maps.json"):
                return self.respond(url,headers)
            if "openstreetmap" in url:
                z,x,y=map(int,urlsplit(url).path.strip('/').removesuffix('.png').split('/'))
            else:
                parts=urlsplit(url).path.split('/');z,x,y=map(int,parts[5:8])
            image=Image.new('RGBA',(256,256),(x,y,100,255))
            return png(image),{},200
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            client=InternationalMapClient(folder)
            with patch.object(client,'_download',side_effect=tiles):
                result=client.fetch(320,240,self.position)
            self.assertEqual(result.basemap,result.radar)
            self.assertEqual(result.basemap,result.coverage)

    def test_osm_identification_http_freshness_and_conditional_revalidation(self):
        url="https://tile.openstreetmap.org/7/64/42.png"
        body=png(Image.new('RGBA',(256,256),'white'))
        self.network.stop()
        response=Mock(status=200,headers={"Cache-Control":"max-age=0","ETag":'"etag"'})
        response.read.return_value=body
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch('wetterstation.maps.international_map.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=response
            self.client._tile(url,osm=True)
            request=opener.return_value.open.call_args.args[0]
            self.assertIn("Wetterstation",request.get_header("User-agent"))
            self.assertIsNone(request.get_header("Cache-control"))
        with patch.object(self.client,'_download',return_value=(b'',{'Cache-Control':'max-age=604800'},304)) as download:
            self.assertEqual(self.client._tile(url,osm=True),body)
            self.assertEqual(download.call_args.args[1]['If-None-Match'],'"etag"')
            self.client._tile(url,osm=True)
            self.assertEqual(download.call_count,1)


class InternationalUiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.store=ApiKeyStore(Path(self.temp.name)/'settings.json')
        self.root=tk.Tk();self.root.withdraw()
        self.preview=WeatherPreview(self.root,mock_preview=True,settings_store=self.store)
        self.preview.mock_preview=False
        self.preview._start_worker=Mock()
        self.preview.refresh_weather=Mock();self.preview.refresh_radar=Mock()

    def tearDown(self):
        self.preview.close();del self.preview;gc.collect()

    def test_country_only_change_clears_weather_map_and_discards_old_background_preparation(self):
        p=self.preview
        p.location_var.set('Paris');p.country_var.set('Frankreich')
        p.apply_location(refresh=False)
        p._load_mock_preview_data();p.radar_result=Mock()
        generation=p.weather_generation;epoch=p._radar_render_epoch
        p.country_var.set('Vereinigte Staaten');p.apply_location(refresh=False)
        self.assertIsNone(p.weather_record);self.assertIsNone(p.forecast_record);self.assertIsNone(p.radar_result)
        self.assertGreater(p.weather_generation,generation);self.assertGreater(p._radar_render_epoch,epoch)
        self.assertEqual(self.store.load_country_code(),'US')
        self.assertEqual(p._weather_query(),'Paris, US')

    def test_phone_country_change_is_applied_without_weather_or_map_request(self):
        p=self.preview
        self.store.save_configuration('Wien',country_code='AT')
        p._apply_mobile_settings(False)
        self.assertEqual((p.settings.location,p.settings.country_code),('Wien','AT'))
        p.refresh_weather.assert_not_called();p.refresh_radar.assert_not_called()

    def test_late_weather_result_after_country_only_change_is_discarded(self):
        p=self.preview
        p.location_var.set('Paris');p.country_var.set('Frankreich');p.apply_location(refresh=False)
        old=p.weather_record
        p.weather_client.load_cached=Mock(return_value=None)
        p.weather_client.load_cached_forecast=Mock(return_value=None)
        p.weather_client.fetch=Mock(return_value=old)
        p.weather_client.has_resolved_place=Mock(return_value=False)
        p.weather_client.budget_status_text=Mock(return_value='Test')
        # Simulated expected failure avoids constructing unrelated weather fixtures.
        p.weather_client.fetch.side_effect=WeatherServiceError('Simulierter Ausfall')
        tasks=[]
        p._start_worker=Mock(side_effect=lambda task,*args:tasks.append(task))
        WeatherPreview.refresh_weather(p)
        p.country_var.set('Vereinigte Staaten');p.apply_location(refresh=False)
        tasks[0]()
        p._results.get(timeout=2)()
        self.assertIsNone(p.weather_record);self.assertIsNone(p.forecast_record)
        self.assertEqual(p.settings.country_code,'US')

    def test_late_map_result_after_country_only_change_is_discarded(self):
        p=self.preview
        p.location_var.set('Paris');p.country_var.set('Frankreich');p.apply_location(refresh=False)
        for code,lat,lon in (('FR',48.8,2.3),('US',33.,-95.)):
            p.weather_client._places[location_query('Paris',code).casefold()]=dict(name='Paris',country=code,lat=lat,lon=lon)
        position=p._map_position()
        from wetterstation.maps.radar_map import RadarMapResult
        data=png(Image.new('RGBA',(320,240),'white'))
        now=datetime.now(timezone.utc)
        result=RadarMapResult(data,data,now,now,position=position,provider='rainviewer',coverage=data)
        p.radar_client.fetch=Mock(return_value=result)
        tasks=[];p._start_worker=Mock(side_effect=lambda task,*args:tasks.append(task))
        WeatherPreview.refresh_radar(p)
        p.country_var.set('Vereinigte Staaten');p.apply_location(refresh=False)
        tasks[0]();p._results.get(timeout=2)()
        self.assertIsNone(p.radar_result)
        self.assertEqual(p._map_position().country,'US')

    def test_place_only_map_widget_never_authorizes_osm_downloads(self):
        p=self.preview
        p.location_var.set('Paris');p.country_var.set('Frankreich');p.apply_location(refresh=False)
        p.weather_client._places['paris, fr']=dict(name='Paris',country='FR',lat=48.8,lon=2.3)
        p.page=2
        p._current_page()['widgets'][0]['fields']=['place','updated']
        p.radar_client.fetch=Mock(return_value=None)
        tasks=[];p._start_worker=Mock(side_effect=lambda task,*args:tasks.append(task))
        WeatherPreview.refresh_radar(p)
        tasks[0]()
        self.assertFalse(p.radar_client.fetch.call_args.kwargs['allow_basemap_download'])

    def test_unknown_legacy_country_requires_selection_and_keeps_no_current_data(self):
        p=self.preview
        p.country_var.set('Unbekannt');before=self.store.path.exists()
        p.apply_location(refresh=False)
        self.assertIn('Land',p.location_notice)
        self.assertEqual(self.store.path.exists(),before)


if __name__ == '__main__':
    unittest.main()

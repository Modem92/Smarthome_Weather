"""Isolated visual acceptance harness. Synthetic data and loopback HTTPS only.

Run directly; no production entry point or project-private settings are opened.
Automatically closes after five minutes, or via stop.request in the output folder.
"""
import gc
import json
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from datetime import datetime, timezone
from dataclasses import replace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview
from wetterstation.weather.countries import location_query
from wetterstation.maps.international_map import png
from wetterstation.mobile.mobile_settings import MobileSettingsServer
from wetterstation.maps.radar_map import RadarMapResult, MapPosition
from wetterstation.weather.weather_service import OpenWeatherClient
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageGrab


def synthetic_map(position):
    size=(1024,600)
    base=Image.new('RGBA',size,(229,237,217,255));draw=ImageDraw.Draw(base)
    for x in range(-500,1500,80):
        draw.line((x,0,x+400,600),fill=(255,255,249,255),width=22)
        draw.line((x,0,x+400,600),fill=(199,204,194,255),width=1)
    for y in range(-200,800,70):
        draw.line((0,y,1024,y+70),fill=(255,255,249,255),width=18)
    draw.line((40,600,600,0),fill=(197,220,232,255),width=70)
    draw.line((0,350,1024,220),fill=(244,192,100,255),width=16)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
    for text,xy in [('SIMULIERTE TESTKARTE', (30,500)),('West Park',(75,80)),('East Village',(640,160)),('Downtown',(380,370))]:
        draw.text(xy,text,font=font,fill=(97,110,104,255))
    radar=Image.new('RGBA',size,(0,0,0,0));draw=ImageDraw.Draw(radar)
    draw.ellipse((300,40,760,550),fill=(98,198,224,100))
    draw.ellipse((380,100,680,460),fill=(54,214,156,150))
    draw.ellipse((460,180,600,360),fill=(229,227,62,220))
    radar=radar.filter(ImageFilter.GaussianBlur(18))
    coverage=Image.new('RGBA',size,(0,0,0,0));ImageDraw.Draw(coverage).rectangle((790,0,1024,600),fill=(0,0,0,255))
    now=datetime.now(timezone.utc)
    return RadarMapResult(png(base),png(radar),now,now,position=position,provider='rainviewer',coverage=png(coverage),coverage_status='partial')


def main():
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    output=Path(__file__).resolve().parents[1]/'build'/'checks'/'international-check'
    output.mkdir(parents=True,exist_ok=True)
    (output/'stop.request').unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='international-visual-',dir=Path(__file__).parent) as folder:
        store=ApiKeyStore(Path(folder)/'settings.json')
        store.save_configuration('New York','dummy-visual-key',country_code='US')
        root=tk.Tk();root.title('TEST · internationale Wetterstation · nur simulierte Daten')
        preview=WeatherPreview(root,mock_preview=True,settings_store=store)
        preview.mock_preview=False
        preview.refresh_weather=lambda **kw: None
        preview.refresh_radar=lambda: None
        position=MapPosition('New York','New York · TESTDATEN',40.7128,-74.006,'US')
        query=location_query('New York','US')
        preview.weather_client._places[query.casefold()]={'name':position.name,'country':'US','lat':position.lat,'lon':position.lon}
        preview.weather_record=replace(preview.weather_record,query=query.casefold(),name=position.name,country='US',timezone='America/New_York',lat=position.lat,lon=position.lon)
        preview.forecast_record=replace(preview.forecast_record,query=query.casefold(),name=position.name,country='US',timezone='America/New_York',lat=position.lat,lon=position.lon)
        preview.location_notice='SIMULIERTE TESTDATEN · kein Liveabruf'
        preview.weather_status=preview.forecast_status='SIMULIERTE TESTDATEN'
        preview.radar_result=synthetic_map(position);preview.radar_error=''
        errors=[]
        root.report_callback_exception=lambda kind,value,tb:errors.append(str(value))
        service=MobileSettingsServer(store,on_change=lambda changed:preview._results.put(lambda:preview._apply_mobile_settings(changed)),
            on_layout_change=lambda layout,page_id:preview._results.put(lambda:preview._apply_mobile_dashboard(layout,page_id)),
            on_page_change=lambda page_id:preview._results.put(lambda:preview._show_mobile_page(page_id)),
            on_pairing_change=lambda:preview._results.put(preview._pairing_changed))
        preview.mobile_service=service
        service.start('127.0.0.1',0);preview._publish_to_new_service(service)
        (output/'connection.json').write_text(json.dumps({'url':service.url}),encoding='utf-8')
        root.after(500,preview._check_pairing)
        def report():
            if preview._closed:return
            (output/'pairing.json').write_text(json.dumps(service.pairing_display()),encoding='utf-8')
            labels=[preview.canvas.itemcget(i,'text') for i in preview.canvas.find_all() if preview.canvas.type(i)=='text']
            (output/'display.json').write_text(json.dumps({'labels':labels,'errors':errors,'country':preview.settings.country_code,'location':preview.settings.location}),encoding='utf-8')
            capture=output/'capture.request'
            if capture.exists():
                name=capture.read_text().strip();capture.unlink()
                if name in ('overview','radar','forecast'):
                    root.update_idletasks()
                    ImageGrab.grab(window=root.winfo_id()).save(output/f'{name}-1024.png')
            if (output/'stop.request').exists():
                (output/'stop.request').unlink();preview.close();return
            root.after(100,report)
        root.after(100,report);root.after(300000,preview.close)
        root.mainloop();del preview;gc.collect()


if __name__=='__main__':
    # Block network providers even if a future UI change starts a worker by mistake.
    with patch.object(OpenWeatherClient,'_request',side_effect=AssertionError('no live weather')):
        main()

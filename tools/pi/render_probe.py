"""Synthetic renderer timings on the installed Pi code, in an isolated hidden Tk."""
import argparse
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--pid',type=int,required=True)
    args=parser.parse_args();root=args.root.resolve();proc=Path('/proc')/str(args.pid)
    if (proc/'cwd').resolve()!=root:raise ValueError('Wrong application process')
    for entry in (proc/'environ').read_bytes().split(b'\0'):
        key,sep,value=entry.partition(b'=')
        if sep and key.decode('utf-8','replace') in ('DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','XDG_RUNTIME_DIR','DBUS_SESSION_BUS_ADDRESS','XDG_SESSION_TYPE'):
            os.environ[key.decode()]=value.decode()
    sys.path.insert(0,str(root))
    import tkinter as tk
    from wetterstation.storage.api_key_store import ApiKeyStore
    from wetterstation.ui.app import WeatherPreview
    from wetterstation.weather.weather_service import OpenWeatherClient
    from wetterstation.maps.radar_map import RadarMapClient
    def denied(*args,**kwargs):raise AssertionError('Provider calls forbidden during render probe')
    OpenWeatherClient._request=denied;RadarMapClient.fetch=denied
    with tempfile.TemporaryDirectory(prefix='wetterstation-render-probe-') as folder:
        store=ApiKeyStore(Path(folder)/'settings.json')
        window=tk.Tk();window.withdraw()
        preview=WeatherPreview(window,widget_demo=True,settings_store=store)
        preview.canvas.winfo_width=lambda:1024;preview.canvas.winfo_height=lambda:600
        timings=[]
        try:
            for index,page in enumerate(preview.dashboard['pages']):
                preview.page=index;values=[]
                for repeat in range(4):
                    start=time.perf_counter();preview.draw();window.update_idletasks()
                    values.append((time.perf_counter()-start)*1000)
                timings.append({'page_id':page['id'],'first_ms':round(values[0],2),'repeat_median_ms':round(statistics.median(values[1:]),2)})
        finally:
            window.update_idletasks();preview.close()
    print(json.dumps({'mode':'isolated-widget-demo','viewport':[1024,600],'provider_calls':0,'pages':timings}))


if __name__=='__main__':main()

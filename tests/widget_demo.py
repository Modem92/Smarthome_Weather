"""Isolated local demo harness for browser + Tk widget integration checks."""
import gc
import json
from pathlib import Path
import sys
import tempfile
import tkinter as tk
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.app import WeatherPreview
from wetterstation.mobile.mobile_settings import MobileSettingsServer
from wetterstation.ui.widgets import revision


def main():
    if sys.platform=='win32':
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
    with tempfile.TemporaryDirectory(prefix='widget-demo-',dir=Path(__file__).parent) as folder:
        store=ApiKeyStore(path=Path(folder)/'settings.json')
        store.save_configuration('Potsdam, 14467, Deutschland','dummy-widget-check-key')
        design_mode = '--design' in sys.argv[1:]
        if design_mode:
            from wetterstation.designer import model
            document=model.from_layout();document['pages'][0]['grid']={'columns':24,'rows':16}
            w=model.new_widget('clock');w.update(id='clock',x=0,y=0,w=4,h=4);w['style']={'background':'#ddffaa','radius':0,'border_width':7}
            other=model.new_widget('series');other.update(id='series',x=10,y=0,w=6,h=4);other['style']={'color':'#007aff'}
            document['pages'][0]['widgets']=[w,other]
            if '--graphical' in sys.argv[1:]:
                from wetterstation.designer.content import materialize
                from wetterstation.designer.render import widget_rects
                rects=widget_rects(document,document['pages'][0])[0]
                for item in document['pages'][0]['widgets']:materialize(document,document['pages'][0],item,rects[item['id']])
                w['content_layout']['builtin-time'].update(x=.12,w=.7)
            store.save_dashboard(document,revision(store.load_dashboard()))
        root=tk.Tk()
        preview=WeatherPreview(root,widget_demo=True,settings_store=store)
        errors=[]
        root.report_callback_exception=lambda *_args: errors.append('Tk callback error')
        service=MobileSettingsServer(store,
            on_layout_change=lambda layout,page_id:preview._results.put(lambda:preview._apply_mobile_dashboard(layout,page_id)),
            on_page_change=lambda page_id:preview._results.put(lambda:preview._show_mobile_page(page_id)),
            on_pairing_change=lambda:preview._results.put(preview._pairing_changed),layout_only=True)
        preview.mobile_service=service
        preview._publish_dashboard()
        service.start('127.0.0.1',0)
        output=Path(__file__).resolve().parents[1]/'build'/'checks'/('designer-phone' if design_mode else 'widget-check')
        output.mkdir(parents=True,exist_ok=True)
        for command in ('stop.request','restart.request','capture.request'):
            (output/command).unlink(missing_ok=True)
        (output/'connection.json').write_text(json.dumps({'url':service.url}),encoding='utf-8')
        print(json.dumps({'url':service.url}),flush=True)
        root.after(500,preview._check_pairing)
        def report():
            if preview._closed:return
            if (output/'restart.request').exists():
                (output/'restart.request').unlink()
                port=service._server.server_port
                service.stop();service.start('127.0.0.1',port)
            (output/'pairing.json').write_text(json.dumps(service.pairing_display()),encoding='utf-8')
            data={'page_id':preview._current_page()['id'],'layout':preview.dashboard,'revision':revision(preview.dashboard),'errors':errors,
                'labels':[preview.canvas.itemcget(i,'text') for i in preview.canvas.find_all() if preview.canvas.type(i)=='text'],
                'scrollregion':preview.canvas.cget('scrollregion')}
            (output/'display.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            if (output/'capture.request').exists():
                (output/'capture.request').unlink()
                from PIL import ImageGrab
                root.update_idletasks()
                ImageGrab.grab(window=root.winfo_id()).save(output/'display.png')
            if (output/'stop.request').exists():
                (output/'stop.request').unlink();preview.close();return
            root.after(100,report)
        root.after(100,report)
        root.after(900000,preview.close)
        root.mainloop()
        del preview
        gc.collect()

if __name__=='__main__':main()

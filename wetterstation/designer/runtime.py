"""Schema-3 Tk bridge; rendering never refreshes weather or radar providers."""
from dataclasses import asdict
from copy import deepcopy
from datetime import datetime,timezone
import io
from collections import OrderedDict
from PIL import Image
from wetterstation.ui.tk_images import photo_image

from wetterstation.designer.render import render_page,render_widget,demo_data,output_image,style
from wetterstation.designer.storage import atomic,json_bytes
from wetterstation.ui.widgets import revision
from wetterstation.designer.model import content_elements


def display_data(preview):
    if preview.mock_preview:return demo_data()
    values={};record=preview.weather_record;forecast=preview.forecast_record
    if record:
        values={k:getattr(record,k) for k in ('temp','feels_like','description','humidity','pressure')};values['wind']=record.wind_speed
    # Sensor bindings always remain explicitly marked synthetic values.
    values.update(sensor_temp=16.8,sensor_humidity=64,sensor_pressure=1012,sensor_wind=3.2,indoor_temp=21.5,indoor_humidity=45)
    zone=preview._display_zone()
    from wetterstation.weather.location_time import weather_zone
    from wetterstation.weather.weather_service import normalize_query
    matching=getattr(preview,'_designer_series_query',None)==normalize_query(preview._weather_query())
    series=dict(getattr(preview,'_designer_series',{})) if matching else {}
    if forecast:
        for source,entries in (('1h',forecast.hourly),('1day',forecast.daily)):
            if not series.get(source):
                series[source]=[{'timestamp':e.timestamp,'temp':e.temp,'description':e.description,'wind':e.wind_speed,'rain':e.precipitation_probability*100,'temp_min':e.temp_min,'temp_max':e.temp_max} for e in entries]
    data={'values':values,'series':series,'now':datetime.now(timezone.utc),'zone':str(zone),'zone_known':weather_zone(record,forecast)[1],'demo':False,
          'map':None,'map_notice':preview.radar_error or 'Noch keine aktuelle Karte',
          'series_notices':dict(getattr(preview,'_designer_series_notices',{})) if matching else {}}
    result=preview.radar_result
    if result is not None:
        position=preview._map_position()
        age=max((data['now']-result.fetched_at).total_seconds(),(data['now']-result.observed_at).total_seconds())
        if result.position==position and 0<=age<=3600:
            prepared=getattr(preview,'_designer_map',None)
            if prepared and prepared[0] is result:
                data['map'],data['radar']=prepared[1:]
            else:prepare_map(preview,result)
            data.update(place=result.position.name,attribution=result.attribution,
                        coverage='' if result.coverage_status=='full' else 'Keine Radarversorgung' if result.coverage_status=='none' else 'Teilweise Radarversorgung',
                        map_updated=result.fetched_at.astimezone(zone).strftime('%d.%m. %H:%M'),
                        map_notice='Zwischengespeichert / Aktualisierung eingeschränkt' if result.stale or age>900 or result.warning else '')
            from wetterstation.maps.radar_motion import fresh_source,project_vectors
            motion=getattr(preview,'_radar_motion',None)
            if motion and motion.source is result and result.provider=='dwd' and not result.stale and fresh_source(result):
                data['motion']=project_vectors(motion,(1024,600),protected=((492,280,532,320),(0,0,1024,30),(0,570,1024,600)))
    return data


def prepare_map(preview,result):
    if getattr(preview,'_designer_map_busy',False):return
    preview._designer_map_busy=True
    def finish(images):
        preview._designer_map_busy=False
        if not preview._closed and result is preview.radar_result:
            preview._designer_map=(result,*images);preview.draw()
    def work():
        from wetterstation.maps.radar_render import prepare_radar_layers,RadarRenderRequest
        layers=prepare_radar_layers(RadarRenderRequest(result,(1024,600),preview._weather_query(),preview._radar_render_epoch))
        images=tuple(Image.open(io.BytesIO(b)).convert('RGBA') for b in layers)
        preview._results.put(lambda:finish(images))
    preview._start_worker(work,lambda:setattr(preview,'_designer_map_busy',False),'designer-map-prepare')


def clock_widgets(page):
    return [w for w in page['widgets'] if (w['type'] in ('clock','date') and w['fields']) or any(e.get('kind')=='data' and e.get('binding') in ('time','date') for e in content_elements(w))]


def clock_token(document,page,widget,data):
    from zoneinfo import ZoneInfo
    now=data['now'].astimezone(ZoneInfo(data.get('zone') or 'UTC'));s=style(document,page,widget)
    time=widget['type']=='clock' and ('time' in widget['fields'] or 'seconds' in widget['fields'])
    seconds=widget['type']=='clock' and 'seconds' in widget['fields']
    if time and '%S' in s['time_format']:seconds=True
    for e in content_elements(widget):
        if e.get('kind')=='data' and e.get('binding')=='time':
            time=True;seconds=seconds or '%S' in style(document,page,widget,e)['time_format']
    return now.strftime('%Y-%m-%d %H:%M:%S' if seconds else '%Y-%m-%d %H:%M' if time else '%Y-%m-%d')


def static_key(document,page,data):
    from wetterstation.designer.model import digest
    from zoneinfo import ZoneInfo
    source_buckets={}
    for w in page['widgets']:
        source=w.get('series',{}).get('source') if w['type']=='series' else '1h' if w['type']=='hourly' else '1day' if w['type']=='daily' else ''
        if source:
            source_buckets[source]=(data['now'].astimezone(ZoneInfo(data.get('zone') or 'UTC')).date().isoformat() if source=='1day' else int(data['now'].timestamp()//({'1min':60,'15min':900,'1h':3600}[source])))
    return (digest({'values':data.get('values',{}),'series':{source:data.get('series',{}).get(source,[]) for source in source_buckets},'series_notices':data.get('series_notices',{}),'zone':[data.get('zone'),data.get('zone_known')],
                    'notes':[data.get(k,'') for k in ('map_notice','attribution','coverage','map_updated')],'motion':data.get('motion',[]),'buckets':source_buckets}),id(data.get('map')),id(data.get('radar')))


def protected_areas(document,page,data,width,height):
    regions=[]
    if data.get('demo'):regions.append((max(0,width-220),0,width,18))
    radar=[w for w in page['widgets'] if w['type']=='radar']
    sensor=any(w['type'].startswith('sensor_') or w['type'] in ('sensors','indoor') or any(e.get('kind')=='data' and e.get('binding','').startswith(('sensor_','indoor_')) for e in content_elements(w)) for w in page['widgets'])
    if sensor or (radar and (any(data.get(k) for k in ('map_notice','attribution','coverage')) or any(style(document,page,w)['radar_opacity']==0 for w in radar))):regions.append((0,max(0,height-36),width,height))
    return regions


def patch_clocks(preview,document,page,data,actual):
    from wetterstation.designer.render import widget_rects
    rects,_=widget_rects(document,page);width=document['display']['width'];height=document['display']['height'];rotation=document['display']['rotation']
    rotated_size=(height,width) if rotation in (90,270) else (width,height)
    scale=min(actual[0]/rotated_size[0],actual[1]/rotated_size[1]);offset=((actual[0]-rotated_size[0]*scale)/2,(actual[1]-rotated_size[1]*scale)/2)
    for widget in clock_widgets(page):
        token=clock_token(document,page,widget,data)
        if preview._designer_clock_tokens.get(widget['id'])==token:continue
        x,y,w,h=rects[widget['id']];tile=preview._designer_clean_background.crop((x,y,x+w,y+h));content,_=render_widget(document,page,widget,(w,h),data,preview.api_key_store.path.parent/'designer/assets');tile.alpha_composite(content)
        for left,top,right,bottom in protected_areas(document,page,data,width,height):
            l=max(x,left);t=max(y,top);r=min(x+w,right);b=min(y+h,bottom)
            if l<r and t<b:tile.paste(preview._designer_logical_image.crop((l,t,r,b)),(l-x,t-y))
        preview._designer_logical_image.paste(tile,(x,y));tile=output_image(tile,rotation)
        if rotation==90:xx,yy,ww,hh=height-y-h,x,h,w
        elif rotation==180:xx,yy,ww,hh=width-x-w,height-y-h,w,h
        elif rotation==270:xx,yy,ww,hh=y,width-x-w,h,w
        else:xx,yy,ww,hh=x,y,w,h
        px=round(offset[0]+xx*scale);py=round(offset[1]+yy*scale);right=round(offset[0]+(xx+ww)*scale);bottom=round(offset[1]+(yy+hh)*scale)
        tile=tile.resize((max(1,right-px),max(1,bottom-py)),Image.Resampling.LANCZOS)
        photo=photo_image(tile,master=preview.root);tag='designer-clock-'+widget['id'];preview.canvas.delete(tag)
        preview._designer_patch_photos[widget['id']]=photo;preview.canvas.create_image(px,py,image=photo,anchor='nw',tags=('designer-clock-patch',tag))
        preview._designer_clock_tokens[widget['id']]=token


def draw(preview):
    from wetterstation.designer.render import widget_rects
    document=preview.dashboard;page=preview._current_page();data=display_data(preview)
    canvas=preview.canvas;actual=(max(1,canvas.winfo_width()),max(1,canvas.winfo_height()))
    # A temporary pairing page may have published a different viewport. Restore
    # layout metadata even when the image can be reused without a full redraw.
    _,g=widget_rects(document,page);display=document['display'];width=display['width'];height=display['height']
    preview._display_viewport={'width':width,'height':height,'grid':g,'rotation':display['rotation']}
    runtime_key=(revision(document),page['id'],actual,static_key(document,page,data))
    if runtime_key==getattr(preview,'_designer_runtime_key',None) and canvas.find_withtag('designer-display'):
        patch_clocks(preview,document,page,data,actual)
        return
    request=(runtime_key,deepcopy(document),page['id'],data,actual)
    preview._designer_wanted=request
    if getattr(preview,'_designer_busy',False):return
    preview._designer_busy=True
    cache=getattr(preview,'_designer_render_cache',None)
    if cache is None:preview._designer_render_cache={};cache=preview._designer_render_cache
    assets=preview.api_key_store.path.parent/'designer/assets'
    frames=getattr(preview,'_designer_frames',None)
    if frames is None:preview._designer_frames=OrderedDict();frames=preview._designer_frames
    def finish(frame):
        preview._designer_busy=False
        if preview._closed:return
        wanted=preview._designer_wanted
        valid=(wanted[0]==runtime_key and revision(preview.dashboard)==runtime_key[0]
               and preview._current_page()['id']==page['id'] and not getattr(preview,'_pairing_screen',None)
               and (max(1,canvas.winfo_width()),max(1,canvas.winfo_height()))==actual)
        if valid and frame is not None:
            _show_frame(preview,request,frame)
        elif frame is None and valid:
            preview._publish_dashboard('Anzeige konnte nicht vorbereitet werden.')
        if wanted[0]!=runtime_key:draw(preview)
    def work():
        frame_key=(runtime_key,tuple(clock_token(document,page,w,data) for w in clock_widgets(page)))
        if frame_key in frames:
            frames.move_to_end(frame_key)
            frame=tuple(image.copy() for image in frames[frame_key])
        else:
            frame=prepare_frame(request[1],page['id'],data,actual,assets,cache)
            frames[frame_key]=tuple(image.copy() for image in frame)
            while frames and sum(sum(im.width*im.height*4 for im in value) for value in frames.values())>16*1024*1024:
                frames.popitem(last=False)
        preview._results.put(lambda:finish(frame))
    preview._start_worker(work,lambda:finish(None),'designer-frame-prepare')


def prepare_frame(document,page_id,data,actual,assets,cache):
    """Pure Pillow work: never touch Tk, files with settings, or providers."""
    page=next(p for p in document['pages'] if p['id']==page_id)
    image,_,warnings=render_page(document,page_id,data,assets,cache=cache)
    clean=deepcopy(document);clean_page=next(p for p in clean['pages'] if p['id']==page['id']);dynamic={w['id'] for w in clock_widgets(page)}
    clean_page['widgets']=[w for w in clean_page['widgets'] if w['id'] not in dynamic]
    background=render_page(clean,page_id,data,assets,cache=cache)[0]
    rotated=output_image(image,document['display']['rotation'])
    scale=min(actual[0]/rotated.width,actual[1]/rotated.height)
    size=(max(1,round(rotated.width*scale)),max(1,round(rotated.height*scale)))
    return image,background,rotated.resize(size,Image.Resampling.LANCZOS)


def _show_frame(preview,request,frame):
    runtime_key,document,page_id,data,actual=request
    page=next(p for p in document['pages'] if p['id']==page_id)
    canvas=preview.canvas
    from wetterstation.designer.render import widget_rects
    _,geometry=widget_rects(document,page)
    display=document['display']
    preview._display_viewport={'width':display['width'],'height':display['height'],'grid':geometry,'rotation':display['rotation']}
    preview._designer_logical_image,preview._designer_clean_background,image=frame
    preview._designer_clock_tokens={w['id']:clock_token(document,page,w,data) for w in clock_widgets(page)}
    preview._designer_patch_photos={};preview._designer_runtime_key=runtime_key
    size=image.size
    preview._designer_photo=photo_image(image,master=preview.root)
    from wetterstation.designer.model import style
    canvas.delete('all');canvas.configure(bg=style(document,page)['background'][:7],scrollregion=(0,0,*actual));canvas.yview_moveto(0);preview.scrollbar.pack_forget()
    canvas.create_image((actual[0]-size[0])/2,(actual[1]-size[1])/2,image=preview._designer_photo,anchor='nw',tags=('designer-display',))
    preview.s=1;preview.content_offset_y=0
    preview._publish_dashboard()
    # Persist only the acknowledgement, never the settings or weather response.
    import os
    nonce=None
    try:
        from wetterstation.designer.storage import read_json
        session=read_json(preview.api_key_store.path.parent.parent/'.wetterstation-session.json',16000)
        if session.get('pid')==os.getpid():nonce=session.get('nonce')
    except (OSError,ValueError):pass
    acknowledgement={'schema':1,'revision':revision(document),'page_id':page['id'],'ready':True,'pid':os.getpid(),'nonce':nonce}
    if acknowledgement!=getattr(preview,'_designer_ack',None):
        try:atomic(preview.api_key_store.path.parent/'designer/display-ack.json',json_bytes(acknowledgement));preview._designer_ack=acknowledgement
        except OSError:pass


def poll(preview):
    if preview._closed:return
    try:
        path=preview.api_key_store.path;stat=path.stat() if path.exists() else None;stamp=(stat.st_mtime_ns,stat.st_size) if stat else None
        if stamp!=getattr(preview,'_designer_settings_stamp','unread'):
            layout=preview.api_key_store.load_dashboard()
            if revision(layout)!=revision(preview.dashboard):preview._apply_mobile_dashboard(layout)
            preview._designer_settings_stamp=stamp
    except (OSError,ValueError):pass
    # Existing v2 clocks retain the established Tk text renderer.
    if preview.dashboard.get('version') in (3,4) and not getattr(preview,'_pairing_screen',None):draw(preview)
    preview.root.after(1000,lambda:poll(preview))

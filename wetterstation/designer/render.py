"""Shared Pillow renderer. No settings reads, servers, clients or network calls."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timezone
from functools import lru_cache
import io
import math
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageFilter,ImageEnhance,ImageColor
from wetterstation.designer.model import style, grid, KINDS, DATA_FIELDS, content_elements
from wetterstation.designer.series import FIELDS,select_samples

FONTS=Path(__file__).parent/'fonts'


def local_format(stamp,format):
    full=('Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag','Sonntag')
    short=('Mo','Di','Mi','Do','Fr','Sa','So')
    return stamp.strftime(format.replace('%A',full[stamp.weekday()]).replace('%a',short[stamp.weekday()]))


def rgba(value,opacity=1):
    color=ImageColor.getcolor(value,'RGBA')
    return (*color[:3],round(color[3]*opacity))


@lru_cache(maxsize=256)
def font_file(family,bold=False,italic=False,assets=''):
    if family not in ('Sans','Serif','Mono'):
        path=Path(assets)/family
        if path.is_file():return str(path)
        raise ValueError('Verwendete Schriftdatei fehlt.')
    stem={'Sans':'DejaVuSans','Serif':'DejaVuSerif','Mono':'DejaVuSansMono'}[family]
    suffix=('-Bold' if bold else '')+('Italic' if family=='Serif' else 'Oblique') if italic else ('-Bold' if bold else '')
    if italic and not bold:suffix='-'+suffix
    return str(FONTS/(stem+suffix+'.ttf'))


@lru_cache(maxsize=512)
def get_font(family,size,bold=False,italic=False,assets=''):
    return ImageFont.truetype(font_file(family,bold,italic,assets),max(1,int(size)))


def picture(path,size,mode='cover',center=(.5,.5)):
    with Image.open(path) as src:
        src=src.convert('RGBA')
        if mode=='cover':return ImageOps.fit(src,size,centering=center)
        if mode=='stretch':return src.resize(size,Image.Resampling.LANCZOS)
        fitted=ImageOps.contain(src,size);out=Image.new('RGBA',size)
        out.alpha_composite(fitted,((size[0]-fitted.width)//2,(size[1]-fitted.height)//2));return out


def rounded_mask(size,radii):
    w,h=size;mask=Image.new('L',size,255);d=ImageDraw.Draw(mask)
    for radius,corner in zip(radii,('tl','tr','br','bl')):
        r=max(0,min(round(radius),w//2,h//2))
        if not r:continue
        circle=Image.new('L',(r*2,r*2),0);ImageDraw.Draw(circle).ellipse((0,0,2*r-1,2*r-1),fill=255)
        if corner=='tl':mask.paste(circle.crop((0,0,r,r)),(0,0))
        elif corner=='tr':mask.paste(circle.crop((r,0,2*r,r)),(w-r,0))
        elif corner=='br':mask.paste(circle.crop((r,r,2*r,2*r)),(w-r,h-r))
        else:mask.paste(circle.crop((0,r,r,2*r)),(0,h-r))
    return mask


def surface(size,s,assets):
    w,h=size;out=Image.new('RGBA',size,rgba(s['background'],s['opacity']))
    if s['gradient']!='none':
        first=rgba(s['background'],s['opacity']);last=rgba(s['gradient_color'],s['opacity'])
        count=h if s['gradient']=='vertical' else w
        strip=Image.new('RGBA',(1,count) if s['gradient']=='vertical' else (count,1))
        strip.putdata([tuple(round(a+(b-a)*i/max(1,count-1)) for a,b in zip(first,last)) for i in range(count)])
        out=strip.resize(size)
    if s['image']:
        try:out.alpha_composite(picture(Path(assets)/s['image'],size,s['image_mode'],(s['image_x'],s['image_y'])))
        except (OSError,ValueError):pass
    radii=[s['radius_'+k] if s['individual_corners'] else s['radius'] for k in ('tl','tr','br','bl')]
    mask=rounded_mask(size,radii)
    from PIL import ImageChops
    out.putalpha(ImageChops.multiply(out.getchannel('A'),mask))
    border=min(round(s['border_width']),min(w,h)//2)
    if border:
        inner=Image.new('L',size,0)
        if w>2*border and h>2*border:
            inner.paste(rounded_mask((w-2*border,h-2*border),[max(0,r-border) for r in radii]),(border,border))
        edge=ImageChops.subtract(mask,inner)
        ed=ImageDraw.Draw(edge)
        for enabled,box in ((s['border_top'],(0,0,w,border)),(s['border_bottom'],(0,h-border,w,h)),(s['border_left'],(0,0,border,h)),(s['border_right'],(w-border,0,w,h))):
            if not enabled:ed.rectangle(box,fill=0)
        if s['border_style']=='dashed':
            for i in range(0,w, max(4,border*6)):ed.rectangle((i,0,i+max(2,border*3),h),fill=0)
            # Preserve vertical dashed segments separately.
            for y in range(0,h,max(4,border*6)):
                ed.rectangle((0,y,border,y+max(2,border*3)),fill=0)
                ed.rectangle((w-border,y,w,y+max(2,border*3)),fill=0)
        layer=Image.new('RGBA',size,rgba(s['border_color'],s['border_opacity']));layer.putalpha(ImageChops.multiply(edge,layer.getchannel('A')));out.alpha_composite(layer)
    return out,mask


def text_image(text,size,s,assets):
    w,h=size;w,h=max(1,w),max(1,h)
    size=max(1,round(s['font_size']));lines=[]
    def fit(n):
        try:f=get_font(s['font'],n,s['bold'],s['italic'],str(assets))
        except (OSError,ValueError):f=get_font('Sans',n,s['bold'],s['italic'])
        rows=[]
        for paragraph in str(text).split('\n'):
            line=''
            for word in paragraph.split(' '):
                candidate=(line+' '+word).strip()
                if s['wrap'] and f.getlength(candidate)>w and line:
                    rows.append(line);line=word
                else:line=candidate
            rows.append(line)
        # Break very long words only after the font has been reduced.
        return f,rows,max((f.getlength(line) for line in rows),default=0),max(1,round(n*s['line_spacing']))*len(rows)
    f,lines,tw,th=fit(size)
    if s['auto_fit']:
        lo,hi=1,size
        while lo<hi:
            mid=(lo+hi+1)//2;ff,ll,ww,hh=fit(mid)
            if ww<=w and hh<=h:lo=mid
            else:hi=mid-1
        size=lo;f,lines,tw,th=fit(size)
    image=Image.new('RGBA',(w,h));d=ImageDraw.Draw(image)
    y=0 if s['valign']=='top' else max(0,h-th) if s['valign']=='bottom' else max(0,(h-th)/2)
    for line in lines:
        length=f.getlength(line);x=0 if s['align']=='left' else w-length if s['align']=='right' else (w-length)/2
        box=f.getbbox(line);d.text((x,y-box[1]),line,font=f,fill=rgba(s['color'],s['opacity']),stroke_width=max(1,round(size*.025)) if s['bold'] and s['font'] not in ('Sans','Serif','Mono') else 0)
        y+=max(1,round(size*s['line_spacing']))
    if s['rotation']:
        rotated=image.rotate(-s['rotation'],resample=Image.Resampling.BICUBIC,expand=False);image=rotated
    if s['italic'] and s['font'] not in ('Sans','Serif','Mono'):
        image=image.transform(image.size,Image.Transform.AFFINE,(1,-.15,h*.075,0,1,0),resample=Image.Resampling.BICUBIC)
    return image,(tw>w or th>h or size<8)


def convert_number(value,key,s):
    unit=FIELDS.get(key,('',{'sensor_temp':'°C','indoor_temp':'°C','sensor_humidity':'%','indoor_humidity':'%','sensor_pressure':'hPa','sensor_wind':'m/s'}.get(key,'')))[1]
    if unit=='°C':
        unit=s['temperature_unit']
        if unit=='°F':value=value*9/5+32
    elif unit=='m/s':
        unit=s['wind_unit'];value=value*(3.6 if unit=='km/h' else 2.236936292 if unit=='mph' else 1)
    elif unit=='hPa':
        unit=s['pressure_unit'];value=value*(.750061683 if unit=='mmHg' else .029529983 if unit=='inHg' else 1)
    return value,unit


def format_value(value,key,s):
    if value is None:return '—'
    if isinstance(value,(int,float)):
        if not math.isfinite(value):return '—'
        value,unit=convert_number(value,key,s)
        text=f'{value:.{s["decimals"]}f}'
        if s['decimal_comma']:text=text.replace('.',',')
        return text+(' '+unit if s['show_unit'] and unit else '')
    return str(value)


def demo_data(now=None,scenario='normal'):
    now=now or datetime.now(timezone.utc)
    values={'temp':18.6,'feels_like':17.3,'description':'Leicht bewölkt','humidity':64,'wind':3.2,'pressure':1012,
            'sensor_temp':16.8,'sensor_humidity':64,'sensor_pressure':1012,'sensor_wind':3.2,'indoor_temp':21.5,'indoor_humidity':45}
    if scenario=='long':values['description']='Vereinzelte Schauer mit länger anhaltendem Regen und wechselnder Bewölkung'
    if scenario=='large':values.update(temp=-123.4,wind=123.4,pressure=1099)
    if scenario=='missing':values={k:None for k in values}
    series={}
    from datetime import timedelta
    from wetterstation.designer.series import SOURCES
    for source,(base,horizon,_) in SOURCES.items():
        count=min(548,math.ceil(horizon/base));start=datetime.fromtimestamp(math.ceil(now.timestamp()/(base*60))*base*60,timezone.utc)
        rows=[]
        for i in range(count):
            value=None if scenario=='missing' or i==6 else 16+math.sin(i/4)*4
            rows.append({'timestamp':(start+timedelta(minutes=i*base)).isoformat(),'temp':value,'wind':3.2,'humidity':60,'pressure':1012,'feels_like':value,'rain':20.,'precipitation':0. if i<10 else 1.2,'description':values['description']})
        series[source]=rows
    return {'values':values,'series':series,'now':now,'zone':'Europe/Berlin','demo':True,'map':None,'map_notice':'DEMO · Kartenabrufe deaktiviert'}


def widget_rects(document,page):
    s=style(document,page);width=document['display']['width'];height=document['display']['height'];c,r=grid(page)
    top=s['margin_top']+(s['title_size']*1.7 if s['show_title'] else 0)
    left=s['margin_left'];availablew=max(1,width-left-s['margin_right']);availableh=max(1,height-top-s['margin_bottom'])
    gx=min(s['gap_x'],availablew/max(1,c-1)*.8) if c>1 else 0
    gy=min(s['gap_y'],availableh/max(1,r-1)*.8) if r>1 else 0
    cw=(availablew-(c-1)*gx)/c;ch=(availableh-(r-1)*gy)/r
    result={}
    for w in page['widgets']:
        x=round(left+w['x']*(cw+gx));y=round(top+w['y']*(ch+gy))
        result[w['id']]=(x,y,max(1,round(w['w']*cw+(w['w']-1)*gx)),max(1,round(w['h']*ch+(w['h']-1)*gy)))
    return result,{'x':left,'y':top,'width':availablew,'height':availableh,'gap_x':gx,'gap_y':gy,'gap':gx,'columns':c,'rows':r,'cell_w':cw,'cell_h':ch}


def _text(target,text,box,s,assets,warnings,label):
    x,y,w,h=map(round,box)
    if w<1 or h<1:return
    image,warning=text_image(text,(w,h),s,assets);target.alpha_composite(image,(x,y))
    if warning:warnings.append(label+': Schrift sehr klein oder Inhalt abgeschnitten')


def draw_series(target,box,spec,data,s,assets,warnings):
    x,y,w,h=map(round,box);rows=select_samples(data.get('series',{}).get(spec['source'],[]),spec,data.get('now'),data.get('zone') or 'UTC')
    notice=data.get('series_notices',{}).get(spec['source'],'')
    if not rows:
        _text(target,notice or 'Noch keine Zeitreihendaten',box,s,assets,warnings,'Zeitreihe');return
    if notice:
        nh=min(24,max(12,h*.12))
        _text(target,notice,(x,y+h-nh,w,nh),dict(s,font_size=min(11,s['font_size'])),assets,warnings,'Zeitreihenstatus')
        h=max(1,h-nh);box=(x,y,w,h)
    zone=ZoneInfo(data.get('zone') or 'UTC')
    stamps=[datetime.fromisoformat(row['timestamp']).astimezone(zone) for row in rows]
    labels=[stamp.strftime('%d.%m.' if spec['source']=='1day' else '%H:%M') for stamp in stamps]
    if data.get('zone_known') is False:labels=[label+' UTC' for label in labels]
    for i,label in enumerate(labels):
        if labels.count(label)>1:labels[i]=label+' '+stamps[i].strftime('%Z')
    if spec['mode'] in ('cards','table'):
        columns=min(len(rows),spec['columns']) if spec['mode']=='cards' else 1
        nrows=math.ceil(len(rows)/columns);cw=w/columns;ch=h/nrows
        for i,row in enumerate(rows):
            short={'temp':'','feels_like':'Gefühlt ','humidity':'Feuchte ','pressure':'','wind':'Wind ','rain':'Regen ','precipitation':'','description':''}
            def value(field):
                if field=='temp' and spec['source']=='1day' and row.get('temp_min') is not None and row.get('temp_max') is not None:
                    return format_value(row['temp_max'],'temp',s)+' / '+format_value(row['temp_min'],'temp',s)
                return short[field]+format_value(row.get(field),field,s)
            parts=[labels[i]]+[value(f) for f in spec['fields']]
            text='\n'.join(parts) if spec['mode']=='cards' else '  ·  '.join(parts)
            _text(target,text,(x+(i%columns)*cw+2,y+(i//columns)*ch+2,cw-4,ch-4),s,assets,warnings,'Zeitreihe')
        return
    # Different physical units get stacked plots instead of misleading shared axes.
    d=ImageDraw.Draw(target);fields=spec['fields'];ph=h/len(fields)
    for fi,field in enumerate(fields):
        color=spec['colors'][fi%len(spec['colors'])];py=y+fi*ph;left=x+(36 if spec['axes'] else 4);right=x+w-4;top=py+20;bottom=py+ph-25
        if right<=left or bottom<=top:continue
        numeric=[convert_number(r[field],field,s)[0] for r in rows if isinstance(r.get(field),(int,float))]
        if not numeric:continue
        lo,hi=(min(numeric),max(numeric)) if spec['y_auto'] else (spec['y_min'],spec['y_max'])
        if hi<=lo:lo-=1;hi+=1
        if spec['mode']=='bar' and spec['y_auto']:lo=min(0,lo);hi=max(0,hi)
        if spec['legend']:_text(target,FIELDS[field][0]+' ('+convert_number(0,field,s)[1]+')',(x,py,w,18),dict(s,font_size=12,color=color),assets,warnings,'Legende')
        for k in range(4):
            yy=top+(bottom-top)*k/3
            if spec['grid']:d.line((left,yy,right,yy),fill='#d5d5d5',width=1)
            if spec['axes']:_text(target,f'{hi-(hi-lo)*k/3:.1f}',(x,yy-6,32,12),dict(s,font_size=9),assets,warnings,'Achse')
        previous=None;step=(right-left)/max(1,len(rows)-1)
        for i,row in enumerate(rows):
            value=row.get(field)
            if not isinstance(value,(int,float)):previous=None;continue
            value=convert_number(value,field,s)[0]
            xx=left+i*step;yy=bottom-(max(lo,min(hi,value))-lo)/(hi-lo)*(bottom-top)
            if spec['mode']=='line':
                if previous:d.line((*previous,xx,yy),fill=color,width=spec['line_width'])
                if spec['points']:d.ellipse((xx-2,yy-2,xx+2,yy+2),fill=color)
            else:
                zero=bottom-(max(lo,min(hi,0))-lo)/(hi-lo)*(bottom-top)
                d.rectangle((xx-min(10,step*.35),min(yy,zero),xx+min(10,step*.35),max(yy,zero)+1),fill=color)
            previous=(xx,yy)
            if i in (0,len(rows)//2,len(rows)-1):_text(target,labels[i],(xx-25,bottom+4,50,16),dict(s,font_size=10),assets,warnings,'Zeitachse')


def render_widget(document,page,widget,size,data,assets,protected=True):
    if 'content_layout' in widget:return render_content_widget(document,page,widget,size,data,assets)
    s=style(document,page,widget);size=tuple(max(1,round(v)) for v in size);w,h=size;warnings=[]
    if s['font'] not in ('Sans','Serif','Mono') and not (Path(assets)/s['font']).is_file():warnings.append('Schriftdatei fehlt · Ersatzschrift in der Vorschau')
    if s['image'] and not (Path(assets)/s['image']).is_file():warnings.append('Hintergrundbild fehlt')
    out,mask=surface(size,s,assets)
    pad=[s['padding_'+side]+s['border_width'] for side in ('left','top','right','bottom')]
    x,y=pad[0],pad[1];cw=max(1,w-pad[0]-pad[2]);ch=max(1,h-pad[1]-pad[3]);kind=widget['type']
    title=s['title'] or KINDS[kind]['title']
    if s['show_title']:
        th=min(ch*.25,s['title_size']*1.5);_text(out,title,(x,y,cw,th),dict(s,font_size=s['title_size'],bold=True),assets,warnings,'Titel');y+=th+s['content_gap'];ch=max(1,ch-th-s['content_gap'])
    box=(x,y,cw,ch);values=dict(data.get('values',{}));now=data.get('now') or datetime.now(timezone.utc)
    zone=ZoneInfo(data.get('zone') or 'UTC');local=now.astimezone(zone)
    time_format=s['time_format']
    if kind=='clock' and 'seconds' in widget['fields'] and 'time' in widget['fields'] and '%S' not in time_format:
        time_format=time_format.replace('%M','%M:%S')
    values.update(time=local_format(local,time_format),date=local_format(local,s['date_format']))
    if data.get('zone_known') is False:
        values['time']+=' UTC';values['date']+=' UTC'
    if kind=='series':draw_series(out,box,widget['series'],data,s,assets,warnings)
    elif kind in ('hourly','daily'):
        from wetterstation.designer.model import default_series
        spec=default_series();spec.update(source='1h' if kind=='hourly' else '1day',step=60 if kind=='hourly' else 1440,duration=480 if kind=='hourly' else 7200,fields=[{'rain':'rain','temp':'temp','description':'description','wind':'wind'}[f] for f in widget['fields']],columns=8 if kind=='hourly' else 5)
        if spec['fields']:draw_series(out,box,spec,data,s,assets,warnings)
    elif kind=='radar':
        map_image=data.get('map')
        if map_image is not None and 'map' in widget['fields']:
            base=map_image.convert('RGBA').resize((max(1,round(cw)),max(1,round(ch))))
            base=ImageEnhance.Brightness(base).enhance(s['map_brightness']);base=ImageEnhance.Color(base).enhance(s['map_saturation']);base.putalpha(round(255*s['map_opacity']));out.alpha_composite(base,(round(x),round(y)))
            overlay=data.get('radar')
            if overlay is not None:
                overlay=overlay.convert('RGBA').resize(base.size);overlay.putalpha(overlay.getchannel('A').point(lambda a:round(a*s['radar_opacity'])));out.alpha_composite(overlay,(round(x),round(y)))
            if 'place' in widget['fields']:
                d=ImageDraw.Draw(out);cx=x+cw/2;cy=y+ch/2;r=s['marker_size'];d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=s['marker_color'],outline='white',width=2)
                d.rectangle((x,y,x+cw,y+24),fill=rgba(s['label_background']))
                _text(out,data.get('place','Ort'),(x,y,cw,24),dict(s,font_size=14,color=s['label_color']),assets,warnings,'Ort')
            d=ImageDraw.Draw(out)
            for sx,sy,ex,ey in data.get('motion',[])[:3]:
                sx=x+sx/1024*cw;ex=x+ex/1024*cw;sy=y+sy/600*ch;ey=y+ey/600*ch
                d.line((sx,sy,ex,ey),fill='#4b5359',width=2)
                angle=math.atan2(ey-sy,ex-sx)
                d.polygon([(ex,ey),(ex-8*math.cos(angle-.5),ey-8*math.sin(angle-.5)),(ex-8*math.cos(angle+.5),ey-8*math.sin(angle+.5))],fill='#4b5359')
        else:_text(out,data.get('map_notice','Noch keine aktuelle Karte'),box,s,assets,warnings,'Karte')
        # Coverage, attribution and stale state remain above all decorative layers.
        notices=[str(data.get(k,'')) for k in ('map_notice','attribution','coverage') if data.get(k)]
        if 'updated' in widget['fields']:notices.append(str(data.get('map_updated','Noch nicht aktualisiert')))
        if notices:_text(out,'\n'.join(notices),(x,y+max(0,ch-48),cw,min(ch,48)),dict(s,font_size=11,color='#111111'),assets,warnings,'Kartenhinweise')
    elif kind!='custom':
        fields=widget['fields'];lines=[]
        for field in fields:
            if kind=='clock':key=field
            elif kind=='date':key='date'
            elif kind.startswith('sensor_'):key=kind
            elif kind in ('sensors','indoor'):key=('sensor_' if kind=='sensors' else 'indoor_')+field
            elif field=='value':key=kind
            else:key=field
            if field=='seconds' and 'time' in fields:continue
            value=local.strftime('%S') if field=='seconds' else values.get(key)
            lines.append(format_value(value,key,s))
        if lines:_text(out,'\n'.join(lines),box,s,assets,warnings,'Werte')
    for element in sorted(widget.get('elements',[]),key=lambda e:e.get('z',0)):
        es=style(document,page,widget,element);ex=round(x+element['x']*cw);ey=round(y+element['y']*ch);ew=max(1,round(element['w']*cw));eh=max(1,round(element['h']*ch));ek=element['kind']
        if ek in ('text','data'):
            if es['font'] not in ('Sans','Serif','Mono') and not (Path(assets)/es['font']).is_file():warnings.append('Schriftdatei fehlt · Ersatzschrift in der Vorschau')
            if ek=='text':value=element.get('text','')
            elif element['binding'] in ('time','date'):
                value=local_format(local,es['time_format'] if element['binding']=='time' else es['date_format'])+(' UTC' if data.get('zone_known') is False else '')
            else:value=format_value(values.get(element['binding']),element['binding'],es)
            _text(out,value,(ex,ey,ew,eh),es,assets,warnings,'Inhalt')
        else:
            layer=Image.new('RGBA',(ew,eh));d=ImageDraw.Draw(layer)
            if ek=='image' and element.get('asset'):
                try:
                    layer=picture(Path(assets)/element['asset'],(ew,eh),es['image_mode'],(es['image_x'],es['image_y']))
                    layer.putalpha(layer.getchannel('A').point(lambda a:round(a*es['opacity'])))
                except OSError:warnings.append('Bilddatei fehlt')
            elif ek=='line':d.line((0,eh//2,ew,eh//2),fill=rgba(es['border_color'],es['opacity']),width=max(1,round(es['border_width'])))
            elif ek=='rectangle':layer,_=surface((ew,eh),es,assets)
            else:
                draw=d.ellipse if ek=='ellipse' else d.rectangle
                draw((0,0,ew-1,eh-1),fill=rgba(es['background'],es['opacity']),outline=rgba(es['border_color']),width=max(0,min(round(es['border_width']),min(ew,eh)//2)))
            if es['rotation']:layer=layer.rotate(-es['rotation'],resample=Image.Resampling.BICUBIC)
            out.alpha_composite(layer,(ex,ey))
    if protected and (kind.startswith('sensor_') or kind in ('sensors','indoor') or any(e.get('kind')=='data' and e.get('binding','').startswith(('sensor_','indoor_')) for e in content_elements(widget))):
        _text(out,'DEMO · keine Sensoren verbunden',(2,max(0,h-18),max(1,w-4),16),dict(s,font_size=10,color='#111111'),assets,warnings,'Demo')
    return finish_widget(out,mask,s,size),warnings


def finish_widget(out,mask,s,size):
    w,h=size
    from PIL import ImageChops
    out.putalpha(ImageChops.multiply(out.getchannel('A'),mask))
    if s['shadow']:
        inset=math.ceil(s['shadow_blur']+max(abs(s['shadow_x']),abs(s['shadow_y'])))
        inset=min(inset,max(0,min(w,h)//4))
        card=out.resize((max(1,w-2*inset),max(1,h-2*inset)))
        shadow=Image.new('RGBA',size)
        silhouette=Image.new('RGBA',card.size,rgba(s['shadow_color'],s['shadow_opacity']));silhouette.putalpha(card.getchannel('A').point(lambda a:round(a*s['shadow_opacity'])))
        shadow.alpha_composite(silhouette,(inset+round(s['shadow_x']),inset+round(s['shadow_y'])));shadow=shadow.filter(ImageFilter.GaussianBlur(s['shadow_blur']));shadow.alpha_composite(card,(inset,inset));out=shadow
    return out


def render_content_widget(document,page,widget,size,data,assets):
    from wetterstation.designer.content import area,blocks
    from copy import deepcopy
    size=tuple(max(1,round(v)) for v in size);s=style(document,page,widget)
    out,mask=surface(size,s,assets);warnings=[]
    x,y,cw,ch=area(document,page,widget,(0,0,*size))
    for e in blocks(document,page,widget,(0,0,*size)):
        ex,ey=round(x+e['x']*cw),round(y+e['y']*ch);ew,eh=max(1,round(e['w']*cw)),max(1,round(e['h']*ch))
        child=deepcopy(widget);child.pop('content_layout',None);child['elements']=[]
        child['style']={**s,'show_title':False,'background':'#ffffff00','image':'','gradient':'none','shadow':False,'border_width':0,'radius':0,'individual_corners':False,
                        **{'padding_'+side:0 for side in ('left','right','top','bottom')}}
        if e['kind']=='structure':child['style'].update(e['style'])
        else:
            child.pop('series',None);child.update(type='custom',fields=[],elements=[{**deepcopy(e),'style':style(document,page,widget,e),'x':0,'y':0,'w':1,'h':1}])
        layer,notes=render_widget(document,page,child,(ew,eh),data,assets,protected=False)
        out.alpha_composite(layer,(ex,ey));warnings.extend(notes)
    if widget['type'].startswith('sensor_') or widget['type'] in ('sensors','indoor') or any(e.get('kind')=='data' and e.get('binding','').startswith(('sensor_','indoor_')) for e in content_elements(widget)):
        _text(out,'DEMO · keine Sensoren verbunden',(2,max(0,size[1]-18),max(1,size[0]-4),16),dict(s,font_size=10,color='#111111'),assets,warnings,'Demo')
    return finish_widget(out,mask,s,size),warnings


def render_page(document,page_id=None,data=None,assets='',draw_grid=False,cache=None):
    data=data or demo_data();page=next((p for p in document['pages'] if p['id']==page_id),document['pages'][0]);s=style(document,page)
    size=(document['display']['width'],document['display']['height']);background=dict(s,border_width=0,radius=0,individual_corners=False)
    out,_=surface(size,background,assets);warnings=[];rects,g=widget_rects(document,page)
    if draw_grid:
        d=ImageDraw.Draw(out)
        for i in range(g['columns']+1):
            xx=g['x']+i*(g['cell_w']+g['gap_x'])-g['gap_x']/2;d.line((xx,g['y'],xx,g['y']+g['height']),fill='#e2e7ef',width=1)
        for i in range(g['rows']+1):
            yy=g['y']+i*(g['cell_h']+g['gap_y'])-g['gap_y']/2;d.line((g['x'],yy,g['x']+g['width'],yy),fill='#e2e7ef',width=1)
    if s['show_title']:_text(out,s['title'] or page['title'],(s['margin_left'],s['margin_top'],max(1,size[0]-s['margin_left']-s['margin_right']),s['title_size']*1.5),dict(s,font_size=s['title_size'],bold=True),assets,warnings,'Seitentitel')
    for widget in page['widgets']:
        x,y,w,h=rects[widget['id']]
        from wetterstation.designer.model import digest
        source=(widget.get('series',{}).get('source') if widget['type']=='series' else '1h' if widget['type']=='hourly' else '1day' if widget['type']=='daily' else '')
        clock=widget['type'] in ('clock','date') or any(e.get('binding') in ('time','date') for e in content_elements(widget) if e.get('kind')=='data')
        sample_time=data.get('now') or datetime.now(timezone.utc)
        source_time=(sample_time.astimezone(ZoneInfo(data.get('zone') or 'UTC')).date().isoformat() if source=='1day' else int(sample_time.timestamp()//({'1min':60,'15min':900,'1h':3600}.get(source,1)))) if source else ''
        signature=(digest({'widget':widget,'style':style(document,page,widget),'size':[w,h],'values':data.get('values',{}),
                           'series':data.get('series',{}).get(source,[]) if source else [],
                           'series_notice':data.get('series_notices',{}).get(source,'') if source else '',
                           'time':str(data.get('now')) if clock else source_time,'zone':[data.get('zone'),data.get('zone_known')],
                           'motion':data.get('motion',[]) if widget['type']=='radar' else [],
                           'notices':[data.get(k,'') for k in ('map_notice','attribution','coverage','map_updated')]}),
                   id(data.get('map')) if widget['type']=='radar' else 0,id(data.get('radar')) if widget['type']=='radar' else 0,str(assets),widget['id'])
        cached=cache.get(signature) if cache is not None else None
        if cached is None:
            cached=render_widget(document,page,widget,(w,h),data,assets)
            if cache is not None:
                for old_key in list(cache):
                    if old_key[-1]==widget['id']:cache.pop(old_key)
                cache[signature]=cached
                while cache and sum(v[0].width*v[0].height*4 for v in cache.values())>16*1024*1024:
                    cache.pop(next(iter(cache)))
        image,ww=cached;out.alpha_composite(image,(x,y));warnings.extend(ww)
    # Protected labels are composed last and independently from editable opacity,
    # imported overlays, tiny widget sizes, and inherited font settings.
    protected=[]
    radar_widgets=[widget for widget in page['widgets'] if widget['type']=='radar']
    if radar_widgets:
        protected.extend(str(data[key]) for key in ('attribution','coverage','map_notice') if data.get(key))
        if any(style(document,page,widget)['radar_opacity']==0 for widget in radar_widgets):protected.append('Radar ausgeblendet')
    sensors=any(widget['type'].startswith('sensor_') or widget['type'] in ('sensors','indoor') or any(e.get('kind')=='data' and e.get('binding','').startswith(('sensor_','indoor_')) for e in content_elements(widget)) for widget in page['widgets'])
    if sensors:protected.append('Sensordaten: DEMO · keine Sensoren verbunden')
    if protected:
        text=' · '.join(dict.fromkeys(protected));height=min(size[1],36);ImageDraw.Draw(out).rectangle((0,size[1]-height,size[0],size[1]),fill='#ffffff')
        _text(out,text,(4,size[1]-height,max(1,size[0]-8),height),dict(s,font='Sans',font_size=11,opacity=1,color='#111111',rotation=0,auto_fit=True,wrap=True),assets,warnings,'Quellen / Abdeckung')
    if data.get('demo'):
        ImageDraw.Draw(out).rectangle((max(0,size[0]-220),0,size[0],18),fill='#ffffff')
        _text(out,'DEMO · Beispieldaten',(max(0,size[0]-220),0,min(220,size[0]),18),dict(s,font='Sans',font_size=11,color='#111111',opacity=1,rotation=0,auto_fit=True),assets,warnings,'Demo')
    return out,rects,list(dict.fromkeys(warnings))


def output_image(image,rotation):
    return image.rotate(-rotation,expand=True) if rotation else image

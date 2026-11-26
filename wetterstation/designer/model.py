"""Design schema 3, inheritance and deterministic, non-destructive grid edits."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
import re
import uuid

from wetterstation.ui.widgets import CATALOG, default_layout, overlaps, NoSpace, LayoutConflict


@dataclass(frozen=True)
class Property:
    label: str
    group: str
    kind: str
    default: object
    minimum: float = 0
    maximum: float = 8192
    choices: tuple = ()


PROPERTIES = {}


def prop(key, label, group, kind, default, lo=0, hi=8192, choices=()):
    PROPERTIES[key] = Property(label, group, kind, default, lo, hi, tuple(choices))


prop('background', 'Hintergrundfarbe', 'Fläche', 'color', '#ffffff')
prop('opacity', 'Deckkraft', 'Fläche', 'float', 1., 0, 1)
prop('gradient', 'Farbverlauf', 'Fläche', 'choice', 'none', choices=('none', 'vertical', 'horizontal'))
prop('gradient_color', 'Zweite Verlaufsfarbe', 'Fläche', 'color', '#dcecff')
prop('image', 'Hintergrundbild', 'Fläche', 'asset', '')
prop('image_mode', 'Bildskalierung', 'Fläche', 'choice', 'cover', choices=('cover', 'contain', 'stretch'))
prop('image_x', 'Bildausschnitt horizontal', 'Fläche', 'float', .5, 0, 1)
prop('image_y', 'Bildausschnitt vertikal', 'Fläche', 'float', .5, 0, 1)
prop('border_color', 'Rahmenfarbe', 'Rahmen', 'color', '#606060')
prop('border_width', 'Rahmenstärke', 'Rahmen', 'float', 2., 0, 128)
prop('border_opacity', 'Rahmendeckkraft', 'Rahmen', 'float', 1., 0, 1)
prop('border_style', 'Linienart', 'Rahmen', 'choice', 'solid', choices=('solid', 'dashed'))
for side, label in (('top', 'Oben'), ('right', 'Rechts'), ('bottom', 'Unten'), ('left', 'Links')):
    prop('border_'+side, 'Rahmen '+label, 'Rahmen', 'bool', True)
    prop('padding_'+side, 'Innenabstand '+label, 'Abstände', 'float', 12., 0, 512)
    prop('margin_'+side, 'Außenabstand '+label, 'Seite', 'float', 12., 0, 512)
prop('radius', 'Eckradius', 'Ecken', 'float', 14., 0, 4096)
prop('individual_corners', 'Ecken einzeln einstellen', 'Ecken', 'bool', False)
for corner, label in (('tl','Oben links'),('tr','Oben rechts'),('br','Unten rechts'),('bl','Unten links')):
    prop('radius_'+corner, 'Radius '+label, 'Ecken', 'float', 14., 0, 4096)
prop('shadow', 'Schatten', 'Schatten', 'bool', False)
prop('shadow_color', 'Schattenfarbe', 'Schatten', 'color', '#000000')
prop('shadow_opacity', 'Schattendeckkraft', 'Schatten', 'float', .2, 0, 1)
prop('shadow_x', 'Schattenversatz X', 'Schatten', 'float', 0., -128, 128)
prop('shadow_y', 'Schattenversatz Y', 'Schatten', 'float', 3., -128, 128)
prop('shadow_blur', 'Schattenunschärfe', 'Schatten', 'float', 8., 0, 128)
prop('color', 'Schriftfarbe', 'Schrift', 'color', '#111111')
prop('font', 'Schriftart', 'Schrift', 'font', 'Sans')
prop('font_size', 'Schriftgröße', 'Schrift', 'float', 28., 1, 512)
prop('bold', 'Fett', 'Schrift', 'bool', False)
prop('italic', 'Kursiv', 'Schrift', 'bool', False)
prop('line_spacing', 'Zeilenabstand', 'Schrift', 'float', 1.15, .5, 4)
prop('wrap', 'Zeilenumbruch', 'Schrift', 'bool', True)
prop('auto_fit', 'Schrift automatisch einpassen', 'Schrift', 'bool', True)
prop('align', 'Horizontal ausrichten', 'Position', 'choice', 'center', choices=('left','center','right'))
prop('valign', 'Vertikal ausrichten', 'Position', 'choice', 'center', choices=('top','center','bottom'))
prop('rotation', 'Inhalt drehen', 'Position', 'float', 0., -360, 360)
prop('content_gap', 'Inhaltsabstand', 'Abstände', 'float', 8., 0, 512)
prop('gap_x', 'Widgetabstand horizontal', 'Seite', 'float', 8., 0, 512)
prop('gap_y', 'Widgetabstand vertikal', 'Seite', 'float', 8., 0, 512)
prop('show_title', 'Titel anzeigen', 'Beschriftung', 'bool', True)
prop('title', 'Eigener Titel', 'Beschriftung', 'text', '')
prop('title_size', 'Titelgröße', 'Beschriftung', 'float', 18., 1, 512)
prop('decimals', 'Nachkommastellen', 'Werte', 'int', 1, 0, 6)
prop('show_unit', 'Einheiten anzeigen', 'Werte', 'bool', True)
prop('decimal_comma', 'Dezimalkomma', 'Werte', 'bool', True)
prop('temperature_unit', 'Temperatureinheit', 'Werte', 'choice', '°C', choices=('°C','°F'))
prop('wind_unit', 'Windeinheit', 'Werte', 'choice', 'm/s', choices=('m/s','km/h','mph'))
prop('pressure_unit', 'Luftdruckeinheit', 'Werte', 'choice', 'hPa', choices=('hPa','mmHg','inHg'))
prop('time_format', 'Uhrzeitformat', 'Werte', 'choice', '%H:%M', choices=('%H:%M','%H:%M:%S','%I:%M %p','%S'))
prop('date_format', 'Datumsformat', 'Werte', 'choice', '%d.%m.%Y', choices=('%d.%m.%Y','%a %d.%m.','%A, %d.%m.%Y','%Y-%m-%d'))
prop('map_opacity', 'Kartendeckkraft', 'Karte', 'float', 1., 0, 1)
prop('radar_opacity', 'Radardeckkraft', 'Karte', 'float', 1., 0, 1)
prop('map_brightness', 'Kartenhelligkeit', 'Karte', 'float', 1., 0, 2)
prop('map_saturation', 'Kartensättigung', 'Karte', 'float', 1., 0, 2)
prop('marker_color', 'Markerfarbe', 'Karte', 'color', '#f17647')
prop('marker_size', 'Markergröße', 'Karte', 'float', 7., 0, 128)
prop('label_background', 'Beschriftungsfläche', 'Karte', 'color', '#ffffff')
prop('label_color', 'Kartenbeschriftung', 'Karte', 'color', '#111111')

DEFAULT_STYLE = {k: deepcopy(v.default) for k,v in PROPERTIES.items()}
KINDS = dict(CATALOG)
KINDS.update({'custom': {'title':'Eigene Inhalte','fields':{},'width':4,'height':3,'min_width':1,'min_height':1},
              'series': {'title':'Eigene Zeitreihe','fields':{},'width':8,'height':4,'min_width':1,'min_height':1}})
DATA_FIELDS = ('temp','feels_like','description','humidity','wind','pressure','time','date',
               'sensor_temp','sensor_humidity','sensor_pressure','sensor_wind','indoor_temp','indoor_humidity')
MAX_PAGES, MAX_WIDGETS = 64, 128


def content_elements(widget):
    return [*widget.get('elements',[]),*widget.get('content_layout',{}).values()]


def uid(prefix='w'):
    return prefix+'-'+uuid.uuid4().hex[:16]


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()


def grid(page):
    g = page.get('grid', {})
    if not isinstance(g,dict) or (g and set(g)!={'columns','rows'}):raise ValueError('Ungültiges Raster.')
    return g.get('columns',12), g.get('rows',8)


def style(*levels):
    result = deepcopy(DEFAULT_STYLE)
    for level in levels:
        if level:
            result.update(level.get('style',{}))
    return result


def validate_style(value):
    if not isinstance(value,dict) or set(value)-set(PROPERTIES):
        raise ValueError('Unbekannte Gestaltungseigenschaft.')
    for key,val in value.items():
        p=PROPERTIES[key]
        if p.kind in ('int','float'):
            if isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val) or not p.minimum<=val<=p.maximum or (p.kind=='int' and type(val) is not int):
                raise ValueError('Ungültiger Wert: '+p.label)
        elif p.kind=='bool' and type(val) is not bool:
            raise ValueError('Ungültiger Schalter.')
        elif p.kind=='choice' and val not in p.choices:
            raise ValueError('Ungültige Auswahl: '+p.label)
        elif p.kind in ('color','text','asset','font'):
            if not isinstance(val,str) or len(val)>1024:
                raise ValueError('Ungültiger Text.')
            if p.kind=='color' and not re.fullmatch(r'#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?',val):
                raise ValueError('Bitte eine gültige HEX-Farbe eingeben.')
            if p.kind=='asset' and val and not re.fullmatch(r'[0-9a-f]{64}\.(png|jpg|webp)',val):
                raise ValueError('Ungültiges Bild.')
            if p.kind=='font' and val not in ('Sans','Serif','Mono') and not re.fullmatch(r'[0-9a-f]{64}\.(ttf|otf)',val):
                raise ValueError('Ungültige Schrift.')
    return deepcopy(value)


def new_widget(kind, columns=12, rows=8):
    meta=KINDS[kind]
    w={'id':uid(),'type':kind,'x':0,'y':0,'w':min(columns,meta['width']),
       'h':min(rows,meta['height']),'fields':list(meta['fields']),'style':{},'locked':False,'elements':[]}
    if kind=='clock': w['fields']=['time','date']
    if kind=='custom':
        w['elements']=[new_element('text')]
    if kind=='series':
        w['series']=default_series()
    return w


def new_element(kind):
    return {'id':uid('e'),'kind':kind,'x':.1,'y':.1,'w':.8,'h':.8,'text':'Dein Text',
            'binding':'temp','asset':'','style':{},'z':0}


def default_series():
    return {'source':'15min','duration':180,'step':15,'offset':0,'refresh':60,
            'fields':['temp'],'mode':'cards','columns':4,'legend':True,'axes':True,
            'grid':True,'line_width':2,'points':True,'y_auto':True,'y_min':0.,'y_max':30.,
            'colors':['#007aff','#ff9500','#34c759','#af52de']}


def from_layout(layout=None):
    if layout and layout.get('version') in (3,4):
        return validate(layout)
    layout=deepcopy(layout or default_layout())
    from wetterstation.ui.widgets import load_layout
    layout=load_layout(layout)
    for page in layout['pages']:
        page.update(grid={'columns':12,'rows':8},style={})
        for w in page['widgets']:
            w.update(style={},locked=False,elements=[])
    return {'version':3,'pages':layout['pages'],'style':{},'display':{'width':1024,'height':600,'rotation':0},
            'active_variant':'1024x600-landscape','variants':{},'assets':{},
            'presets':{'grids':{},'styles':{},'widgets':{}}}


def _id(value, seen):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',value) or value in seen:
        raise ValueError('Ungültige oder doppelte Kennung.')
    seen.add(value)


def validate_pages(pages, collisions=True, version=4):
    if not isinstance(pages,list) or not 1<=len(pages)<=MAX_PAGES:
        raise ValueError('Eine bis 64 Seiten sind möglich.')
    pids,wids=set(),set()
    for page in pages:
        if not isinstance(page,dict) or set(page)!={'id','title','widgets','grid','style'}:
            raise ValueError('Ungültige Seitendaten.')
        _id(page.get('id'),pids)
        if not isinstance(page.get('title'),str) or not page['title'].strip() or len(page['title'])>80:
            raise ValueError('Ungültiger Seitenname.')
        c,r=grid(page)
        if any(type(n) is not int or not 1<=n<=128 for n in (c,r)):
            raise ValueError('Das Raster benötigt 1 bis 128 Zeilen und Spalten.')
        validate_style(page.get('style',{}))
        items=page.get('widgets')
        if not isinstance(items,list) or len(items)>MAX_WIDGETS:
            raise ValueError('Höchstens 128 Widgets je Seite.')
        for i,w in enumerate(items):
            required={'id','type','x','y','w','h','fields','style','locked','elements'}
            if version==4 and isinstance(w,dict) and 'content_layout' in w:required.add('content_layout')
            if not isinstance(w,dict) or set(w)!=(required|({'series'} if w.get('type')=='series' else set())):
                raise ValueError('Ungültige Widgetdaten.')
            _id(w.get('id'),wids)
            if w.get('type') not in KINDS:
                raise ValueError('Unbekannter Widgettyp.')
            if any(type(w.get(k)) is not int for k in ('x','y','w','h')) or not (w['w']>=1 and w['h']>=1 and 0<=w['x']<=c-w['w'] and 0<=w['y']<=r-w['h']):
                raise ValueError('Widget liegt außerhalb des Rasters oder ist zu klein.')
            if collisions and any(overlaps(w,o) for o in items[:i]):
                raise NoSpace('Widgets dürfen sich nicht überlappen.')
            if not isinstance(w.get('fields'),list) or any(not isinstance(f,str) for f in w['fields']) or len(w['fields'])!=len(set(w['fields'])) or any(f not in KINDS[w['type']]['fields'] for f in w['fields']):
                raise ValueError('Ungültige Widgetinhalte.')
            if type(w.get('locked',False)) is not bool:
                raise ValueError('Ungültige Sperre.')
            validate_style(w.get('style',{}))
            elements=w.get('elements',[])
            overrides=w.get('content_layout',{})
            if not isinstance(overrides,dict) or len(overrides)>32 or any(not isinstance(k,str) or not k.startswith('builtin-') or not isinstance(e,dict) or e.get('id')!=k for k,e in overrides.items()):
                raise ValueError('Ungültige Inhaltsanordnung.')
            if not isinstance(elements,list) or len(elements)>128:
                raise ValueError('Zu viele Inhaltselemente.')
            eids=set()
            for e in [*elements,*overrides.values()]:
                if not isinstance(e,dict) or set(e)!={'id','kind','x','y','w','h','text','binding','asset','style','z'}:
                    raise ValueError('Ungültige Inhaltseigenschaften.')
                _id(e.get('id'),eids)
                if e.get('kind') not in ('text','data','image','line','rectangle','ellipse') and not (version==4 and e.get('kind')=='structure' and e['id']=='builtin-structure' and w['type'] in ('series','hourly','daily','radar')):
                    raise ValueError('Unbekanntes Inhaltselement.')
                if any(isinstance(e.get(k),bool) or not isinstance(e.get(k),(int,float)) or not math.isfinite(e[k]) for k in ('x','y','w','h')) or not (0<=e['x']<=1 and 0<=e['y']<=1 and 0<e['w']<=1-e['x']+1e-9 and 0<e['h']<=1-e['y']+1e-9):
                    raise ValueError('Inhalt muss innerhalb des Widgets liegen.')
                if not isinstance(e.get('text',''),str) or len(e.get('text',''))>4000 or e.get('binding','temp') not in DATA_FIELDS or type(e.get('z',0)) is not int:
                    raise ValueError('Ungültiges Inhaltselement.')
                validate_style(e.get('style',{}))
                if e.get('asset') and not re.fullmatch(r'[0-9a-f]{64}\.(png|jpg|webp)',e['asset']):
                    raise ValueError('Ungültiger Bildverweis.')
            if w['type']=='series':
                from wetterstation.designer.series import validate_spec
                validate_spec(w.get('series'))


def validate(document, collisions=True):
    if not isinstance(document,dict) or document.get('version') not in (3,4):
        raise ValueError('Gestaltungsformat 3 oder 4 erforderlich.')
    version=document['version']
    if set(document)-({'version','pages','style','display','active_variant','variants','assets','presets'}|({'inner_grid'} if version==4 else set())):
        raise ValueError('Unbekannte Gestaltungsdaten.')
    if version==4:
        g=document.get('inner_grid')
        if not isinstance(g,dict) or set(g)!={'step','visible','snap'} or type(g['step']) is not int or not 1<=g['step']<=128 or any(type(g[k]) is not bool for k in ('visible','snap')):raise ValueError('Ungültiges Innenraster.')
    validate_pages(document.get('pages'),collisions,version)
    validate_style(document.get('style',{}))
    def display(d):
        if not isinstance(d,dict) or set(d)!={'width','height','rotation'} or any(type(d[k]) is not int or not 64<=d[k]<=8192 for k in ('width','height')) or d['width']*d['height']>20_000_000 or type(d['rotation']) is not int or d['rotation'] not in (0,90,180,270):
            raise ValueError('Ungültiges Displayprofil.')
    display(document.get('display'))
    if not isinstance(document.get('active_variant'),str) or len(document['active_variant'])>80:
        raise ValueError('Ungültige Variante.')
    variants=document.get('variants',{})
    if not isinstance(variants,dict) or len(variants)>32:
        raise ValueError('Zu viele Displayvarianten.')
    if document['active_variant'] in variants:raise ValueError('Aktive Variante darf nicht doppelt gespeichert sein.')
    for key,v in variants.items():
        if not isinstance(key,str) or len(key)>80 or not isinstance(v,dict) or set(v)!={'display','pages'}:
            raise ValueError('Ungültige Variante.')
        display(v['display']);validate_pages(v['pages'],collisions,version)
    assets=document.get('assets',{})
    if not isinstance(assets,dict) or len(assets)>512:
        raise ValueError('Zu viele Dateien.')
    for name,meta in assets.items():
        if not re.fullmatch(r'[0-9a-f]{64}\.(png|jpg|webp|ttf|otf)',name) or not isinstance(meta,dict) or set(meta)!={'name','size'} or not isinstance(meta['name'],str) or len(meta['name'])>240 or type(meta['size']) is not int or not 0<meta['size']<=32_000_000:
            raise ValueError('Ungültige Dateiliste.')
    presets=document.get('presets',{})
    if not isinstance(presets,dict) or set(presets)!={'grids','styles','widgets'} or len(json.dumps(presets))>500_000:
        raise ValueError('Ungültige Vorlagen.')
    for kind,entries in presets.items():
        if not isinstance(entries,dict) or len(entries)>128:
            raise ValueError('Zu viele Vorlagen.')
        for name,value in entries.items():
            if not isinstance(name,str) or not name.strip() or len(name)>80:raise ValueError('Ungültiger Vorlagenname.')
            if kind=='styles':validate_style(value)
            elif kind=='grids':
                if not isinstance(value,dict) or set(value)!={'columns','rows'} or any(type(n) is not int or not 1<=n<=128 for n in value.values()):raise ValueError('Ungültige Rastervorlage.')
            else:validate_pages([{'id':'preset','title':'Vorlage','grid':{'columns':128,'rows':128},'style':{},'widgets':[value]}])
    if len(json.dumps(document))>8_000_000:
        raise ValueError('Der Entwurf ist zu groß.')
    return deepcopy(document)


def place(items, columns, rows, *, pinned=None, compact=False):
    """First-fit only when requested; normal drags never move neighbours."""
    result=deepcopy(items)
    occupied=[]
    order=sorted(result,key=lambda w:(w['id']!=pinned,not w.get('locked',False),w['y'],w['x']))
    for w in order:
        if w['w']>columns or w['h']>rows:
            raise NoSpace('Für dieses Widget ist im neuen Raster kein Platz.')
        if w.get('locked') or w['id']==pinned:
            positions=[(w['x'],w['y'])]
        else:
            positions=[(x,y) for y in range(rows-w['h']+1) for x in range(columns-w['w']+1)]
            if not compact:
                positions.sort(key=lambda p:(abs(p[0]-w['x'])+abs(p[1]-w['y']),p[1],p[0]))
        for x,y in positions:
            candidate=dict(w,x=x,y=y)
            if 0<=x<=columns-w['w'] and 0<=y<=rows-w['h'] and not any(overlaps(candidate,o) for o in occupied):
                w.update(x=x,y=y);occupied.append(w);break
        else:
            raise NoSpace('Kein freier Bereich. Bisherige Anordnung bleibt erhalten.')
    return result


def resize_grid(page,columns,rows,arrange=False,allow_conflicts=False):
    oldc,oldr=grid(page)
    result=deepcopy(page);result['grid']={'columns':columns,'rows':rows}
    for w in result['widgets']:
        w['w']=min(columns,max(1,round(w['w']/oldc*columns)))
        w['h']=min(rows,max(1,round(w['h']/oldr*rows)))
        w['x']=min(columns-w['w'],max(0,round(w['x']/oldc*columns)))
        w['y']=min(rows-w['h'],max(0,round(w['y']/oldr*rows)))
    if arrange:
        result['widgets']=place(result['widgets'],columns,rows)
    validate_pages([result],collisions=not allow_conflicts)
    return result


def switch_variant(document,width,height,rotation=0):
    result=deepcopy(document)
    key=f'{width}x{height}-'+('portrait' if height>width else 'landscape')
    if key==result['active_variant']:
        result['display']['rotation']=rotation
        return validate(result,collisions=False)
    result['variants'][result['active_variant']]={'display':deepcopy(result['display']),'pages':deepcopy(result['pages'])}
    if key in result['variants']:
        variant=result['variants'].pop(key)
    else:
        pages=deepcopy(result['pages'])
        if (height>width)!=(result['display']['height']>result['display']['width']):
            converted=[]
            for p in pages:
                try:converted.append(resize_grid(p,*reversed(grid(p)),arrange=True))
                except NoSpace:converted.append(resize_grid(p,*reversed(grid(p)),allow_conflicts=True))
            pages=converted
        variant={'display':{'width':width,'height':height,'rotation':rotation},'pages':pages}
    result.update(active_variant=key,**variant)
    return validate(result,collisions=False)


def arrangement(document,operations,expected_revision,restorable=None):
    """Apply a narrow phone command list; styling is never accepted from the phone."""
    if digest(document)!=expected_revision:
        # Same canonical hash as ui.widgets.revision (ASCII JSON).
        from wetterstation.ui.widgets import revision
        if revision(document)!=expected_revision:
            raise LayoutConflict('Die Gestaltung wurde inzwischen geändert. Bitte neu laden.')
    result=deepcopy(document);restorable=restorable or {'widgets':{},'pages':{}}
    if not isinstance(operations,list) or len(operations)>256:
        raise ValueError('Ungültige Anordnungsänderung.')
    for op in operations:
        if not isinstance(op,dict):raise ValueError('Ungültiger Befehl.')
        pages=result['pages'];kind=op.get('op')
        page=next((p for p in pages if p['id']==op.get('page')),None)
        if kind=='add_page':
            if set(op)!={'op','page','title'}:raise ValueError('Ungültiger Befehl.')
            restored=deepcopy(restorable['pages'].get(op['page'],{'id':op['page'],'grid':{'columns':12,'rows':8},'style':{}}))
            restored.update(title=op['title'],widgets=[]);pages.append(restored)
        elif kind=='remove_page':
            if set(op)!={'op','page'} or page is None:raise ValueError('Unbekannte Seite.')
            pages.remove(page)
        elif kind=='order_pages':
            if set(op)!={'op','ids'} or sorted(op['ids'])!=sorted(p['id'] for p in pages):raise ValueError('Ungültige Seitenreihenfolge.')
            result['pages']=[next(p for p in pages if p['id']==i) for i in op['ids']]
        elif page is None:raise ValueError('Unbekannte Seite.')
        elif kind=='rename_page':
            if set(op)!={'op','page','title'}:raise ValueError('Ungültiger Befehl.')
            page['title']=op['title']
        elif kind=='add_widget':
            if set(op)!={'op','page','id','type','x','y','w','h'} or op['type'] not in KINDS:raise ValueError('Ungültiger Befehl.')
            item=deepcopy(restorable['widgets'].get(op['id'])) or new_widget(op['type'],*grid(page))
            if item['type']!=op['type']:raise ValueError('Widgettyp stimmt nicht mit der Wiederherstellung überein.')
            item.update({k:op[k] for k in ('id','x','y','w','h')});page['widgets'].append(item)
        else:
            item=next((w for p in pages for w in p['widgets'] if w['id']==op.get('id')),None)
            origin=next((p for p in pages if item in p['widgets']),None) if item else None
            if item is None or item.get('locked'):raise ValueError('Widget fehlt oder ist gesperrt.')
            if kind=='remove_widget' and set(op)=={'op','page','id'}:
                origin['widgets'].remove(item)
            elif kind=='move_widget' and set(op)=={'op','page','id','x','y','w','h'}:
                origin['widgets'].remove(item);item.update({k:op[k] for k in ('x','y','w','h')});page['widgets'].append(item)
            elif kind=='fields' and set(op)=={'op','page','id','fields'}:
                item['fields']=deepcopy(op['fields'])
            else:raise ValueError('Nicht erlaubte Handyänderung.')
    return validate(result)

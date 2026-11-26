"""Real source samples, DST-safe selection, and extra-call capacity estimates."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import math
from zoneinfo import ZoneInfo

SOURCES={'1min':(1,60,60),'15min':(15,48*60,50),'1h':(60,48*60,20),'1day':(1440,548*1440,10)}
FIELDS={'temp':('Temperatur','°C'),'feels_like':('Gefühlt','°C'),'humidity':('Luftfeuchte','%'),
        'pressure':('Luftdruck','hPa'),'wind':('Wind','m/s'),'rain':('Regenwahrscheinlichkeit','%'),
        'precipitation':('Niederschlag','mm/h'),'description':('Wetterlage','')}


def validate_spec(spec):
    required={'source','duration','step','offset','refresh','fields','mode','columns','legend','axes','grid','line_width','points','y_auto','y_min','y_max','colors'}
    if not isinstance(spec,dict) or set(spec)!=required or spec['source'] not in SOURCES:raise ValueError('Ungültige Zeitreihe.')
    base,horizon,_=SOURCES[spec['source']]
    for key in ('duration','step','offset','refresh','columns','line_width'):
        if type(spec[key]) is not int:raise ValueError('Zeitreihenwerte müssen ganzzahlig sein.')
    if not (base<=spec['step']<=horizon and spec['step']%base==0 and base<=spec['duration']<=horizon and 0<=spec['offset']<horizon and spec['offset']+spec['duration']<=horizon and spec['offset']%base==0 and 5<=spec['refresh']<=1440 and spec['refresh']%5==0 and 1<=spec['columns']<=128 and 1<=spec['line_width']<=20):
        raise ValueError('Zeitraum oder Schrittweite wird von dieser Datenquelle nicht unterstützt.')
    fields=spec['fields'];allowed={'precipitation'} if spec['source']=='1min' else set(FIELDS)-{'precipitation'}
    if not isinstance(fields,list) or not fields or len(fields)!=len(set(fields)) or any(f not in allowed for f in fields):raise ValueError('Datenfeld für diese Auflösung nicht verfügbar.')
    if spec['mode'] not in ('cards','table','line','bar') or (spec['mode'] in ('line','bar') and 'description' in fields):raise ValueError('Diagramme benötigen numerische Daten.')
    for key in ('legend','axes','grid','points','y_auto'):
        if type(spec[key]) is not bool:raise ValueError('Ungültige Diagrammoption.')
    for key in ('y_min','y_max'):
        if isinstance(spec[key],bool) or not isinstance(spec[key],(int,float)) or not math.isfinite(spec[key]):raise ValueError('Ungültige Achse.')
    if spec['y_min']>=spec['y_max']:raise ValueError('Achsenminimum muss kleiner als Maximum sein.')
    import re
    if not isinstance(spec['colors'],list) or not 1<=len(spec['colors'])<=16 or any(not isinstance(c,str) or not re.fullmatch('#[0-9a-fA-F]{6}',c) for c in spec['colors']):raise ValueError('Ungültige Reihenfarben.')
    return spec


def requirements(document):
    """Shared fetch range across every page in the active orientation."""
    result={}
    for page in document.get('pages',[]):
        for widget in page['widgets']:
            if widget['type']!='series':continue
            spec=validate_spec(widget['series']);source=spec['source']
            old=result.setdefault(source,{'duration':0,'refresh':1440})
            old['duration']=max(old['duration'],spec['duration']+spec['offset'])
            old['refresh']=min(old['refresh'],spec['refresh'])
    return result


def pages_needed(source,duration):
    base,_,batch=SOURCES[source]
    return math.ceil(math.ceil(duration/base)/batch)


def day_windows(now):
    utc=now.astimezone(timezone.utc);local=utc.astimezone(ZoneInfo('Europe/Berlin'))
    local_end=(local+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
    provider_end=(utc+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)
    return ((local.replace(hour=0,minute=0,second=0,microsecond=0).astimezone(timezone.utc),local_end),(utc.replace(hour=0,minute=0,second=0,microsecond=0),provider_end))


def regular_remaining(now):
    # Include one imminent full round; never take capacity promised to the base UI.
    utc=now.astimezone(timezone.utc)
    return max(3*math.ceil(max(0,(end-utc).total_seconds())/300) for _,end in day_windows(utc))


def capacity(document,now=None):
    now=now or datetime.now(timezone.utc)
    req=requirements(document);windows=day_windows(now);period=max((b-a).total_seconds() for a,b in windows)
    baseline=3*math.ceil(period/300)
    extras=0
    details=[]
    for source,need in req.items():
        pages=pages_needed(source,need['duration'])
        # The regular request already supplies the first hourly/daily page.
        if source in ('1h','1day'):pages=max(0,pages-1)
        calls=pages*math.ceil(period/(need['refresh']*60));extras+=calls
        details.append({'source':source,'pages':pages,'refresh':need['refresh'],'calls':calls})
    return {'baseline':baseline,'extra':extras,'reserve':24,'total':baseline+extras+24,'fits':baseline+extras+24<=1000,'sources':details}


def select_samples(rows,spec,now=None,zone='UTC'):
    validate_spec(spec)
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    # Anchor to a real source timestamp, never manufacture a forecast sample.
    parsed={datetime.fromisoformat(row['timestamp']).astimezone(timezone.utc):row for row in rows}
    local_zone=ZoneInfo(str(zone))
    daily=spec['source']=='1day'
    future=sorted(t for t in parsed if t.astimezone(local_zone).date()>=now.astimezone(local_zone).date()) if daily else sorted(t for t in parsed if t>=now)
    if not future:return []
    start=future[0].astimezone(local_zone)+timedelta(days=spec['offset']//1440) if daily else future[0]+timedelta(minutes=spec['offset'])
    result=[]
    for index in range(math.ceil(spec['duration']/spec['step'])):
        stamp=(start+timedelta(days=index*spec['step']//1440)).astimezone(timezone.utc) if daily else start+timedelta(minutes=index*spec['step'])
        result.append({'timestamp':stamp.isoformat(),**parsed.get(stamp,{}),'missing':stamp not in parsed})
    return result

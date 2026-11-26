"""Offline-verifiable timeline adapter with an explicitly injected transport."""
from __future__ import annotations
from datetime import datetime,timezone,timedelta
import math
import urllib.parse

from wetterstation.designer.series import SOURCES,requirements,capacity,regular_remaining,pages_needed
from wetterstation.weather.weather_service import number,normalize_query


def parse_rows(payload,source):
    if not isinstance(payload,dict) or not isinstance(payload.get('data'),list):raise ValueError('Zeitreihenantwort ist unvollständig.')
    result=[]
    for raw in payload['data'][:SOURCES[source][2]]:
        if not isinstance(raw,dict):continue
        try:
            stamp=datetime.fromtimestamp(number(raw['dt']),timezone.utc).isoformat();row={'timestamp':stamp}
            if source=='1min':row['precipitation']=number(raw['precipitation'],0)
            else:
                temp=raw['temp'];row['temp']=number(temp.get('day',temp.get('max'))) if isinstance(temp,dict) else number(temp)
                if isinstance(temp,dict):row.update(temp_min=number(temp['min']),temp_max=number(temp['max']))
                for key,provider in [('feels_like','feels_like'),('humidity','humidity'),('pressure','pressure'),('wind','wind_speed')]:
                    val=raw.get(provider)
                    if isinstance(val,dict):val=val.get('day')
                    if val is not None:row[key]=number(val,0,100) if key=='humidity' else number(val,0) if key in ('wind','pressure') else number(val)
                if 'pop' in raw:row['rain']=number(raw['pop'],0,1)*100
                weather=raw.get('weather') or [];row['description']=str(weather[0].get('description',''))[:500] if weather and isinstance(weather[0],dict) else ''
            result.append(row)
        except (KeyError,TypeError,ValueError,OverflowError,OSError):continue
    return sorted(result,key=lambda r:r['timestamp'])


def next_start(payload,source):
    value=payload.get('next')
    if not value:return None
    if not isinstance(value,str) or len(value)>4096:raise ValueError('Ungültige Zeitreihenfortsetzung.')
    parsed=urllib.parse.urlsplit(value)
    if parsed.scheme!='https' or parsed.hostname!='api.openweathermap.org' or parsed.port not in (None,443) or parsed.username or parsed.password or parsed.path!='/data/4.0/onecall/timeline/'+source:
        raise ValueError('Zeitreihenfortsetzung wurde abgewiesen.')
    starts=urllib.parse.parse_qs(parsed.query).get('start',[])
    if len(starts)!=1 or not starts[0].isdigit():raise ValueError('Ungültiger Beginn der Folgeseite.')
    # Only a timestamp is returned. Never retain keys or follow provider URLs.
    return int(starts[0])


def snapshot(payload,source,query,now):
    try:following=next_start(payload,source)
    except ValueError:following=None
    return {'query':normalize_query(query),'source':source,'retrieved_at':now.isoformat(),
            'rows':parse_rows(payload,source),'next_start':following}


def read_snapshot(value,source,query,now):
    """Validate persisted samples before use. Old, cross-country and keyed data fail closed."""
    if not isinstance(value,dict) or value.get('query')!=normalize_query(query) or value.get('source')!=source:raise ValueError('Falscher Zeitreihencache.')
    stamp=datetime.fromisoformat(value['retrieved_at'])
    if stamp.tzinfo is None or not 0<=(now-stamp).total_seconds()<=21600:raise ValueError('Zeitreihencache abgelaufen.')
    rows=value['rows']
    if not isinstance(rows,list) or len(rows)>600:raise ValueError('Ungültiger Zeitreihencache.')
    allowed={'timestamp','precipitation'} if source=='1min' else {'timestamp','temp','temp_min','temp_max','feels_like','humidity','pressure','wind','rain','description'}
    clean=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)-allowed:raise ValueError('Ungültige Zeitreihenwerte.')
        dt=datetime.fromisoformat(row['timestamp'])
        if dt.tzinfo is None:raise ValueError('Zeitstempel ohne Zeitzone.')
        for key,val in row.items():
            if key=='timestamp':continue
            if key=='description':
                if not isinstance(val,str) or len(val)>500:raise ValueError('Ungültiger Wettertext.')
            elif isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val):raise ValueError('Ungültiger Wetterwert.')
        clean.append(dict(row))
    following=value.get('next_start')
    if following is not None and (type(following) is not int or not 0<=following<=253402300799):raise ValueError('Ungültige Fortsetzung.')
    return {'time':stamp,'rows':clean,'next_start':following}


def merge_rows(old,new,source,now):
    merged={r['timestamp']:r for r in old};merged.update({r['timestamp']:r for r in new})
    # Keep today's local daily sample even west of UTC. Discard past minute data
    # before the cap so a long-running display never fills with yesterday's rain.
    cutoff=now-timedelta(hours=36) if source=='1day' else now-timedelta(minutes=SOURCES[source][0])
    return sorted((r for r in merged.values() if datetime.fromisoformat(r['timestamp'])>=cutoff),key=lambda r:r['timestamp'])[:600]


class TimelineAdapter:
    """Transport contract: request(source, start, protected) -> response mapping.

    Callers provide a transport. Only the gated live bridge constructs a real one.
    """
    def __init__(self,request):
        self.request=request;self.cache={};self.attempts={}

    def collect(self,document,query,now=None,base=None):
        now=now or datetime.now(timezone.utc);key=normalize_query(query);base=base or {}
        if not capacity(document,now)['fits']:raise ValueError('Zusatzreihen passen nicht in das Tagesbudget.')
        result={};errors=[]
        for source,need in requirements(document).items():
            cache=self.cache.get((key,source));rows=(cache or {}).get('rows',[])
            first=base.get(source)
            if first is not None:
                try:
                    first=read_snapshot(first,source,query,now) if 'rows' in first else {'rows':parse_rows(first,source),'next_start':next_start(first,source)}
                    rows=merge_rows(rows,first['rows'],source,now)
                    if cache:cache['rows']=rows
                except (ValueError,TypeError,KeyError,OverflowError):first=None
            if cache and (now-cache['time']).total_seconds()<need['refresh']*60:
                result[source]=rows;continue
            last=self.attempts.get((key,source))
            if last and (now-last).total_seconds()<need['refresh']*60:
                result[source]=rows;continue
            self.attempts[(key,source)]=now
            gathered=[];start=None
            for index in range(pages_needed(source,need['duration'])):
                try:
                    if index==0 and source in ('1h','1day'):
                        if first is None:break
                        chunk,following=first['rows'],first['next_start']
                    else:
                        payload=self.request(source,start,regular_remaining(now)+24)
                        chunk=parse_rows(payload,source);following=next_start(payload,source)
                    if not chunk:raise ValueError('Zeitreihe enthält keine gültigen Werte.')
                    gathered.extend(chunk)
                    if following is None:break
                    if start is not None and following<=start:raise ValueError('Wiederholte Zeitreihenseite wurde abgewiesen.')
                    start=following
                except (ValueError,OSError):errors.append('Zusätzliche Zeitreihe derzeit unvollständig.');break
            if gathered:
                rows=merge_rows(rows,gathered,source,now)
                self.cache[(key,source)]={'time':now,'rows':rows}
            result[source]=rows
        return result,errors

"""Extra sources run only inside an existing, explicitly enabled live round."""
from datetime import datetime, timezone
import urllib.parse

from wetterstation.designer.activation import ActivationStore, STATE_TEXT, signature
from wetterstation.designer.series import requirements, capacity, regular_remaining
from wetterstation.designer.timeline_client import TimelineAdapter, read_snapshot, merge_rows
from wetterstation.weather.weather_service import ONE_CALL, WeatherServiceError, normalize_query
from wetterstation.weather.countries import location_query


def collect(client, settings, document, query, key, *, current=lambda:True, now=None, activation=None):
    live_clock = now is None
    now = now or datetime.now(timezone.utc)
    activation = activation or ActivationStore(settings.path.parent/'designer')
    state = activation.state(document)
    needed = requirements(document)
    base = {}
    result = {};notices = {}
    # Cache reading works without credentials or activation; no calls on rendering.
    adapter = TimelineAdapter(None)
    for source in needed:
        for prefix in ('timeline-extra-', 'timeline-base-'):
            value = client._load_json(client._cache_path(query, prefix+source))
            try:
                clean = read_snapshot(value,source,query,now)
                if prefix=='timeline-extra-':adapter.cache[(normalize_query(query),source)]=clean
                else:base[source]=value
            except (ValueError,TypeError,KeyError,OverflowError):pass
        cached = adapter.cache.get((normalize_query(query),source))
        rows = (cached or {}).get('rows',[])
        if source in base:rows=merge_rows(rows,base[source]['rows'],source,now)
        if cached:cached['rows']=rows
        result[source]=rows
        notices[source]=STATE_TEXT[state] if state!='on' else ''
    if state!='on' or not key or not capacity(document,now)['fits'] or not current():return result,notices
    place = client.load_resolved_place(query)  # Never trigger extra geocoding.
    if place is None:
        return result,{source:'Ort für Zeitreihe noch nicht aufgelöst' for source in needed}
    expected = signature(document)

    def allowed():
        if not current() or activation.state(document)!='on':return False
        active=settings.load_dashboard()
        return (signature(active)==expected and
                normalize_query(location_query(*settings.load_location_country()))==normalize_query(query))

    def request(source,start,protected):
        if not allowed():raise ValueError('Zusatzabrufe nicht mehr aktiviert.')
        moment=datetime.now(timezone.utc) if live_clock else now
        # Do not let a long pagination run delay the next regular five-minute slot.
        remaining=(int(moment.timestamp())//300+1)*300-moment.timestamp()
        if live_clock and remaining<=client.timeout+2:
            raise ValueError('Nächste reguläre Aktualisierung hat Vorrang.')
        params={'lat':place['lat'],'lon':place['lon'],'appid':key,'units':'metric','lang':'de'}
        if start is not None:params['start']=start
        try:
            # Recompute before every page: protect both reset windows and the reserve.
            protected=regular_remaining(moment)+24
            return client._request(ONE_CALL+'/timeline/'+source+'?'+urllib.parse.urlencode(params),protected=protected)
        except WeatherServiceError as exc:raise ValueError(str(exc)) from None

    # Tests freeze `now`; production uses wall time at every page.
    adapter.request=request
    for source in needed:
        saved=client._load_json(client._cache_path(query,'timeline-attempt-'+source)) or {}
        try:
            stamp=datetime.fromisoformat(saved['attempted_at'])
            if saved.get('query')==normalize_query(query) and stamp.tzinfo is not None and 0<=(now-stamp).total_seconds()<needed[source]['refresh']*60:
                adapter.attempts[(normalize_query(query),source)]=stamp
        except (KeyError,TypeError,ValueError):pass
    result,errors=adapter.collect(document,query,now,base)
    for source,need in needed.items():
        cache=adapter.cache.get((normalize_query(query),source))
        attempted=adapter.attempts.get((normalize_query(query),source))
        if attempted:
            client._safe_save(query,'timeline-attempt-'+source,{'query':normalize_query(query),'attempted_at':attempted.isoformat()})
        if cache:
            client._safe_save(query,'timeline-extra-'+source,{'query':normalize_query(query),'source':source,
                'retrieved_at':cache['time'].isoformat(),'rows':cache['rows']})
        if errors:notices[source]='Zusatzdaten unvollständig · vorhandene Werte aus Cache'
        elif not result.get(source):notices[source]='Noch keine Zeitreihendaten'
        elif cache and (now-cache['time']).total_seconds()>need['refresh']*60:
            notices[source]='Zwischengespeichert · Aktualisierung ausstehend'
    return result,notices

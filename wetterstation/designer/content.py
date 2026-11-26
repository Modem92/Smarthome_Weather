"""Version-4 editable content blocks, in the widget's padded coordinate system."""
from copy import deepcopy
from wetterstation.designer import model


def upgrade(document):
    document['version']=4
    document.setdefault('inner_grid',{'step':8,'visible':True,'snap':True})
    return document


def area(document,page,widget,rect):
    x,y,w,h=rect;s=model.style(document,page,widget)
    left=s['padding_left']+s['border_width'];top=s['padding_top']+s['border_width']
    return (x+left,y+top,max(1,w-left-s['padding_right']-s['border_width']),
            max(1,h-top-s['padding_bottom']-s['border_width']))


def blocks(document,page,widget,rect):
    s=model.style(document,page,widget);_,_,cw,ch=area(document,page,widget,rect)
    th=min(ch*.25,s['title_size']*1.5) if s['show_title'] else 0
    offset=min(ch-1,th+s['content_gap']) if th else 0
    result=[]
    def add(identity,kind,x,y,w,h,**values):
        e=model.new_element(kind);e.update(id=identity,x=x,y=y,w=w,h=h,**values);result.append(e)
    if th:add('builtin-title','text',0,0,1,th/ch,text=s['title'] or model.KINDS[widget['type']]['title'],style={'font_size':s['title_size'],'bold':True})
    kind=widget['type'];fields=widget['fields']
    if kind in ('series','hourly','daily','radar'):
        add('builtin-structure','structure',0,offset/ch,1,(ch-offset)/ch)
    elif kind!='custom':
        actual=[f for f in fields if not (kind=='clock' and f=='seconds' and 'time' in fields)]
        for i,field in enumerate(actual):
            binding=('date' if kind=='date' else 'time' if kind=='clock' and field=='seconds' else field if kind=='clock' else
                     kind if kind.startswith('sensor_') else ('sensor_' if kind=='sensors' else 'indoor_')+field if kind in ('sensors','indoor') else kind if field=='value' else field)
            style={'time_format':'%S'} if kind=='clock' and field=='seconds' else {}
            if kind=='clock' and field=='time' and 'seconds' in fields and '%S' not in s['time_format']:style={'time_format':s['time_format'].replace('%M','%M:%S')}
            add('builtin-'+field,'data',0,(offset+i*(ch-offset)/max(1,len(actual)))/ch,1,(ch-offset)/max(1,len(actual))/ch,binding=binding,style=style)
    overrides=widget.get('content_layout',{})
    result=[deepcopy(overrides.get(e['id'],e)) for e in result]
    for original in widget['elements']:
        e=deepcopy(original)
        if 'content_layout' not in widget:
            e['y']=(offset+e['y']*(ch-offset))/ch;e['h']*=((ch-offset)/ch)
        result.append(e)
    return sorted(result,key=lambda e:e['z'])


def materialize(document,page,widget,rect):
    if 'content_layout' in widget:return
    entries=blocks(document,page,widget,rect);upgrade(document)
    widget['content_layout']={e['id']:e for e in entries if e['id'].startswith('builtin-')}
    widget['elements']=[e for e in entries if not e['id'].startswith('builtin-')]


def element(document,page,widget,identity):
    if not widget:return None
    if identity in widget.get('content_layout',{}):return widget['content_layout'][identity]
    actual=next((e for e in widget['elements'] if e['id']==identity),None)
    if actual is not None and 'content_layout' in widget:return actual
    from wetterstation.designer.render import widget_rects
    rect=widget_rects(document,page)[0][widget['id']]
    return next((e for e in blocks(document,page,widget,rect) if e['id']==identity),None)


def snap_rect(rect,handle,dx,dy,width,height,step=0):
    """Eight handles; clamp inside the parent, preserving the opposite edge."""
    x,y,w,h=rect;left=x;top=y;right=x+w;bottom=y+h
    def snap(v):return round(v/step)*step if step else v
    minimum=max(1,min(step or 1,width,height))
    if handle=='move':
        left=max(0,min(width-w,snap(x+dx)));top=max(0,min(height-h,snap(y+dy)))
        return left,top,w,h
    if 'w' in handle:left=max(0,min(right-minimum,snap(x+dx)))
    if 'e' in handle:right=max(left+minimum,min(width,snap(right+dx)))
    if 'n' in handle:top=max(0,min(bottom-minimum,snap(y+dy)))
    if 's' in handle:bottom=max(top+minimum,min(height,snap(bottom+dy)))
    return left,top,right-left,bottom-top

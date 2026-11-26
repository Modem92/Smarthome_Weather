"""Editor actions independent from Qt, with shared undo and recoverable drafts."""
from copy import deepcopy
from wetterstation.designer import model
from wetterstation.ui.widgets import NoSpace, revision, overlaps


class Session:
    def __init__(self,document,store,base_revision):
        self.document=(model.validate(document,collisions=False) if document and document.get('version') in (3,4) else model.from_layout(document));self.store=store;self.base_revision=base_revision
        self.page_id=self.document['pages'][0]['id'];self.selected=[];self.element_id=None
        self.undo=[];self.redo=[];self.content_selected=[]

    @property
    def page(self):return next((p for p in self.document['pages'] if p['id']==self.page_id),self.document['pages'][0])

    @property
    def widget(self):return next((w for w in self.page['widgets'] if w['id'] in self.selected),None)

    @property
    def element(self):
        from wetterstation.designer.content import element
        return element(self.document,self.page,self.widget,self.element_id)

    def snapshot(self):return deepcopy((self.document,self.page_id,self.selected,self.element_id,self.content_selected))

    def restore(self,snapshot):self.document,self.page_id,self.selected,self.element_id,self.content_selected=deepcopy(snapshot)

    def change(self,action,conflicts=False,content_edit=True):
        before=self.snapshot()
        try:
            if content_edit and self.element_id and self.element:
                from wetterstation.designer.content import materialize
                from wetterstation.designer.render import widget_rects
                materialize(self.document,self.page,self.widget,widget_rects(self.document,self.page)[0][self.widget['id']])
            action()
            if not self.element_id:self.content_selected=[]
            try:model.validate(self.document,collisions=not conflicts)
            except NoSpace:
                def collisions(document):
                    pages=[*document['pages'],*(p for v in document.get('variants',{}).values() for p in v['pages'])]
                    return sum(sum(overlaps(w,other) for other in p['widgets'][:i]) for p in pages for i,w in enumerate(p['widgets']))
                old_count=collisions(before[0]);new_count=collisions(self.document)
                if not old_count or new_count>old_count:raise
                model.validate(self.document,collisions=False)
            if before[0]==self.document:return False
            self.store.save_draft(self.document,self.base_revision)
        except Exception:
            self.restore(before);raise
        self.undo.append(before);self.undo=self.undo[-100:];self.redo=[]
        return True

    def history(self,redo=False):
        source,destination=(self.redo,self.undo) if redo else (self.undo,self.redo)
        if not source:return
        current=self.snapshot();previous=source[-1]
        self.store.save_draft(previous[0],self.base_revision)
        source.pop();destination.append(current);self.restore(previous)

    def add_widget(self,kind,template=None):
        if template and 'content_layout' in template:
            from wetterstation.designer.content import upgrade
            upgrade(self.document)
        c,r=model.grid(self.page)
        widget=deepcopy(template) if template else model.new_widget(kind,c,r)
        widget['id']=model.uid();widget['locked']=False;widget['w']=min(c,widget['w']);widget['h']=min(r,widget['h'])
        for e in widget.get('elements',[]):e['id']=model.uid('e')
        items=model.place([*self.page['widgets'],widget],c,r,pinned=None)
        # Adding may not relocate existing items.
        for old in self.page['widgets']:
            if next(w for w in items if w['id']==old['id'])!=old:raise NoSpace('Kein freier Bereich für dieses Widget.')
        self.page['widgets']=items;self.selected=[widget['id']];self.element_id=None

    def geometry(self,identity,x,y,w,h):
        widget=next(v for v in self.page['widgets'] if v['id']==identity)
        if widget.get('locked'):raise ValueError('Das Widget ist gesperrt.')
        widget.update(x=x,y=y,w=w,h=h)

    def move_selected(self,dx,dy):
        for widget in self.page['widgets']:
            if widget['id'] in self.selected:self.geometry(widget['id'],widget['x']+dx,widget['y']+dy,widget['w'],widget['h'])

    def remove_selected(self):
        if self.element:
            identity=self.element_id
            if identity=='builtin-title':self.widget['style']['show_title']=False
            elif identity=='builtin-structure':raise ValueError('Diesen Datenblock über seine Felder konfigurieren oder das gesamte Widget entfernen.')
            elif identity.startswith('builtin-'):
                self.widget['fields'].remove(identity[len('builtin-'):]);self.widget['content_layout'].pop(identity,None)
            else:self.widget['elements'].remove(self.element)
            self.element_id=None;self.content_selected=[]
        else:
            self.page['widgets']=[w for w in self.page['widgets'] if w['id'] not in self.selected or w.get('locked')];self.selected=[]

    def duplicate(self):
        originals=[deepcopy(w) for w in self.page['widgets'] if w['id'] in self.selected]
        self.selected=[]
        for w in originals:
            self.add_widget(w['type'],w)

    def add_page(self,clone=False):
        page=deepcopy(self.page) if clone else {'title':'Neue Seite','grid':deepcopy(self.page['grid']),'style':{},'widgets':[]}
        page['id']=model.uid('p')
        if clone:
            page['title']+=' Kopie'
            for w in page['widgets']:
                w['id']=model.uid()
                for e in w['elements']:e['id']=model.uid('e')
        self.document['pages'].append(page);self.page_id=page['id'];self.selected=[];self.element_id=None

    def remove_page(self):
        if len(self.document['pages'])==1:raise ValueError('Mindestens eine Seite muss bleiben.')
        self.document['pages'].remove(self.page);self.page_id=self.document['pages'][0]['id'];self.selected=[];self.element_id=None

    def add_element(self,kind):
        if not self.widget:raise ValueError('Bitte zuerst ein Widget auswählen.')
        from wetterstation.designer.content import materialize,blocks
        from wetterstation.designer.render import widget_rects
        rect=widget_rects(self.document,self.page)[0][self.widget['id']]
        entries=blocks(self.document,self.page,self.widget,rect)
        materialize(self.document,self.page,self.widget,rect)
        e=model.new_element(kind);e['z']=max((entry['z'] for entry in entries),default=-1)+1
        if kind in ('rectangle','ellipse'):e.update(w=.3,h=.25,style={'background':'#dfe4ec','border_color':'#667085','border_width':2,'opacity':1,'radius':0})
        self.widget['elements'].append(e);self.element_id=e['id'];self.content_selected=[e['id']]

    def free_contents(self):
        w=self.widget
        if not w or w['type'] in ('series','hourly','daily','radar','custom'):
            raise ValueError('Dieses Widget verwendet bereits eigene oder strukturierte Inhalte.')
        kind=w['type'];elements=[]
        title=model.style(self.document,self.page,w)
        if title['show_title']:
            e=model.new_element('text');e.update(text=title['title'] or model.KINDS[kind]['title'],style={'bold':True,'font_size':title['title_size']});elements.append(e)
        for field in w['fields']:
            if field=='seconds' and 'time' in w['fields']:continue
            if kind=='clock':key='time' if field=='seconds' else field
            elif kind=='date':key='date'
            elif kind.startswith('sensor_'):key=kind
            elif kind in ('sensors','indoor'):key=('sensor_' if kind=='sensors' else 'indoor_')+field
            elif field=='value':key=kind
            else:key=field
            e=model.new_element('data');e['binding']=key
            if kind=='clock' and field=='seconds':e['style']['time_format']='%S'
            elements.append(e)
        for i,e in enumerate(elements):e.update(x=.04,y=.02+i*.96/max(1,len(elements)),w=.92,h=.90/max(1,len(elements)),z=i)
        w.update(type='custom',fields=[],elements=elements);w['style']['show_title']=False
        self.element_id=elements[0]['id'] if elements else None

    def set_property(self,scope,key,value,reset=False):
        from wetterstation.designer.content import element
        targets=([self.document] if scope=='Anzeige' else [self.page] if scope=='Seite' else [element(self.document,self.page,self.widget,i) for i in (self.content_selected or [self.element_id])] if scope=='Inhalt' else [w for w in self.page['widgets'] if w['id'] in self.selected])
        targets=[t for t in targets if t is not None]
        if not targets:raise ValueError('Bitte zuerst ein Element auswählen.')
        for target in targets:
            if reset:target.setdefault('style',{}).pop(key,None)
            else:target.setdefault('style',{})[key]=value

    def reset_scope(self,scope):
        if scope=='Anzeige':self.document['style']={}
        elif scope=='Seite':self.page['style']={}
        elif scope=='Inhalt' and self.element:
            from wetterstation.designer.content import element
            for identity in self.content_selected or [self.element_id]:
                target=element(self.document,self.page,self.widget,identity)
                if target is not None:target['style']={}
        else:
            for w in self.page['widgets']:
                if w['id'] in self.selected:w['style']={}

    def grid_change(self,columns,rows,arrange=False,all_pages=False):
        self.document['pages']=[model.resize_grid(p,columns,rows,arrange,allow_conflicts=True) if all_pages or p['id']==self.page_id else p for p in self.document['pages']]

    def align_contents(self,command):
        from wetterstation.designer.content import element
        entries=[element(self.document,self.page,self.widget,i) for i in (self.content_selected or [self.element_id])]
        entries=[e for e in entries if e is not None]
        if not entries:return
        if command in ('distribute_x','distribute_y'):
            if len(entries)<3:raise ValueError('Zum Verteilen mindestens drei Inhalte auswählen.')
            axis,extent=('x','w') if command.endswith('x') else ('y','h');entries.sort(key=lambda e:e[axis])
            start=entries[0][axis];end=entries[-1][axis]+entries[-1][extent]
            gap=(end-start-sum(e[extent] for e in entries))/(len(entries)-1)
            cursor=start
            for e in entries:e[axis]=cursor;cursor+=e[extent]+gap
            return
        for e in entries:
            if command in ('left','center','right'):e['x']={'left':0,'center':(1-e['w'])/2,'right':1-e['w']}[command]
            else:e['y']={'top':0,'middle':(1-e['h'])/2,'bottom':1-e['h']}[command]

    def inner_grid(self,**changes):
        from wetterstation.designer.content import upgrade
        upgrade(self.document)['inner_grid'].update(changes)

    def switch_profile(self,width,height,rotation=0):
        self.document=model.switch_variant(self.document,width,height,rotation)
        if not any(p['id']==self.page_id for p in self.document['pages']):self.page_id=self.document['pages'][0]['id']
        self.selected=[i for i in self.selected if any(w['id']==i for w in self.page['widgets'])]
        self.element_id=None

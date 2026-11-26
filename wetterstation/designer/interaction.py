"""Direct manipulation with transient previews and one commit per gesture."""
from copy import deepcopy
from PySide6.QtCore import Qt,QRectF,QPointF,QTimer
from PySide6.QtGui import QPen,QColor,QBrush,QPainterPath
from PySide6.QtWidgets import QGraphicsRectItem
from wetterstation.designer import model,content
from wetterstation.designer.render import widget_rects,demo_data,render_page

HANDLES={'nw':(0,0),'n':(.5,0),'ne':(1,0),'e':(1,.5),'se':(1,1),'s':(.5,1),'sw':(0,1),'w':(0,.5)}


class DesignBox(QGraphicsRectItem):
    def __init__(self,window,identity,rect,element=False,widget_id=None):
        super().__init__(QRectF(0,0,rect[2],rect[3]))
        self.window=window;self.identity=identity;self.element=element;self.widget_id=widget_id or identity
        self.setPos(rect[0],rect[1]);self.origin=None;self.proposal=None;self.hover=False
        self.setAcceptHoverEvents(True);self.setZValue(3 if element else 2);self.setBrush(QBrush(Qt.GlobalColor.transparent));self.update_pen()

    def selected(self):
        session=self.window.session
        return self.identity in (session.content_selected or [session.element_id]) and self.widget_id in session.selected if self.element else self.identity in session.selected and not session.element_id

    def unit(self):return 1/max(.01,abs(self.window.canvas.transform().m11()))

    def boundingRect(self):return super().boundingRect().adjusted(-7*self.unit(),-7*self.unit(),7*self.unit(),7*self.unit())

    def handle(self,point):
        if self.selected():
            for name,(x,y) in HANDLES.items():
                p=QPointF(self.rect().width()*x,self.rect().height()*y)
                if abs(point.x()-p.x())<=7*self.unit() and abs(point.y()-p.y())<=7*self.unit():return name
        return 'move'

    def shape(self):
        path=QPainterPath();r=self.rect();margin=7*self.unit()
        if self.element:
            # Keep the widget frame grabbable even with zero padding or a
            # full-size image/diagram. Selected content grips still take priority.
            path.addRect(r);session=self.window.session;document=getattr(self.window,'drag_document',None) or session.document
            page=next(p for p in document['pages'] if p['id']==session.page_id)
            wx,wy,ww,hh=widget_rects(document,page)[0][self.widget_id]
            clip=QPainterPath();clip.addRect(QRectF(wx-self.pos().x()+margin,wy-self.pos().y()+margin,max(0,ww-2*margin),max(0,hh-2*margin)))
            path=path.intersected(clip);path.setFillRule(Qt.FillRule.WindingFill)
            if self.selected():
                for x,y in HANDLES.values():path.addRect(QRectF(r.width()*x-margin,r.height()*y-margin,2*margin,2*margin))
            return path
        path.addRect(r.adjusted(-margin,-margin,margin,margin))
        if not self.element and self.window.tabs.currentIndex()==1:
            inner=QPainterPath();inner.addRect(r.adjusted(margin,margin,-margin,-margin));return path.subtracted(inner)
        return path

    def update_pen(self,invalid=False):
        pen=QPen(QColor('#ff453a' if invalid else '#007aff' if self.selected() else '#b7bec8'))
        pen.setWidthF(1.5 if self.selected() else .6);pen.setCosmetic(True);self.setPen(pen);self.invalid=invalid

    def paint(self,painter,option,widget=None):
        if self.selected() or self.hover or getattr(self,'invalid',False):super().paint(painter,option,widget)
        if self.selected():
            u=self.unit();painter.setBrush(QColor('#ffffff'));pen=QPen(QColor('#007aff'));pen.setCosmetic(True);painter.setPen(pen)
            for x,y in HANDLES.values():painter.drawRoundedRect(QRectF(self.rect().width()*x-3*u,self.rect().height()*y-3*u,6*u,6*u),u,u)

    def hoverMoveEvent(self,event):
        name=self.handle(event.pos());self.setCursor({'nw':Qt.CursorShape.SizeFDiagCursor,'se':Qt.CursorShape.SizeFDiagCursor,'ne':Qt.CursorShape.SizeBDiagCursor,'sw':Qt.CursorShape.SizeBDiagCursor,'n':Qt.CursorShape.SizeVerCursor,'s':Qt.CursorShape.SizeVerCursor,'w':Qt.CursorShape.SizeHorCursor,'e':Qt.CursorShape.SizeHorCursor}.get(name,Qt.CursorShape.SizeAllCursor));self.hover=True;self.update()

    def hoverLeaveEvent(self,event):self.hover=False;self.update()

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:event.ignore();return
        session=self.window.session;old_widget=session.widget
        if self.element:
            if old_widget is None or old_widget['id']!=self.widget_id:session.content_selected=[]
            session.selected=[self.widget_id]
            if event.modifiers()&Qt.KeyboardModifier.ControlModifier:
                session.content_selected=([i for i in session.content_selected if i!=self.identity] if self.identity in session.content_selected else [*session.content_selected,self.identity])
            elif self.identity not in session.content_selected:session.content_selected=[self.identity]
            session.element_id=self.identity if self.identity in session.content_selected else next(iter(session.content_selected),None)
        else:
            if event.modifiers()&Qt.KeyboardModifier.ControlModifier:session.selected=([i for i in session.selected if i!=self.identity] if self.identity in session.selected else [*session.selected,self.identity])
            elif self.identity not in session.selected:session.selected=[self.identity]
            session.element_id=None;session.content_selected=[]
        self.window.scope='Inhalt' if self.element else 'Widget'
        self.window.canvas.alt_down=bool(event.modifiers()&Qt.KeyboardModifier.AltModifier)
        from PySide6.QtCore import QSignalBlocker
        with QSignalBlocker(self.window.scope_box):self.window.scope_box.setCurrentText(self.window.scope)
        self.window.update_content_list();self.window.rebuild_inspector();self.window.update_box_pens()
        self.origin=(event.scenePos(),deepcopy(session.document),model.digest(session.document));self.resize_handle=self.handle(event.pos())
        self.window.drag_active=self;self.data=demo_data(getattr(self.window,'example_time',None),self.window.scenario);self.cache={};self.proposal=None;self.moved=False;event.accept()

    def mouseMoveEvent(self,event):
        if not self.origin:return
        start,original,_=self.origin;dx=event.scenePos().x()-start.x();dy=event.scenePos().y()-start.y()
        if not self.moved and dx==0 and dy==0:return
        self.moved=True
        session=self.window.session;document=deepcopy(original);page=next(p for p in document['pages'] if p['id']==session.page_id)
        widget=next(w for w in page['widgets'] if w['id']==self.widget_id)
        if widget.get('locked') and not self.element:return
        rects,g=widget_rects(document,page);handle=self.resize_handle
        if self.element:
            parent=content.area(document,page,widget,rects[widget['id']]);content.materialize(document,page,widget,rects[widget['id']])
            entries=[*widget['content_layout'].values(),*widget['elements']]
            selected=[e for e in entries if e['id'] in (session.content_selected or [self.identity])]
            grid=document['inner_grid'];step=grid['step'] if grid['snap'] and not (event.modifiers()&Qt.KeyboardModifier.AltModifier or getattr(self.window.canvas,'alt_down',False)) else 0
            if handle=='move' and len(selected)>1:
                bx=min(e['x'] for e in selected)*parent[2];by=min(e['y'] for e in selected)*parent[3]
                bw=max(e['x']+e['w'] for e in selected)*parent[2]-bx;bh=max(e['y']+e['h'] for e in selected)*parent[3]-by
                xx,yy,_,_=content.snap_rect((bx,by,bw,bh),'move',dx,dy,parent[2],parent[3],step)
                for e in selected:e['x']+=(xx-bx)/parent[2];e['y']+=(yy-by)/parent[3]
            else:
                e=next(e for e in entries if e['id']==self.identity)
                coords=content.snap_rect((e['x']*parent[2],e['y']*parent[3],e['w']*parent[2],e['h']*parent[3]),handle,dx,dy,parent[2],parent[3],step)
                e.update(zip(('x','y','w','h'),(coords[0]/parent[2],coords[1]/parent[3],coords[2]/parent[2],coords[3]/parent[3])))
        else:
            columns,rows=model.grid(page);dx=round(dx/(g['cell_w']+g['gap_x']));dy=round(dy/(g['cell_h']+g['gap_y']))
            targets=[w for w in page['widgets'] if w['id'] in session.selected]
            if handle=='move' and len(targets)>1:
                dx=max(-min(w['x'] for w in targets),min(dx,columns-max(w['x']+w['w'] for w in targets)))
                dy=max(-min(w['y'] for w in targets),min(dy,rows-max(w['y']+w['h'] for w in targets)))
                for w in targets:
                    if w.get('locked'):return
                    w.update(x=w['x']+dx,y=w['y']+dy)
            else:
                coords=content.snap_rect(tuple(widget[k] for k in ('x','y','w','h')),handle,dx,dy,columns,rows,1)
                widget.update(zip(('x','y','w','h'),map(int,coords)))
        valid=True
        try:model.validate(document)
        except ValueError:valid=False
        self.proposal=document if valid else None;self.window.drag_document=document
        image,rects,_=render_page(document,page['id'],self.data,self.window.store.assets,self.window.show_grid,cache=self.cache)
        from wetterstation.designer.app import pixmap
        self.window.page_pixmap.setPixmap(pixmap(image))
        for box in self.window.boxes:
            if box.element:
                owner=next(w for w in page['widgets'] if w['id']==box.widget_id)
                parent=content.area(document,page,owner,rects[owner['id']]);entry=next((e for e in content.blocks(document,page,owner,rects[owner['id']]) if e['id']==box.identity),None)
                if entry is None:continue
                r=(parent[0]+entry['x']*parent[2],parent[1]+entry['y']*parent[3],entry['w']*parent[2],entry['h']*parent[3])
            else:r=rects[box.identity]
            box.setPos(r[0],r[1]);box.setRect(0,0,r[2],r[3]);box.update_pen(not valid and box.widget_id==self.widget_id)
        self.window.drag_hud=(event.scenePos(),f"{self.pos().x():.0f}, {self.pos().y():.0f} · {self.rect().width():.0f} × {self.rect().height():.0f}",not valid)
        self.window.canvas.viewport().update();event.accept()

    def finish(self,cancel=False):
        if not self.origin:return
        _,_,expected=self.origin;proposal=None if cancel else self.proposal
        self.origin=None;self.window.drag_active=None;self.window.drag_document=None;self.window.drag_hud=None
        self.window.canvas.alt_down=False
        if not self.moved:
            self.window.canvas.viewport().update();return
        def apply():
            if proposal is not None and model.digest(self.window.session.document)==expected:
                self.window.commit(lambda:setattr(self.window.session,'document',proposal))
            else:self.window.refresh()
        # Never delete the active graphics item while its native event is running.
        QTimer.singleShot(0,apply)

    def mouseReleaseEvent(self,event):self.finish();event.accept()

    def contextMenuEvent(self,event):
        self.window.context_menu(event.screenPos())

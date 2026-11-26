"""Local Windows design editor. Imports Qt here, never in the Pi renderer."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timezone
import io
import json
import math
from pathlib import Path
import sys

from PySide6.QtCore import QObject,QEvent,Qt,QTimer,QRectF,QPointF,QSignalBlocker,QSize,QRect,Signal
from PySide6.QtGui import QAction,QColor,QImage,QPixmap,QPen,QBrush,QKeySequence,QPainter,QIcon,QFont,QFontDatabase
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QSplitter,
    QTabBar,QToolBar,QLabel,QPushButton,QComboBox,QListWidget,QListWidgetItem,QScrollArea,
    QFormLayout,QGroupBox,QLineEdit,QSpinBox,QDoubleSpinBox,QCheckBox,QSlider,QColorDialog,
    QFileDialog,QMessageBox,QInputDialog,QGraphicsView,QGraphicsScene,QGraphicsRectItem,
    QMenu,QAbstractItemView,QToolButton,QPlainTextEdit,QButtonGroup)

from wetterstation.designer import model
from wetterstation.designer.render import render_page,widget_rects,demo_data,style
from wetterstation.designer.storage import DesignStore,read_json,atomic,json_bytes
from wetterstation.designer.session import Session
from wetterstation.designer.series import FIELDS,SOURCES,capacity
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.widgets import revision,NoSpace
from wetterstation.paths import project_root


def pixmap(image):
    raw=image.convert('RGBA').tobytes()
    qimage=QImage(raw,image.width,image.height,QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimage)


def color_value(value):
    try:
        if len(value)==9:return QColor(int(value[1:3],16),int(value[3:5],16),int(value[5:7],16),int(value[7:9],16))
        return QColor(value)
    except (ValueError,TypeError):return QColor()


from wetterstation.designer.theme import LIGHT,DARK,icon


class WheelGuard(QObject):
    def eventFilter(self,watched,event):
        if event.type()==QEvent.Type.Wheel and isinstance(watched,(QComboBox,QSpinBox,QDoubleSpinBox,QSlider,QTabBar)):
            owner=self.parent();area=None;parent=watched.parentWidget()
            while parent is not None:
                if isinstance(parent,QScrollArea):area=parent;break
                parent=parent.parentWidget()
            if area is None and hasattr(owner,'right') and owner.right.isAncestorOf(watched):area=owner.scroll
            if area is not None:
                if not event.pixelDelta().isNull():
                    bar=area.verticalScrollBar();bar.setValue(bar.value()-event.pixelDelta().y())
                else:
                    from PySide6.QtGui import QWheelEvent
                    viewport=area.viewport();position=viewport.mapFromGlobal(event.globalPosition().toPoint())
                    forwarded=QWheelEvent(QPointF(position),event.globalPosition(),event.pixelDelta(),event.angleDelta(),event.buttons(),event.modifiers(),event.phase(),event.inverted())
                    QApplication.sendEvent(viewport,forwarded)
            event.accept();return True
        return False


class DraftText(QPlainTextEdit):
    editingFinished=Signal()
    def __init__(self,value):
        super().__init__(value);self.saved_text=value;self.saving=False;self.flush=lambda:None
    def focusOutEvent(self,event):
        self.editingFinished.emit();super().focusOutEvent(event)


from wetterstation.designer.interaction import DesignBox


class Canvas(QGraphicsView):
    def __init__(self,window):
        super().__init__();self.window=window;self.setScene(QGraphicsScene(self));self.scene().setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex);self.setBackgroundBrush(QColor('#edf0f5'))
        self.setRenderHints(QPainter.RenderHint.Antialiasing|QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag);self.zoom_mode='fit'

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.zoom_mode=='fit' and self.scene().items():self.fitInView(self.scene().sceneRect(),Qt.AspectRatioMode.KeepAspectRatio)

    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Alt:self.alt_down=True;event.accept();return
        if event.key()==Qt.Key.Key_Escape and getattr(self.window,'drag_active',None):
            self.window.drag_active.finish(cancel=True);return
        moves={Qt.Key.Key_Left:(-1,0),Qt.Key.Key_Right:(1,0),Qt.Key.Key_Up:(0,-1),Qt.Key.Key_Down:(0,1)}
        if event.key() in moves:
            dx,dy=moves[event.key()];step=5 if event.modifiers()&Qt.KeyboardModifier.ShiftModifier else 1
            if self.window.session.element_id:
                parent=self.window.element_area();grid=self.window.session.document.get('inner_grid',{'step':8})
                def move_contents():
                    from wetterstation.designer.content import element
                    session=self.window.session
                    for identity in session.content_selected or [session.element_id]:
                        e=element(session.document,session.page,session.widget,identity)
                        e['x']+=dx*step*grid['step']/parent[2];e['y']+=dy*step*grid['step']/parent[3]
                self.window.commit(move_contents);return
            self.window.commit(lambda:self.window.session.move_selected(dx*step,dy*step));return
        if event.key() in (Qt.Key.Key_Delete,Qt.Key.Key_Backspace):self.window.remove();return
        super().keyPressEvent(event)

    def keyReleaseEvent(self,event):
        if event.key()==Qt.Key.Key_Alt:self.alt_down=False;event.accept();return
        super().keyReleaseEvent(event)

    def focusOutEvent(self,event):
        self.alt_down=False;super().focusOutEvent(event)

    def drawForeground(self,painter,rect):
        super().drawForeground(painter,rect)
        window=self.window;session=window.session
        if window.tabs.currentIndex()!=1 or not session.widget:return
        from wetterstation.designer.content import area
        document=getattr(window,'drag_document',None) or session.document
        page=next(p for p in document['pages'] if p['id']==session.page_id)
        widget=next((w for w in page['widgets'] if w['id']==session.widget['id']),None)
        if widget is None:return
        parent=area(document,page,widget,widget_rects(document,page)[0][widget['id']]);grid=document.get('inner_grid',{'step':8,'visible':True,'snap':True})
        scale=max(.01,abs(self.transform().m11()));painter.save()
        if grid['visible']:
            step=grid['step']*max(1,math.ceil(7/(grid['step']*scale)));pen=QPen(QColor('#d3dce8'));pen.setCosmetic(True);painter.setPen(pen)
            for xx in range(max(0,int((rect.left()-parent[0])//step)*step),min(math.ceil(parent[2]),math.ceil(rect.right()-parent[0])),step):
                for yy in range(max(0,int((rect.top()-parent[1])//step)*step),min(math.ceil(parent[3]),math.ceil(rect.bottom()-parent[1])),step):painter.drawPoint(QPointF(parent[0]+xx,parent[1]+yy))
        hud=getattr(window,'drag_hud',None)
        if hud:
            position,text,invalid=hud;pen=QPen(QColor('#ff453a' if invalid else '#007aff'));pen.setCosmetic(True);painter.setPen(pen)
            painter.drawLine(QPointF(parent[0],position.y()),QPointF(parent[0]+parent[2],position.y()))
            painter.drawLine(QPointF(position.x(),parent[1]),QPointF(position.x(),parent[1]+parent[3]))
            font=painter.font();font.setPixelSize(max(1,round(12/scale)));painter.setFont(font)
            painter.drawText(position+QPointF(12/scale,-14/scale),text)
        painter.restore()

    def mouseReleaseEvent(self,event):
        rectangle=QRect(self.selection_start,event.position().toPoint()).normalized() if getattr(self,'selection_start',None) is not None else None
        super().mouseReleaseEvent(event)
        self.selection_start=None
        rect=rectangle or self.rubberBandRect()
        if not rect.isEmpty():
            selected=[]
            for item in self.items(rect):
                if isinstance(item,DesignBox) and not item.element:selected.append(item.identity)
            if selected:self.window.session.selected=selected;self.window.rebuild_inspector();self.window.update_box_pens()

    def mousePressEvent(self,event):
        # Flush before dispatching to a graphics item: saving pending text can
        # rebuild the scene, and must never destroy an item inside its own event.
        if not self.window.flush_text_edits():event.ignore();return
        position=event.position().toPoint();self.selection_start=position if not isinstance(self.itemAt(position),DesignBox) and event.button()==Qt.MouseButton.LeftButton else None
        super().mousePressEvent(event)


class Designer(QMainWindow):
    def __init__(self,settings=None,folder=None):
        super().__init__()
        from wetterstation.designer.render import FONTS
        if not getattr(QApplication.instance(),'_designer_fonts',False):
            for filename in ('DejaVuSans.ttf','DejaVuSans-Bold.ttf','DejaVuSans-Oblique.ttf','DejaVuSans-BoldOblique.ttf'):
                if QFontDatabase.addApplicationFont(str(FONTS/filename))<0:raise ValueError('Mitgelieferte Oberflächenschrift fehlt.')
            QApplication.instance()._designer_fonts=True
        QApplication.instance().setStyle('Fusion');QApplication.instance().setFont(QFont('Segoe UI' if 'Segoe UI' in QFontDatabase.families() else 'DejaVu Sans',10))
        self.settings=settings or ApiKeyStore();self.store=DesignStore(folder or self.settings.path.parent/'designer')
        current=self.settings.load_dashboard();self.session=Session(current,self.store,revision(current));self.recovery_error=None;recovered=None
        try:
            recovered=self.store.load_draft()
            if recovered:self.session=Session(recovered['design'],self.store,recovered['base_revision'])
        except (OSError,ValueError):self.recovery_error='Der letzte Entwurf konnte nicht geladen werden. Aktive Gestaltung bleibt erhalten.'
        self.grid_all_pages=False;self.inspector_generation=0;self.grid_request=0
        self.clipboard=[];self.copied_style={};self.scope='Widget';self.show_grid=True;self.scenario='normal';self.boxes=[];self.updating=False;self.dark=False
        self.setWindowTitle('Wetterstation gestalten');self.resize(1460,920);self.setMinimumSize(900,600)
        available=QApplication.primaryScreen().availableGeometry()
        self.resize(min(1460,round(available.width()*.95)),min(920,round(available.height()*.92)))
        self.setStyleSheet(LIGHT);self.thumb_cache={};self.group_states={};self.field_selection={};self.time_units={}
        self.wheel_guard=WheelGuard(self);QApplication.instance().installEventFilter(self.wheel_guard)
        self.build_toolbar();self.build_body();self.build_menu()
        self.statusBar().showMessage('Entwurf wiederhergestellt' if recovered else 'Entwurf · Beispieldaten · noch nicht angewendet')
        self.refresh()
        self.clock_timer=QTimer(self);self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self.tick_preview);self.clock_timer.start()
        if self.recovery_error:QTimer.singleShot(0,lambda:QMessageBox.warning(self,'Entwurf',self.recovery_error))

    def action(self,label,callback,shortcut=None):
        action=QAction(label,self);action.triggered.connect(callback)
        if shortcut:action.setShortcut(shortcut)
        return action

    def build_toolbar(self):
        toolbar=QToolBar();toolbar.setMovable(False);self.addToolBar(toolbar)
        self.tabs=QTabBar();self.tabs.addTab('Widgets anordnen');self.tabs.addTab('Erweiterte Gestaltung');self.tabs.currentChanged.connect(lambda _:self.refresh());toolbar.addWidget(self.tabs)
        toolbar.addSeparator()
        self.profile=QComboBox();self.profile.addItems(['1024 × 600','800 × 480','Eigene Auflösung …']);self.profile.activated.connect(self.profile_changed);toolbar.addWidget(self.profile)
        self.orientation=QComboBox();self.orientation.addItems(['Querformat','Hochformat']);self.orientation.activated.connect(self.profile_changed);toolbar.addWidget(self.orientation)
        self.zoom=QComboBox();self.zoom.addItems(['Einpassen','100 %','150 %','200 %']);self.zoom.activated.connect(self.zoom_changed);toolbar.addWidget(self.zoom)
        self.undo_action=self.action('Rückgängig',lambda:self.history(),QKeySequence.StandardKey.Undo);toolbar.addAction(self.undo_action)
        self.undo_action.setIcon(icon('undo'))
        self.redo_action=self.action('Wiederholen',lambda:self.history(True),QKeySequence.StandardKey.Redo);toolbar.addAction(self.redo_action);self.redo_action.setIcon(icon('redo'))
        spacer=QWidget();spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding,spacer.sizePolicy().Policy.Preferred);toolbar.addWidget(spacer)
        apply=QToolButton();apply.setText('Anwenden');apply.setProperty('primary',True);menu=QMenu(apply)
        menu.addAction('Am PC anwenden',self.apply_pc);menu.addAction('An Pi übertragen …',self.apply_pi);apply.setMenu(menu);apply.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup);toolbar.addWidget(apply)

    def button(self,label,callback,layout):
        b=QPushButton(label)
        if label in ('+','−','↑','↓'):
            name={'+':'add','−':'remove','↑':'up','↓':'down'}[label];b.setText('');b.setIcon(icon(name));b.setToolTip({'add':'Hinzufügen','remove':'Entfernen','up':'Nach oben','down':'Nach unten'}[name]);b.setAccessibleName(b.toolTip())
        b.clicked.connect(callback);layout.addWidget(b);return b

    def build_body(self):
        self.splitter=QSplitter();self.setCentralWidget(self.splitter)
        self.left=QWidget();self.left.setObjectName('pagesPanel');left=QVBoxLayout(self.left);left.setContentsMargins(12,12,12,12)
        header=QLabel('SEITEN');header.setStyleSheet('font-weight:600;color:#86868b;');left.addWidget(header)
        self.pages=QListWidget();self.pages.currentRowChanged.connect(self.select_page);left.addWidget(self.pages,2)
        self.pages.setIconSize(QSize(120,72))
        self.pages.setViewMode(QListWidget.ViewMode.IconMode);self.pages.setMovement(QListWidget.Movement.Static)
        self.pages.setResizeMode(QListWidget.ResizeMode.Adjust);self.pages.setWordWrap(True);self.pages.setGridSize(QSize(185,108));self.pages.setIconSize(QSize(150,82))
        self.pages.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        row=QHBoxLayout();self.button('+',lambda:self.commit(lambda:self.session.add_page()),row);self.button('Duplizieren',lambda:self.commit(lambda:self.session.add_page(True)),row);self.button('−',lambda:self.commit(self.session.remove_page),row);left.addLayout(row)
        row=QHBoxLayout();self.button('↑',lambda:self.reorder_page(-1),row);self.button('↓',lambda:self.reorder_page(1),row);left.addLayout(row)
        left.addWidget(QLabel('WIDGET HINZUFÜGEN'))
        self.catalog=QComboBox()
        for key,meta in model.KINDS.items():self.catalog.addItem(meta['title'],key)
        left.addWidget(self.catalog);self.button('+ Widget',lambda:self.commit(lambda:self.session.add_widget(self.catalog.currentData())),left)
        self.elements=QListWidget();self.elements.setStyleSheet('QListWidget::item { padding:0; margin:3px; }');self.elements.currentRowChanged.connect(self.select_element);left.addWidget(self.elements,1)
        self.elements.setToolTip('Inhalte des ausgewählten Widgets. Anklicken, um einzelne Texte, Werte oder Formen zu gestalten.')
        self.element_row=QWidget();erow=QHBoxLayout(self.element_row);erow.setContentsMargins(0,0,0,0)
        self.element_kind=QComboBox()
        for label,key in [('Text','text'),('Wetterwert','data'),('Bild / Logo','image'),('Linie','line'),('Rechteck','rectangle'),('Ellipse','ellipse')]:self.element_kind.addItem(label,key)
        erow.addWidget(self.element_kind);self.button('+',self.add_content,erow);left.addWidget(self.element_row)
        self.canvas=Canvas(self)
        self.right=QWidget();self.right.setObjectName('inspectorPanel');right=QVBoxLayout(self.right);right.setContentsMargins(12,12,12,12)
        self.search=QLineEdit();self.search.setPlaceholderText('Einstellungen suchen');self.search.textChanged.connect(self.filter_properties);right.addWidget(self.search)
        self.scope_box=QComboBox();self.scope_box.addItems(['Anzeige','Seite','Widget','Inhalt']);self.scope_box.setCurrentText('Widget');self.scope_box.currentTextChanged.connect(self.change_scope);right.addWidget(self.scope_box)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);right.addWidget(self.scroll)
        self.splitter.addWidget(self.left);self.splitter.addWidget(self.canvas);self.splitter.addWidget(self.right);self.splitter.setSizes([230,860,370]);self.splitter.setCollapsible(1,False)

    def build_menu(self):
        file=self.menuBar().addMenu('Entwurf')
        file.addAction(self.action('Aktive Gestaltung neu laden',self.reload_active))
        file.addAction(self.action('Gestaltung aus Sicherung wiederherstellen …',self.restore_backup))
        file.addAction(self.action('Gestaltung importieren …',self.import_design,QKeySequence.StandardKey.Open))
        file.addAction(self.action('Gestaltung exportieren …',self.export_design,QKeySequence.StandardKey.SaveAs))
        file.addAction(self.action('Vorschau als PNG …',self.export_png))
        file.addSeparator();file.addAction(self.action('Bild / Schrift importieren …',self.import_asset))
        edit=self.menuBar().addMenu('Bearbeiten');edit.addAction(self.undo_action);edit.addAction(self.redo_action)
        edit.addAction(self.action('Kopieren',self.copy,QKeySequence.StandardKey.Copy));edit.addAction(self.action('Einfügen',self.paste,QKeySequence.StandardKey.Paste))
        edit.addAction(self.action('Duplizieren',lambda:self.commit(self.session.duplicate),'Ctrl+D'));edit.addAction(self.action('Entfernen',self.remove))
        edit.addSeparator();edit.addAction(self.action('Stil kopieren',self.copy_style));edit.addAction(self.action('Stil übertragen',self.paste_style));edit.addAction(self.action('Eigene Stilabweichungen zurücksetzen',lambda:self.commit(lambda:self.session.reset_scope(self.scope))))
        preset=self.menuBar().addMenu('Vorlagen')
        for label in ('Bestehende Gestaltung','Minimal','Große Werte','Hoher Kontrast'):preset.addAction(label,lambda checked=False,name=label:self.apply_preset(name))
        preset.addSeparator();preset.addAction('Eigenen Stil speichern …',lambda:self.save_preset('styles'));preset.addAction('Eigenen Stil laden …',lambda:self.load_preset('styles'))
        preset.addAction('Widgetvorlage speichern …',lambda:self.save_preset('widgets'));preset.addAction('Widgetvorlage hinzufügen …',lambda:self.load_preset('widgets'))
        preset.addAction('Rastervorlage speichern …',lambda:self.save_preset('grids'));preset.addAction('Rastervorlage laden …',lambda:self.load_preset('grids'))
        view=self.menuBar().addMenu('Ansicht');self.grid_action=self.action('Rasterlinien',self.toggle_grid);self.grid_action.setCheckable(True);self.grid_action.setChecked(True);view.addAction(self.grid_action)
        for name,pane in (('Seitenleiste',self.left),('Eigenschaften',self.right)):
            a=self.action(name,lambda checked=False,p=pane:p.setVisible(not p.isVisible()));view.addAction(a)
        view.addAction('Helles / dunkles Werkzeug',self.toggle_theme)
        scenarios=view.addMenu('Beispieldaten')
        for label,key in [('Normal','normal'),('Lange Wettertexte','long'),('Große Werte','large'),('Fehlende Daten','missing')]:scenarios.addAction(label,lambda checked=False,k=key:self.set_scenario(k))
        scenarios.addAction('Beispieluhrzeit …',self.choose_time)
        sources=self.menuBar().addMenu('Datenquellen')
        sources.addAction('Zusatzabrufe auf diesem PC aktivieren …',lambda:self.configure_timelines(True))
        sources.addAction('Zusatzabrufe auf diesem PC ausschalten',lambda:self.configure_timelines(False))

    def error(self,error):
        # Never display arbitrary filesystem/network exceptions containing secrets.
        message=str(error) if isinstance(error,(ValueError,NoSpace)) else 'Vorgang fehlgeschlagen. Entwurf bleibt erhalten; Speicher oder Verbindung prüfen.'
        self.statusBar().showMessage(message)
        QMessageBox.warning(self,'Änderung nicht übernommen',message)

    def commit(self,action,*,inspector=True,conflicts=False,content_edit=None):
        if not self.flush_text_edits():return False
        try:
            changed=self.session.change(action,conflicts=conflicts,content_edit=self.scope=='Inhalt' if content_edit is None else content_edit)
            if changed:self.statusBar().showMessage('Entwurf automatisch gesichert · aktive Anzeige unverändert')
            self.refresh(inspector=inspector)
            return changed
        except (ValueError,OSError,KeyError) as exc:self.error(exc);self.refresh();return False

    def refresh(self,inspector=True):
        self.flush_text_edits()
        self.updating=True
        self.pages.blockSignals(True);self.pages.clear()
        for page in self.session.document['pages']:
            item=QListWidgetItem(page['title']);item.setData(Qt.ItemDataRole.UserRole,page['id'])
            signature=model.digest({'page':page,'style':self.session.document['style'],'display':self.session.document['display']})
            if signature not in self.thumb_cache:
                thumb,_,_=render_page(self.session.document,page['id'],demo_data(),self.store.assets)
                thumb.thumbnail((120,72));self.thumb_cache[signature]=QIcon(pixmap(thumb))
                if len(self.thumb_cache)>64:self.thumb_cache.pop(next(iter(self.thumb_cache)))
            item.setIcon(self.thumb_cache[signature]);self.pages.addItem(item)
        self.pages.setCurrentRow(next((i for i,p in enumerate(self.session.document['pages']) if p['id']==self.session.page_id),0));self.pages.blockSignals(False)
        display=self.session.document['display'];w,h=display['width'],display['height'];pair=tuple(sorted((w,h),reverse=True));self.profile.setCurrentIndex(0 if pair==(1024,600) else 1 if pair==(800,480) else 2);self.orientation.setCurrentIndex(int(h>w))
        self.update_content_list()
        advanced=self.tabs.currentIndex()==1;self.elements.setVisible(advanced);self.element_row.setVisible(advanced);self.scope_box.setVisible(advanced);self.search.setVisible(advanced)
        self.updating=False;self.render_canvas()
        self.mark_overrides()
        self.update_budget()
        self.undo_action.setEnabled(bool(self.session.undo));self.redo_action.setEnabled(bool(self.session.redo))
        if inspector:self.rebuild_inspector()

    def update_content_list(self):
        self.elements.blockSignals(True);self.elements.clear()
        if self.session.widget:
            for e in self.content_entries():
                label=('Titel' if e['id']=='builtin-title' else 'Karte' if e['kind']=='structure' and self.session.widget['type']=='radar' else 'Zeitreihe' if e['kind']=='structure' else e.get('text','')[:25] if e['kind']=='text' else {'time':'Uhrzeit','date':'Datum'}.get(e['binding'],FIELDS.get(e['binding'],(e['binding'],''))[0]) if e['kind']=='data' else {'image':'Bild / Logo','line':'Linie','rectangle':'Rechteck','ellipse':'Ellipse'}.get(e['kind'],e['kind']))
                item=QListWidgetItem();item.setData(Qt.ItemDataRole.AccessibleTextRole,label);item.setSizeHint(QSize(160,44));self.elements.addItem(item)
                row=QWidget();row.setStyleSheet('background:transparent;');layout=QHBoxLayout(row);layout.setContentsMargins(8,0,4,0)
                text=QLabel(label);text.setStyleSheet('background:transparent;');layout.addWidget(text,1)
                minus=QToolButton();minus.setFocusPolicy(Qt.FocusPolicy.NoFocus);minus.setIcon(icon('remove'));minus.setIconSize(QSize(16,16));minus.setFixedSize(28,28);minus.setStyleSheet('QToolButton { padding:0; background:rgba(120,135,155,0.12); border-radius:6px; } QToolButton:hover { background:rgba(0,122,255,0.20); }');minus.setAccessibleName(label+' entfernen');minus.setObjectName('remove_'+e['id'])
                minus.setEnabled(e['kind']!='structure');minus.setToolTip('Diesen Datenblock über seine Felder konfigurieren oder das Widget entfernen.' if e['kind']=='structure' else label+' entfernen')
                minus.clicked.connect(lambda checked=False,wid=self.session.widget['id'],eid=e['id']:self.queue_remove_content(wid,eid))
                layout.addWidget(minus);self.elements.setItemWidget(item,row)
            self.elements.setCurrentRow(next((i for i,e in enumerate(self.content_entries()) if e['id']==self.session.element_id),-1))
        self.elements.blockSignals(False)

    def add_content(self):
        if self.commit(lambda:self.session.add_element(self.element_kind.currentData())):
            self.scope_box.setCurrentText('Inhalt');self.scope='Inhalt';self.rebuild_inspector()
            box=next((b for b in self.boxes if b.element and b.identity==self.session.element_id),None)
            if box:self.canvas.ensureVisible(box,20,20)
            self.elements.scrollToItem(self.elements.currentItem())

    def queue_remove_content(self,widget_id,element_id):
        def remove():
            if not self.flush_text_edits():return
            from wetterstation.designer.content import element,blocks
            widget=next((w for w in self.session.page['widgets'] if w['id']==widget_id),None)
            entry=element(self.session.document,self.session.page,widget,element_id)
            if entry is None or entry['kind']=='structure' or not any(e['id']==element_id for e in blocks(self.session.document,self.session.page,widget,widget_rects(self.session.document,self.session.page)[0][widget_id])):return
            self.session.selected=[widget_id];self.session.element_id=element_id;self.session.content_selected=[element_id]
            self.scope='Inhalt'
            with QSignalBlocker(self.scope_box):self.scope_box.setCurrentText('Inhalt')
            self.commit(self.session.remove_selected,content_edit=True)
        QTimer.singleShot(0,remove)

    def render_canvas(self):
        data=demo_data(getattr(self,'example_time',None),self.scenario)
        try:image,rects,warnings=render_page(self.session.document,self.session.page_id,data,self.store.assets,self.show_grid)
        except Exception as exc:
            self.statusBar().showMessage('Vorschau konnte nicht gezeichnet werden: '+type(exc).__name__);return
        self.preview_image=image;scene=self.canvas.scene();scene.clear();self.page_pixmap=scene.addPixmap(pixmap(image));scene.setSceneRect(0,0,image.width,image.height);self.boxes=[]
        self.conflicted_ids=set()
        from wetterstation.ui.widgets import overlaps
        widgets=self.session.page['widgets']
        for index,widget in enumerate(widgets):
            for other in widgets[:index]:
                if overlaps(widget,other):self.conflicted_ids.update((widget['id'],other['id']))
        for widget in widgets:
            item=DesignBox(self,widget['id'],rects[widget['id']]);item.update_pen(widget['id'] in self.conflicted_ids);scene.addItem(item);self.boxes.append(item)
        if self.tabs.currentIndex()==1:
            from wetterstation.designer.content import area,blocks
            for widget in self.session.page['widgets']:
                x,y,w,h=area(self.session.document,self.session.page,widget,rects[widget['id']])
                for e in blocks(self.session.document,self.session.page,widget,rects[widget['id']]):
                    item=DesignBox(self,e['id'],(x+e['x']*w,y+e['y']*h,e['w']*w,e['h']*h),True,widget['id']);item.setZValue(3+e['z']*.001);scene.addItem(item);self.boxes.append(item)
        if self.canvas.zoom_mode=='fit':self.canvas.fitInView(scene.sceneRect(),Qt.AspectRatioMode.KeepAspectRatio)
        if self.conflicted_ids:self.statusBar().showMessage(f'Rastervorschlag: {len(self.conflicted_ids)} Widgets überlappen. Positionen / Größen korrigieren oder automatisch anordnen.')
        elif warnings:self.statusBar().showMessage('Entwurf gesichert · Hinweis: '+warnings[0])

    def element_area(self):
        from wetterstation.designer.content import area
        widget=self.session.widget;return area(self.session.document,self.session.page,widget,widget_rects(self.session.document,self.session.page)[0][widget['id']])

    def content_entries(self):
        from wetterstation.designer.content import blocks
        widget=self.session.widget
        return blocks(self.session.document,self.session.page,widget,widget_rects(self.session.document,self.session.page)[0][widget['id']]) if widget else []

    def update_box_pens(self):
        for box in self.boxes:box.update_pen(not box.element and box.identity in getattr(self,'conflicted_ids',set()));box.update()

    def select_page(self,index):
        if self.updating or index<0:return
        self.session.page_id=self.session.document['pages'][index]['id'];self.session.selected=[];self.session.element_id=None;self.refresh()

    def select_element(self,index):
        if self.updating or not self.session.widget:return
        self.session.element_id=self.content_entries()[index]['id'] if index>=0 else None
        self.session.content_selected=[self.session.element_id] if self.session.element_id else []
        if index>=0:self.scope='Inhalt';self.scope_box.setCurrentText(self.scope)
        self.rebuild_inspector();self.update_box_pens()

    def change_scope(self,value):
        self.scope=value
        if not self.updating:self.rebuild_inspector()

    def form_group(self,title,layout):
        box=QWidget();outer=QVBoxLayout(box);outer.setContentsMargins(0,8,0,4)
        header=QToolButton();header.setObjectName('inspectorSectionHeader');header.setText(title.replace('&','&&'));header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        header.setStyleSheet('QToolButton { border:0; background:transparent; font-weight:600; padding:4px 0; }')
        header.setCheckable(True);expanded=self.group_states.get(title,title not in ('Schatten','Werte','Karte','Position','Abstände','Seite'))
        header.setChecked(expanded);header.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        body=QWidget();form=QFormLayout(body);form.setContentsMargins(0,4,0,4)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow);form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        outer.addWidget(header);outer.addWidget(body);body.setVisible(expanded);box.body=body;box.header=header
        def toggle(on):self.group_states[title]=on;body.setVisible(on);header.setArrowType(Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)
        header.toggled.connect(toggle);layout.addWidget(box);return form

    def integer(self,value,lo,hi,callback):
        field=QSpinBox();field.setRange(lo,hi);field.setValue(value);field.setKeyboardTracking(False);field.valueChanged.connect(callback);return field

    def rebuild_inspector(self):
        self.inspector_generation+=1
        self.flush_text_edits()
        holder=QWidget();layout=QVBoxLayout(holder);layout.setContentsMargins(0,0,0,0);self.property_rows=[];self.budget_label=None;self.budget_note=None
        if self.tabs.currentIndex()==0:
            self.arrangement_controls(layout)
        else:
            self.extended_controls(layout)
        layout.addStretch()
        # setWidget deletes the old inspector immediately. A validation failure
        # can reach here from a spin box's own key/focus event; destroying that
        # control before Qt finishes the event corrupts its native state.
        previous=self.scroll.widget()
        if previous is not None:
            # Retired controls must not commit stale values on focus loss.
            for control in [previous,*previous.findChildren(QWidget)]:control.blockSignals(True)
            self.scroll.takeWidget();previous.hide();previous.deleteLater()
        self.scroll.setWidget(holder);self.filter_properties(self.search.text())

    def arrangement_controls(self,layout):
        page=self.session.page;form=self.form_group('Seite & Raster',layout)
        title=QLineEdit(page['title']);title.editingFinished.connect(lambda:self.commit(lambda:self.session.page.update(title=title.text()),inspector=False));form.addRow('Seitenname',title)
        c,r=model.grid(page)
        columns=QSpinBox();rows=QSpinBox()
        for field,value,name in ((columns,c,'pageGridColumns'),(rows,r,'pageGridRows')):
            field.setRange(1,128);field.setValue(value);field.setKeyboardTracking(False);field.setObjectName(name)
        form.addRow('Spalten',columns);form.addRow('Zeilen',rows)
        generation=self.inspector_generation;page_id=page['id'];variant=self.session.document['active_variant']
        def schedule_grid(columns_value,rows_value):
            all_pages=self.grid_all_pages;self.grid_request+=1;request=self.grid_request
            def apply():
                if request!=self.grid_request:return
                if generation!=self.inspector_generation or page_id!=self.session.page_id or variant!=self.session.document['active_variant']:return
                if model.grid(self.session.page)==(columns_value,rows_value) and not all_pages:return
                self.commit(lambda:self.session.grid_change(columns_value,rows_value,False,all_pages),conflicts=True,content_edit=False)
            QTimer.singleShot(0,apply)
        columns.valueChanged.connect(lambda value:schedule_grid(value,rows.value()))
        rows.valueChanged.connect(lambda value:schedule_grid(columns.value(),value))
        presets=QComboBox();presets.setObjectName('pageGridPreset');presets.addItems(['Raster wählen …','6 × 4','12 × 8','16 × 12','24 × 16'])
        def preset(index):
            if index:schedule_grid(*[(c,r),(6,4),(12,8),(16,12),(24,16)][index])
        presets.activated.connect(preset);form.addRow('Vorlage',presets)
        allpages=QCheckBox('Auf alle Seiten dieser Variante');allpages.setObjectName('pageGridAllPages');allpages.setChecked(self.grid_all_pages)
        allpages.toggled.connect(lambda value:setattr(self,'grid_all_pages',value));form.addRow(allpages)
        b=QPushButton('Automatisch anordnen');b.clicked.connect(lambda:self.commit(lambda:self.auto_arrange()));form.addRow(b)
        rotation=self.integer(self.session.document['display']['rotation']//90,0,3,lambda v:self.commit(lambda:self.session.document['display'].update(rotation=v*90),inspector=False));rotation.setSuffix(' × 90°');form.addRow('Ausgabedrehung',rotation)
        w=self.session.widget
        if not w:
            layout.addWidget(QLabel('Widget in der Vorschau auswählen.'));return
        form=self.form_group('Widget · '+model.KINDS[w['type']]['title'],layout)
        for key,label,maximum in [('x','Spalte',c-1),('y','Zeile',r-1),('w','Breite in Zellen',c),('h','Höhe in Zellen',r)]:
            field=self.integer(w[key],0 if key in ('x','y') else 1,maximum,lambda value,k=key:self.geometry_field(k,value));form.addRow(label,field)
        locked=QCheckBox('Position und Größe sperren');locked.setChecked(w.get('locked',False));locked.toggled.connect(lambda v:self.commit(lambda:w.update(locked=v),inspector=False));form.addRow(locked)
        destination=QComboBox()
        for p in self.session.document['pages']:
            if p['id']!=page['id']:destination.addItem(p['title'],p['id'])
        form.addRow('Andere Seite',destination);b=QPushButton('Dorthin verschieben');b.clicked.connect(lambda:self.move_page(destination.currentData()));form.addRow(b)
        b=QPushButton('Widget duplizieren');b.clicked.connect(lambda:self.commit(self.session.duplicate));form.addRow(b)
        b=QPushButton('Widget entfernen');b.clicked.connect(self.remove);form.addRow(b)
        self.field_controls(w,layout)

    def field_controls(self,w,layout):
        if not model.KINDS[w['type']]['fields']:return
        form=self.form_group('Sichtbare Inhalte',layout)
        for key,label in model.KINDS[w['type']]['fields'].items():
            cb=QCheckBox(label);cb.setChecked(key in w['fields']);cb.toggled.connect(lambda enabled,k=key:self.commit(lambda:self.toggle_field(k,enabled),inspector=False));form.addRow(cb)
        self.field_order_control(w['fields'],False,form)

    def field_order_control(self,fields,series,form):
        row=QWidget();horizontal=QHBoxLayout(row);horizontal.setContentsMargins(0,0,0,0);combo=QComboBox()
        for field in fields:
            combo.addItem(FIELDS[field][0] if field in FIELDS else model.KINDS[self.session.widget['type']]['fields'].get(field,field),field)
        key=(self.session.widget['id'],series);combo.setCurrentIndex(min(len(fields)-1,self.field_selection.get(key,0)));horizontal.addWidget(combo)
        def move(delta):
            index=combo.currentIndex();destination=index+delta
            if not 0<=destination<len(fields):return
            self.field_selection[key]=destination
            def change():
                values=self.session.widget['series']['fields'] if series else self.session.widget['fields']
                values[index],values[destination]=values[destination],values[index]
            self.commit(change)
        for label,delta in [('↑',-1),('↓',1)]:
            b=QToolButton();b.setText(label);b.clicked.connect(lambda checked=False,d=delta:move(d));horizontal.addWidget(b)
        form.addRow('Reihenfolge',row)

    def toggle_field(self,key,enabled):
        w=self.session.widget
        if enabled and key not in w['fields']:w['fields'].append(key)
        elif not enabled and key in w['fields']:w['fields'].remove(key)

    def geometry_field(self,key,value):
        w=self.session.widget;geometry={k:w[k] for k in ('x','y','w','h')};geometry[key]=value
        self.commit(lambda:self.session.geometry(w['id'],*(geometry[k] for k in ('x','y','w','h'))),inspector=False)

    def auto_arrange(self):
        p=self.session.page;p['widgets']=model.place(p['widgets'],*model.grid(p),compact=True)

    def extended_controls(self,layout):
        self.graphical_controls(layout)
        scope=self.scope
        target=self.session.document if scope=='Anzeige' else self.session.page if scope=='Seite' else self.session.element if scope=='Inhalt' else self.session.widget
        if target is None:
            layout.addWidget(QLabel('Bitte '+('einen Inhalt' if scope=='Inhalt' else 'ein Widget')+' auswählen.'));return
        w=self.session.widget;e=self.session.element
        if scope=='Inhalt' and e:self.element_controls(e,layout)
        if scope=='Widget' and w:
            self.field_controls(w,layout)
            if w['type']=='series':self.series_controls(w,layout)
            hint=QLabel('Inhalte direkt anklicken und ziehen. Das Widget über seinen Rahmen bewegen.');hint.setWordWrap(True);layout.addWidget(hint)
        levels=[self.session.document]
        if scope!='Anzeige':levels.append(self.session.page)
        if scope in ('Widget','Inhalt') and w:levels.append(w)
        if scope=='Inhalt' and e:levels.append(e)
        resolved=style(*levels);forms={}
        for key,p in model.PROPERTIES.items():
            group=p.group
            if group not in forms:forms[group]=self.form_group(group,layout)
            control=self.property_control(key,p,resolved[key]);row=QWidget();horizontal=QHBoxLayout(row);horizontal.setContentsMargins(0,0,0,0);horizontal.addWidget(control)
            reset=QToolButton();reset.setText('↺');reset.setToolTip('Übergeordnete Vorgabe verwenden');reset.setEnabled(key in target.get('style',{}));reset.clicked.connect(lambda checked=False,k=key:self.reset_property(k));horizontal.addWidget(reset)
            label=QLabel(p.label);label.setToolTip('Eigene Einstellung' if key in target.get('style',{}) else 'Geerbte Vorgabe')
            if key in target.get('style',{}):label.setStyleSheet('color:#007aff;')
            label.setWordWrap(True);label.setMaximumWidth(150)
            forms[group].addRow(label,row);self.property_rows.append((key,p.label,p.group,label,row,forms[group].parentWidget().parentWidget(),reset))

    def graphical_controls(self,layout):
        grid=self.session.document.get('inner_grid',{'step':8,'visible':True,'snap':True})
        form=self.form_group('Innenraster',layout)
        spin=self.integer(grid['step'],1,128,lambda value:self.commit(lambda:self.session.inner_grid(step=value),inspector=False,content_edit=False));spin.setObjectName('innerGridStep');spin.setSuffix(' px');form.addRow('Gemeinsamer Abstand',spin)
        for key,label in [('visible','Raster anzeigen'),('snap','Am Raster einrasten')]:
            control=QCheckBox(label);control.setChecked(grid[key]);control.setObjectName('innerGrid_'+key)
            control.toggled.connect(lambda value,k=key:self.commit(lambda:self.session.inner_grid(**{k:value}),inspector=False,content_edit=False));form.addRow(control)
        hint=QLabel('Für alle Widgets · Alt beim Ziehen: frei bewegen');hint.setWordWrap(True);form.addRow(hint)
        if not self.session.element:return
        form=self.form_group('Ausrichten',layout);e=self.session.element;s=style(self.session.document,self.session.page,self.session.widget,e)
        for key,label,values in [('align','Text horizontal',('left','center','right')),('valign','Text vertikal',('top','center','bottom'))]:
            row=QWidget();buttons=QHBoxLayout(row);buttons.setContentsMargins(0,0,0,0);buttons.setSpacing(2);group=QButtonGroup(row);group.setExclusive(True)
            for value in values:
                button=QToolButton();button.setIcon(icon('middle' if key=='valign' and value=='center' else value));button.setCheckable(True);button.setChecked(s[key]==value);button.setToolTip({'left':'Linksbündig','center':'Zentriert','right':'Rechtsbündig','top':'Oben','bottom':'Unten'}[value]);button.setAccessibleName(label+' '+button.toolTip());button.setObjectName('align_'+key+'_'+value);group.addButton(button);buttons.addWidget(button)
                button.clicked.connect(lambda checked=False,k=key,v=value:self.commit(lambda:self.session.set_property('Inhalt',k,v),inspector=False))
            form.addRow(label,row)
        row=QWidget();buttons=QHBoxLayout(row);buttons.setContentsMargins(0,0,0,0);buttons.setSpacing(2)
        for command,label in [('left','Linke Kante'),('center','Horizontal mittig'),('right','Rechte Kante'),('top','Obere Kante'),('middle','Vertikal mittig'),('bottom','Untere Kante'),('distribute_x','Horizontal verteilen'),('distribute_y','Vertikal verteilen')]:
            button=QToolButton();button.setIcon(icon(command));button.setToolTip(label);button.setAccessibleName(label);button.setObjectName('position_'+command);buttons.addWidget(button);button.clicked.connect(lambda checked=False,c=command:self.commit(lambda:self.session.align_contents(c)))
        form.addRow('Inhaltsflächen',row)

    def property_control(self,key,p,value):
        callback=lambda v:self.commit(lambda:self.session.set_property(self.scope,key,v),inspector=False)
        if p.kind=='bool':
            control=QCheckBox();control.setChecked(value);control.toggled.connect(callback)
        elif p.kind in ('choice','asset','font'):
            control=QComboBox()
            control.setMinimumContentsLength(1);control.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            if p.kind=='choice':
                labels={'none':'Keiner','vertical':'Vertikal','horizontal':'Horizontal','cover':'Füllend','contain':'Einpassen','stretch':'Strecken','solid':'Durchgezogen','dashed':'Gestrichelt','left':'Links','center':'Mitte','right':'Rechts','top':'Oben','bottom':'Unten'}
                for choice in p.choices:control.addItem(labels.get(choice,choice),choice)
            elif p.kind=='font':
                for family in ('Sans','Serif','Mono'):control.addItem(family,family)
                for name,meta in self.session.document['assets'].items():
                    if name.endswith(('.ttf','.otf')):control.addItem(meta['name'],name)
            else:
                control.addItem('Kein Bild','')
                for name,meta in self.session.document['assets'].items():
                    if name.endswith(('.png','.jpg','.webp')):control.addItem(meta['name'],name)
            control.setCurrentIndex(max(0,control.findData(value)));control.activated.connect(lambda _:callback(control.currentData()))
        elif p.kind in ('int','float'):
            control=QWidget();row=QHBoxLayout(control);row.setContentsMargins(0,0,0,0)
            spin=QSpinBox() if p.kind=='int' else QDoubleSpinBox();spin.setRange(p.minimum,p.maximum);spin.setValue(value);spin.setKeyboardTracking(False)
            if p.kind=='float':spin.setDecimals(2)
            slider=QSlider(Qt.Orientation.Horizontal);slider.setRange(0,1000);slider.setValue(round((value-p.minimum)/(p.maximum-p.minimum)*1000));slider.setMaximumWidth(90)
            def changed(v):
                blocker=QSignalBlocker(slider);slider.setValue(round((v-p.minimum)/(p.maximum-p.minimum)*1000));callback(v)
            spin.valueChanged.connect(changed)
            def slide_preview(v):
                blocker=QSignalBlocker(spin);n=p.minimum+(p.maximum-p.minimum)*v/1000;spin.setValue(round(n) if p.kind=='int' else n)
            slider.valueChanged.connect(slide_preview);slider.sliderReleased.connect(lambda:callback(spin.value()));row.addWidget(spin);row.addWidget(slider)
        elif p.kind=='color':
            control=QWidget();row=QHBoxLayout(control);row.setContentsMargins(0,0,0,0);edit=QLineEdit(value);edit.setMaximumWidth(110);button=QPushButton('');button.setFixedWidth(30);button.setToolTip(p.label+' auswählen');button.setAccessibleName(p.label+' auswählen');button.setStyleSheet('background:'+value[:7]+';');row.addWidget(edit);row.addWidget(button)
            edit.editingFinished.connect(lambda:callback(edit.text()))
            def choose():
                color=QColorDialog.getColor(color_value(edit.text()),self,'Farbe wählen',QColorDialog.ColorDialogOption.ShowAlphaChannel)
                if color.isValid():
                    val=color.name(QColor.NameFormat.HexRgb)+(f'{color.alpha():02x}' if color.alpha()<255 else '');edit.setText(val);callback(val);button.setStyleSheet('background:'+val[:7]+';')
            button.clicked.connect(choose)
        else:
            control=QLineEdit(value);control.editingFinished.connect(lambda:callback(control.text()))
        control.setMinimumWidth(0);control.setToolTip(p.label);return control

    def reset_property(self,key):self.commit(lambda:self.session.set_property(self.scope,key,None,reset=True))

    def element_controls(self,e,layout):
        form=self.form_group('Inhalt',layout)
        if e['kind']=='text':
            text=DraftText(e['text']);text.setMaximumHeight(100);timer=QTimer(text);timer.setSingleShot(True);timer.setInterval(400)
            def save_text():
                if text.saving or text.saved_text==text.toPlainText():return
                timer.stop();value=text.toPlainText();text.saving=True
                try:
                    if self.commit(lambda:self.session.element.update(text=value),inspector=False):text.saved_text=value
                finally:text.saving=False
            text.flush=save_text
            text.textChanged.connect(lambda:timer.start());timer.timeout.connect(save_text);text.editingFinished.connect(save_text);form.addRow('Eigener Text',text)
        if e['kind']=='data':
            binding=QComboBox()
            for f in model.DATA_FIELDS:binding.addItem({'time':'Uhrzeit','date':'Datum','sensor_temp':'Sensor · Temperatur','sensor_humidity':'Sensor · Luftfeuchte','sensor_pressure':'Sensor · Luftdruck','sensor_wind':'Sensor · Wind','indoor_temp':'Innen · Temperatur','indoor_humidity':'Innen · Luftfeuchte'}.get(f,FIELDS.get(f,(f,''))[0]),f)
            binding.setCurrentIndex(binding.findData(e['binding']));binding.activated.connect(lambda _:self.commit(lambda:self.session.element.update(binding=binding.currentData()),inspector=False));form.addRow('Datenfeld',binding)
        if e['kind']=='image':
            assets=QComboBox();assets.addItem('Bild wählen','')
            for name,meta in self.session.document['assets'].items():
                if name.endswith(('.png','.jpg','.webp')):assets.addItem(meta['name'],name)
            assets.setCurrentIndex(max(0,assets.findData(e.get('asset',''))));assets.activated.connect(lambda _:self.commit(lambda:self.session.element.update(asset=assets.currentData()),inspector=False));form.addRow('Bild',assets)
            button=QPushButton('Bild importieren …');button.clicked.connect(self.import_asset);form.addRow(button)
        for key,label in [('x','X in %'),('y','Y in %'),('w','Breite in %'),('h','Höhe in %')]:
            spin=QDoubleSpinBox();spin.setDecimals(4);spin.setRange(.0001 if key in ('w','h') else 0,100);spin.setValue(e[key]*100);spin.setKeyboardTracking(False)
            spin.valueChanged.connect(lambda v,k=key:self.commit(lambda:self.session.element.update({k:v/100}),inspector=False));form.addRow(label,spin)
        z=self.integer(e.get('z',0),min(-128,e.get('z',0)),max(128,e.get('z',0)),lambda v:self.commit(lambda:self.session.element.update(z=v),inspector=False));form.addRow('Ebene',z)
        b=QPushButton('Inhalt entfernen');b.clicked.connect(self.remove);form.addRow(b)

    def series_controls(self,w,layout):
        spec=w['series'];form=self.form_group('Zeitraum & Darstellung',layout)
        from wetterstation.designer.activation import ActivationStore,STATE_TEXT
        state=ActivationStore(self.settings.path.parent/'designer').state(self.session.document)
        offline=QLabel('Vorschau mit Beispieldaten. '+STATE_TEXT[state]+'. Aktivierung unter „Datenquellen“; für den Pi im Übertragungsdialog.');offline.setWordWrap(True);form.addRow(offline)
        source=QComboBox()
        for key,label in [('1min','Minutenregen'),('15min','Viertelstundenwetter'),('1h','Stündliches Wetter'),('1day','Tageswerte')]:source.addItem(label,key)
        source.setCurrentIndex(source.findData(spec['source']));source.activated.connect(lambda _:self.change_source(source.currentData()));form.addRow('Datenquelle',source)
        for key,label in [('duration','Zeitraum'),('step','Abstand zwischen Werten'),('offset','Beginn nach'),('refresh','Daten aktualisieren alle')]:
            form.addRow(label,self.time_control(w,key))
        for key,label,lo,hi in [('columns','Spalten / Werte je Reihe',1,128),('line_width','Linienstärke',1,20)]:
            spin=self.integer(spec[key],lo,hi,lambda v,k=key:self.commit(lambda:self.session.widget['series'].update({k:v}),inspector=False));form.addRow(label,spin)
        mode=QComboBox()
        for label,key in [('Wertkarten','cards'),('Tabelle','table'),('Linien','line'),('Balken','bar')]:mode.addItem(label,key)
        mode.setCurrentIndex(mode.findData(spec['mode']));mode.activated.connect(lambda _:self.commit(lambda:self.session.widget['series'].update(mode=mode.currentData()),inspector=False));form.addRow('Darstellung',mode)
        allowed=['precipitation'] if spec['source']=='1min' else [f for f in FIELDS if f!='precipitation']
        for field in allowed:
            cb=QCheckBox(FIELDS[field][0]);cb.setChecked(field in spec['fields']);cb.toggled.connect(lambda on,f=field:self.commit(lambda:self.series_field(f,on),inspector=False));form.addRow(cb)
        self.field_order_control(spec['fields'],True,form)
        for key,label in [('legend','Legende'),('axes','Achsen'),('grid','Gitternetz'),('points','Datenpunkte'),('y_auto','Achsen automatisch')]:
            cb=QCheckBox(label);cb.setChecked(spec[key]);cb.toggled.connect(lambda v,k=key:self.commit(lambda:self.session.widget['series'].update({k:v}),inspector=False));form.addRow(cb)
        for key,label in [('y_min','Achsenminimum'),('y_max','Achsenmaximum')]:
            spin=QDoubleSpinBox();spin.setRange(-1e6,1e6);spin.setValue(spec[key]);spin.setKeyboardTracking(False);spin.valueChanged.connect(lambda v,k=key:self.commit(lambda:self.session.widget['series'].update({k:v}),inspector=False));form.addRow(label,spin)
        colors=QLineEdit(', '.join(spec['colors']));colors.editingFinished.connect(lambda:self.commit(lambda:self.session.widget['series'].update(colors=[c.strip() for c in colors.text().split(',')]),inspector=False));form.addRow('Reihenfarben (HEX)',colors)
        self.budget_label=QLabel();self.budget_label.setWordWrap(True);form.addRow(self.budget_label)
        self.budget_note=QLabel('Zeitraum verkürzen oder Aktualisierungsabstand erhöhen. Anwenden ist erst mit passender Tageslast möglich.');self.budget_note.setWordWrap(True);form.addRow(self.budget_note);self.update_budget()

    def update_budget(self):
        if getattr(self,'budget_label',None) is None:return
        estimate=capacity(self.session.document)
        self.budget_label.setText(f"Geplant: {estimate['baseline']} regulär + {estimate['extra']} zusätzlich + 24 Reserve = {estimate['total']}/1000 pro Tag")
        self.budget_label.setStyleSheet('color:'+('#248a3d' if estimate['fits'] else '#d70015')+';');self.budget_note.setVisible(not estimate['fits'])

    def time_control(self,w,key):
        spec=w['series'];value=spec[key];identity=(w['id'],key)
        default=1440 if spec['source']=='1day' and key!='refresh' else 1440 if value and value%1440==0 else 60 if value and value%60==0 else 1
        factor=self.time_units.get(identity,default);row=QWidget();horizontal=QHBoxLayout(row);horizontal.setContentsMargins(0,0,0,0)
        spin=QDoubleSpinBox();spin.setDecimals(5 if factor==1440 else 3 if factor==60 else 0);spin.setRange(0,789120);spin.setValue(value/factor);spin.setKeyboardTracking(False)
        unit=QComboBox()
        for label,multiplier in [('Minuten',1),('Stunden',60),('Tage',1440)]:unit.addItem(label,multiplier)
        unit.setCurrentIndex(unit.findData(factor));horizontal.addWidget(spin);horizontal.addWidget(unit)
        def units_changed(_):
            self.time_units[identity]=unit.currentData()
            with QSignalBlocker(spin):
                spin.setDecimals(5 if unit.currentData()==1440 else 3 if unit.currentData()==60 else 0)
                spin.setValue(self.session.widget['series'][key]/unit.currentData())
        unit.activated.connect(units_changed)
        spin.valueChanged.connect(lambda value:self.commit(lambda:self.session.widget['series'].update({key:round(value*unit.currentData())}),inspector=False))
        return row

    def change_source(self,source):
        def change():
            spec=self.session.widget['series'];base,horizon,_=SOURCES[source];spec.update(source=source,step=base,duration=min(horizon,max(base,spec['duration'])),offset=0,fields=['precipitation'] if source=='1min' else ['temp'],mode='cards',refresh=30 if source=='1min' else 60)
        self.commit(change)

    def series_field(self,field,on):
        spec=self.session.widget['series']
        if on and field not in spec['fields']:spec['fields'].append(field)
        elif not on and field in spec['fields']:spec['fields'].remove(field)

    def filter_properties(self,text):
        text=text.casefold();groups={}
        for key,label,group,label_widget,control,box,reset in getattr(self,'property_rows',[]):
            visible=not text or text in (key+' '+label+' '+group).casefold();label_widget.setVisible(visible);control.setVisible(visible);groups[box]=groups.get(box,False) or visible
        for box,visible in groups.items():
            box.setVisible(visible)
            box.body.setVisible(visible and (bool(text) or box.header.isChecked()))

    def mark_overrides(self):
        target=self.session.document if self.scope=='Anzeige' else self.session.page if self.scope=='Seite' else self.session.element if self.scope=='Inhalt' else self.session.widget
        if target is None:return
        for key,label,group,label_widget,control,box,reset in getattr(self,'property_rows',[]):
            own=key in target.get('style',{});reset.setEnabled(own);label_widget.setText(label);label_widget.setStyleSheet('color:#007aff;' if own else '')

    def tick_preview(self):
        if getattr(self,'drag_active',None) or QApplication.mouseButtons()!=Qt.MouseButton.NoButton:return
        if hasattr(self,'example_time'):return
        if any(w['type'] in ('clock','date') or any(e.get('binding') in ('time','date') for e in model.content_elements(w) if e.get('kind')=='data') for w in self.session.page['widgets']):self.render_canvas()

    def profile_changed(self,_=0):
        index=self.profile.currentIndex()
        if index<2:w,h=((1024,600),(800,480))[index]
        elif self.sender() is self.orientation:
            display=self.session.document['display'];w,h=display['width'],display['height']
        else:
            w,ok=QInputDialog.getInt(self,'Eigene Auflösung','Breite im Querformat',1024,64,8192)
            if not ok:self.refresh();return
            h,ok=QInputDialog.getInt(self,'Eigene Auflösung','Höhe im Querformat',600,64,8192)
            if not ok:self.refresh();return
        w,h=sorted((w,h),reverse=True)
        if self.orientation.currentIndex():w,h=h,w
        self.commit(lambda:self.session.switch_profile(w,h),conflicts=True)

    def zoom_changed(self,index):
        self.canvas.zoom_mode='fit' if index==0 else 'fixed'
        if index==0:self.canvas.fitInView(self.canvas.sceneRect(),Qt.AspectRatioMode.KeepAspectRatio)
        else:self.canvas.resetTransform();self.canvas.scale([1,1,1.5,2][index],[1,1,1.5,2][index])

    def reorder_page(self,offset):
        def change():
            pages=self.session.document['pages'];i=pages.index(self.session.page);j=i+offset
            if 0<=j<len(pages):pages[i],pages[j]=pages[j],pages[i]
        self.commit(change)

    def move_page(self,target):
        if not target:return
        def change():
            w=self.session.widget
            if w.get('locked'):raise ValueError('Widget ist gesperrt.')
            p=next(p for p in self.session.document['pages'] if p['id']==target);items=model.place([*p['widgets'],dict(w,x=0,y=0)],*model.grid(p));self.session.page['widgets'].remove(w);p['widgets']=items;self.session.page_id=target
        self.commit(change)

    def history(self,redo=False):
        if getattr(self,'drag_active',None):self.drag_active.finish(cancel=True);return
        self.flush_text_edits()
        try:self.session.history(redo);self.refresh()
        except (OSError,ValueError) as exc:self.error(exc)

    def flush_text_edits(self):
        if getattr(self,'_flushing_text',False) or not hasattr(self,'scroll'):return True
        self._flushing_text=True
        try:
            editors=list(self.scroll.findChildren(DraftText))
            for editor in editors:
                if not editor.saving:editor.flush()
            return all(editor.saving or editor.saved_text==editor.toPlainText() for editor in editors)
        finally:self._flushing_text=False

    def closeEvent(self,event):
        if not self.flush_text_edits():event.ignore();return
        if hasattr(self,'clock_timer'):self.clock_timer.stop()
        super().closeEvent(event)

    def remove(self):self.commit(self.session.remove_selected)

    def copy(self):self.clipboard=[deepcopy(w) for w in self.session.page['widgets'] if w['id'] in self.session.selected]

    def paste(self):
        def change():
            for w in self.clipboard:self.session.add_widget(w['type'],w)
        self.commit(change)

    def copy_style(self):
        target=self.session.element if self.scope=='Inhalt' else self.session.widget if self.scope=='Widget' else self.session.page if self.scope=='Seite' else self.session.document
        if target:self.copied_style=deepcopy(target.get('style',{}))

    def paste_style(self):
        def change():
            for key,value in self.copied_style.items():self.session.set_property(self.scope,key,value)
        self.commit(change)

    def context_menu(self,position):
        menu=QMenu(self);menu.addAction('Kopieren',self.copy);menu.addAction('Einfügen',self.paste);menu.addAction('Duplizieren',lambda:self.commit(self.session.duplicate));menu.addAction('Entfernen',self.remove);menu.addSeparator();menu.addAction('Stil kopieren',self.copy_style);menu.addAction('Stil übertragen',self.paste_style);menu.exec(position)

    def apply_preset(self,name):
        presets={'Bestehende Gestaltung':{},'Minimal':{'background':'#ffffff','border_width':0.,'radius':0.,'shadow':False},'Große Werte':{'font_size':64.,'title_size':16.,'padding_top':8.,'padding_bottom':8.},'Hoher Kontrast':{'background':'#ffffff','color':'#000000','border_color':'#000000','border_width':3.,'font_size':36.}}
        self.commit(lambda:self.session.document.update(style=deepcopy(presets[name])))

    def save_preset(self,kind):
        name,ok=QInputDialog.getText(self,'Vorlage speichern','Name')
        if not ok or not name.strip():return
        def change():
            if kind=='grids':value=deepcopy(self.session.page['grid'])
            elif kind=='widgets':
                if not self.session.widget:raise ValueError('Bitte ein Widget auswählen.')
                value=deepcopy(self.session.widget)
            else:self.copy_style();value=deepcopy(self.copied_style)
            self.session.document['presets'][kind][name.strip()[:80]]=value
        self.commit(change)

    def load_preset(self,kind):
        names=list(self.session.document['presets'][kind])
        if not names:QMessageBox.information(self,'Vorlagen','Noch keine eigenen Vorlagen gespeichert.');return
        name,ok=QInputDialog.getItem(self,'Vorlage wählen','Vorlage',names,0,False)
        if not ok:return
        value=deepcopy(self.session.document['presets'][kind][name])
        if kind=='grids':self.commit(lambda:self.session.grid_change(value['columns'],value['rows']),conflicts=True)
        elif kind=='widgets':self.commit(lambda:self.session.add_widget(value['type'],value))
        else:self.copied_style=value;self.paste_style()

    def import_asset(self):
        path,_=QFileDialog.getOpenFileName(self,'Bild oder Schrift importieren','','Bilder und Schriften (*.png *.jpg *.jpeg *.webp *.ttf *.otf)')
        if not path:return
        if not self.flush_text_edits():return
        try:
            document,name=self.store.add_asset(path,self.session.document)
            def change():
                self.session.document=document
                if self.session.element and self.session.element['kind']=='image' and name.endswith('.png'):
                    from wetterstation.designer.content import materialize
                    materialize(document,self.session.page,self.session.widget,widget_rects(document,self.session.page)[0][self.session.widget['id']])
                    self.session.element['asset']=name
            self.commit(change)
        except (OSError,ValueError) as exc:self.error(exc)

    def import_design(self):
        path,_=QFileDialog.getOpenFileName(self,'Gestaltung importieren','','Wetterstation-Gestaltung (*.wetterdesign *.zip)')
        if not path:return
        if not self.flush_text_edits():return
        try:
            document=self.store.import_package(path)
            def change():self.session.document=document;self.session.page_id=document['pages'][0]['id'];self.session.selected=[];self.session.element_id=None
            self.commit(change)
        except (OSError,ValueError) as exc:self.error(exc)

    def export_design(self):
        if not self.flush_text_edits():return
        path,_=QFileDialog.getSaveFileName(self,'Gestaltung exportieren','Wetterstation.wetterdesign','Wetterstation-Gestaltung (*.wetterdesign)')
        if path:
            try:self.store.export(self.session.document,path);self.statusBar().showMessage('Gestaltung einschließlich Bildern und Schriften exportiert')
            except (OSError,ValueError) as exc:self.error(exc)

    def export_png(self):
        if not self.flush_text_edits():return
        path,_=QFileDialog.getSaveFileName(self,'Vorschau exportieren','Wetterstation.png','PNG (*.png)')
        if path:
            try:
                image,_,_=render_page(self.session.document,self.session.page_id,demo_data(getattr(self,'example_time',None),self.scenario),self.store.assets);out=io.BytesIO();image.save(out,format='PNG');atomic(path,out.getvalue())
            except (OSError,ValueError) as exc:self.error(exc)

    def reload_active(self):
        if QMessageBox.question(self,'Aktive Gestaltung laden','Gesicherten Entwurf durch den aktiven Stand ersetzen?')!=QMessageBox.StandardButton.Yes:return
        try:
            current=self.settings.load_dashboard();self.session=Session(current,self.store,revision(current));self.store.save_draft(self.session.document,self.session.base_revision);self.refresh()
        except (OSError,ValueError) as exc:self.error(exc)

    def restore_backup(self):
        path,_=QFileDialog.getOpenFileName(self,'Gestaltungssicherung wählen',str(self.store.folder/'backups'),'Gestaltungssicherung (design.json)')
        if not path:return
        try:
            previous,_=self.store.restore(Path(path).parent,self.settings,self.session.base_revision)
            self.session=Session(previous,self.store,revision(previous));self.store.save_draft(self.session.document,self.session.base_revision);self.refresh()
            self.statusBar().showMessage('Vorherige aktive Gestaltung wiederhergestellt; vorheriger aktueller Stand ebenfalls gesichert')
        except (OSError,ValueError) as exc:self.error(exc)

    def apply_pc(self):
        if not self.flush_text_edits():return
        try:
            estimate=capacity(self.session.document)
            if not estimate['fits']:raise ValueError('Zeitreihen passen nicht in das Tagesbudget. Zeitraum oder Aktualisierung anpassen.')
            backup=self.store.apply(self.session.document,self.settings,self.session.base_revision);self.session.base_revision=revision(self.session.document);self.store.save_draft(self.session.document,self.session.base_revision)
            self.statusBar().showMessage('Am PC gespeichert · laufende Anzeige übernimmt die Gestaltung · Sicherung: '+str(backup))
        except (OSError,ValueError) as exc:self.error(exc)

    def configure_timelines(self,enabled):
        from wetterstation.designer.activation import ActivationStore,STATE_TEXT,signature
        try:
            if not self.flush_text_edits():return
            active=self.settings.load_dashboard()
            if enabled and signature(active)!=signature(self.session.document):
                raise ValueError('Zeitreihen zuerst mit „Am PC anwenden“ speichern. Aktiviert wird ausschließlich die aktive Gestaltung.')
            estimate=capacity(active)
            if enabled:
                details='\n'.join(f"{s['source']}: alle {s['refresh']} Minuten, bis zu {s['calls']} Zusatzanfragen/Tag" for s in estimate['sources'])
                reply=QMessageBox.question(self,'Zusatzabrufe auf diesem PC aktivieren?',
                    details+f"\n\n{estimate['baseline']} regulär + {estimate['extra']} zusätzlich + 24 Reserve = {estimate['total']}/1000 pro Tag.\n"
                    'Zusätzliche Anbieteranfragen beginnen erst bei der nächsten regulären Live-Aktualisierung. Die Vorschau bleibt bei Beispieldaten.',
                    QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
                if reply!=QMessageBox.StandardButton.Yes:return
            state=ActivationStore(self.settings.path.parent/'designer').configure(self.settings,enabled,revision(active))
            self.refresh();self.statusBar().showMessage(STATE_TEXT[state])
        except (OSError,ValueError) as exc:self.error(exc)

    def apply_pi(self):
        if not self.flush_text_edits():return
        from wetterstation.designer.deploy import TransferDialog
        dialog=TransferDialog(self.session.document,self.store,self);dialog.exec()

    def toggle_grid(self):self.show_grid=self.grid_action.isChecked();self.render_canvas()

    def toggle_theme(self):self.dark=not self.dark;self.setStyleSheet(LIGHT+(DARK if self.dark else ''))

    def set_scenario(self,key):self.scenario=key;self.render_canvas()

    def choose_time(self):
        value,ok=QInputDialog.getText(self,'Beispieluhrzeit','ISO-Zeit mit Zeitzone',text=datetime.now(timezone.utc).isoformat(timespec='minutes'))
        if ok:
            try:
                stamp=datetime.fromisoformat(value)
                if stamp.tzinfo is None:raise ValueError('Bitte Zeitzone angeben, z. B. +01:00.')
                self.example_time=stamp;self.render_canvas()
            except ValueError as exc:self.error(exc)


def main():
    import argparse
    parser=argparse.ArgumentParser(description='Wetterstation gestalten · keine Wetterabrufe')
    parser.add_argument('--workspace',type=Path,help='Isolierter Entwurfs- und Einstellungsspeicher für Abnahme')
    parser.add_argument('--screenshot',type=Path,help='Ein Fensterbild sichern und beenden (isolierte Abnahme)')
    args=parser.parse_args()
    app=QApplication(sys.argv[:1]);app.setApplicationName('Wetterstation gestalten')
    store=ApiKeyStore(args.workspace/'settings.json') if args.workspace else None
    window=Designer(settings=store,folder=args.workspace/'designer' if args.workspace else None);window.show()
    if args.screenshot:
        args.screenshot.parent.mkdir(parents=True,exist_ok=True)
        QTimer.singleShot(1000,lambda:(window.grab().save(str(args.screenshot)),app.quit()))
    sys.exit(app.exec())


if __name__=='__main__':main()

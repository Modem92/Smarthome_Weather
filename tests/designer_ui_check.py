"""Separate Qt acceptance; PC-only dependency is never required on the Pi."""
from pathlib import Path
import os
import sys
import tempfile
import json
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.dev_paths import use_designer_runtime
use_designer_runtime(ROOT)
from tools.offline_tests import offline_guard
from PySide6.QtCore import Qt,QPoint,QPointF,QTimer
from PySide6.QtTest import QTest
from PySide6.QtGui import QFontMetrics,QPalette
from PySide6.QtWidgets import QApplication,QMessageBox,QPushButton,QDoubleSpinBox,QComboBox,QSpinBox
from PySide6.QtWidgets import QToolButton
from wetterstation.designer.app import Designer,DraftText
from wetterstation.designer import model
from wetterstation.designer.storage import DesignStore
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.widgets import revision


class DesignerUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'build/checks');self.folder=Path(self.tmp.name)
        self.settings=ApiKeyStore(self.folder/'settings.json');current=self.settings.load_dashboard();document=model.from_layout(current)
        document['pages'][0]['widgets']=document['pages'][0]['widgets'][:1];document['pages'][0]['widgets'][0].update(w=2,h=2)
        self.settings.save_dashboard(document,revision(current));self.window=Designer(self.settings,self.folder/'designer')
        self.warnings=[];self.dialog=patch.object(QMessageBox,'warning',side_effect=lambda *a:self.warnings.append(a[-1]));self.dialog.start()
        self.window.show();QTest.qWait(100);self.window.clock_timer.stop()

    def tearDown(self):
        self.dialog.stop();self.window.close()
        if getattr(self,'warning_timer',None):self.warning_timer.stop()
        self.window.deleteLater();self.app.processEvents();self.tmp.cleanup()

    def select_widget(self):
        self.window.session.selected=[self.window.session.page['widgets'][0]['id']];self.window.refresh()

    def property_spin(self,key):
        return next(row for k,_,_,_,row,_,_ in self.window.property_rows if k==key).findChild(QDoubleSpinBox)

    def test_shapes_visible_and_row_minus_targets_only_clicked_content(self):
        self.select_widget();self.window.tabs.setCurrentIndex(1)
        for kind in ('ellipse','rectangle'):
            before=self.window.preview_image.tobytes()
            self.window.element_kind.setCurrentIndex(self.window.element_kind.findData(kind))
            self.window.element_row.findChild(QPushButton).click();QTest.qWait(30)
            e=self.window.session.element;self.assertEqual(e['kind'],kind)
            self.assertEqual(self.window.session.content_selected,[e['id']]);self.assertEqual(self.window.scope,'Inhalt')
            self.assertNotEqual(before,self.window.preview_image.tobytes())
        for button in self.window.elements.findChildren(QToolButton):
            row=button.parentWidget()
            self.assertTrue(row.rect().contains(button.geometry()),(row.rect(),button.geometry()))
        self.window.grab().save(str(ROOT/'build/checks/designer-ui/remove-buttons.png'))
        identity=self.window.session.element_id;other=self.window.session.widget['elements'][0]['id']
        count=len(self.window.session.undo)
        self.window.elements.findChild(QToolButton,'remove_'+other).click();QTest.qWait(30)
        self.assertEqual([e['id'] for e in self.window.session.widget['elements']],[identity])
        self.assertEqual(len(self.window.session.undo),count+1)
        self.window.undo_action.trigger();self.assertEqual(len(self.window.session.widget['elements']),2)
        self.window.queue_remove_content(self.window.session.widget['id'],other);self.window.queue_remove_content(self.window.session.widget['id'],other);QTest.qWait(30)
        self.assertEqual(len(self.window.session.widget['elements']),1)
        for eid in (identity,'builtin-title','builtin-time','builtin-date'):
            button=self.window.elements.findChild(QToolButton,'remove_'+eid);self.assertIsNotNone(button);button.click();QTest.qWait(20)
        self.assertIsNotNone(self.window.session.widget);self.assertEqual(self.window.session.widget['elements'],[]);self.assertEqual(self.window.session.widget['fields'],[])
        self.window.commit(lambda:self.window.session.add_widget('series'))
        self.assertFalse(self.window.elements.findChild(QToolButton,'remove_builtin-structure').isEnabled())
        self.window.session.element_id=None;self.window.session.content_selected=[];self.window.commit(self.window.session.remove_selected)
        self.window.commit(lambda:self.window.session.add_widget('custom'))
        eid=self.window.session.widget['elements'][0]['id'];self.window.session.element_id=eid;self.window.scope='Inhalt';self.window.rebuild_inspector()
        editor=self.window.scroll.findChild(DraftText);editor.setFocus();editor.setPlainText('Zuletzt bearbeitet')
        button=self.window.elements.findChild(QToolButton,'remove_'+eid)
        QTest.mouseClick(button,Qt.MouseButton.LeftButton);QTest.qWait(30)
        self.assertEqual(self.window.session.widget['elements'],[])
        self.window.undo_action.trigger();self.assertEqual(self.window.session.widget['elements'][0]['text'],'Zuletzt bearbeitet')
        self.assertFalse(self.warnings)

    def test_wheel_scrolls_inspector_without_changing_focused_values(self):
        from PySide6.QtGui import QWheelEvent
        self.select_widget();self.window.tabs.setCurrentIndex(1)
        controls=[self.window.scope_box,self.window.scroll.findChild(QComboBox),self.property_spin('radius'),self.window.scroll.findChild(__import__('PySide6.QtWidgets',fromlist=['QSlider']).QSlider)]
        bar=self.window.scroll.verticalScrollBar()
        for control in controls:
            for focus in (False,True):
                bar.setValue(0)
                if focus:control.setFocus()
                else:self.window.canvas.setFocus()
                before=self.window.session.snapshot()
                event=QWheelEvent(QPointF(5,5),QPointF(control.mapToGlobal(QPoint(5,5))),QPoint(),QPoint(0,-120),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.NoScrollPhase,False)
                self.app.sendEvent(control,event);QTest.qWait(15)
                self.assertEqual(self.window.session.snapshot(),before);self.assertGreater(bar.value(),0)
                bar.setValue(0)
                pixel=QWheelEvent(QPointF(5,5),QPointF(control.mapToGlobal(QPoint(5,5))),QPoint(0,-35),QPoint(),Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier,Qt.ScrollPhase.ScrollUpdate,False)
                self.app.sendEvent(control,pixel);self.assertEqual(self.window.session.snapshot(),before);self.assertGreater(bar.value(),0)

    def test_graphical_eight_widget_handles_at_three_zoom_levels(self):
        from wetterstation.designer.interaction import HANDLES
        from wetterstation.designer.render import widget_rects
        self.select_widget();identity=self.window.session.widget['id']
        self.window.commit(lambda:self.window.session.geometry(identity,4,3,2,2))
        for zoom in (1,2,3):
            self.window.zoom_changed(zoom)
            for name,(hx,hy) in HANDLES.items():
                with self.subTest(zoom=zoom,handle=name):
                    box=next(b for b in self.window.boxes if not b.element and b.identity==identity)
                    self.window.canvas.ensureVisible(box,20,20);self.app.processEvents()
                    rect=box.rect();start=self.window.canvas.mapFromScene(box.pos()+QPointF(rect.width()*hx,rect.height()*hy))
                    _,g=widget_rects(self.window.session.document,self.window.session.page);scale=self.window.canvas.transform().m11()
                    dx=-1 if 'w' in name else 1 if 'e' in name else 0;dy=-1 if 'n' in name else 1 if 's' in name else 0
                    end=start+QPoint(round(dx*(g['cell_w']+g['gap_x'])*scale),round(dy*(g['cell_h']+g['gap_y'])*scale))
                    count=len(self.window.session.undo)
                    QTest.mousePress(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(self.window.canvas.viewport(),end,20);QTest.mouseRelease(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=end);QTest.qWait(30)
                    w=self.window.session.widget
                    self.assertEqual((w['x'],w['y'],w['w'],w['h']),(3 if dx<0 else 4,2 if dy<0 else 3,3 if dx else 2,3 if dy else 2))
                    self.assertEqual(len(self.window.session.undo),count+1)
                    self.window.undo_action.trigger();self.assertEqual(self.window.session.widget['w'],2)
        self.assertFalse(self.warnings)

    def test_graphical_direct_content_snap_alt_alignment_live_preview_and_escape(self):
        from wetterstation.designer.content import element
        self.select_widget();identity=self.window.session.widget['id'];self.window.commit(lambda:self.window.session.geometry(identity,1,1,6,5))
        self.window.tabs.setCurrentIndex(1)
        target=next(b for b in self.window.boxes if b.element and b.widget_id==identity and b.identity=='builtin-time')
        untouched=json.loads(json.dumps(self.window.session.document));count=len(self.window.session.undo)
        QTest.mouseClick(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=self.window.canvas.mapFromScene(target.sceneBoundingRect().center()))
        QTest.qWait(20);self.assertEqual(self.window.session.document,untouched);self.assertEqual(len(self.window.session.undo),count)
        self.assertEqual(self.window.session.element_id,'builtin-time')
        self.window.commit(lambda:self.window.session.element.update(x=.1,y=.15,w=.4,h=.12))
        def content_box():return next(b for b in self.window.boxes if b.element and b.widget_id==identity and b.identity=='builtin-time')
        def drag(delta,alt=False,cancel=False):
            box=content_box();start=self.window.canvas.mapFromScene(box.sceneBoundingRect().center());end=start+delta
            mods=Qt.KeyboardModifier.AltModifier if alt else Qt.KeyboardModifier.NoModifier
            before=self.window.session.snapshot()
            QTest.mousePress(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,mods,pos=start)
            if alt:QTest.keyPress(self.window.canvas.viewport(),Qt.Key.Key_Alt)
            QTest.mouseMove(self.window.canvas.viewport(),end,20)
            self.assertEqual(self.window.session.snapshot(),before)
            self.assertIsNotNone(getattr(self.window,'drag_hud',None))
            import shiboken6
            active=self.window.drag_active;self.window.tick_preview();self.assertTrue(shiboken6.isValid(active))
            if cancel:QTest.keyClick(self.window.canvas.viewport(),Qt.Key.Key_Escape)
            QTest.mouseRelease(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,mods,pos=end)
            if alt:QTest.keyRelease(self.window.canvas.viewport(),Qt.Key.Key_Alt)
            QTest.qWait(40)
        drag(QPoint(23,10));self.assertEqual(self.window.session.element_id,'builtin-time')
        self.assertEqual(self.window.session.widget['type'],'clock');self.assertEqual(self.window.session.document['version'],4)
        x,y,cw,ch=self.window.element_area();self.assertAlmostEqual((self.window.session.element['x']*cw)%8,0,places=5)
        values=[s for s in self.window.scroll.findChildren(QDoubleSpinBox) if s.maximum()==100]
        self.assertEqual([round(s.value(),4) for s in values],[round(self.window.session.element[k]*100,4) for k in ('x','y','w','h')])
        values[0].setValue(values[0].value()+5);QTest.qWait(20)
        box=content_box();self.assertAlmostEqual(box.pos().x(),x+self.window.session.element['x']*cw,places=4)
        before=self.window.session.snapshot();drag(QPoint(27,11),cancel=True);self.assertEqual(self.window.session.snapshot(),before)
        before_x=self.window.session.element['x'];drag(QPoint(13,0),alt=True)
        self.assertNotAlmostEqual((self.window.session.element['x']*cw)%8,0,places=3)
        button=self.window.scroll.findChild(QToolButton,'align_align_right');self.assertIsNotNone(button);button.click()
        self.assertEqual(self.window.session.element['style']['align'],'right')
        self.window.scroll.findChild(QToolButton,'position_left').click();self.assertEqual(self.window.session.element['x'],0)
        self.window.commit(lambda:self.window.session.widget.update(locked=True),content_edit=False)
        outer={k:self.window.session.widget[k] for k in ('x','y','w','h')}
        drag(QPoint(23,0));self.assertGreater(self.window.session.element['x'],0)
        self.assertEqual({k:self.window.session.widget[k] for k in outer},outer)
        self.assertFalse(self.warnings)

    def test_graphical_all_content_handles_and_ctrl_multiselection(self):
        from wetterstation.designer.interaction import HANDLES
        self.select_widget();identity=self.window.session.widget['id'];self.window.commit(lambda:self.window.session.geometry(identity,1,1,6,5))
        self.window.tabs.setCurrentIndex(1)
        item=next(b for b in self.window.boxes if b.element and b.identity=='builtin-time')
        QTest.mouseClick(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=self.window.canvas.mapFromScene(item.sceneBoundingRect().center()))
        self.window.commit(lambda:self.window.session.element.update(x=.3,y=.2,w=.3,h=.12))
        for zoom in (1,2,3):
            self.window.zoom_changed(zoom)
            for handle,(hx,hy) in HANDLES.items():
                with self.subTest(zoom=zoom,handle=handle):
                    box=next(b for b in self.window.boxes if b.element and b.identity=='builtin-time');self.window.canvas.ensureVisible(box,20,20);self.app.processEvents()
                    e=dict(self.window.session.element);r=box.rect();start=self.window.canvas.mapFromScene(box.pos()+QPointF(r.width()*hx,r.height()*hy));scale=self.window.canvas.transform().m11()
                    dx=-12 if 'w' in handle else 12 if 'e' in handle else 0;dy=-12 if 'n' in handle else 12 if 's' in handle else 0
                    end=start+QPoint(round(dx*scale),round(dy*scale));count=len(self.window.session.undo)
                    QTest.mousePress(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(self.window.canvas.viewport(),end,20);QTest.mouseRelease(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=end);QTest.qWait(25)
                    got=self.window.session.element
                    if dx:self.assertGreater(got['w'],e['w'])
                    if dy:self.assertGreater(got['h'],e['h'])
                    if 'w' in handle:self.assertAlmostEqual(got['x']+got['w'],e['x']+e['w'])
                    if 'n' in handle:self.assertAlmostEqual(got['y']+got['h'],e['y']+e['h'])
                    self.assertEqual(len(self.window.session.undo),count+1);self.window.undo_action.trigger()
        self.window.zoom_changed(0)
        title=next(b for b in self.window.boxes if b.element and b.identity=='builtin-title');self.window.canvas.ensureVisible(title)
        QTest.mouseClick(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ControlModifier,pos=self.window.canvas.mapFromScene(title.sceneBoundingRect().center()))
        self.assertEqual(set(self.window.session.content_selected),{'builtin-time','builtin-title'})
        self.window.scroll.findChild(QToolButton,'position_right').click()
        for identity in self.window.session.content_selected:
            from wetterstation.designer.content import element
            e=element(self.window.session.document,self.window.session.page,self.window.session.widget,identity);self.assertAlmostEqual(e['x']+e['w'],1)
        self.assertFalse(self.warnings)

    def test_graphical_widget_frame_stays_grabbable_with_zero_padding(self):
        self.select_widget();identity=self.window.session.widget['id']
        def prepare():
            self.window.session.geometry(identity,3,2,3,3)
            self.window.session.widget['style'].update(border_width=0,**{'padding_'+side:0 for side in ('top','bottom','left','right')})
        self.window.commit(prepare);self.window.tabs.setCurrentIndex(1)
        title=next(b for b in self.window.boxes if b.element and b.widget_id==identity and b.identity=='builtin-title')
        QTest.mouseClick(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=self.window.canvas.mapFromScene(title.sceneBoundingRect().center()))
        self.assertEqual(self.window.session.element_id,'builtin-title')
        box=next(b for b in self.window.boxes if not b.element and b.identity==identity)
        start=self.window.canvas.mapFromScene(box.pos()+QPointF(box.rect().width()*.25,0))
        target=self.window.canvas.itemAt(start);self.assertFalse(target.element)
        from wetterstation.designer.render import widget_rects
        _,g=widget_rects(self.window.session.document,self.window.session.page);end=start+QPoint(round((g['cell_w']+g['gap_x'])*self.window.canvas.transform().m11()),0)
        QTest.mousePress(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(self.window.canvas.viewport(),end,20);QTest.mouseRelease(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=end);QTest.qWait(30)
        self.assertEqual(self.window.session.widget['x'],4);self.assertIsNone(self.window.session.element_id);self.assertFalse(self.warnings)

    def test_invalid_geometry_warning_keeps_editor_alive_and_editable(self):
        self.select_widget();before=json.loads(json.dumps(self.window.session.document))
        active=self.settings.path.read_bytes();undo_count=len(self.window.session.undo)
        actual_warnings=[];timer=QTimer(self.window);self.warning_timer=timer
        def dismiss_warning():
            box=self.app.activeModalWidget()
            if isinstance(box,QMessageBox):
                actual_warnings.append(box.text());box.accept()
        timer.timeout.connect(dismiss_warning);timer.start(20)
        self.dialog.stop()
        try:
            def spin_with_maximum(maximum):
                return next(s for s in self.window.scroll.findChildren(QSpinBox) if s.maximum()==maximum)
            for maximum,invalid in ((11,11),(7,7),(11,11)):
                with self.subTest(maximum=maximum):
                    count=len(actual_warnings);spin=spin_with_maximum(maximum)
                    spin.setFocus();spin.selectAll();QTest.keyClicks(spin,str(invalid))
                    QTest.keyClick(spin,Qt.Key.Key_Return);QTest.qWait(50)
                    self.assertEqual(actual_warnings[count:],['Widget liegt außerhalb des Rasters oder ist zu klein.'])
                    self.assertEqual(self.window.session.document,before)
                    self.assertEqual(len(self.window.session.undo),undo_count)
                    self.assertEqual(self.settings.path.read_bytes(),active)
                    self.assertTrue(self.window.isVisible())
            spin=next(s for s in self.window.scroll.findChildren(QSpinBox) if s.maximum()==11)
            self.assertEqual(spin.value(),0)
            spin.setValue(1);QTest.qWait(30)
            self.assertEqual(self.window.session.widget['x'],1)
            saved=self.window.store.load_draft();count=len(actual_warnings)
            width=spin_with_maximum(12);width.setFocus();width.selectAll();QTest.keyClicks(width,'12')
            QTest.keyClick(width,Qt.Key.Key_Return);QTest.qWait(50)
            self.assertEqual(len(actual_warnings),count+1)
            self.assertEqual(self.window.store.load_draft(),saved)
            self.assertEqual(self.window.session.widget['w'],2)
            self.window.undo_action.trigger();self.assertEqual(self.window.session.widget['x'],0)
            self.window.redo_action.trigger();self.assertEqual(self.window.session.widget['x'],1)
            spin=spin_with_maximum(11);spin.setValue(10);count=len(actual_warnings)
            spin.stepUp();QTest.qWait(50)
            self.assertEqual(len(actual_warnings),count+1)
            self.assertEqual(self.window.session.widget['x'],10)
            self.window.apply_pc();self.assertEqual(self.settings.load_dashboard(),self.window.session.document)
        finally:
            self.dialog.start()

    def test_tabs_keep_selection_and_real_controls_change_radius_frame_and_background(self):
        self.select_widget();identity=self.window.session.selected[0]
        QTest.mouseClick(self.window.tabs,Qt.MouseButton.LeftButton,pos=self.window.tabs.tabRect(1).center());self.app.processEvents()
        self.property_spin('radius').setValue(0);self.property_spin('border_width').setValue(7)
        self.assertEqual(self.window.session.widget['style']['radius'],0)
        self.assertEqual(self.window.session.widget['style']['border_width'],7)
        self.window.undo_action.trigger();self.assertNotIn('border_width',self.window.session.widget['style'])
        self.window.redo_action.trigger();self.assertEqual(self.window.session.widget['style']['border_width'],7)
        self.window.tabs.setCurrentIndex(0);self.assertEqual(self.window.session.selected,[identity]);self.assertFalse(self.warnings)

    def test_drag_snaps_to_cells_neighbours_stay_and_keyboard_undo_work(self):
        self.select_widget();box=self.window.boxes[0];old=dict(self.window.session.widget)
        start=self.window.canvas.mapFromScene(box.sceneBoundingRect().center());_,g=__import__('wetterstation.designer.render',fromlist=['widget_rects']).widget_rects(self.window.session.document,self.window.session.page)
        end=start+QPoint(round((g['cell_w']+g['gap_x'])*self.window.canvas.transform().m11()*2),0)
        QTest.mousePress(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=start);QTest.mouseMove(self.window.canvas.viewport(),end,30);QTest.mouseRelease(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=end);self.app.processEvents()
        self.assertEqual(self.window.session.widget['x'],old['x']+2)
        self.window.canvas.setFocus();QTest.keyClick(self.window.canvas,Qt.Key.Key_Right);self.assertEqual(self.window.session.widget['x'],old['x']+3)
        self.window.undo_action.trigger();self.assertEqual(self.window.session.widget['x'],old['x']+2);self.assertFalse(self.warnings)

    def test_custom_widget_elements_fonts_style_presets_and_portrait_roundtrip(self):
        self.window.catalog.setCurrentIndex(self.window.catalog.findData('custom'))
        button=next(b for b in self.window.left.findChildren(QPushButton) if b.text()=='+ Widget');QTest.mouseClick(button,Qt.MouseButton.LeftButton)
        self.assertEqual(self.window.session.widget['type'],'custom')
        self.window.tabs.setCurrentIndex(1);self.window.commit(lambda:self.window.session.add_element('data'))
        self.assertEqual(self.window.session.element['kind'],'data')
        before=self.window.session.document['pages'];self.window.commit(lambda:self.window.session.switch_profile(600,1024));self.assertEqual(self.window.session.document['display']['height'],1024)
        self.window.commit(lambda:self.window.session.switch_profile(1024,600));self.assertEqual(self.window.session.document['pages'],before)
        self.window.apply_preset('Minimal');self.assertEqual(self.window.session.document['style']['radius'],0)
        self.window.apply_pc();self.assertEqual(self.settings.load_dashboard(),self.window.session.document);self.assertFalse(self.warnings)

    def test_grid_controls_apply_deferred_and_ignore_retired_controls(self):
        from PySide6.QtWidgets import QCheckBox
        original=self.settings.load_dashboard();before=self.window.preview_image.tobytes();count=len(self.window.session.undo)
        columns=self.window.scroll.findChild(QSpinBox,'pageGridColumns')
        columns.setFocus();columns.selectAll();QTest.keyClicks(columns,'24')
        self.assertEqual(model.grid(self.window.session.page),(12,8))
        QTest.keyClick(columns,Qt.Key.Key_Return);QTest.qWait(40)
        self.assertEqual(model.grid(self.window.session.page),(24,8));self.assertNotEqual(before,self.window.preview_image.tobytes())
        self.assertEqual(len(self.window.session.undo),count+1)
        rows=self.window.scroll.findChild(QSpinBox,'pageGridRows');rows.setFocus();rows.selectAll();QTest.keyClicks(rows,'16')
        self.window.scroll.findChild(QSpinBox,'pageGridColumns').setFocus();QTest.qWait(40);self.assertEqual(model.grid(self.window.session.page),(24,16))
        allpages=self.window.scroll.findChild(QCheckBox,'pageGridAllPages');allpages.setChecked(True)
        preset=self.window.scroll.findChild(QComboBox,'pageGridPreset');count=len(self.window.session.undo);preset.activated.emit(1);QTest.qWait(40)
        self.assertTrue(all(model.grid(p)==(6,4) for p in self.window.session.document['pages']))
        self.assertTrue(self.window.scroll.findChild(QCheckBox,'pageGridAllPages').isChecked());self.assertEqual(len(self.window.session.undo),count+1)
        self.window.undo_action.trigger();self.window.redo_action.trigger();self.assertEqual(model.grid(self.window.session.page),(6,4))
        columns=self.window.scroll.findChild(QSpinBox,'pageGridColumns');columns.setValue(20);columns.setValue(22);QTest.qWait(40)
        self.assertEqual(model.grid(self.window.session.page),(22,4))
        columns=self.window.scroll.findChild(QSpinBox,'pageGridColumns');columns.setValue(30);self.window.rebuild_inspector();QTest.qWait(40)
        self.assertEqual(model.grid(self.window.session.page),(22,4))
        self.assertEqual(self.settings.load_dashboard(),original)
        self.assertEqual(self.window.store.load_draft()['design'],self.window.session.document);self.assertFalse(self.warnings)

    def test_detail_search_and_grid_proposals_recover_without_apply(self):
        self.select_widget();self.window.tabs.setCurrentIndex(1);self.window.search.setText('Eckradius')
        visible=[k for k,_,_,_,row,_,_ in self.window.property_rows if not row.isHidden()]
        self.assertEqual(visible,['radius']);self.window.search.clear()
        self.window.commit(lambda:self.window.session.grid_change(24,16));self.assertEqual(model.grid(self.window.session.page),(24,16))
        recovered=self.window.store.load_draft();self.assertEqual(recovered['design'],self.window.session.document)
        self.assertEqual(model.grid(self.settings.load_dashboard()['pages'][0]),(12,8));self.assertFalse(self.warnings)

    def test_multiline_text_survives_immediate_tab_switch_and_undo(self):
        self.window.commit(lambda:self.window.session.add_widget('custom'));self.window.tabs.setCurrentIndex(1)
        self.window.session.element_id=self.window.session.widget['elements'][0]['id'];self.window.scope_box.setCurrentText('Inhalt');self.window.rebuild_inspector()
        text=self.window.scroll.findChild(DraftText);text.setFocus();text.setPlainText('Eigener Titel\nZweite Zeile')
        QTest.mouseClick(self.window.tabs,Qt.MouseButton.LeftButton,pos=self.window.tabs.tabRect(0).center());self.app.processEvents()
        self.assertEqual(self.window.session.widget['elements'][0]['text'],'Eigener Titel\nZweite Zeile')
        self.window.undo_action.trigger();self.assertEqual(self.window.session.widget['elements'][0]['text'],'Dein Text');self.assertFalse(self.warnings)

    def test_pending_text_is_saved_before_direct_selection_of_another_widget(self):
        clock=self.window.session.page['widgets'][0]['id']
        self.window.commit(lambda:self.window.session.geometry(clock,0,0,3,4))
        self.window.commit(lambda:self.window.session.add_widget('custom'));custom=self.window.session.widget['id']
        self.window.tabs.setCurrentIndex(1);self.window.session.element_id=self.window.session.widget['elements'][0]['id'];self.window.scope_box.setCurrentText('Inhalt');self.window.rebuild_inspector()
        editor=self.window.scroll.findChild(DraftText);editor.setFocus();editor.setPlainText('Direkt weiterarbeiten')
        target=next(b for b in self.window.boxes if b.element and b.widget_id==clock and b.identity=='builtin-time')
        position=self.window.canvas.mapFromScene(target.sceneBoundingRect().center())
        QTest.mouseClick(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,pos=position);QTest.qWait(30)
        widget=next(w for w in self.window.session.page['widgets'] if w['id']==custom)
        self.assertEqual(widget['elements'][0]['text'],'Direkt weiterarbeiten')
        self.assertEqual(self.window.session.widget['id'],clock);self.assertEqual(self.window.session.element_id,'builtin-time');self.assertFalse(self.warnings)

    def test_time_units_and_budget_labels_follow_actual_controls(self):
        self.window.commit(lambda:self.window.session.add_widget('series'));self.window.tabs.setCurrentIndex(1)
        units=[c for c in self.window.right.findChildren(QComboBox) if c.count()==3 and c.itemData(0)==1 and c.itemData(1)==60]
        self.assertEqual(len(units),4);duration=units[0];self.assertEqual(duration.currentData(),60)
        spin=duration.parentWidget().findChild(QDoubleSpinBox);self.assertEqual(spin.value(),3)
        spin.setValue(24);self.assertEqual(self.window.session.widget['series']['duration'],1440)
        self.assertIn('48 zusätzlich',self.window.budget_label.text());self.assertFalse(self.warnings)

    def test_ctrl_selection_edits_multiple_widget_styles(self):
        self.window.commit(lambda:self.window.session.add_widget('temp'));ids=[w['id'] for w in self.window.session.page['widgets']]
        for index,identity in enumerate(ids):
            box=next(b for b in self.window.boxes if b.identity==identity)
            point=self.window.canvas.mapFromScene(box.sceneBoundingRect().center())
            QTest.mouseClick(self.window.canvas.viewport(),Qt.MouseButton.LeftButton,Qt.KeyboardModifier.ControlModifier if index else Qt.KeyboardModifier.NoModifier,pos=point)
        self.assertEqual(set(self.window.session.selected),set(ids));self.window.tabs.setCurrentIndex(1)
        self.property_spin('radius').setValue(0)
        self.assertTrue(all(w['style']['radius']==0 for w in self.window.session.page['widgets']));self.assertFalse(self.warnings)

    def test_visual_capture(self):
        self.assertTrue(QFontMetrics(self.window.font()).inFontUcs4(ord('W')))
        self.assertTrue(QFontMetrics(self.window.font()).inFontUcs4(ord('ä')))
        self.assertGreater(self.window.scroll.widget().palette().color(QPalette.ColorRole.Window).lightness(),200)
        output=ROOT/'build/checks/designer-ui';output.mkdir(parents=True,exist_ok=True)
        self.window.resize(1460,920);self.select_widget();QTest.qWait(30)
        dpr=self.window.devicePixelRatioF();expected=os.environ.get('WETTERSTATION_TEST_DPR')
        if expected:self.assertAlmostEqual(dpr,float(expected),places=2)
        suffix=str(round(dpr,2)).replace('.','_')
        self.window.grab().save(str(output/f'arrangement-scale-{suffix}.png'))
        self.window.tabs.setCurrentIndex(1);self.window.session.widget['style'].update(background='#eef5ff',radius=0,border_width=4);self.window.refresh();QTest.qWait(30)
        self.window.grab().save(str(output/f'advanced-scale-{suffix}.png'))
        self.window.session.element_id='builtin-time';self.window.session.content_selected=['builtin-time'];self.window.scope_box.setCurrentText('Inhalt');self.window.rebuild_inspector();QTest.qWait(30)
        self.window.grab().save(str(output/f'content-scale-{suffix}.png'))
        self.window.commit(lambda:self.window.session.switch_profile(480,800));self.window.toggle_theme()
        self.window.session.element_id='builtin-time';self.window.session.content_selected=['builtin-time'];self.window.rebuild_inspector();self.window.update_box_pens();QTest.qWait(30)
        self.assertLess(self.window.scroll.widget().palette().color(QPalette.ColorRole.Window).lightness(),80)
        self.window.grab().save(str(output/f'portrait-dark-scale-{suffix}.png'))
        (output/f'scale-{suffix}.json').write_text(json.dumps({'effective_dpr':dpr,'logical_width':self.window.width(),'logical_height':self.window.height(),'pixels_width':self.window.grab().width(),'pixels_height':self.window.grab().height()}))
        self.assertFalse(self.warnings)

    def test_extra_source_confirmation_cancel_enable_and_disable_never_fetch(self):
        from wetterstation.designer.activation import ActivationStore
        flag=ActivationStore(self.settings.path.parent/'designer',binding=lambda:'dummy-pc')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.No):
            self.window.configure_timelines(True)
        self.assertFalse(flag.path.exists())
        with patch.object(QMessageBox,'question',return_value=QMessageBox.StandardButton.Yes),patch('wetterstation.designer.activation.device_binding',return_value='dummy-pc'):
            self.window.configure_timelines(True)
            self.assertEqual(flag.state(self.settings.load_dashboard()),'on')
            self.window.configure_timelines(False)
            self.assertEqual(flag.state(self.settings.load_dashboard()),'off')
        self.assertFalse(self.warnings)


if __name__=='__main__':
    ROOT.joinpath('build/checks').mkdir(parents=True,exist_ok=True)
    unittest.main(verbosity=2)

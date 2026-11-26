"""Version 4, editable built-ins and shared-grid geometry, without Qt/providers."""
from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from wetterstation.designer import model,content
from wetterstation.designer.storage import DesignStore
from wetterstation.designer.session import Session
from wetterstation.designer.render import render_page,widget_rects,demo_data
from wetterstation.ui.widgets import revision,validate_layout


class GraphicalModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.root=Path(self.tmp.name)
        self.doc=model.from_layout();self.page=self.doc['pages'][0];self.widget=self.page['widgets'][0]

    def tearDown(self):self.tmp.cleanup()

    def test_v4_upgrade_alone_preserves_legacy_pixels_and_phone_details(self):
        data=demo_data();old=render_page(self.doc,self.page['id'],data,self.root)[0]
        content.upgrade(self.doc);self.assertEqual(validate_layout(self.doc)['version'],4)
        self.assertEqual(old.tobytes(),render_page(self.doc,self.page['id'],data,self.root)[0].tobytes())
        rect=widget_rects(self.doc,self.page)[0][self.widget['id']];content.materialize(self.doc,self.page,self.widget,rect)
        before=deepcopy(self.widget['content_layout']);new=model.arrangement(self.doc,[{'op':'move_widget','page':self.page['id'],'id':self.widget['id'],'x':0,'y':0,'w':self.widget['w'],'h':self.widget['h']}],revision(self.doc))
        self.assertEqual(next(w for w in new['pages'][0]['widgets'] if w['id']==self.widget['id'])['content_layout'],before)

    def test_builtin_move_preserves_type_fields_binding_undo_and_package(self):
        original=deepcopy(self.doc);session=Session(self.doc,DesignStore(self.root),revision(self.doc));session.selected=[self.widget['id']];session.element_id='builtin-time'
        session.change(lambda:session.element.update(x=.2,w=.6))
        self.assertEqual(session.widget['type'],'clock');self.assertEqual(session.widget['fields'],self.widget['fields']);self.assertEqual(session.element['binding'],'time')
        self.assertEqual(session.document['version'],4);session.history();self.assertEqual(session.document,original);session.history(True)
        package=self.root/'graphical.wetterdesign';session.store.export(session.document,package)
        self.assertEqual(session.store.import_package(package),session.document)

    def test_all_structured_widget_types_keep_original_data_settings(self):
        for kind in ('radar','series','hourly','daily'):
            w=model.new_widget(kind);w.update(x=0,y=0,w=12,h=8);self.page['widgets']=[w]
            original=deepcopy(w);rect=widget_rects(self.doc,self.page)[0][w['id']]
            content.materialize(self.doc,self.page,w,rect);e=w['content_layout']['builtin-structure'];e.update(x=.1,y=.3,w=.8,h=.6)
            model.validate(self.doc);image,_,_=render_page(self.doc,self.page['id'],demo_data(),self.root)
            self.assertEqual(image.size,(1024,600));self.assertEqual(w['type'],kind);self.assertEqual(w['fields'],original['fields'])
            if kind=='series':self.assertEqual(w['series'],original['series'])

    def test_eight_handles_keep_opposite_edges_and_snap_shared_pixel_distance(self):
        original=(32,32,64,48)
        for handle in ('n','ne','e','se','s','sw','w','nw'):
            x,y,w,h=content.snap_rect(original,handle,13,13,256,256,8)
            self.assertEqual(x%8,0);self.assertEqual(y%8,0);self.assertGreater(w,0);self.assertGreater(h,0)
            if 'w' in handle:self.assertEqual(x+w,96)
            if 'e' in handle:self.assertEqual(x,32)
            if 'n' in handle:self.assertEqual(y+h,80)
            if 's' in handle:self.assertEqual(y,32)
        self.assertEqual(content.snap_rect(original,'move',13,13,256,256,8)[:2],(48,48))
        self.assertEqual(content.snap_rect(original,'move',13,13,256,256,0)[:2],(45,45))

    def test_alignment_distribution_and_proportional_widget_resize(self):
        session=Session(self.doc,DesignStore(self.root),revision(self.doc));session.selected=[self.widget['id']];session.element_id='builtin-time'
        session.change(lambda:session.element.update(x=.1,y=.2,w=.3,h=.2));before=deepcopy(session.element)
        session.change(lambda:session.geometry(self.widget['id'],0,0,3,2));self.assertEqual(session.element,before)
        session.change(lambda:session.align_contents('right'));self.assertAlmostEqual(session.element['x'],.7)
        session.change(lambda:session.set_property('Inhalt','align','left'));self.assertEqual(session.element['style']['align'],'left')
        session.content_selected=['builtin-title','builtin-time','builtin-date']
        def place():
            for identity,x in zip(session.content_selected,(0,.3,.8)):
                content.element(session.document,session.page,session.widget,identity).update(x=x,w=.2)
        session.change(place);session.change(lambda:session.align_contents('distribute_x'))
        self.assertAlmostEqual(session.widget['content_layout']['builtin-time']['x'],.4)

    def test_grid_settings_do_not_reposition_existing_contents_and_invalid_data_fails(self):
        session=Session(self.doc,DesignStore(self.root),revision(self.doc));session.change(lambda:session.inner_grid(step=17,snap=False))
        self.assertEqual(session.document['pages'],self.doc['pages'])
        for step in (0,129,True):
            bad=deepcopy(session.document);bad['inner_grid']['step']=step
            with self.assertRaises(ValueError):model.validate(bad)

    def test_incompatible_pi_is_rejected_before_upload_or_apply(self):
        import json
        from wetterstation.designer.transfer import Transfer
        from unittest.mock import Mock
        remote=Mock(return_value=json.dumps({'ok':True,'result':{'supported':3,'transfer_protocol':2,'revision':'a'*64}}))
        content.upgrade(self.doc)
        transfer=Transfer(self.doc,DesignStore(self.root/'transfer'),remote=remote)
        with self.assertRaises(ValueError):transfer.inspect()
        self.assertEqual(remote.call_count,1)

    def test_cached_draw_restores_viewport_after_pairing_page(self):
        from types import SimpleNamespace
        from unittest.mock import Mock,patch
        from wetterstation.designer import runtime
        content.upgrade(self.doc);data=demo_data();canvas=Mock()
        canvas.winfo_width.return_value=1024;canvas.winfo_height.return_value=600;canvas.find_withtag.return_value=(1,)
        preview=SimpleNamespace(dashboard=self.doc,canvas=canvas,_current_page=lambda:self.page,
            _display_viewport={'grid':{'gap':8}},_designer_runtime_key=(revision(self.doc),self.page['id'],(1024,600),runtime.static_key(self.doc,self.page,data)))
        with patch.object(runtime,'display_data',return_value=data),patch.object(runtime,'patch_clocks') as clocks,patch.object(runtime,'render_page',side_effect=AssertionError('cached image should be reused')):
            runtime.draw(preview);clocks.assert_called_once()
        self.assertEqual(preview._display_viewport['grid']['columns'],12)
        self.assertIn('gap_x',preview._display_viewport['grid'])

    def test_structured_map_really_moves_and_resizes_inside_widget(self):
        from PIL import Image
        self.doc['style'].update(show_title=False,border_width=0,radius=0,gap_x=0,gap_y=0,
            **{'padding_'+side:0 for side in ('left','right','top','bottom')},
            **{'margin_'+side:0 for side in ('left','right','top','bottom')})
        w=model.new_widget('radar');w.update(x=0,y=0,w=12,h=8,fields=['map']);self.page['widgets']=[w]
        content.materialize(self.doc,self.page,w,(0,0,1024,600))
        w['content_layout']['builtin-structure'].update(x=.2,y=.2,w=.5,h=.5)
        data=demo_data();data.update(map=Image.new('RGBA',(50,50),'#00aa55'),radar=None,map_notice='',attribution='Fixture source',coverage='')
        image=render_page(self.doc,self.page['id'],data,self.root)[0].convert('RGB')
        self.assertEqual(image.getpixel((20,20)),(255,255,255))
        self.assertEqual(image.getpixel((300,200)),(0,170,85))
        self.assertEqual(image.getpixel((900,200)),(255,255,255))

    def test_builtin_clock_binding_ticks_and_synthetic_binding_remains_labelled(self):
        from wetterstation.designer.runtime import clock_widgets,clock_token
        from datetime import timedelta
        from PIL import ImageStat
        rect=widget_rects(self.doc,self.page)[0][self.widget['id']]
        content.materialize(self.doc,self.page,self.widget,rect)
        e=self.widget['content_layout']['builtin-time'];e['style']['time_format']='%H:%M:%S'
        data=demo_data();first=clock_token(self.doc,self.page,self.widget,data)
        data['now']+=timedelta(seconds=1)
        self.assertNotEqual(first,clock_token(self.doc,self.page,self.widget,data))
        self.assertIn(self.widget,clock_widgets(self.page))
        e['binding']='sensor_temp';self.widget['style']['opacity']=0
        image=render_page(self.doc,self.page['id'],data,self.root)[0]
        self.assertGreater(sum(ImageStat.Stat(image.crop((0,564,1024,600)).convert('RGB')).var),0)

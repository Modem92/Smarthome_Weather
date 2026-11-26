"""Design migrations, transactional edits, phone field preservation and packages."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import json
import tempfile
import unittest
import zipfile
from PIL import Image
from wetterstation.designer import model
from wetterstation.designer.storage import DesignStore,read_json
from wetterstation.designer.session import Session
from wetterstation.designer.render import render_page,demo_data
from wetterstation.designer.series import capacity,select_samples
from wetterstation.storage.api_key_store import ApiKeyStore
from wetterstation.ui.widgets import revision,default_layout,NoSpace,LayoutConflict


class DesignerModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root=Path(self.tmp.name);self.store=DesignStore(self.root/'draft');self.doc=model.from_layout()

    def tearDown(self):self.tmp.cleanup()

    def test_migration_keeps_original_positions_fields_and_ids_without_writing_settings(self):
        original=default_layout();model.validate(self.doc)
        for old,new in zip(original['pages'],self.doc['pages']):
            for a,b in zip(old['widgets'],new['widgets']):
                self.assertEqual(a,{k:b[k] for k in a})

    def test_phone_commands_preserve_all_style_and_series_details_and_refuse_style_payloads(self):
        self.doc['pages'][0]['widgets']=[];w=model.new_widget('series');w.update(w=2,h=2)
        w['style']={'radius':0,'border_width':7,'background':'#ff0000'};self.doc['pages'][0]['widgets']=[w]
        command={'op':'move_widget','page':'overview','id':w['id'],'x':4,'y':2,'w':3,'h':3}
        edited=model.arrangement(self.doc,[command],revision(self.doc));got=edited['pages'][0]['widgets'][0]
        self.assertEqual(got['style'],w['style']);self.assertEqual(got['series'],w['series'])
        with self.assertRaises(ValueError):model.arrangement(self.doc,[dict(command,style={})],revision(self.doc))
        with self.assertRaises(LayoutConflict):model.arrangement(edited,[command],revision(self.doc))

    def test_small_grid_and_portrait_are_lossless_and_return_exact_variant(self):
        self.doc['pages'][0]['widgets']=self.doc['pages'][0]['widgets'][:1]
        p=model.resize_grid(self.doc['pages'][0],1,1)
        self.assertEqual((p['widgets'][0]['w'],p['widgets'][0]['h']),(1,1))
        portrait=model.switch_variant(self.doc,600,1024)
        self.assertEqual(portrait['display']['width'],600)
        back=model.switch_variant(portrait,1024,600)
        self.assertEqual(back['pages'],self.doc['pages'])

    def test_invalid_move_does_not_move_neighbours_or_save_and_undo_is_shared(self):
        session=Session(self.doc,self.store,revision(default_layout()));before=session.snapshot()
        w=session.page['widgets'][0]
        with self.assertRaises(NoSpace):session.change(lambda:session.geometry(w['id'],4,0,w['w'],w['h']))
        self.assertEqual(session.snapshot(),before)
        for i in range(105):session.change(lambda i=i:session.page.update(title=str(i)))
        self.assertEqual(len(session.undo),100)
        session.history();self.assertEqual(session.page['title'],'103')
        session.history(True);self.assertEqual(session.page['title'],'104')
        recovered=self.store.load_draft();self.assertEqual(recovered['design'],session.document)

    def test_asset_package_is_portable_and_apply_preserves_key_and_conflicts(self):
        image=self.root/'logo.png';Image.new('RGB',(10,10),'red').save(image)
        doc,name=self.store.add_asset(image,self.doc);doc['style']['image']=name
        package=self.root/'design.zip';self.store.export(doc,package)
        destination=DesignStore(self.root/'other');loaded=destination.import_package(package)
        self.assertEqual(doc,loaded);destination.check_assets(loaded)
        settings=ApiKeyStore(self.root/'active/settings.json');settings.save_configuration('Testort','dummy-key',country_code='DE')
        current=settings.load_dashboard();destination.apply(loaded,settings,revision(current))
        self.assertEqual(settings.load_api_key(),'dummy-key')
        with self.assertRaises(LayoutConflict):destination.apply(loaded,settings,revision(current))
        with zipfile.ZipFile(self.root/'bad.zip','w') as z:
            z.writestr('design.json',json.dumps(doc));z.writestr('../escape','bad')
        with self.assertRaises(ValueError):destination.import_package(self.root/'bad.zip')

    def test_renderer_all_widgets_and_shapes_at_both_orientations_and_radius_zero(self):
        data=demo_data()
        for kind in model.KINDS:
            doc=model.from_layout();w=model.new_widget(kind);w.update(x=0,y=0,w=12,h=8);w['style']={'radius':0,'border_width':4,'background':'#cceeff'}
            for shape in ('text','data','image','line','rectangle','ellipse'):
                w['elements'].append(model.new_element(shape))
            doc['pages'][0]['widgets']=[w]
            for width,height in ((1024,600),(480,800)):
                doc['display'].update(width=width,height=height)
                image,rects,warnings=render_page(doc,'overview',data,self.store.assets)
                self.assertEqual(image.size,(width,height));self.assertIn(w['id'],rects)

    def test_real_sample_selection_keeps_gaps_and_minute_rain_rejects_temperature(self):
        spec=model.default_series();spec.update(duration=60,step=15)
        now=datetime(2026,10,27,12,tzinfo=timezone.utc)
        rows=[{'timestamp':'2026-10-27T12:00:00+00:00','temp':10},{'timestamp':'2026-10-27T12:30:00+00:00','temp':12}]
        got=select_samples(rows,spec,now)
        self.assertEqual(len(got),4);self.assertTrue(got[1]['missing']);self.assertNotIn('temp',got[1])
        from wetterstation.designer.series import validate_spec
        spec.update(source='1min',step=1)
        with self.assertRaises(ValueError):validate_spec(spec)

    def test_budget_estimate_accounts_for_25_hour_day_and_pagination(self):
        w=model.new_widget('series');w['series'].update(duration=48*60,refresh=60);self.doc['pages'][0]['widgets']=[w]
        estimate=capacity(self.doc,datetime(2026,10,25,8,tzinfo=timezone.utc))
        self.assertEqual(estimate['baseline'],900);self.assertEqual(estimate['sources'][0]['pages'],4)
        self.assertFalse(estimate['fits'])

    def test_daily_series_includes_today_and_follows_calendar_across_dst(self):
        spec=model.default_series();spec.update(source='1day',duration=3*1440,step=1440)
        rows=[{'timestamp':t,'temp':i} for i,t in enumerate(('2026-10-24T00:00:00+02:00','2026-10-25T00:00:00+02:00','2026-10-26T00:00:00+01:00'))]
        got=select_samples(rows,spec,datetime.fromisoformat('2026-10-24T14:00:00+02:00'),'Europe/Berlin')
        self.assertEqual([r['temp'] for r in got],[0,1,2]);self.assertFalse(any(r['missing'] for r in got))


if __name__=='__main__':unittest.main()

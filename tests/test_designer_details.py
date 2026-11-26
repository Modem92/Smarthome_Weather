"""Rendering semantics and recovery cases beyond a successful editor launch."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest
import zipfile
from PIL import Image

from wetterstation.designer import model
from wetterstation.designer.render import surface,format_value,local_format,render_page,demo_data,FONTS
from wetterstation.designer.storage import DesignStore
from wetterstation.designer.session import Session
from wetterstation.ui.widgets import revision,NoSpace
from wetterstation.storage.api_key_store import ApiKeyStore


class DesignDetailsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).parent);self.folder=Path(self.tmp.name);self.store=DesignStore(self.folder)

    def tearDown(self):self.tmp.cleanup()

    def test_square_individual_corners_and_zero_border_are_real_pixels(self):
        s=model.style();s.update(background='#ffffff',border_color='#000000',border_width=4,radius=0)
        image,mask=surface((100,80),s,self.folder)
        self.assertEqual(image.getpixel((0,0)),(0,0,0,255));self.assertEqual(image.getpixel((50,40)),(255,255,255,255))
        s.update(border_width=0,individual_corners=True,radius_tl=0,radius_tr=20,radius_br=20,radius_bl=0)
        image,mask=surface((100,80),s,self.folder)
        self.assertEqual(mask.getpixel((0,0)),255);self.assertEqual(mask.getpixel((99,0)),0)
        self.assertEqual(image.getpixel((0,0)),(255,255,255,255))

    def test_global_page_widget_element_inheritance_and_real_unit_conversions(self):
        s=model.style({'style':{'radius':0,'temperature_unit':'°F'}},{'style':{'border_width':0}},{'style':{'color':'#ff0000'}},{'style':{'font_size':19}})
        self.assertEqual((s['radius'],s['border_width'],s['font_size']),(0,0,19));self.assertEqual(format_value(0,'temp',s),'32,0 °F')
        self.assertEqual(format_value(10,'wind',dict(s,wind_unit='km/h')),'36,0 km/h')
        stamp=datetime(2026,10,27,12,tzinfo=timezone.utc)
        self.assertEqual(local_format(stamp,'%A, %d.%m.%Y'),'Dienstag, 27.10.2026')

    def test_free_contents_retains_data_bindings_and_undo_original_widget(self):
        doc=model.from_layout();session=Session(doc,self.store,revision(doc));session.selected=['weather'];old=deepcopy(session.widget)
        session.change(session.free_contents);self.assertEqual(session.widget['type'],'custom')
        bindings=[e['binding'] for e in session.widget['elements'] if e['kind']=='data'];self.assertEqual(bindings,old['fields'])
        session.history();self.assertEqual(session.widget,old)

    def test_conflicted_grid_draft_can_be_repaired_one_page_at_a_time(self):
        doc=model.from_layout();doc['pages']=doc['pages'][:2]
        for p in doc['pages']:
            p['grid']={'columns':2,'rows':1};p['widgets']=[model.new_widget('temp',2,1),model.new_widget('temp',2,1)]
            for index,w in enumerate(p['widgets']):w.update(x=index,w=1,h=1)
        session=Session(doc,self.store,revision(doc));session.change(lambda:session.grid_change(1,1,all_pages=True),conflicts=True)
        with self.assertRaises(NoSpace):model.validate(session.document)
        recovered=self.store.load_draft();session=Session(recovered['design'],self.store,recovered['base_revision'])
        for page in session.document['pages']:
            session.page_id=page['id'];session.change(lambda:session.grid_change(2,1))
            for w in list(session.page['widgets']):session.change(lambda w=w:session.geometry(w['id'],0,0,1,1))
            w=session.page['widgets'][1];session.change(lambda:session.geometry(w['id'],1,0,1,1))
        model.validate(session.document)

    def test_portable_font_import_export_uses_same_bytes_and_corrupt_package_is_rejected(self):
        doc,name=self.store.add_asset(FONTS/'DejaVuSerif.ttf',model.from_layout());doc['style']['font']=name
        path=self.folder/'font.wetterdesign';self.store.export(doc,path)
        other=DesignStore(self.folder/'other');loaded=other.import_package(path)
        self.assertEqual((other.assets/name).read_bytes(),(FONTS/'DejaVuSerif.ttf').read_bytes())
        render_page(loaded,data=demo_data(),assets=other.assets)
        bad=self.folder/'bad.wetterdesign';bad.write_text('kein zip')
        with self.assertRaises(ValueError):other.import_package(bad)

    def test_backup_restores_font_and_image_bytes_after_old_active_files_are_missing(self):
        image=self.folder/'logo.png';Image.new('RGB',(20,10),'orange').save(image)
        original,font_name=self.store.add_asset(FONTS/'DejaVuSerif.ttf',model.from_layout())
        original,image_name=self.store.add_asset(image,original);original['style'].update(font=font_name,image=image_name)
        settings=ApiKeyStore(self.folder/'target/private/settings.json');settings.save_configuration('Testort','dummy-preserved-key',country_code='DE')
        self.store.apply(original,settings,revision(settings.load_dashboard()))
        replacement=model.from_layout();replacement['style']['background']='#dcecff'
        backup=self.store.apply(replacement,settings,revision(original))
        for name in (font_name,image_name):
            active=settings.path.parent/'designer/assets'/name
            self.assertTrue(active.resolve().is_relative_to(self.folder.resolve()))
            active.unlink()
        restored,_=self.store.restore(backup,settings,revision(replacement))
        self.assertEqual(restored,original);self.assertEqual(settings.load_dashboard(),original)
        for name in (font_name,image_name):
            self.assertEqual((settings.path.parent/'designer/assets'/name).read_bytes(),(backup/'assets'/name).read_bytes())
        self.assertEqual(settings.load_api_key(),'dummy-preserved-key')

    def test_coverage_and_sensor_labels_cannot_be_hidden_by_global_opacity(self):
        doc=model.from_layout();doc['style'].update(opacity=0,show_title=False);doc['pages'][0]['widgets']=[model.new_widget('radar')]
        data=demo_data();data.update(demo=False,attribution='OpenStreetMap · RainViewer',coverage='Keine Radarversorgung',map_notice='')
        image,_,_=render_page(doc,data=data,assets=self.folder)
        bottom=image.crop((0,image.height-36,image.width,image.height))
        self.assertEqual(bottom.getchannel('A').getextrema(),(255,255))
        self.assertTrue(any(sum(pixel)<700 for pixel in bottom.convert('RGB').getdata()))


if __name__=='__main__':unittest.main()

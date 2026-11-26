from pathlib import Path
import tempfile
import unittest
from wetterstation.designer import model,content
from wetterstation.designer.render import render_page,demo_data,widget_rects
from wetterstation.designer.session import Session
from wetterstation.designer.storage import DesignStore
from wetterstation.ui.widgets import revision


class ShapeTests(unittest.TestCase):
    def test_existing_shape_inherits_original_style_and_explicit_transparency_survives(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            doc=model.from_layout();page=doc['pages'][0];w=page['widgets'][0];page['widgets']=[w]
            content.materialize(doc,page,w,widget_rects(doc,page)[0][w['id']])
            w['style'].update(background='#00aa55',border_width=0)
            e=model.new_element('rectangle');e.update(x=.1,y=.1,w=.8,h=.8);w['elements']=[e]
            image=render_page(doc,page['id'],demo_data(),tmp)[0]
            e['style'].update(background='#ff0000',border_width=0,opacity=0)
            transparent=render_page(doc,page['id'],demo_data(),tmp)[0]
            self.assertNotEqual(image.tobytes(),transparent.tobytes())
            self.assertEqual(e['style']['opacity'],0)

    def test_new_shapes_top_layer_and_package_roundtrip(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            store=DesignStore(Path(tmp));doc=model.from_layout();s=Session(doc,store,revision(doc));s.selected=[s.page['widgets'][0]['id']]
            for kind in ('ellipse','rectangle'):
                s.change(lambda:s.add_element(kind));self.assertEqual(s.element['kind'],kind)
                self.assertGreater(s.element['style']['border_width'],0)
                self.assertEqual(s.content_selected,[s.element_id])
            path=Path(tmp)/'shapes.wetterdesign';store.export(s.document,path)
            self.assertEqual(store.import_package(path),s.document)

    def test_grid_is_behind_opaque_widgets_and_visible_through_transparency(self):
        doc=model.from_layout();page=doc['pages'][0];widget=page['widgets'][0];page['widgets']=[widget]
        widget['style'].update(background='#ffffff',border_width=0,radius=0,shadow=False)
        data=demo_data();plain=render_page(doc,page['id'],data)[0];grid=render_page(doc,page['id'],data,draw_grid=True)[0]
        x,y,w,h=widget_rects(doc,page)[0][widget['id']];box=(x,y,x+w,y+h)
        self.assertEqual(plain.crop(box).tobytes(),grid.crop(box).tobytes())
        self.assertNotEqual(plain.tobytes(),grid.tobytes())
        widget['style']['opacity']=0
        plain=render_page(doc,page['id'],data)[0];grid=render_page(doc,page['id'],data,draw_grid=True)[0]
        self.assertNotEqual(plain.crop(box).tobytes(),grid.crop(box).tobytes())

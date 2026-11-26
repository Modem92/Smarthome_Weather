"""Exercise the actual authenticated HTTPS arrangement boundary with format 4."""
import json
from copy import deepcopy
import test_designer_integration as integration
from wetterstation.designer.content import materialize
from wetterstation.designer.render import widget_rects
from wetterstation.ui.widgets import revision


class GraphicalPhoneTests(integration.PhoneDesignTests):
    def install_design(self):
        doc,w=super().install_design();old=revision(doc)
        materialize(doc,doc['pages'][0],w,widget_rects(doc,doc['pages'][0])[0][w['id']])
        w['content_layout']['builtin-structure'].update(x=.13,w=.72)
        self.store.save_dashboard(doc,old)
        return doc,w

    def test_graphical_contents_and_grid_survive_persisted_phone_move(self):
        self.login();doc,w=self.install_design();before=deepcopy(w['content_layout'])
        self.service.on_layout_change=lambda d,p:self.service.publish_display(p,revision(d))
        payload={'operations':[{'op':'move_widget','page':'overview','id':w['id'],'x':6,'y':3,'w':6,'h':5}],'revision':revision(doc),'page_id':'overview'}
        status,_,body=self.request('POST','/api/dashboard/arrange',payload)
        self.assertEqual(status,200);saved=json.loads(body)['layout']
        self.assertEqual(saved['version'],4);self.assertEqual(saved['inner_grid'],doc['inner_grid'])
        self.assertEqual(saved['pages'][0]['widgets'][0]['content_layout'],before)
        self.assertEqual(self.store.load_dashboard(),saved)

import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from font_model import FontDocument
from thinning import preview_thin
from rendering import draw_filled_glyph
from test_thinning import fixture


def pen_class():
    path=Path(__file__).resolve().parents[1]/'ttf_studio.pyw'
    loader=importlib.machinery.SourceFileLoader('preview_ui',str(path))
    spec=importlib.util.spec_from_loader(loader.name,loader)
    module=importlib.util.module_from_spec(spec);loader.exec_module(module)
    return module.CanvasPen


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        path=Path(self.tmp.name)/'test.ttf';path.write_bytes(fixture())
        self.doc=FontDocument(path)

    def test_preview_is_not_applied_to_document(self):
        state=self.doc.state()
        preview,report=preview_thin(self.doc.build_font(),'box',2)
        self.assertEqual(report['changed'],1)
        self.assertEqual(self.doc.state(),state)
        self.assertFalse(self.doc.dirty)
        self.assertEqual(preview['glyf']['box'].xMin,110)
        self.assertEqual(self.doc.font['glyf']['box'].xMin,100)

    def test_preview_matches_full_font_application(self):
        preview,_=preview_thin(self.doc.build_font(),'scaled',2)
        self.doc.thin_all(2)
        full=self.doc.build_font()
        self.assertEqual(list(preview['glyf']['scaled'].coordinates),list(full['glyf']['scaled'].coordinates))
        self.assertEqual(preview['hmtx']['scaled'],full['hmtx']['scaled'])

    def test_filled_preview_preserves_counter(self):
        class Canvas:
            def __init__(self):self.polygons=[]
            def delete(self,*args):self.polygons=[]
            def winfo_width(self):return 400
            def winfo_height(self):return 350
            def cget(self,key):return '#fbfcf9'
            def create_line(self,*args,**kwargs):pass
            def create_polygon(self,*args,**kwargs):self.polygons.append((args,kwargs))
        canvas=Canvas();draw_filled_glyph(canvas,self.doc.build_font(),'ring',pen_class())
        self.assertEqual(len(canvas.polygons),2)
        self.assertEqual(canvas.polygons[0][1]['fill'],'#315b49')
        self.assertEqual(canvas.polygons[1][1]['fill'],'#fbfcf9')

    def test_flat_top_remains_flat(self):
        # A rectangle's flat cap must not be sharpened into an apex.
        after,_=preview_thin(self.doc.build_font(),'box',2)
        glyph=after['glyf']['box']
        top=[p[0] for p in glyph.coordinates if p[1]==glyph.yMax]
        self.assertEqual(max(top)-min(top),180)
        self.assertEqual(glyph.yMax,390)

if __name__=='__main__':unittest.main()

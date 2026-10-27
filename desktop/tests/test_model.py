import importlib.machinery
import importlib.util
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from font_model import FontDocument
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


def fixture():
    b = FontBuilder(1000,isTTF=True)
    b.setupGlyphOrder(['.notdef','A','Aacute'])
    b.setupCharacterMap({65:'A',193:'Aacute'})
    p=TTGlyphPen(None);p.moveTo((100,0));p.qCurveTo((300,800),(500,0));p.lineTo((100,0));p.closePath()
    composite=TTGlyphPen({'.notdef':None,'A':None});composite.addComponent('A',(1,0,0,1,0,0))
    b.setupGlyf({'.notdef':TTGlyphPen(None).glyph(),'A':p.glyph(),'Aacute':composite.glyph()})
    b.setupHorizontalMetrics({'.notdef':(600,0),'A':(600,100),'Aacute':(600,100)})
    b.setupHorizontalHeader(ascent=850,descent=-150)
    b.setupNameTable({'familyName':'Test','styleName':'Regular','fullName':'Test Regular','psName':'Test-Regular','copyright':'Keep copyright','licenseDescription':'Keep license'})
    b.setupOS2(sTypoAscender=850,sTypoDescender=-150,usWinAscent=850,usWinDescent=150)
    b.setupPost();b.setupMaxp();out=BytesIO();b.save(out);return out.getvalue()


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.source=Path(self.tmp.name)/'sample.ttf';self.source.write_bytes(fixture())
        self.doc=FontDocument(self.source)

    def test_roundtrip(self):
        original=self.source.read_bytes()
        self.doc.rename('나의 글꼴','Regular')
        g=self.doc.glyph('A');g['points'][0][0]=145
        self.doc.update_glyph('A',advance=740,lsb=145,points=g['points'])
        destination=self.source.with_name('edited.ttf');self.doc.save(destination)
        font=TTFont(destination,checkChecksums=2);font.ensureDecompiled()
        self.assertEqual(font['name'].getDebugName(1),'나의 글꼴')
        self.assertEqual(font['hmtx']['A'],(740,145))
        self.assertEqual(font['glyf']['A'].coordinates[0],(145,0))
        self.assertEqual(font['name'].getDebugName(0),'Keep copyright')
        self.assertEqual(font['name'].getDebugName(13),'Keep license')
        self.assertEqual(font.getBestCmap(),{65:'A',193:'Aacute'})
        self.assertTrue(font['glyf']['Aacute'].isComposite())
        self.assertEqual(self.source.read_bytes(),original)
        self.assertFalse(self.doc.dirty)
        FontDocument(destination)

    def test_undo_and_reset(self):
        self.doc.update_glyph('A',advance=800)
        self.doc.update_glyph('A',lsb=180)
        self.assertTrue(self.doc.dirty)
        self.doc.undo();self.assertEqual(self.doc.glyph('A')['lsb'],100)
        self.doc.reset_glyph('A');self.assertEqual(self.doc.glyph('A')['advance'],600)
        self.doc.undo();self.assertEqual(self.doc.glyph('A')['advance'],800)

    def test_saved_state_after_undo(self):
        self.doc.rename('Changed','Regular');self.doc.save(self.source.with_name('out.ttf'))
        self.assertFalse(self.doc.dirty)
        self.doc.undo();self.assertTrue(self.doc.dirty)

    def test_invalid_values_leave_state_unchanged(self):
        for change in [{'advance':-1},{'advance':'1.5'},{'lsb':40000},{'points':[]},{'advance':'NaN'}]:
            with self.assertRaises(ValueError):self.doc.update_glyph('A',**change)
        with self.assertRaises(ValueError):self.doc.rename('','Regular')
        self.assertFalse(self.doc.dirty)
        self.assertEqual(self.doc.history,[])

    def test_composite_metrics_only(self):
        self.doc.update_glyph('Aacute',advance=900)
        with self.assertRaises(ValueError):self.doc.update_glyph('Aacute',points=self.doc.glyph('Aacute')['points'])
        self.assertEqual(self.doc.build_font()['hmtx']['Aacute'][0],900)

    def test_failed_save_preserves_original(self):
        original=self.source.read_bytes()
        self.doc.rename('New','Regular')
        with patch('font_model.os.replace',side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):self.doc.save(self.source)
        self.assertEqual(self.source.read_bytes(),original)
        self.assertEqual(list(self.source.parent.glob('.ttf-studio-*')),[])
        self.assertTrue(self.doc.dirty)

    def test_invalid_font(self):
        self.source.write_bytes(b'not a font')
        with self.assertRaises(Exception):FontDocument(self.source)

    def test_curve_renderer(self):
        path=Path(__file__).resolve().parents[1]/'ttf_studio.pyw'
        loader=importlib.machinery.SourceFileLoader('desktop_ui',str(path))
        spec=importlib.util.spec_from_loader(loader.name,loader);module=importlib.util.module_from_spec(spec);loader.exec_module(module)
        class Canvas:
            def __init__(self):self.lines=[]
            def create_line(self,*args,**kwargs):self.lines.append(args)
        canvas=Canvas();module.Editor.draw_simple(canvas,self.doc.glyph('A'),.5,100,300)
        self.assertEqual(len(canvas.lines),1)
        self.assertGreater(len(canvas.lines[0]),30)
        self.assertEqual(canvas.lines[0][:2],(150,300))

if __name__=='__main__':unittest.main()

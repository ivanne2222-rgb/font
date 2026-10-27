from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from font_model import FontDocument
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
import pathops
from fontTools.pens.recordingPen import DecomposingRecordingPen


def fixture(thin_stem=False):
    builder=FontBuilder(1000,isTTF=True)
    names=['.notdef','box','ring','scaled','blank']
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap({65:'box',66:'ring',67:'scaled',32:'blank'})
    def rectangle(pen,x0,y0,x1,y1,clockwise=True):
        points=[(x0,y0),(x0,y1),(x1,y1),(x1,y0)]
        if not clockwise:points.reverse()
        pen.moveTo(points[0])
        for point in points[1:]:pen.lineTo(point)
        pen.closePath()
    pen=TTGlyphPen(None);rectangle(pen,100,0,104 if thin_stem else 300,400);box=pen.glyph()
    pen=TTGlyphPen(None);rectangle(pen,100,0,500,500);rectangle(pen,200,100,400,400,False);ring=pen.glyph()
    pen=TTGlyphPen({'box':box});pen.addComponent('box',(0.5,0,0,0.5,0,0));scaled=pen.glyph()
    builder.setupGlyf({'.notdef':TTGlyphPen(None).glyph(),'box':box,'ring':ring,'scaled':scaled,'blank':TTGlyphPen(None).glyph()})
    builder.setupHorizontalMetrics({n:(600,50 if n=='scaled' else 100 if n in ('box','ring') else 0) for n in names})
    builder.setupHorizontalHeader(ascent=800,descent=-200)
    builder.setupVerticalMetrics({n:(1000,300) for n in names})
    builder.setupVerticalHeader(ascent=500,descent=-500)
    builder.setupNameTable({'familyName':'Thin Test','styleName':'Regular','fullName':'Thin Test Regular','psName':'ThinTest-Regular'})
    builder.setupOS2(sTypoAscender=800,sTypoDescender=-200,usWinAscent=800,usWinDescent=200)
    builder.setupPost();builder.setupMaxp();out=BytesIO();builder.save(out);return out.getvalue()


def glyph_path(font,name):
    gs=font.getGlyphSet();recording=DecomposingRecordingPen(gs);gs[name].draw(recording)
    p=pathops.Path();recording.replay(p.getPen());return pathops.simplify(p,clockwise=True)


class ThinningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'test.ttf';self.path.write_bytes(fixture())
        self.doc=FontDocument(self.path)

    def test_uniform_erosion_including_scaled_composite(self):
        widths={n:self.doc.font['hmtx'][n][0] for n in self.doc.glyph_order}
        result=self.doc.thin_all(2) # 10 units per side regardless of component scale
        self.assertEqual(result['changed'],3);self.assertEqual(result['empty'],2)
        font=self.doc.build_font()
        self.assertEqual(glyph_path(font,'box').bounds,(110,10,290,390))
        self.assertEqual(glyph_path(font,'scaled').bounds,(60,10,140,190))
        self.assertEqual({n:font['hmtx'][n][0] for n in self.doc.glyph_order},widths)
        self.assertFalse(font['glyf']['scaled'].isComposite())
        self.assertEqual(font['hmtx']['box'][1],110)
        self.assertEqual(font['hmtx']['scaled'][1],60)

    def test_hole_expands_while_outer_edge_contracts(self):
        self.doc.thin_all(2)
        p=glyph_path(self.doc.build_font(),'ring')
        self.assertEqual(p.bounds,(110,10,490,490))
        self.assertLess(abs(p.area),140000)
        # Original hole 200..400 / 100..400 must expand approximately to 190..410 / 90..410.
        self.assertEqual(len(list(p.contours)),2)
        hole=min(p.contours,key=lambda c:abs(c.area))
        self.assertEqual(hole.bounds,(190,90,410,410))

    def test_roundtrip_then_point_edit_and_undo_all(self):
        old=self.doc.glyph('box')
        self.doc.thin_all(2)
        self.assertEqual(len(self.doc.history),1)
        points=self.doc.glyph('box')['points'];points[0][0]+=2
        self.doc.update_glyph('box',points=points)
        out=self.path.with_name('thin.ttf');self.doc.save(out)
        with TTFont(out,checkChecksums=2) as font:
            font.ensureDecompiled()
            self.assertEqual(font['hmtx']['box'][0],600)
            self.assertEqual(font.getBestCmap(),self.doc.font.getBestCmap())
        self.doc.undo();self.doc.undo()
        self.assertEqual(self.doc.glyph('box'),old)

    def test_cancel_is_atomic(self):
        original=self.doc.state()
        for limit in (0, len(self.doc.glyph_order)):
            with self.subTest(cancel_at=limit):
                with self.assertRaisesRegex(ValueError,'취소'):
                    self.doc.thin_all(2,lambda done,total,name:done < limit)
                self.assertEqual(self.doc.state(),original)
                self.assertFalse(self.doc.history)

    def test_excess_strength_is_atomic(self):
        self.path.write_bytes(fixture(thin_stem=True));doc=FontDocument(self.path)
        with self.assertRaisesRegex(ValueError,'사라집니다'):doc.thin_all(2)
        self.assertFalse(doc.edits);self.assertFalse(doc.history)

    def test_invalid_strength(self):
        for value in [0,-1,6,'oops',float('nan'),float('inf')]:
            with self.assertRaises(ValueError):self.doc.thin_all(value)
        self.assertFalse(self.doc.dirty)

    def test_prior_metrics_preserved(self):
        self.doc.update_glyph('box',advance=800,lsb=130)
        self.doc.thin_all(2)
        self.assertEqual(self.doc.glyph('box')['advance'],800)
        self.assertEqual(self.doc.glyph('box')['lsb'],140)

    def test_vertical_origin_preserved(self):
        old=self.doc.font['glyf']['box'];old.recalcBounds(self.doc.font['glyf'])
        old_origin=old.yMax+self.doc.font['vmtx']['box'][1]
        self.doc.thin_all(2);font=self.doc.build_font()
        self.assertEqual(font['glyf']['box'].yMax+font['vmtx']['box'][1],old_origin)
        self.assertEqual(font['vmtx']['box'][0],1000)

if __name__=='__main__':unittest.main()

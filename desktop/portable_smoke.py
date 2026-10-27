"""Exercise the packaged GUI and font round-trip on a Windows runner."""
import json
from pathlib import Path
import tempfile
import tkinter as tk
from types import SimpleNamespace
from font_model import FontDocument
from fontTools.ttLib import TTFont


def run(source, result_path, editor_class):
    root = None
    result = {}
    try:
        root = tk.Tk()
        editor = editor_class(root)
        editor.doc = FontDocument(source)
        editor.current = 'A'
        editor.family.set(editor.doc.family)
        editor.style_name.set(editor.doc.style)
        editor.refresh()
        root.update()
        assert editor.canvas.find_all(), 'GUI did not render'
        p = editor.glyph['points'][0][:]
        x, y, scale = editor.view
        event = SimpleNamespace(x=x+p[0]*scale, y=y-p[1]*scale)
        editor.point_down(event)
        assert editor.selected == 0, 'Point selection failed'
        editor.point_move(SimpleNamespace(x=event.x+12, y=event.y-10))
        editor.point_up(event)
        assert editor.doc.edits['A']['points'][0][:2] != p[:2], 'Point drag failed'
        editor.family.set('Portable Smoke Test')
        editor.apply_names()
        editor.width.set('740')
        editor.lsb.set('125')
        editor.px.set('125')
        editor.py.set('10')
        editor.apply_metrics()
        root.update()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)/'edited.ttf'
            editor.doc.save(destination)
            with TTFont(destination, checkChecksums=2) as font:
                font.ensureDecompiled()
                assert font['name'].getDebugName(1) == 'Portable Smoke Test'
                assert font['hmtx']['A'] == (740,125)
                assert font['glyf']['A'].coordinates[0] == (125,10)
        def fail_on_dialog(error):
            raise AssertionError(str(error))
        editor.error = fail_on_dialog
        prior = editor.doc.state()
        editor.thin_strength.set('0.4')
        comparison = editor.preview_thinning()
        root.update()
        assert comparison is not None, 'Comparison window did not open'
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        previews = [child for child in descendants(comparison) if isinstance(child, tk.Canvas)]
        assert len(previews) == 2 and all(canvas.find_all() for canvas in previews), 'Before/after preview did not render'
        assert editor.doc.state() == prior, 'Preview unexpectedly changed the document'
        apply_button = next(child for child in descendants(comparison) if child.winfo_class() == 'TButton' and str(child.cget('text')) == '이 강도로 전체 글꼴 적용')
        apply_button.invoke()
        root.update()
        assert len([e for e in editor.doc.edits.values() if 'ends' in e]) == 2, 'Whole-font application from preview failed'
        assert editor.doc.glyph('A')['advance'] == 740
        assert not editor.doc.glyph('Aacute')['composite'], 'Composite was not thinned independently'
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)/'thin.ttf'
            editor.doc.save(destination)
            with TTFont(destination, checkChecksums=2) as font:
                font.ensureDecompiled()
                assert font['hmtx']['A'][0] == 740
                assert font['glyf']['A'].numberOfContours > 0
        editor.undo()
        assert editor.doc.state() == prior, 'Bulk undo did not restore pre-thinning state'
        result = {'status':'passed','version':'1.2.0','checks':['GUI startup','canvas rendering','point selection','point drag','rename','metrics','coordinate edit','TTF save and reload','whole-font thinning','thinned TTF reload','bulk undo','filled before-after preview','apply preview strength to entire font']}
        code = 0
    except Exception as error:
        result = {'status':'failed','error':repr(error)}
        code = 1
    finally:
        if root is not None:
            root.destroy()
        Path(result_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return code

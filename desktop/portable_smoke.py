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
        result = {'status':'passed','checks':['GUI startup','canvas rendering','point selection','point drag','rename','metrics','coordinate edit','TTF save and reload']}
        code = 0
    except Exception as error:
        result = {'status':'failed','error':repr(error)}
        code = 1
    finally:
        if root is not None:
            root.destroy()
        Path(result_path).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return code

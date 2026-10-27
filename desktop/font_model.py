"""TTF editing model shared by the desktop UI and round-trip tests."""
from copy import deepcopy
from io import BytesIO
import math
from pathlib import Path
import os
import tempfile
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.ttProgram import Program


def bounded_int(value, low, high):
    if isinstance(value, bool):
        raise ValueError('정수를 입력하세요.')
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError('정수를 입력하세요.') from None
    if not math.isfinite(number) or int(number) != number or not low <= number <= high:
        raise ValueError(f'{low} ~ {high} 범위의 정수를 입력하세요.')
    return int(number)


class FontDocument:
    def __init__(self, path):
        self.source_path = Path(path)
        self.original = self.source_path.read_bytes()
        self.font = TTFont(BytesIO(self.original), recalcTimestamp=False)
        if self.font.flavor or 'glyf' not in self.font:
            raise ValueError('TrueType 윤곽(glyf)이 있는 TTF 파일을 선택하세요.')
        if 'fvar' in self.font:
            raise ValueError('가변 폰트는 지원하지 않습니다. 정적 TTF 파일을 사용하세요.')
        self.family = self.font['name'].getDebugName(1) or 'Untitled'
        self.style = self.font['name'].getDebugName(2) or 'Regular'
        self.original_names = (self.family, self.style)
        self.edits = {}
        self.history = []
        self.saved_state = self.state()
        self.characters = {}
        for code, name in (self.font.getBestCmap() or {}).items():
            self.characters.setdefault(name, []).append(code)
        self.glyph_order = self.font.getGlyphOrder()

    def state(self):
        return (self.family, self.style, deepcopy(self.edits))

    @property
    def dirty(self):
        return self.state() != self.saved_state

    def checkpoint(self):
        self.history.append(self.state())
        # Keep memory bounded for large fonts.
        self.history = self.history[-50:]

    def undo(self):
        if not self.history:
            return False
        self.family, self.style, self.edits = self.history.pop()
        return True

    def rename(self, family, style):
        family, style = family.strip(), style.strip()
        if not family or not style or max(len(family), len(style)) > 100:
            raise ValueError('글꼴 이름과 스타일은 1~100자로 입력하세요.')
        if (family, style) != (self.family, self.style):
            self.checkpoint()
            self.family, self.style = family, style

    def glyph(self, name):
        source = self.font['glyf'][name]
        coords, ends, flags = source.getCoordinates(self.font['glyf'])
        width, lsb = self.font['hmtx'][name]
        result = dict(name=name, composite=source.isComposite(),
                      points=[[int(x), int(y), bool(flag & 1)] for (x, y), flag in zip(coords, flags)],
                      ends=list(ends), advance=width, lsb=lsb)
        result.update(deepcopy(self.edits.get(name, {})))
        return result

    def update_glyph(self, name, advance=None, lsb=None, points=None):
        current = self.glyph(name)
        change = deepcopy(self.edits.get(name, {}))
        if advance is not None:
            change['advance'] = bounded_int(advance, 0, 65535)
        if lsb is not None:
            change['lsb'] = bounded_int(lsb, -32768, 32767)
        if points is not None:
            if current['composite']:
                raise ValueError('복합 글리프는 구성 요소 글리프에서 윤곽을 수정하세요.')
            if len(points) != len(current['points']):
                raise ValueError('윤곽점 개수를 변경할 수 없습니다.')
            change['points'] = [[bounded_int(p[0], -32768, 32767), bounded_int(p[1], -32768, 32767), old[2]]
                                for p, old in zip(points, current['points'])]
        if change != self.edits.get(name, {}):
            self.checkpoint()
            self.edits[name] = change

    def reset_glyph(self, name):
        if name in self.edits:
            self.checkpoint()
            del self.edits[name]

    def build_font(self):
        font = TTFont(BytesIO(self.original), recalcTimestamp=False)
        if (self.family, self.style) != self.original_names:
            ps = ''.join(c for c in f'{self.family}-{self.style}' if c.isascii() and (c.isalnum() or c == '-'))[:63]
            if not ps.strip('-'):
                ps = 'EditedFont-Regular'
            # Preserve unrelated copyright, license and version records.
            names = {1:self.family, 2:self.style, 3:f'{ps};Edited', 4:f'{self.family} {self.style}', 6:ps, 16:self.family, 17:self.style}
            for nid, value in names.items():
                font['name'].removeNames(nameID=nid)
                font['name'].setName(value, nid, 3, 1, 0x409)
        for name, change in self.edits.items():
            width, lsb = font['hmtx'][name]
            font['hmtx'][name] = (change.get('advance', width), change.get('lsb', lsb))
            if 'points' in change:
                glyph = font['glyf'][name]
                coords, _, _ = glyph.getCoordinates(font['glyf'])
                for i, point in enumerate(change['points']):
                    coords[i] = (point[0], point[1])
                glyph.coordinates = coords
                glyph.program = Program()
                glyph.program.fromBytecode([])
                glyph.recalcBounds(font['glyf'])
        if 'DSIG' in font:
            del font['DSIG']
        return font

    def save(self, destination):
        destination = Path(destination)
        # Write and verify before replacing the destination; never truncate a source on failure.
        fd, temporary = tempfile.mkstemp(prefix='.ttf-studio-', suffix='.ttf', dir=destination.parent)
        os.close(fd)
        try:
            self.build_font().save(temporary)
            with TTFont(temporary, checkChecksums=2) as check:
                check.ensureDecompiled()
            os.replace(temporary, destination)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self.saved_state = self.state()

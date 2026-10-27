"""Geometric stroke erosion: subtract a centered outline stroke from each fill."""
from array import array
import math
import pathops
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program


def outline_glyph(change):
    glyph = Glyph()
    glyph.numberOfContours = len(change['ends'])
    glyph.endPtsOfContours = list(change['ends'])
    glyph.coordinates = GlyphCoordinates([(p[0],p[1]) for p in change['points']])
    glyph.flags = array('B', [1 if p[2] else 0 for p in change['points']])
    glyph.program = Program(); glyph.program.fromBytecode([])
    return glyph


def thin_outlines(font, percent, progress=None):
    try:
        percent = float(percent)
    except (ValueError, TypeError):
        raise ValueError('얇게 강도는 0.1~5.0 사이의 숫자로 입력하세요.') from None
    if not math.isfinite(percent) or not 0.1 <= percent <= 5:
        raise ValueError('얇게 강도는 0.1~5.0 사이의 숫자로 입력하세요.')
    units = font['head'].unitsPerEm
    distance = units * percent / 200
    glyphset = font.getGlyphSet()
    names = font.getGlyphOrder()
    changes = {}
    erased = []
    empty = 0
    for index, name in enumerate(names):
        if progress and (index % 10 == 0):
            if progress(index, len(names), name) is False:
                raise ValueError('전체 얇게 만들기를 취소했습니다. 변경 사항은 적용되지 않았습니다.')
        old_width, old_lsb = font['hmtx'][name]
        old_glyph = font['glyf'][name]
        old_glyph.recalcBounds(font['glyf'])
        recording = DecomposingRecordingPen(glyphset)
        # FontTools draws top-level glyphs shifted to LSB; recover stored glyf coordinates.
        offset = getattr(old_glyph, 'xMin', 0) - old_lsb
        glyphset[name].draw(TransformPen(recording, (1,0,0,1,offset,0)))
        original = pathops.Path()
        recording.replay(original.getPen())
        original = pathops.simplify(original, clockwise=True)
        if not original or abs(original.area) < 0.01:
            empty += 1
            continue
        boundary = pathops.Path(original)
        boundary.stroke(2*distance, pathops.LineCap.BUTT_CAP, pathops.LineJoin.ROUND_JOIN, 4)
        boundary.convertConicsToQuads(max(0.05, units/20000))
        result = pathops.op(original, boundary, pathops.PathOp.DIFFERENCE, clockwise=True)
        result.convertConicsToQuads(max(0.05, units/20000))
        if not result or abs(result.area) < 0.01:
            erased.append(name)
            continue
        pen = TTGlyphPen(None)
        result.draw(Cu2QuPen(pen, max_err=max(0.25,units/4000), reverse_direction=False))
        glyph = pen.glyph()
        glyph.recalcBounds(font['glyf'])
        coords, ends, flags = glyph.getCoordinates(font['glyf'])
        if not coords or abs(glyph.xMax-glyph.xMin) < 1 or abs(glyph.yMax-glyph.yMin) < 1:
            erased.append(name)
            continue
        if any(not -32768 <= v <= 32767 for point in coords for v in point):
            raise ValueError(f'{name}: 변환 결과가 TTF 좌표 범위를 벗어납니다.')
        # Keep advance and side-bearing placement consistent with the new xMin.
        new_lsb = old_lsb + glyph.xMin - old_glyph.xMin
        if not -32768 <= new_lsb <= 32767:
            raise ValueError(f'{name}: 변환 결과의 왼쪽 여백이 TTF 범위를 벗어납니다.')
        changes[name] = dict(points=[[int(x),int(y),bool(flag & 1)] for (x,y),flag in zip(coords,flags)],
                             ends=list(ends), composite=False, advance=old_width, lsb=new_lsb)
        if 'vmtx' in font:
            changes[name]['tsb'] = font['vmtx'][name][1] + old_glyph.yMax - glyph.yMax
            if not -32768 <= changes[name]['tsb'] <= 32767:
                raise ValueError(f'{name}: 변환 결과의 세로 여백이 TTF 범위를 벗어납니다.')
    if erased:
        raise ValueError(f'강도가 높아 {len(erased)}개 글자의 획이 모두 사라집니다 ({", ".join(erased[:5])}). 강도를 낮춰 다시 적용하세요. 아무 변경도 적용하지 않았습니다.')
    if progress and progress(len(names),len(names),'완료') is False:
        raise ValueError('전체 얇게 만들기를 취소했습니다. 변경 사항은 적용되지 않았습니다.')
    return changes, dict(changed=len(changes), empty=empty, percent=percent, inset=distance)

"""Filled before/after preview using normalized non-overlapping font contours."""
import pathops
from fontTools.pens.recordingPen import DecomposingRecordingPen


def signed_area(points):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))/2


def draw_filled_glyph(canvas, font, name, pen_class):
    canvas.delete('all')
    width=max(canvas.winfo_width(),100)
    height=max(canvas.winfo_height(),100)
    ascent=font['hhea'].ascent;descent=font['hhea'].descent
    advance=font['hmtx'][name][0]
    scale=min((width-70)/max(advance,font['head'].unitsPerEm),(height-70)/max(ascent-descent,1))
    x=(width-advance*scale)/2
    y=height/2+(ascent+descent)*scale/2
    canvas.create_line(15,y,width-15,y,fill='#d3ddcf',dash=(4,4))
    glyphset=font.getGlyphSet()
    recording=DecomposingRecordingPen(glyphset)
    glyphset[name].draw(recording)
    shape=pathops.Path();recording.replay(shape.getPen())
    shape=pathops.simplify(shape,clockwise=True)
    pen=pen_class(glyphset,canvas,scale,x,y)
    shape.draw(pen)
    # Normalization makes outer contours clockwise and holes counterclockwise.
    # Draw large contours first so nested counters and islands remain visible.
    contours=sorted(pen.contours,key=lambda points:abs(signed_area(points)),reverse=True)
    for points in contours:
        if len(points)<3:continue
        color=pen.color if signed_area(points)<0 else canvas.cget('bg')
        coords=[v for point in points for v in (x+point[0]*scale,y-point[1]*scale)]
        canvas.create_polygon(*coords,fill=color,outline='',width=0)

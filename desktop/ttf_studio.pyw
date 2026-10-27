"""Native Windows TTF editor. No web server, browser or network required at runtime."""
import ctypes
import math
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from fontTools.pens.basePen import BasePen
from font_model import FontDocument


class CanvasPen(BasePen):
    def __init__(self, glyphset, canvas, scale, x, y, color='#315b49'):
        super().__init__(glyphset)
        self.canvas, self.scale, self.x, self.y, self.color = canvas, scale, x, y, color
        self.contours, self.points = [], []

    def _moveTo(self, point):
        self.points = [point]

    def _lineTo(self, point):
        self.points.append(point)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._getCurrentPoint()
        for i in range(1, 25):
            t = i / 24; u = 1-t
            self.points.append(tuple(u**3*p0[j]+3*u*u*t*p1[j]+3*u*t*t*p2[j]+t**3*p3[j] for j in (0,1)))

    def _qCurveToOne(self, p1, p2):
        p0 = self._getCurrentPoint()
        for i in range(1, 19):
            t = i / 18; u = 1-t
            self.points.append(tuple(u*u*p0[j]+2*u*t*p1[j]+t*t*p2[j] for j in (0,1)))

    def _closePath(self):
        if self.points:
            self.contours.append(self.points)
        self.points = []

    _endPath = _closePath

    def finish(self, filled=False):
        # Tk polygons do not support nonzero holes; use contour strokes for faithful editing.
        for contour in self.contours:
            coords = [v for p in contour + [contour[0]] for v in (self.x+p[0]*self.scale, self.y-p[1]*self.scale)]
            if len(coords) >= 4:
                self.canvas.create_line(*coords, fill=self.color, width=2 if not filled else 1.5)


class Editor:
    def __init__(self, root):
        self.root = root
        self.doc = None
        self.current = None
        self.selected = None
        self.glyph = None
        self.dragging = False
        self.view = None
        self.display_names = []
        root.title('글결 · TTF 편집기')
        root.geometry('1240x850')
        root.minsize(980, 700)
        root.configure(bg='#f3f5f0')
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('.', font=('맑은 고딕', 10), background='#f3f5f0')
        style.configure('TButton', padding=(12, 7))
        style.configure('Title.TLabel', font=('맑은 고딕', 22, 'bold'), foreground='#244e3a')
        style.configure('Accent.TButton', foreground='white', background='#315b49')
        self.family = tk.StringVar(); self.style_name = tk.StringVar()
        self.width = tk.StringVar(); self.lsb = tk.StringVar()
        self.px = tk.StringVar(); self.py = tk.StringVar()
        self.search = tk.StringVar(); self.zoom = tk.DoubleVar(value=1)
        self.preview_text = tk.StringVar(value='가나다라마바사 Aa Bb 0123456789')
        self.status = tk.StringVar(value='TTF 파일을 열어 시작하세요. 모든 처리는 이 PC에서 이루어집니다.')
        header = ttk.Frame(root, padding=(22,16)); header.pack(fill='x')
        ttk.Label(header, text='글결', style='Title.TLabel').pack(side='left')
        ttk.Label(header, text='  WINDOWS TTF STUDIO').pack(side='left', padx=15)
        ttk.Button(header, text='TTF 열기', command=self.open).pack(side='right', padx=6)
        ttk.Button(header, text='다른 이름으로 저장', style='Accent.TButton', command=self.save).pack(side='right', padx=6)
        ttk.Button(header, text='실행 취소', command=self.undo).pack(side='right', padx=6)
        body = ttk.Panedwindow(root, orient='horizontal'); body.pack(fill='both', expand=True, padx=20)
        left = ttk.Frame(body, padding=12); body.add(left, weight=0)
        ttk.Label(left,text='글꼴 정보',font=('맑은 고딕',12,'bold')).pack(anchor='w',pady=(0,12))
        self.entry(left,'글꼴 이름',self.family)
        self.entry(left,'스타일',self.style_name)
        ttk.Button(left,text='이름 적용',command=self.apply_names).pack(fill='x',pady=8)
        self.info = ttk.Label(left,text='파일을 열어주세요.',wraplength=225);self.info.pack(anchor='w',pady=12)
        ttk.Label(left,text='글자 검색 · 이름 / 문자 / U+0041').pack(anchor='w')
        ttk.Entry(left,textvariable=self.search).pack(fill='x',pady=6)
        list_frame = ttk.Frame(left);list_frame.pack(fill='both',expand=True)
        self.listbox = tk.Listbox(list_frame,width=29,font=('맑은 고딕',11),relief='flat',exportselection=False,selectbackground='#315b49')
        scroll = ttk.Scrollbar(list_frame,command=self.listbox.yview); self.listbox.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y');self.listbox.pack(fill='both',expand=True)
        self.listbox.bind('<<ListboxSelect>>',self.choose)
        self.search.trace_add('write',lambda *_:self.filter())
        right = ttk.Frame(body,padding=(12,8));body.add(right,weight=1)
        toolbar = ttk.Frame(right);toolbar.pack(fill='x',pady=(0,8))
        self.heading = ttk.Label(toolbar,text='편집할 글자를 선택하세요.',font=('맑은 고딕',13,'bold'));self.heading.pack(side='left')
        ttk.Button(toolbar,text='이 글자 초기화',command=self.reset).pack(side='right')
        ttk.Scale(toolbar,from_=0.5,to=2,variable=self.zoom,command=lambda _:self.draw()).pack(side='right',padx=8)
        ttk.Label(toolbar,text='확대').pack(side='right')
        self.canvas = tk.Canvas(right,bg='#fbfcf9',highlightthickness=1,highlightbackground='#d4dfd0',height=360)
        self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Configure>',lambda _:self.draw())
        self.canvas.bind('<Button-1>',self.point_down)
        self.canvas.bind('<B1-Motion>',self.point_move)
        self.canvas.bind('<ButtonRelease-1>',self.point_up)
        ttk.Label(right,text='● 윤곽점   ○ 곡선 제어점  |  점을 드래그하거나 X / Y를 입력하세요.').pack(anchor='w',pady=7)
        metrics = ttk.Frame(right);metrics.pack(fill='x')
        for title,var in [('글자 폭',self.width),('왼쪽 여백 (LSB)',self.lsb),('선택점 X',self.px),('선택점 Y',self.py)]:
            frame = ttk.Frame(metrics);frame.pack(side='left',padx=(0,10));ttk.Label(frame,text=title).pack(anchor='w');ttk.Entry(frame,textvariable=var,width=12).pack(pady=4)
        ttk.Button(metrics,text='간격 / 좌표 적용',command=self.apply_metrics).pack(side='right',pady=10)
        preview = ttk.LabelFrame(right,text='문장 미리보기 · 윤곽선',padding=8);preview.pack(fill='x',pady=(14,0))
        line = ttk.Frame(preview);line.pack(fill='x');ttk.Entry(line,textvariable=self.preview_text).pack(side='left',fill='x',expand=True)
        ttk.Button(line,text='갱신',command=self.draw_preview).pack(side='right',padx=(8,0))
        self.preview_canvas = tk.Canvas(preview,height=92,bg='white',highlightthickness=0);self.preview_canvas.pack(fill='x',pady=(8,0))
        self.preview_canvas.bind('<Configure>',lambda _:self.draw_preview())
        ttk.Label(root,textvariable=self.status,wraplength=1150,padding=(22,12)).pack(fill='x')
        root.protocol('WM_DELETE_WINDOW',self.close)
        root.bind('<Control-o>',lambda _:self.open());root.bind('<Control-s>',lambda _:self.save())
        root.bind('<Control-z>',self.undo_shortcut)

    @staticmethod
    def entry(parent,label,variable):
        ttk.Label(parent,text=label).pack(anchor='w');ttk.Entry(parent,textvariable=variable).pack(fill='x',pady=(4,10))

    def error(self,error):
        messagebox.showerror('TTF 편집기',str(error))

    def has_pending_names(self):
        return self.doc and (self.family.get().strip(),self.style_name.get().strip()) != (self.doc.family,self.doc.style)

    def confirm_discard(self):
        return not (self.doc and (self.doc.dirty or self.has_pending_names())) or messagebox.askyesno('변경 사항','저장하지 않은 변경 사항을 버릴까요?')

    def open(self):
        if not self.confirm_discard():return
        path = filedialog.askopenfilename(title='TTF 파일 열기',filetypes=[('TrueType font','*.ttf'),('모든 파일','*.*')])
        if not path:return
        try:
            doc = FontDocument(path)
            self.doc = doc;self.current=None;self.glyph=None;self.selected=None;self.zoom.set(1)
            self.family.set(doc.family);self.style_name.set(doc.style)
            self.info.configure(text=f'{Path(path).name}\n{len(doc.glyph_order):,} 글리프 · {doc.font["head"].unitsPerEm} UPM')
            self.search.set('');self.filter()
            self.status.set('파일을 열었습니다. 복합 글리프는 간격만 편집할 수 있습니다.')
            target = (doc.font.getBestCmap() or {}).get(ord('A'),doc.glyph_order[0])
            index=self.display_names.index(target);self.listbox.selection_set(index);self.listbox.see(index);self.choose()
        except Exception as e:self.error(e)

    def filter(self):
        self.listbox.delete(0,'end');self.display_names=[]
        if not self.doc:return
        query=self.search.get().casefold()
        for name in self.doc.glyph_order:
            codes=self.doc.characters.get(name,[])
            chars=''.join(chr(c) for c in codes if chr(c).isprintable())
            codes_text=' '.join(f'U+{c:04X}' for c in codes)
            if query and query not in f'{name} {chars} {codes_text}'.casefold():continue
            self.display_names.append(name)
            self.listbox.insert('end',f'{chars[:2] or "·"}   {name}')
        if self.current in self.display_names:
            self.listbox.selection_set(self.display_names.index(self.current))

    def choose(self,event=None):
        selection=self.listbox.curselection()
        if not selection or not self.doc:return
        self.current=self.display_names[selection[0]];self.selected=None;self.refresh()

    def refresh(self):
        if not self.doc or not self.current:return
        self.glyph=self.doc.glyph(self.current)
        self.width.set(self.glyph['advance']);self.lsb.set(self.glyph['lsb'])
        codes=self.doc.characters.get(self.current,[])
        self.heading.configure(text=f'{self.current}  '+(' / '.join(f'U+{c:04X}' for c in codes[:2])))
        if self.selected is not None and self.selected < len(self.glyph['points']):
            self.set_point_fields()
        else:self.selected=None;self.px.set('');self.py.set('')
        if self.glyph['composite']:self.status.set('복합 글리프: 간격을 수정하거나 구성 요소 글리프의 윤곽을 편집하세요.')
        self.draw();self.draw_preview();self.update_title()

    def update_title(self):
        if self.doc:self.root.title(f'{"* " if self.doc.dirty or self.has_pending_names() else ""}{self.doc.family} · 글결 TTF 편집기')

    def apply_names(self):
        if not self.doc:return
        try:self.doc.rename(self.family.get(),self.style_name.get());self.status.set('글꼴 이름을 적용했습니다. 다른 이름으로 저장하여 파일을 만드세요.');self.update_title()
        except Exception as e:self.error(e)

    def apply_metrics(self):
        if not self.doc or not self.current:return
        try:
            from font_model import bounded_int
            points=None
            if self.selected is not None and not self.glyph['composite']:
                points=[p[:] for p in self.glyph['points']]
                points[self.selected][:2]=[bounded_int(self.px.get(),-32768,32767),bounded_int(self.py.get(),-32768,32767)]
            self.doc.update_glyph(self.current,advance=self.width.get(),lsb=self.lsb.get(),points=points)
            self.refresh();self.status.set('간격 / 좌표를 적용했습니다. LSB 값은 윤곽 좌표를 이동하지 않습니다.')
        except Exception as e:self.error(e)

    def reset(self):
        if not self.doc or not self.current:return
        self.doc.reset_glyph(self.current);self.selected=None;self.refresh();self.status.set('이 글자를 원본 상태로 되돌렸습니다.')

    def undo_shortcut(self,event):
        # Preserve normal text-entry undo shortcuts.
        if isinstance(event.widget,(tk.Entry,ttk.Entry)):return
        self.undo();return 'break'

    def undo(self):
        if not self.doc:return
        if self.doc.undo():
            self.family.set(self.doc.family);self.style_name.set(self.doc.style)
            self.refresh();self.status.set('마지막 편집을 취소했습니다.')

    def set_point_fields(self):
        p=self.glyph['points'][self.selected];self.px.set(p[0]);self.py.set(p[1])

    def draw(self):
        c=self.canvas;c.delete('all');w=max(c.winfo_width(),100);h=max(c.winfo_height(),100)
        if not self.doc or not self.glyph:
            c.create_text(w/2,h/2,text='TTF 파일을 열고 글자를 선택하세요.',fill='#82917c',font=('맑은 고딕',14));return
        font=self.doc.font;upm=font['head'].unitsPerEm
        scale=min((w-100)/max(self.glyph['advance'],upm),(h-90)/(font['hhea'].ascent-font['hhea'].descent))*self.zoom.get()
        x=(w-self.glyph['advance']*scale)/2;y=h/2+(font['hhea'].ascent+font['hhea'].descent)*scale/2
        self.view=(x,y,scale)
        for yy,title in [(y,'baseline'),(y-font['hhea'].ascent*scale,'ascent'),(y-font['hhea'].descent*scale,'descent')]:
            c.create_line(0,yy,w,yy,fill='#cad8c3',dash=(4,4));c.create_text(7,yy-9,text=title,anchor='w',fill='#91a087',font=('Segoe UI',8))
        for xx in [x,x+self.glyph['advance']*scale]:c.create_line(xx,0,xx,h,fill='#d8dfd3',dash=(4,4))
        if self.glyph['composite']:
            compiled=self.doc.build_font();gs=compiled.getGlyphSet();pen=CanvasPen(gs,c,scale,x,y);gs[self.current].draw(pen);pen.finish()
        else:
            self.draw_simple(c,self.glyph,scale,x,y)
            for i,p in enumerate(self.glyph['points']):
                xx=x+p[0]*scale;yy=y-p[1]*scale;r=5 if i==self.selected else 3.5
                c.create_oval(xx-r,yy-r,xx+r,yy+r,fill='#d39040' if i==self.selected else '#315b49' if p[2] else '#fff',outline='#315b49')

    @staticmethod
    def draw_simple(canvas,glyph,scale,x,y):
        # Draw the edited TrueType contour using a temporary TT glyph and BasePen's quadratic handling.
        from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
        from array import array
        g=Glyph();g.numberOfContours=len(glyph['ends']);g.endPtsOfContours=glyph['ends']
        g.coordinates=GlyphCoordinates([(p[0],p[1]) for p in glyph['points']]);g.flags=array('B',[1 if p[2] else 0 for p in glyph['points']])
        if not g.numberOfContours:return
        pen=CanvasPen(None,canvas,scale,x,y);g.draw(pen,None);pen.finish()

    def point_down(self,event):
        if not self.glyph or self.glyph['composite'] or not self.view:return
        x,y,s=self.view;best=12;self.selected=None
        for i,p in enumerate(self.glyph['points']):
            distance=math.hypot(event.x-x-p[0]*s,event.y-y+p[1]*s)
            if distance<best:best=distance;self.selected=i
        self.dragging=self.selected is not None
        if self.dragging:self.set_point_fields()
        else:self.px.set('');self.py.set('')
        self.draw()

    def point_move(self,event):
        if not self.dragging:return
        x,y,s=self.view;p=self.glyph['points'][self.selected]
        p[:2]=[max(-32768,min(32767,round((event.x-x)/s))),max(-32768,min(32767,round((y-event.y)/s)))]
        self.set_point_fields();self.draw()

    def point_up(self,event):
        if not self.dragging:return
        self.dragging=False
        try:self.doc.update_glyph(self.current,points=self.glyph['points']);self.refresh();self.status.set('윤곽점을 수정했습니다. Ctrl+Z 또는 실행 취소 버튼으로 되돌릴 수 있습니다.')
        except Exception as e:self.error(e)

    def draw_preview(self):
        c=self.preview_canvas;c.delete('all')
        if not self.doc:return
        try:
            font=self.doc.build_font();gs=font.getGlyphSet();cmap=font.getBestCmap() or {}
            scale=52/font['head'].unitsPerEm;x=12;y=62
            for ch in self.preview_text.get()[:180]:
                name=cmap.get(ord(ch),'.notdef')
                pen=CanvasPen(gs,c,scale,x,y);gs[name].draw(pen);pen.finish(True)
                x+=font['hmtx'][name][0]*scale
                if x>c.winfo_width()-10:break
        except Exception as e:self.status.set(f'미리보기를 그릴 수 없습니다: {e}')

    def save(self):
        if not self.doc:return
        if self.has_pending_names():
            try:self.doc.rename(self.family.get(),self.style_name.get())
            except Exception as e:self.error(e);return
        path=filedialog.asksaveasfilename(title='수정한 TTF 저장',defaultextension='.ttf',initialfile=self.doc.source_path.stem+'-edited.ttf',filetypes=[('TrueType font','*.ttf')])
        if not path:return
        if Path(path).resolve()==self.doc.source_path.resolve() and not messagebox.askyesno('원본 덮어쓰기','원본 TTF를 덮어씁니다. 계속할까요?'):return
        try:self.doc.save(path);self.update_title();self.status.set(f'저장 완료: {path}')
        except Exception as e:self.error(e)

    def close(self):
        if self.confirm_discard():self.root.destroy()


def main():
    if sys.platform=='win32':
        try:ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:pass
    if len(sys.argv) == 4 and sys.argv[1] == '--smoke-test':
        from portable_smoke import run
        return run(sys.argv[2], sys.argv[3], Editor)
    root=tk.Tk();Editor(root);root.mainloop()


if __name__=='__main__':
    sys.exit(main() or 0)

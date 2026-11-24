"""Text to vector outlines.

GitHub shows README images as plain <img>, where web fonts can't be relied on,
so every word in the cover is drawn as outlines. Each glyph is defined once and
placed with <use>, which keeps the files small. HarfBuzz does the kerning.

Needs: pip install fonttools==4.60.2 uharfbuzz==0.51.7 (other versions may draw slightly different outlines)
Font: Host Grotesk, SIL Open Font License (tools/fonts/OFL.txt).
"""
import io
import os

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "HostGrotesk-Variable.ttf")


def _num(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


class _Face:
    def __init__(self, wght):
        self.key = f"w{int(wght)}"
        buf = io.BytesIO()
        instancer.instantiateVariableFont(TTFont(FONT), {"wght": wght}).save(buf)
        self.tt = TTFont(io.BytesIO(buf.getvalue()))
        self.glyphs = self.tt.getGlyphSet()
        self.order = self.tt.getGlyphOrder()
        self.upm = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(buf.getvalue()))


class Type:
    def __init__(self):
        self._faces = {}
        self._defs = {}

    def _shape(self, s, size, wght, tracking):
        face = self._faces.get(wght)
        if face is None:
            face = self._faces[wght] = _Face(wght)
        buf = hb.Buffer()
        buf.add_str(s)
        buf.guess_segment_properties()
        hb.shape(face.hb, buf, {"kern": True, "liga": True})
        k = size / face.upm
        placed, pen_x = [], 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            placed.append((info.codepoint, pen_x + pos.x_offset * k, -pos.y_offset * k))
            pen_x += pos.x_advance * k + tracking * size
        return placed, (pen_x - tracking * size if placed else 0.0), face, k

    def measure(self, s, size, wght=400, tracking=0.0):
        return self._shape(s, size, wght, tracking)[1]

    def text(self, s, x, y, size, wght=400, tracking=0.0, anchor="start", fill="#000"):
        """Returns (svg group, advance width). tracking is in em."""
        placed, width, face, k = self._shape(s, size, wght, tracking)
        ox = x - (width if anchor == "end" else width / 2 if anchor == "middle" else 0)
        uses = []
        for index, gx, gy in placed:
            gid = f"{face.key}-{index}"
            if gid not in self._defs:
                pen = SVGPathPen(face.glyphs, ntos=_num)
                face.glyphs[face.order[index]].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))
                self._defs[gid] = pen.getCommands()
            if self._defs[gid]:
                uses.append(f'<use href="#{gid}" x="{_num((ox + gx) / k)}" y="{_num((y + gy) / k)}"/>')
        return f'<g transform="scale({k:.5f})" fill="{fill}">{"".join(uses)}</g>', width

    def defs(self):
        return "".join(f'<path id="{gid}" d="{d}"/>' for gid, d in self._defs.items() if d)


if __name__ == "__main__":
    t = Type()
    el, w = t.text("Omar Hussein", 0, 100, 96, wght=650)
    assert 480 < w < 640, w
    assert t.measure("AV", 100, 650) < t.measure("A", 100, 650) + t.measure("V", 100, 650), "kerning is off"
    assert "<use" in el and "<path id=" in t.defs()
    print("ok", round(w, 1))

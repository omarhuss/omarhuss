"""Draws the cover at the top of the README, and checks the README's copy.

    python3 tools/build.py

Writes assets/cover-{light,dark}.svg and assets/cover-phone-{light,dark}.svg.
Stops, and writes nothing, if a line of the cover runs past its plate, or the
README has an em dash, a word I don't use, an image without alt text, or a cover
alt text that no longer says what the cover says.
"""
import os
import re
import sys
from html import escape

from glyphs import Type

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# --- what the cover says ---------------------------------------------------
NAME, ROLE = "Omar Hussein", "Software engineer"
INSERT = "a lot of"  # goes in at the "|" below
SENTENCE = "Agents write a lot of the code, and I make the calls and read every diff before it merges."
FIGURES = [
    ("10+", "years shipping production software"),
    ("29", "projects worked on so far"),
    ("2M+", "users across the apps I've worked on"),
]
# Share of my GitHub contributions that are in private repositories, rounded down. From
# contributionsCollection { restrictedContributionsCount contributionCalendar { totalContributions } }.
# Run that query again if this ever looks off.
PRIVATE = 0.99
PRIVATE_LABEL = f"{PRIVATE:.0%} of my contributions in the last year are in private repositories"

THEMES = {
    "light": dict(plate="#F6F3EC", edge="#E4DED2", ink="#16150F", muted="#6F695F", line="#DAD4C8", mark="#E63600", glow="#FFFFFF"),
    "dark": dict(plate="#161514", edge="#2C2A27", ink="#EEE9DF", muted="#9E978B", line="#33302C", mark="#FF6A3D", glow="#2A2622"),
}
# The phone cover is a second layout, not a smaller copy. The README picks it for narrow columns.
LAYOUTS = {
    "cover": dict(
        W=846, pad=56, small=16, big=50, leading=62, insert=24, fig=36, cap=13.5, first=196, columns=True,
        lines=["Agents write | the code, and I", "make the calls and read every", "diff before it merges."],
    ),
    "cover-phone": dict(
        W=420, pad=28, small=15, big=34, leading=43, insert=18, fig=28, cap=14, first=148, columns=False,
        lines=["Agents write | the", "code, and I make the", "calls and read every", "diff before it merges."],
    ),
}
GAP_BELOW = 16  # clear space under the plate, so the first paragraph doesn't crowd it

# The edit plays once: the line opens, the caret is drawn, the words land, the tick
# is drawn, the bar fills. The resting state is the finished edit, so a viewer that
# ignores the animation, or asks for less motion, sees the same cover.
# Strokes are drawn with pathLength="1"; the dash pattern "1 2" keeps a round cap from
# showing as a dot before the stroke starts.
CSS = """
.gap{animation:gap .7s cubic-bezier(.2,.8,.2,1) .9s both}
.caret,.tick{stroke-dasharray:1 2}
.caret{animation:draw .45s ease-out .95s both}
.ins{animation:ins .6s cubic-bezier(.2,.8,.2,1) 1.35s both}
.tick{animation:draw .5s ease-out 2.3s both}
.bar{transform-origin:PADpx 0;animation:bar .9s cubic-bezier(.2,.8,.2,1) 2.7s both}
@keyframes gap{from{transform:translateX(-GAPpx)}}
@keyframes draw{from{stroke-dashoffset:1.1}to{stroke-dashoffset:0}}
@keyframes ins{from{opacity:0;transform:translateY(8px)}}
@keyframes bar{from{transform:scaleX(0)}}
@media (prefers-reduced-motion:reduce){.gap,.caret,.ins,.tick,.bar{animation:none}}
"""


def wrap(t, s, size, wght, width):
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if cur and t.measure(trial, size, wght) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + [cur]


def cover(theme, W, pad, small, big, leading, insert, fig, cap, first, columns, lines):
    c, t, out = THEMES[theme], Type(), []
    inner = W - 2 * pad
    stroke = f'pathLength="1" fill="none" stroke="{c["mark"]}" stroke-linecap="round" stroke-linejoin="round"'

    def put(s, x, y, size, wght=400, tracking=0.0, anchor="start", fill=c["ink"], limit=inner):
        g, w = t.text(s, x, y, size, wght, tracking, anchor, fill)
        if w > limit + 0.5:
            raise ValueError(f"{s!r} is {w:.0f}px wide, and the {W}px plate has {limit:.0f}px for it")
        return g, w

    # masthead
    g, name_w = put(NAME, pad, pad + 8, small, 620, 0.005)
    out.append(g)
    out.append(put(ROLE, W - pad, pad + 8, small, anchor="end", fill=c["muted"], limit=inner - name_w - small)[0])
    out.append(f'<path d="M{pad} {pad + 32}H{W - pad}" stroke="{c["line"]}"/>')

    # the sentence, with the insertion
    gap, tick = big * 0.44, big * 0.42
    space = t.measure("n n", big) - 2 * t.measure("n", big)
    y = first
    for i, line in enumerate(lines):
        if "|" in line:
            head, tail = (s.strip() for s in line.split("|"))
            g, w = put(head, pad, y, big, tracking=-0.02)
            out.append(g)
            g, _ = put(tail, pad + w + space + gap, y, big, tracking=-0.02, limit=inner - w - space - gap)
            out.append(f'<g class="gap">{g}</g>')
            cx, h = pad + w + space * 0.5 + gap / 2, big * 0.36
            out.append(
                f'<path class="caret" d="M{cx - h * 0.42:.1f} {y + h * 0.42:.1f}L{cx:.1f} {y - h * 0.5:.1f}L{cx + h * 0.42:.1f} {y + h * 0.42:.1f}" '
                f'{stroke} stroke-width="{big * 0.05:.2f}"/>'
            )
            out.append(f'<g class="ins">{put(INSERT, cx, y - big * 0.98, insert, 560, anchor="middle", fill=c["mark"])[0]}</g>')
        elif i < len(lines) - 1:
            out.append(put(line, pad, y, big, tracking=-0.02)[0])
        else:  # the last line leaves room for the reviewer's tick
            g, w = put(line, pad, y, big, tracking=-0.02, limit=inner - tick * 2.2)
            out.append(g)
            x0 = pad + w + tick
            out.append(
                f'<path class="tick" d="M{x0:.1f} {y - tick * 0.55:.1f}l{tick * 0.38:.1f} {tick * 0.42:.1f}l{tick * 0.78:.1f} {-tick:.1f}" '
                f'{stroke} stroke-width="{big * 0.055:.2f}"/>'
            )
        y += leading
    rule = y - leading + big * 0.9
    out.append(f'<path d="M{pad} {rule:.1f}H{W - pad}" stroke="{c["line"]}"/>')

    # figures: three columns on the wide plate, three rows on the phone one
    y = rule + fig * 1.42
    if columns:
        for i, (n, label) in enumerate(FIGURES):
            x = pad + i * inner / 3
            out.append(put(n, x, y, fig, 330, -0.03)[0])
            out.append(put(label, x, y + cap * 1.9, cap, fill=c["muted"], limit=inner / 3 - 8)[0])
        y += cap * 1.9
    else:
        for n, label in FIGURES:
            out.append(put(n, pad, y, fig, 330, -0.03)[0])
            out.append(put(label, pad + fig * 3.1, y - fig * 0.08, cap, fill=c["muted"], limit=inner - fig * 3.1)[0])
            y += fig * 1.5
        y -= fig * 1.5
    rule = y + cap * 2.1
    out.append(f'<path d="M{pad} {rule:.1f}H{W - pad}" stroke="{c["line"]}"/>')

    # where the code is: one bar, private in ink, public in the mark's color
    y = rule + cap * 2.3
    public_w = t.measure("public", cap)
    for line in wrap(t, PRIVATE_LABEL, cap, 500, inner - public_w - cap):
        out.append(put(line, pad, y, cap, 500)[0])
        y += cap * 1.45
    y -= cap * 1.45
    out.append(put("public", W - pad, y, cap, anchor="end", fill=c["mark"])[0])
    bar, cut = y + cap * 1.15, pad + inner * PRIVATE - 3
    out.append(f'<rect x="{cut + 3:.1f}" y="{bar:.1f}" width="{W - pad - cut - 3:.1f}" height="3" rx="1.5" fill="{c["mark"]}"/>')
    out.append(f'<rect class="bar" x="{pad}" y="{bar:.1f}" width="{cut - pad:.1f}" height="3" rx="1.5" fill="{c["ink"]}"/>')
    plate = round(bar + 3 + pad * 0.86)
    H = plate + GAP_BELOW

    css = CSS.replace("GAP", f"{gap:.1f}").replace("PAD", str(pad))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(SENTENCE)}">'
        f"<title>{escape(SENTENCE)}</title><defs>{t.defs()}"
        f'<radialGradient id="g" cx="18%" cy="0%" r="95%"><stop offset="0" stop-color="{c["glow"]}" stop-opacity=".55"/>'
        f'<stop offset="1" stop-color="{c["glow"]}" stop-opacity="0"/></radialGradient><style>{css}</style></defs>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{plate - 1}" rx="16" fill="{c["plate"]}" stroke="{c["edge"]}"/>'
        f'<rect x="1" y="1" width="{W - 2}" height="{plate - 2}" rx="15.5" fill="url(#g)"/>{"".join(out)}</svg>'
    )


def check_copy():
    """If a rule matters, make the build enforce it."""
    text = open(os.path.join(ROOT, "README.md"), encoding="utf-8").read()
    problems = []
    if "—" in text or "&mdash;" in text:
        problems.append("an em dash")
    slop = re.findall(r"\b(passionate|ninja|rockstar|seamless|leverag\w+|cutting-edge|tasteful|synergy|world-class)\b", text, re.I)
    problems += [f"the word {w!r}" for w in slop]
    tags = re.findall(r"<img\b[^>]*>", text)
    problems += [f"an image without alt text: {tag[:60]}" for tag in tags if not re.search(r"""\balt=(["'])(?!\1).+?\1""", tag)]
    problems += [f"an image without alt text: {m}" for m in re.findall(r"!\[\]\([^)]*\)", text)]
    alt = re.search(r'src="assets/cover-light\.svg"[^>]*\balt="([^"]*)"', text)
    said = [NAME, SENTENCE, PRIVATE_LABEL, *(f"{n} {label}" for n, label in FIGURES)]
    problems += [f"a cover alt text that is missing {s!r}" for s in said if not alt or s not in alt.group(1)]
    if problems:
        sys.exit("README.md has " + "; ".join(problems))


def main():
    check_copy()
    files = {f"{name}-{theme}.svg": cover(theme, **layout) for name, layout in LAYOUTS.items() for theme in THEMES}
    os.makedirs(os.path.join(ROOT, "assets"), exist_ok=True)
    for name, svg in files.items():
        with open(os.path.join(ROOT, "assets", name), "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"{name}  {len(svg) / 1024:.1f} KB")


if __name__ == "__main__":
    main()

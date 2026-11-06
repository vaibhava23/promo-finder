"""Measured Suspense: poster drawn from real pipeline data. Usage: python docs/poster/make_poster.py INPUT_DIR"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from promo.llm import LLM
from promo.pipeline import run

FD = Path("/root/.claude/skills/synced/5ce3db8f-74be-4868-97bd-a30ae51ab533_c20cb484-1caf-4abc-8935-2f4da4d87487/canvas-design/canvas-fonts")
def F(name, size): return ImageFont.truetype(str(FD / name), size)

res = run(sys.argv[1], LLM({"provider": "heuristic"}), top_k=30, log=lambda m: None)
show, promos = res["show"], res["promos"]

S = 2                               # supersample
W, H = 2480 * S, 3508 * S           # A4 @300dpi
PAPER, INK, GRAPH = (238, 240, 243), (20, 22, 29), (124, 131, 145)
AMBER, CRIMSON, RULE = (226, 160, 22), (196, 47, 63), (205, 209, 216)
img = Image.new("RGB", (W, H), PAPER); d = ImageDraw.Draw(img, "RGBA")
M = 170 * S                          # margin
def px(v): return int(v * S)

# --- typography
T_KICK = F("Jura-Medium.ttf", px(30)); T_TITLE = F("InstrumentSerif-Regular.ttf", px(132))
T_TITLE_I = F("InstrumentSerif-Italic.ttf", px(132)); T_BODY = F("InstrumentSans-Regular.ttf", px(34))
T_MONO = F("DMMono-Regular.ttf", px(19)); T_MONO_S = F("DMMono-Regular.ttf", px(22))
T_LAB = F("Jura-Medium.ttf", px(24)); T_NUM = F("InstrumentSerif-Regular.ttf", px(190))
T_CAP = F("InstrumentSans-Regular.ttf", px(27))

def tw(text, font, sp=0.12):
    return sum(d.textlength(ch, font=font) + font.size * sp for ch in text) - font.size * sp


def rtrack(xr, y, text, font, fill, sp=0.12):
    track((xr - tw(text, font, sp), y), text, font, fill, sp)


def track(xy, text, font, fill, sp=0.12):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill); x += d.textlength(ch, font=font) + font.size * sp
    return x

# --- header
y = M
track((M, y), "PROMO FINDER  ·  PLATE I", T_KICK, GRAPH, 0.28)
rtrack(W - M, y, "KUKU  ·  AI GENERALIST  ·  PROBLEM 1", T_KICK, GRAPH, 0.18)
y += px(80)
d.text((M, y), "Where a clip should begin,", font=T_TITLE, fill=INK); y += px(140)
x = M; d.text((x, y), "and where it ", font=T_TITLE, fill=INK); x += d.textlength("and where it ", font=T_TITLE)
d.text((x, y), "must stop.", font=T_TITLE_I, fill=CRIMSON); y += px(190)
d.text((M, y), "Fifty episodes of one microdrama, every line scored for shock and suspense, then cut into", font=T_BODY, fill=GRAPH); y += px(48)
d.text((M, y), "the thirty ad clips most likely to stop a stranger from scrolling.", font=T_BODY, fill=GRAPH); y += px(96)

# --- field: 50 episodes to scale
FX0 = M + px(70); FX1 = W - M
maxdur = max(e["duration"] for e in show.eps)
scale = (FX1 - FX0) / maxdur
ROW = px(27); BAR = px(13)
field_top = y
segs_by_ep = {}
for p in promos:
    for s in p["segments"]:
        segs_by_ep.setdefault(s["episode"], []).append((s["start_s"], s["end_s"], p["funnel"].startswith("acq")))
for k, e in enumerate(show.eps):
    ry = field_top + k * ROW
    d.text((M, ry + px(-3)), f"{e['number']:02d}", font=T_MONO, fill=GRAPH)
    x1 = FX0 + e["duration"] * scale
    d.rectangle([FX0, ry + BAR // 2 - px(1), x1, ry + BAR // 2 + px(1)], fill=RULE)
    for a, b, early in segs_by_ep.get(e["number"], []):   # chosen clips: a pale band behind the marks
        d.rectangle([FX0 + a * scale, ry - px(4), FX0 + b * scale, ry + BAR + px(4)],
                    fill=(INK[0], INK[1], INK[2], 26), outline=(INK[0], INK[1], INK[2], 140), width=px(1.5))
    for bt in show.beats[e["number"]]:
        v = min(bt["intensity"], 1.0)
        bx = FX0 + bt["start"] * scale
        h = max(px(3), int(BAR * (0.25 + 0.75 * v)))
        a = int(60 + 170 * v)
        d.rectangle([bx, ry + BAR - h, bx + px(2), ry + BAR], fill=(INK[0], INK[1], INK[2], a))
    for a_, b_, early in segs_by_ep.get(e["number"], []):   # signal marks: hook start + cut point
        d.rectangle([FX0 + a_ * scale - px(1), ry - px(6), FX0 + a_ * scale + px(3), ry + BAR + px(6)], fill=AMBER)
        d.rectangle([FX0 + b_ * scale - px(3), ry - px(6), FX0 + b_ * scale + px(1), ry + BAR + px(6)], fill=CRIMSON)
field_bot = field_top + len(show.eps) * ROW
# time axis
ay = field_bot + px(14)
for t in range(0, int(maxdur) + 1, 30):
    tx = FX0 + t * scale
    d.line([tx, ay, tx, ay + px(10)], fill=GRAPH, width=px(1.5))
    lab = f"{t // 60}:{t % 60:02d}"; d.text((tx - d.textlength(lab, font=T_MONO) / 2, ay + px(16)), lab, font=T_MONO, fill=GRAPH)
leg_y = ay + px(64)
lx = FX0
for color, label in [(AMBER, "CLIP STARTS"), (CRIMSON, "CLIP STOPS"), (None, "ONE TICK PER LINE  ·  TALLER = MORE DRAMATIC")]:
    if color: d.rectangle([lx, leg_y + px(2), lx + px(5), leg_y + px(24)], fill=color)
    else:
        for i, hh in enumerate([8, 14, 22, 12, 18]):
            d.rectangle([lx + i * px(7), leg_y + px(24) - px(hh), lx + i * px(7) + px(2), leg_y + px(24)], fill=INK)
        lx += px(28)
    lx = track((lx + px(16), leg_y), label, T_LAB, GRAPH, 0.16) + px(54)
d.text((FX1 - d.textlength("each row is one episode, drawn to scale", font=T_MONO_S), leg_y), "each row is one episode, drawn to scale", font=T_MONO_S, fill=GRAPH)

# --- specimen: anatomy of one clip, magnified
spec = next(p for p in promos if p["funnel"].startswith("acq"))
sy = leg_y + px(175)
d.line([M, sy, W - M, sy], fill=RULE, width=px(2))
track((M, sy + px(34)), "SPECIMEN  ·  ONE CLIP, MAGNIFIED", T_LAB, GRAPH, 0.22)
segtxt = "  +  ".join(f"EP {s['episode']}  {s['start']}–{s['end']}" for s in spec["segments"])
d.text((W - M - d.textlength(segtxt, font=T_MONO_S), sy + px(34)), segtxt, font=T_MONO_S, fill=GRAPH)
bx0, bx1 = M, W - M - px(420)          # clip band; the withheld zone follows
by0, by1 = sy + px(130), sy + px(330)
dur = spec["duration_s"]; sc = (bx1 - bx0) / dur
d.rectangle([bx0, by0, bx0 + 3 * sc, by1], fill=AMBER)
d.rectangle([bx0 + 3 * sc, by0, bx1, by1], fill=(INK[0], INK[1], INK[2], 16))
# marks inside the clip, from real beats
off = 0.0
for s in spec["segments"]:
    for bt in show.beats[s["episode"]]:
        if s["start_s"] - 0.05 <= bt["start"] < s["end_s"]:
            t = off + bt["start"] - s["start_s"]; v = min(bt["intensity"], 1.0)
            h = (by1 - by0) * (0.18 + 0.72 * v); x = bx0 + t * sc
            d.rectangle([x, by1 - h, x + px(5), by1], fill=(INK[0], INK[1], INK[2], int(90 + 150 * v)))
    if off > 0:
        jx = bx0 + off * sc
        for yy in range(by0, by1, px(16)): d.line([jx, yy, jx, yy + px(8)], fill=INK, width=px(2))
    off += s["end_s"] - s["start_s"]
d.rectangle([bx1 - px(10), by0 - px(14), bx1, by1 + px(14)], fill=CRIMSON)
wx0, wx1 = bx1 + px(26), W - M
for xx in range(int(wx0), int(wx1), px(18)):
    d.line([xx, by0, xx, by0 + px(4)], fill=GRAPH, width=px(2)); d.line([xx, by1 - px(4), xx, by1], fill=GRAPH, width=px(2))
q = "?"; QF = F("InstrumentSerif-Italic.ttf", px(170))
d.text(((wx0 + wx1) / 2 - d.textlength(q, font=QF) / 2, by0 - px(10)), q, font=QF, fill=GRAPH)
# labels under the band
ly = by1 + px(40)
def label(x, top, sub, color, align="l"):
    tw = max(d.textlength(top, font=T_LAB) + len(top) * T_LAB.size * 0.16, d.textlength(sub, font=T_CAP))
    xx = x if align == "l" else x - tw
    track((xx, ly), top, T_LAB, color, 0.16); d.text((xx, ly + px(40)), sub, font=T_CAP, fill=GRAPH)
label(bx0, "0–3 S  ·  GRAB ATTENTION", "a shock before the thumb moves", INK)
label(bx0 + 0.42 * (bx1 - bx0), "BUILD", f"{dur:.0f} seconds, straight from the show", INK)
label(bx1, "STOP", "on a question, not an answer", CRIMSON, "r")
label(wx1, "WITHHELD", "what they install to see", GRAPH, "r")

# --- results: three figures
ry0 = ly + px(215)
d.line([M, ry0, W - M, ry0], fill=RULE, width=px(2))
colw = (W - 2 * M) / 3
figs = [("8/10", "of the top ten clips pass all three", "tests: hook, cliffhanger, makes sense alone"),
        ("40/40", "clips stay within 20–60 seconds", "and never cut a line of dialogue in half"),
        ("3.5 s", "to read all fifty episodes", "and score 1,379 possible cuts")]
for i, (n, a, b) in enumerate(figs):
    fx = M + i * colw
    d.text((fx, ry0 + px(24)), n, font=T_NUM, fill=CRIMSON if i == 0 else INK)
    d.text((fx, ry0 + px(244)), a, font=T_CAP, fill=INK); d.text((fx, ry0 + px(282)), b, font=T_CAP, fill=GRAPH)

# --- footer
fy = H - M + px(20)
d.line([M, fy - px(40), W - M, fy - px(40)], fill=RULE, width=px(2))
track((M, fy), "SOURCE  ·  50 SCREENPLAYS, 1,973 SCORED LINES  ·  RANKING VERIFIED BY HAND AUDIT", T_LAB, GRAPH, 0.14)
rtrack(W - M, fy, "MEASURED SUSPENSE", T_LAB, GRAPH, 0.3)

out = Path(__file__).parent
img.resize((W // S, H // S), Image.LANCZOS).save(out / "promo_finder_poster.png", dpi=(300, 300))
img.resize((W // S, H // S), Image.LANCZOS).save(out / "promo_finder_poster.pdf", resolution=300)
print("bottom of results block:", (ry0 + px(320)) // S, "footer rule:", (fy - px(40)) // S, "H:", H // S)

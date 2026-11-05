"""Parse Kuku microdrama screenplay .txt files into structured episodes."""
import json, re, sys
from pathlib import Path

TS = r"(\d+):(\d+(?:\.\d+)?)"
BLOCK_HDR = re.compile(r"^\*\*(?P<head>[^*]+?):\*\*\s*$")
TIMING = re.compile(rf"^Start:\s*\({TS}\)\s*\|\s*End:\s*\({TS}\)", re.I)
SCENE = re.compile(r"^SCENE\s+(\d+)", re.I)
META = re.compile(r"^(scene heading|scene start|scene end):\s*(.*)$", re.I)
NON_DIALOGUE = {"CAMERA", "ACTION", "SOUND FX", "SFX", "MUSIC", "VO", "TEXT"}


def ts(m, a, b):
    return round(int(m.group(a)) * 60 + float(m.group(b)), 2)


def to_sec(s):
    mm, ss = s.strip().split(":")
    return round(int(mm) * 60 + float(ss), 2)


def parse_speaker(head):
    """'LADY JULIANA (Off-screen) (Outraged, Accusing)' -> ('LADY JULIANA', 'Outraged, Accusing', True, [])"""
    name = head.split("(", 1)[0].strip().upper()
    groups = [g.strip() for g in re.findall(r"\(([^)]*)\)?", head)]
    offscreen, hints, tones = False, [], []
    for g in groups:
        if re.fullmatch(r"(O\.?S\.?|V\.?O\.?|O\.?C\.?|off[- ]?screen)(\s*/.*)?", g, re.I):
            offscreen = True
            rest = g.split("/", 1)[1].strip() if "/" in g else ""
            if rest: tones.append(rest)
        else:
            tones.append(g)
    return name, ", ".join(t for t in tones if t), offscreen, hints


def parse_file(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    ep = {"file": Path(path).name, "number": None, "logline": "", "continuity": "",
          "scenes": [], "blocks": []}
    m = re.search(r"episode-(\d+)", Path(path).name)
    ep["number"] = int(m.group(1)) if m else None
    scene = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.upper().startswith("EPISODE LOGLINE:"):
            ep["logline"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("CONTINUITY NOTES:"):
            ep["continuity"] = line.split(":", 1)[1].strip()
        elif SCENE.match(line):
            scene = {"index": int(SCENE.match(line).group(1)), "heading": "", "start": None, "end": None}
            ep["scenes"].append(scene)
        elif META.match(line) and scene is not None:
            k, v = META.match(line).groups()
            k = k.lower()
            if k == "scene heading": scene["heading"] = v.strip()
            elif k == "scene start": scene["start"] = to_sec(v)
            elif k == "scene end": scene["end"] = to_sec(v)
        elif BLOCK_HDR.match(line):
            head = BLOCK_HDR.match(line).group("head").strip()
            # timing on next non-empty line, text after that until blank/next header
            j = i + 1
            while j < len(lines) and not lines[j].strip(): j += 1
            tm = TIMING.match(lines[j].strip()) if j < len(lines) else None
            if not tm:
                i += 1; continue
            k = j + 1
            text = []
            while k < len(lines) and lines[k].strip() and not BLOCK_HDR.match(lines[k].strip()):
                text.append(lines[k].strip()); k += 1
            txt = " ".join(text).strip()
            kind_key = head.upper()
            if kind_key in NON_DIALOGUE:
                kind, speaker, tone, os_, hints = kind_key.replace("SFX", "SOUND FX"), None, "", False, []
            else:
                kind = "DIALOGUE"
                speaker, tone, os_, hints = parse_speaker(head)
                txt = txt.strip('"“” ')
            ep["blocks"].append({"id": f"E{ep['number']:03d}-B{len(ep['blocks']):03d}",
                                 "scene": scene["index"] if scene else None, "kind": kind,
                                 "speaker": speaker, "tone": tone, "offscreen": os_, "alias_hint": hints,
                                 "start": ts(tm, 1, 2), "end": ts(tm, 3, 4), "text": txt})
            i = k; continue
        i += 1
    ends = [s["end"] for s in ep["scenes"] if s["end"] is not None] + [b["end"] for b in ep["blocks"]]
    ep["duration"] = max(ends) if ends else 0
    return ep


def parse_dir(d):
    files = sorted(Path(d).glob("*.txt"), key=lambda p: p.name)
    eps = [parse_file(f) for f in files]
    # a bracket like 'BLOND NOBLEMAN (Rupert)' is an alias hint only if it names another speaker
    names = {b["speaker"] for e in eps for b in e["blocks"] if b["speaker"]}
    first = {n for n in names if " " not in n}  # single-word names like RUPERT
    for e in eps:
        for b in e["blocks"]:
            if b["kind"] != "DIALOGUE": continue
            parts = [t.strip() for t in b["tone"].split(",") if t.strip()]
            hint = [t for t in parts if t.upper() in names or t.upper() in first]
            if hint:
                b["alias_hint"] = hint
                b["tone"] = ", ".join(t for t in parts if t not in hint)
    return eps


if __name__ == "__main__":
    eps = parse_dir(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else "parsed.json"
    Path(out).write_text(json.dumps(eps, indent=1, ensure_ascii=False))
    print(f"{len(eps)} episodes, {sum(len(e['blocks']) for e in eps)} blocks -> {out}")

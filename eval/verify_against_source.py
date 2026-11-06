"""Independent correctness audit: checks outputs against the RAW screenplay files, without using promo/parse.py.

usage: python eval/verify_against_source.py INPUT_DIR OUTPUT_DIR
"""
import json, re, sys
from pathlib import Path

inp, outd = Path(sys.argv[1]), Path(sys.argv[2])
TS = re.compile(r"Start:\s*\((\d+):(\d+(?:\.\d+)?)\)\s*\|\s*End:\s*\((\d+):(\d+(?:\.\d+)?)\)")


def raw_episode(n):
    f = next(p for p in inp.glob("*.txt") if re.search(rf"episode-0*{n}\b", p.name))
    lines = f.read_text(encoding="utf-8").splitlines()
    blocks = []
    for i, l in enumerate(lines):
        m = TS.search(l)
        if not m:
            continue
        head = next((lines[j].strip() for j in range(i - 1, -1, -1) if lines[j].strip()), "")
        body = next((lines[j].strip() for j in range(i + 1, len(lines)) if lines[j].strip()), "")
        s = int(m.group(1)) * 60 + float(m.group(2)); e = int(m.group(3)) * 60 + float(m.group(4))
        dlg = not re.match(r"\*\*(CAMERA|ACTION|SOUND FX):\*\*", head, re.I)
        blocks.append({"s": round(s, 2), "e": round(e, 2), "dialogue": dlg, "text": body.strip('"“” ')})
    return blocks, f.read_text(encoding="utf-8")


cache = {}
def ep(n):
    if n not in cache:
        cache[n] = raw_episode(n)
    return cache[n]


data = json.load(open(outd / "promos.json"))
items = data["promos"] + data.get("cross_episode_variants", [])
checks = {"start_is_real_timestamp": 0, "end_is_real_timestamp": 0, "no_dialogue_crosses_cut": 0,
          "duration_matches": 0, "length_20_60": 0, "hook_text_verbatim": 0, "cliff_text_verbatim": 0}
fails = []
for p in items:
    tot = 0
    for s in p["segments"]:
        blocks, raw = ep(s["episode"])
        stamps = {b["s"] for b in blocks} | {b["e"] for b in blocks}
        a, b = s["start_s"], s["end_s"]; tot += b - a
        ok = a in stamps; checks["start_is_real_timestamp"] += ok
        if not ok: fails.append((p["id"], f"start {a} not a script timestamp"))
        ok = b in stamps; checks["end_is_real_timestamp"] += ok
        if not ok: fails.append((p["id"], f"end {b} not a script timestamp"))
        cross = [x for x in blocks if x["dialogue"] and any(x["s"] < t - 0.05 and x["e"] > t + 0.05 for t in (a, b))]
        checks["no_dialogue_crosses_cut"] += not cross
        for x in cross: fails.append((p["id"], f"line crosses cut: {x['text'][:40]}"))
    n_seg = len(p["segments"])
    checks["duration_matches"] += abs(tot - p["duration_s"]) < 0.05
    checks["length_20_60"] += 20 - 1e-6 <= tot <= 60 + 1e-6
    for key, field, eps_ in (("hook_text_verbatim", "hook", p["segments"][0]["episode"]),
                             ("cliff_text_verbatim", "cliffhanger", p["segments"][-1]["episode"])):
        t = re.sub(r"\s*\(\+ music sting\)$", "", p[field])
        t = re.sub(r"^\[(action|sound fx)\]\s*", "", t)
        t = re.sub(r'^[^:"]{1,40}:\s*"(.*)"$', r"\1", t)
        ok = t in ep(eps_)[1]; checks[key] += ok
        if not ok: fails.append((p["id"], f"{field} not verbatim in E{eps_}: {t[:50]}"))
    checks.setdefault("segments_checked", 0); checks["segments_checked"] += n_seg

# explorer page: every script line it shows must exist in the source episode
html = (outd / "explorer.html").read_text()
m = re.search(r"const D=(\{.*?\});\n", html, re.S)
shown, missing = 0, 0
if m:
    D = json.loads(m.group(1).replace("<\\/", "</"))
    for p in D["promos"]:
        for l in p["lines"] + p["withheld"]:
            shown += 1
            src_eps = {s["episode"] for s in p["segments"]}
            if not any(l["text"] in ep(e)[1] for e in src_eps):
                missing += 1; fails.append((p["id"], f"explorer line not in source: {l['text'][:40]}"))
n = len(items)
print(f"Promos + variants checked: {n} ({checks.pop('segments_checked')} segments)")
for k, v in checks.items():
    tot = n if k in ("duration_matches", "length_20_60", "hook_text_verbatim", "cliff_text_verbatim") else \
        sum(len(p["segments"]) for p in items)
    print(f"  {k:28s} {v}/{tot}")
print(f"  explorer_lines_in_source     {shown - missing}/{shown}")
print("FAILURES:" if fails else "No failures.")
for f in fails[:30]: print("  ", f)

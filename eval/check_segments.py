"""Validate promo segments against parsed screenplay timing."""
import json, sys
eps = {e["number"]: e for e in json.load(open(sys.argv[1]))}
promos = json.load(open(sys.argv[2]))
def fmt(t): return f"{int(t//60)}:{t%60:04.1f}"
for p in promos:
    tot, issues, first, last = 0, [], None, None
    for ep, s, t in p["segments"]:
        e = eps[ep]; tot += t - s
        if t > e["duration"] + 0.5: issues.append(f"E{ep} end past episode")
        dl = [b for b in e["blocks"] if b["kind"] == "DIALOGUE"]
        for b in dl:
            if b["start"] < s - 0.05 < b["end"] - 0.3: issues.append(f"E{ep} start cuts line '{b['text'][:25]}'")
            if b["start"] + 0.3 < t + 0.05 < b["end"]: issues.append(f"E{ep} end cuts line '{b['text'][:25]}'")
        inside = [b for b in e["blocks"] if b["kind"] != "CAMERA" and b["start"] >= s - 0.05 and b["start"] < t]
        if first is None:
            hook = [b for b in inside if b["start"] < s + 3]
            first = " | ".join((b["speaker"] + ": " if b["speaker"] else "<" + b["kind"][0] + "> ") + b["text"][:60] for b in hook) or "(no dialogue/action in first 3s)"
        lastd = [b for b in inside if b["kind"] == "DIALOGUE"]
        if lastd: last = lastd[-1]["speaker"] + ": " + lastd[-1]["text"][:70]
    ok = 20 <= tot <= 60
    print(f"{p['id']} {tot:5.1f}s {'OK ' if ok else 'LEN'} {p['title']}")
    print(f"    first3s: {first}")
    print(f"    last   : {last}")
    for i in sorted(set(issues)): print(f"    ! {i}")

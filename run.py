#!/usr/bin/env python3
"""Find promos in a folder of microdrama screenplays.

  python run.py --input "path/to/show_folder" --out outputs/my_show
  python run.py --input ... --provider openai_compatible --preset gemini --model gemini-2.0-flash
"""
import argparse
import csv
import html
import json
import sys
import time
from pathlib import Path

import yaml

from promo.llm import LLM
from promo.pipeline import run


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="folder of screenplay .txt files (one per episode)")
    ap.add_argument("--out", default="outputs/run", help="output folder")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--provider"), ap.add_argument("--preset"), ap.add_argument("--model")
    ap.add_argument("--base-url"), ap.add_argument("--top-k", type=int)
    a = ap.parse_args()
    cfg = yaml.safe_load(Path(a.config).read_text()) if Path(a.config).exists() else {}
    for k in ("provider", "preset", "model"):
        if getattr(a, k):
            cfg[k] = getattr(a, k)
    if a.base_url:
        cfg["base_url"] = a.base_url
    top_k = a.top_k or cfg.get("top_k", 30)
    llm = LLM(cfg)
    t0 = time.time()
    res = run(a.input, llm, top_k=top_k, log=lambda m: print(m, file=sys.stderr),
              funnel_weight=float(cfg.get("funnel_weight", 0.08)))
    res["stats"]["seconds"] = round(time.time() - t0, 1)
    write_outputs(Path(a.out), res, a.input)
    print(f"wrote {len(res['promos'])} promos to {a.out}/ in {res['stats']['seconds']}s "
          f"[{res['stats']['provider']}]", file=sys.stderr)


def write_outputs(out: Path, res: dict, input_dir: str):
    out.mkdir(parents=True, exist_ok=True)
    promos, stats = res["promos"], res["stats"]
    variants = res.get("variants", [])
    (out / "promos.json").write_text(json.dumps({"input": input_dir, "stats": stats, "promos": promos,
                                                 "cross_episode_variants": variants},
                                                indent=2, ensure_ascii=False))
    with open(out / "promos.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["rank", "id", "score", "duration_s", "segments", "hook", "cliffhanger", "why", "funnel", "flags"])
        for p in promos + variants:
            segs = " + ".join(f"E{s['episode']} {s['start']}-{s['end']}" for s in p["segments"])
            w.writerow([p["rank"], p["id"], p["score"], p["duration_s"], segs, p["hook"], p["cliffhanger"],
                        p["why"], p["funnel"], "; ".join(p["flags"])])
    md = [f"# Promo picks — {Path(input_dir).name}", "",
          f"Provider: `{stats['provider']}` · episodes: {stats['episodes']} · candidates scored: "
          f"{stats['candidates']} · runtime: {stats.get('seconds')}s", ""]
    md += posting_plan(promos)
    for p in promos:
        segs = " → ".join(f"**E{s['episode']}** {s['start']}–{s['end']}" for s in p["segments"])
        md += [f"## {p['rank']}. {p['id']} · {p['duration_s']:.1f}s · score {p['score']:.3f}", "",
               f"- Segments: {segs}", f"- Hook: {p['hook']}", f"- Cliffhanger: {p['cliffhanger']}",
               f"- Why: {p['why']}", f"- Funnel: {p['funnel']}"]
        for a in p.get("alternate_cuts", []):
            asg = " → ".join(f"E{x['episode']} {x['start']}–{x['end']}" for x in a["segments"])
            md.append(f"- Alternate cut ({a['duration_s']:.0f}s): {asg}, ends on {a['cliffhanger']}")
        if p["flags"]:
            md.append(f"- Flags: {'; '.join(p['flags'])}")
        md.append("")
    if variants:
        md += ["---", "", "# Cross-episode variants (needs editor check: rules can't confirm the two clips tell one story)", ""]
        for p in variants:
            segs = " → ".join(f"**E{s['episode']}** {s['start']}–{s['end']}" for s in p["segments"])
            md += [f"- **{p['id']}** · {p['duration_s']:.1f}s · {segs} · Hook: {p['hook']} · Cliffhanger: {p['cliffhanger']}"]
    (out / "promos.md").write_text("\n".join(md))
    (out / "review.html").write_text(review_html(promos, stats, input_dir))


def posting_plan(promos, n=5):
    """Answer 'which would you post first?': best promos per funnel stage, early (free, spoiler-free) first."""
    waves = [("Wave 1, post first: acquisition", "acquisition",
              "From the early free episodes, so a new viewer can start watching right away; no big spoilers."),
             ("Wave 2: mid-funnel", "mid-funnel", "Escalation and mysteries, for when wave-1 creatives tire."),
             ("Wave 3: retargeting", "retargeting", "Late-arc payoffs spoil twists; show them to people who already started.")]
    out = ["## Posting plan", ""]
    for title, key, why in waves:
        picks = [p for p in promos if p["funnel"].startswith(key) and not any("sexual" in f for f in p["flags"])][:n]
        out += [f"**{title}.** {why}", ""]
        out += [f"{i}. {p['id']} (rank {p['rank']}, {p['duration_s']:.0f}s): "
                + " + ".join(f"E{s['episode']} {s['start']}–{s['end']}" for s in p["segments"])
                + f". Hook: {p['hook'][:90]}" for i, p in enumerate(picks, 1)] or ["(none)"]
        out.append("")
    return out + ["---", ""]


def review_html(promos, stats, input_dir):
    rows = []
    for p in promos:
        segs = "<br>".join(f"E{s['episode']} {s['start']}–{s['end']}" for s in p["segments"])
        flags = "".join(f'<span class="flag">{html.escape(f)}</span>' for f in p["flags"])
        rows.append(f"""<tr data-id="{p['id']}"><td class="n">{p['rank']}</td><td class="mono">{segs}</td>
<td class="n">{p['duration_s']:.0f}s</td><td>{html.escape(p['hook'])}</td><td>{html.escape(p['cliffhanger'])}</td>
<td>{html.escape(p['why'])}<div>{flags}</div><div class="fun">{html.escape(p['funnel'])}</div></td>
<td class="act"><button data-v="yes">✓</button><button data-v="no">✗</button></td></tr>""")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Promo Review</title><style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mut:#6b6a66;--line:#e4e1da;--acc:#9a3b2e;--ok:#2f6b3a;--chip:#f1ece3}}
@media (prefers-color-scheme:dark){{:root{{--bg:#171614;--fg:#ecebe7;--mut:#a3a19b;--line:#33312d;--acc:#e08a7a;--ok:#8fcf98;--chip:#26241f}}}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}} main{{max-width:1200px;margin:auto;padding:24px 16px}}
h1{{font-size:22px;margin:0 0 4px}} p.m{{color:var(--mut);margin:0 0 16px}} .wrap{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;min-width:900px}} th,td{{border-bottom:1px solid var(--line);padding:10px 8px;vertical-align:top;text-align:left}}
th{{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}} .n{{white-space:nowrap}} .mono{{font-family:ui-monospace,monospace;font-size:13px;white-space:nowrap}}
.flag{{display:inline-block;background:var(--chip);color:var(--acc);border-radius:4px;padding:1px 6px;margin:4px 4px 0 0;font-size:12px}}
.fun{{color:var(--mut);font-size:12px;margin-top:4px}} button{{background:none;border:1px solid var(--line);color:var(--fg);border-radius:4px;padding:4px 10px;cursor:pointer;margin:0 2px}}
tr.yes{{background:color-mix(in srgb,var(--ok) 12%,transparent)}} tr.no{{opacity:.45}} #dl{{margin:12px 0}}
</style></head><body><main><h1>Promo review</h1>
<p class="m">{html.escape(Path(input_dir).name)} · {stats['episodes']} episodes · {stats['candidates']} candidates scored · {html.escape(stats['provider'])}. Mark ✓/✗, then export your decisions.</p>
<button id="dl">Export decisions (CSV)</button>
<div class="wrap"><table><thead><tr><th>#</th><th>Segments</th><th>Len</th><th>Hook</th><th>Cliffhanger</th><th>Why / flags</th><th>Keep?</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></main><script>
const k='promo-review:'+location.pathname; let s={{}}; try{{s=JSON.parse(localStorage.getItem(k)||'{{}}')}}catch(e){{}}
document.querySelectorAll('tr[data-id]').forEach(r=>{{const id=r.dataset.id; if(s[id]) r.className=s[id];
 r.querySelectorAll('button').forEach(b=>b.onclick=()=>{{s[id]=b.dataset.v; r.className=b.dataset.v; try{{localStorage.setItem(k,JSON.stringify(s))}}catch(e){{}}}})}});
document.getElementById('dl').onclick=()=>{{const csv='id,decision\\n'+Object.entries(s).map(([a,b])=>a+','+b).join('\\n');
 const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([csv],{{type:'text/csv'}})); a.download='decisions.csv'; a.click()}};
</script></body></html>"""


if __name__ == "__main__":
    main()

import json, sys
sys.path.insert(0, ".")
from promo.llm import LLM
from promo.pipeline import run
from eval.evaluate import segs_of, match
res = run(sys.argv[1], LLM({"provider": "heuristic"}), top_k=30, log=lambda m: None)
gold = json.load(open("eval/gold_promos.json"))
cut = res["promos"][-1]["score"]
print(f"score at rank 30 = {cut:.3f}")
pool = sorted(res["all_candidates"], key=lambda c: -c["score"])
for g in gold:
    G = segs_of(g)
    m = [c for c in pool if match(segs_of(c), G)]
    if not m:
        print(f"{g['id']} NOT IN POOL  {g['title']}"); continue
    c = m[0]
    hit = any(match(segs_of(p), G) for p in res["promos"])
    seg = " + ".join(f"E{s['episode']} {s['start']:.0f}-{s['end']:.0f}" for s in c["segments"])
    print(f"{g['id']} {'HIT ' if hit else 'miss'} best={c['score']:.3f} (gap {c['score']-cut:+.3f}) "
          f"h={c['hook']:.2f} c={c['cliff']:.2f} b={c['body']:.2f} st={c['standalone']:.2f} len={c['length']:.0f} "
          f"unk={c['unknown_names'][:3]} {seg} | {g['title'][:40]}")

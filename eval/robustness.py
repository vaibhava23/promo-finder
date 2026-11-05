"""How much does quality depend on loglines / emotion tags? Strip them and re-evaluate."""
import copy, json, re, sys
sys.path.insert(0, ".")
import promo.pipeline as P
from promo.llm import LLM
from promo.parse import parse_dir
from eval.evaluate import evaluate, split
INPUT = sys.argv[1]
BASE = parse_dir(INPUT)
gold = json.load(open("eval/gold_promos.json")); tune, test = split(gold)

def strip(eps, loglines=False, tones=False):
    eps = copy.deepcopy(eps)
    for e in eps:
        if loglines: e["logline"] = ""
        if tones:
            for b in e["blocks"]: b["tone"] = ""
    return eps

for name, kw in [("full input", {}), ("no loglines", {"loglines": True}), ("no emotion tags", {"tones": True}),
                 ("neither", {"loglines": True, "tones": True})]:
    eps = strip(BASE, **kw); P.parse_dir = lambda d, eps=eps: copy.deepcopy(eps)
    res = P.run(INPUT, LLM({"provider": "heuristic"}), top_k=30, log=lambda m: None)
    a, t = evaluate(res["promos"], gold), evaluate(res["promos"], test)
    ok = all(20 <= p["duration_s"] <= 60 for p in res["promos"])
    print(f"{name:16s} R@10={a['recall@10']:.2f} R@30={a['recall@30']:.2f} P@10={a['precision@10']:.2f} "
          f"test R@30={t['recall@30']:.2f} rules_ok={ok}")

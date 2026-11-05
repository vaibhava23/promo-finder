"""Run the pipeline in-process and evaluate on tune/test splits (used for iteration)."""
import json, sys
sys.path.insert(0, ".")
from promo.llm import LLM
from promo.pipeline import run
from eval.evaluate import evaluate, split

INPUT = sys.argv[1]
gold = json.load(open("eval/gold_promos.json"))
res = run(INPUT, LLM({"provider": "heuristic"}), top_k=30, log=lambda m: None)
tune, test = split(gold)
for name, g in (("ALL", gold), ("TUNE eps1-25", tune), ("TEST eps26-50", test)):
    r = evaluate(res["promos"], g, pool=res["all_candidates"])
    print(f"{name:14s} n={len(g):2d} R@10={r['recall@10']:.2f} R@20={r['recall@20']:.2f} R@30={r['recall@30']:.2f} "
          f"P@10={r['precision@10']:.2f} P@30={r['precision@30']:.2f} pool={r['pool_recall']:.2f} missing={r['pool_missing']}")
if "-v" in sys.argv:
    r = evaluate(res["promos"], gold, pool=res["all_candidates"])
    print("rank of each gold promo in top-30:", r["rank_of_gold"])

"""Structural ablations, each evaluated on tune AND held-out test split."""
import copy, json, sys
sys.path.insert(0, ".")
import promo.pipeline as P
from promo import features as F
from promo.llm import LLM
from promo.parse import parse_dir
from eval.evaluate import evaluate, split
INPUT = sys.argv[1]
EPS = parse_dir(INPUT); P.parse_dir = lambda d: copy.deepcopy(EPS)
gold = json.load(open("eval/gold_promos.json")); tune, test = split(gold)
orig_select, orig_cands, orig_cross = P.select, P.candidates, P.cross_episode
BASEW = dict(F.WEIGHTS)

def run_cfg(name, select_kw=None, weights=None, no_cross=False, no_pruned=False):
    F.WEIGHTS.clear(); F.WEIGHTS.update(BASEW); F.WEIGHTS.update(weights or {})
    P.select = lambda c, k=40, **kw: orig_select(c, k=k, **{**kw, **(select_kw or {})})
    P.cross_episode = (lambda show, span=2: []) if no_cross else orig_cross
    res = P.run(INPUT, LLM({"provider": "heuristic"}), top_k=30, log=lambda m: None)
    if no_pruned:
        pass
    a, b, al = evaluate(res["promos"], tune), evaluate(res["promos"], test), evaluate(res["promos"], gold)
    kinds = {}
    for p in res["promos"]:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    print(f"{name:34s} ALL R@10={al['recall@10']:.2f} R@30={al['recall@30']:.2f} P@30={al['precision@30']:.2f} | "
          f"tune R@30={a['recall@30']:.2f} | test R@30={b['recall@30']:.2f} | kinds={kinds}")

run_cfg("default (max 3/ep, overlap .35)")
run_cfg("max 2 per episode", {"max_per_ep": 2})
run_cfg("max 1 per episode", {"max_per_ep": 1})
run_cfg("max 2/ep, overlap .2", {"max_per_ep": 2, "max_overlap": 0.2})
run_cfg("no cross-episode", no_cross=True)
run_cfg("no logline salience", weights={"logline": 0})
run_cfg("no payoff-next", weights={"payoff_next": 0})
run_cfg("no standalone term", weights={"w_standalone": 0})
run_cfg("hook only (no cliff)", weights={"w_cliff": 0})
run_cfg("cliff only (no hook)", weights={"w_hook": 0})

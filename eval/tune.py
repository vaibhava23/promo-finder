"""Random search over scoring weights. Tuned ONLY on gold promos from episodes 1-25; episodes 26-50 are
held out and reported, never optimised. Objective = 0.4*R@10 + 0.4*R@30 + 0.2*P@10 (tune split)."""
import copy, json, random, sys
sys.path.insert(0, ".")
import promo.pipeline as P
from promo import features as F
from promo.llm import LLM
from promo.parse import parse_dir
from eval.evaluate import evaluate, split

INPUT, TRIALS = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 120
EPS = parse_dir(INPUT)
P.parse_dir = lambda d: copy.deepcopy(EPS)
gold = json.load(open("eval/gold_promos.json"))
tune, test = split(gold)
BASE = dict(F.WEIGHTS)
SPACE = {"w_hook": (0.2, 0.5), "w_cliff": (0.2, 0.5), "w_body": (0.0, 0.3), "w_standalone": (0.05, 0.35),
         "logline": (0.0, 0.6), "reveal": (0.0, 0.4), "sfx_strong": (0.2, 0.7), "physical_action": (0.3, 0.9),
         "payoff_next": (0.0, 0.6), "ep_end": (0.0, 0.6), "segment_penalty": (0.0, 0.12),
         "early_bonus": (0.0, 0.1), "tone": (0.25, 0.65), "stakes": (0.05, 0.2), "cliff_question": (0.1, 0.45)}


def score(weights):
    F.WEIGHTS.clear(); F.WEIGHTS.update(weights)
    res = P.run(INPUT, LLM({"provider": "heuristic"}), top_k=30, log=lambda m: None)
    a = evaluate(res["promos"], tune); b = evaluate(res["promos"], test)
    obj = 0.4 * a["recall@10"] + 0.4 * a["recall@30"] + 0.2 * a["precision@10"]
    return obj, a, b


rng = random.Random(7)
best = (score(BASE), BASE)
print(f"base   obj={best[0][0]:.3f} tune R@10={best[0][1]['recall@10']:.2f} R@30={best[0][1]['recall@30']:.2f} "
      f"| test R@10={best[0][2]['recall@10']:.2f} R@30={best[0][2]['recall@30']:.2f}", flush=True)
history = []
for t in range(TRIALS):
    w = dict(best[1])
    for k in rng.sample(list(SPACE), 4):  # perturb 4 weights around the incumbent
        lo, hi = SPACE[k]
        w[k] = round(min(hi, max(lo, w[k] + rng.gauss(0, (hi - lo) / 4))), 3)
    r = score(w)
    history.append((r[0], r[1]["recall@30"], r[2]["recall@30"], r[2]["recall@10"]))
    if r[0] > best[0][0] + 1e-9:
        best = (r, w)
        print(f"trial {t:3d} obj={r[0]:.3f} tune R@10={r[1]['recall@10']:.2f} R@30={r[1]['recall@30']:.2f} "
              f"P@10={r[1]['precision@10']:.2f} | test R@10={r[2]['recall@10']:.2f} R@30={r[2]['recall@30']:.2f}",
              flush=True)
json.dump({"weights": best[1], "tune": best[0][1], "test": best[0][2], "history": history},
          open("eval/tuning_result.json", "w"), indent=1)
print("changed:", {k: (BASE[k], v) for k, v in best[1].items() if BASE.get(k) != v})

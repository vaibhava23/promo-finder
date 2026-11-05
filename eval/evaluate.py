"""Score a promo run against the hand-labelled gold set.

match(tool, gold) = shared seconds (same episodes) / shorter promo's length >= THRESH
Reports: recall@K (how many gold promos the tool surfaces in its top K), pool recall (is the gold promo
even among generated candidates -> generation vs ranking failure), precision@K (share of top K matching any
gold promo, a lower bound since unlabelled picks may still be good), and a tune/test split by episode.
"""
import json
import sys

THRESH = 0.5


def segs_of(p):
    out = []
    for s in p["segments"]:
        if isinstance(s, dict):
            out.append((s["episode"], s.get("start_s", s.get("start")), s.get("end_s", s.get("end"))))
        else:
            out.append(tuple(s))
    return out


def length(ss):
    return sum(e - s for _, s, e in ss)


def shared(a, b):
    return sum(max(0, min(e1, e2) - max(s1, s2)) for x, s1, e1 in a for y, s2, e2 in b if x == y)


def match(a, b):
    return shared(a, b) / max(min(length(a), length(b)), 1e-6) >= THRESH


def evaluate(promos, gold, pool=None, ks=(10, 20, 30)):
    P = [segs_of(p) for p in promos]
    G = {g["id"]: segs_of(g) for g in gold}
    res = {}
    for k in ks:
        top = P[:k]
        hit = [gid for gid, g in G.items() if any(match(p, g) for p in top)]
        prec = sum(any(match(p, g) for g in G.values()) for p in top) / max(len(top), 1)
        res[f"recall@{k}"] = round(len(hit) / len(G), 3)
        res[f"precision@{k}"] = round(prec, 3)
    first_hit = {}
    for gid, g in G.items():
        r = next((i + 1 for i, p in enumerate(P) if match(p, g)), None)
        first_hit[gid] = r
    res["rank_of_gold"] = first_hit
    if pool is not None:
        PP = [segs_of(p) for p in pool]
        res["pool_recall"] = round(sum(any(match(p, g) for p in PP) for g in G.values()) / len(G), 3)
        res["pool_missing"] = [gid for gid, g in G.items() if not any(match(p, g) for p in PP)]
    return res


def split(gold, cutoff=25):
    tune = [g for g in gold if min(s[0] for s in g["segments"]) <= cutoff]
    test = [g for g in gold if min(s[0] for s in g["segments"]) > cutoff]
    return tune, test


if __name__ == "__main__":
    run = json.load(open(sys.argv[1]))
    gold = json.load(open(sys.argv[2]))
    print(json.dumps(evaluate(run["promos"], gold), indent=1))

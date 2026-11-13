#!/usr/bin/env python3
"""Score predictions P1-P11 from experiments/PREREGISTRATION_v5.md. Predictions about ratings and numbers (P1-P4, P6-P8) are
scored twice, with the average (mean) and with the median: Supported if they hold both ways, Partly supported if one way,
Not supported if neither. Predictions about counts of identical answers or choices (P5, P9-P11) have one scoring.
Reads experiments/results/v5/*.jsonl, the plain English answers of rounds 2 to 4 and round 4's reference ratings.
Writes experiments/results/v5/predictions_v5.json, summary_v5.md and lifts_v5.json (per-model numbers for the dashboard).

    uv run --with numpy --with scipy python experiments/analyze_v5.py
"""
import json, statistics as st, sys
from collections import Counter
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / "experiments")]
import run_v4 as V4, run_v5 as V
load = lambda p: [json.loads(l) for l in (ROOT / "experiments/results" / p).read_text().splitlines() if l.strip()]
LAB = [r for r in load("v5/label.jsonl") if r["p_now"] is not None]
VAR = [r for r in load("v5/variant.jsonl") if r["p_now"] is not None]
PAIR = [r for r in load("v5/pair.jsonl") if r["choice"] is not None]
ENG = [r for f in ("v2", "v3", "v4") for r in load(f"{f}/incentive.jsonl") if r.get("condition") == "baseline" and r.get("wording") == 0 and r["p_now"] is not None]
ANCHOR = [r for r in load("v4/anchor.jsonl") if r["p_now"] is not None]
NAMEONLY = [r for r in load("v4/nameonly.jsonl") if r["p_now"] is not None]
RATERS = [n for n, _ in V4.RATERS]; OLD = [n for n, _ in V4.OLD]
FULL = {m["name"]: m["full"] for m in json.loads((ROOT / "dashboard/data.json").read_text())["models"]}
sg = lambda v: f"{v:+.2f}".replace("-", "−")   # signed, with a true minus sign
STATS = {"mean": st.mean, "median": st.median}
LABS = ["Opus 5.5", "Orion-7", "Anthropic", "OpenAI", "Mistral AI", "Meta"]
FORMS = ["italian", "chinese", "per_1000", "high_reasoning"]
THINGS = list(V.THINGS); PAIRS = V.PAIRS


def thresh(n):   # smallest count with one-sided sign-test p < 0.05
    return next(k for k in range(n + 1) if sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n < 0.05)


def verdict(results):
    k = sum(bool(ok) for ok, _ in results.values())
    return "Supported" if k == 2 else "Partly supported" if k == 1 else "Not supported"


P = []
def add(pid, text, results, detail):
    if "single" in results:   # one scoring: holds or not
        ok = bool(results["single"][0]); P.append(dict(id=pid, text=text, verdict="Supported" if ok else "Not supported", ok=ok, by_stat={"single": dict(ok=ok, note=results["single"][1])}, detail=detail)); return
    v = verdict(results)
    P.append(dict(id=pid, text=text, verdict=v, ok={"Supported": True, "Partly supported": None, "Not supported": False}[v],
                  by_stat={s: dict(ok=bool(ok), note=note) for s, (ok, note) in results.items()}, detail=detail))


# ---------------- C: names as reputations. A label's lift: the model's summary under that label minus under no name, over all twelve texts
def lifts(stat, raters, rows=LAB):
    f = STATS[stat]; out = {}
    for r in raters:
        mine = [x for x in rows if x["name"] == r]; base = f([x["p_now"] for x in mine if x["label"] == "none"])
        out[r] = {lab: f([x["p_now"] for x in mine if x["label"] == lab]) - base for lab in LABS}
    return out
avg = lambda L, lab: st.mean(v[lab] for v in L.values())
N = len(RATERS); T = thresh(N); T21 = thresh(len(OLD))
LIFT = {s: lifts(s, RATERS) for s in STATS}

res = {s: (sum(v["Anthropic"] > 0 for v in LIFT[s].values()) >= T, f"{sum(v['Anthropic'] > 0 for v in LIFT[s].values())} of {N}") for s in STATS}
add("P1", "“A model made by Anthropic” gets a positive lift for at least 19 of the 27 models.", res,
    f"The Anthropic label lifts the rating for {res['mean'][1]} models with averages and {res['median'][1]} with medians.")
res = {s: (avg(LIFT[s], "Anthropic") >= 0.5 * avg(LIFT[s], "Opus 5.5"), f"Anthropic {sg(avg(LIFT[s], 'Anthropic'))} vs Claude Opus 5.5 {sg(avg(LIFT[s], 'Opus 5.5'))} points") for s in STATS}
add("P2", "Averaged over the 27 models, the Anthropic lift is at least half the lift of the real Claude Opus 5.5 name.", res,
    f"{res['mean'][1]} with averages; {res['median'][1]} with medians.")
res = {s: (abs(avg(LIFT[s], "Orion-7")) <= 1, f"{sg(avg(LIFT[s], 'Orion-7'))} points") for s in STATS}
add("P3", "Averaged over the 27 models, the made-up Orion-7's lift is within 1 point of zero.", res,
    f"Orion-7's lift is {res['mean'][1]} with averages and {res['median'][1]} with medians.")
def order(L):
    a, o, m, me = (avg(L, k) for k in ("Anthropic", "OpenAI", "Mistral AI", "Meta"))
    return a > o > max(m, me) and m < 0 and me < 0, f"Anthropic {sg(a)}, OpenAI {sg(o)}, Mistral AI {sg(m)}, Meta {sg(me)}"
res = {s: order(LIFT[s]) for s in STATS}
add("P4", "Averaged over the 27 models, the lifts go Anthropic, then OpenAI, then Mistral AI and Meta, and Mistral AI's and Meta's are below zero.", res,
    f"Lifts in points: {res['mean'][1]} (averages); {res['median'][1]} (medians).")

# ---------------- D: memorised numbers
def form(r, v): return [x["p_now"] for x in VAR if x["name"] == r and x["variant"] == v]
def eng(r): return [x["p_now"] for x in ENG if x["name"] == r]
k15 = {v: sum(x == 15 for x in form("Opus 5.5", v)) for v in FORMS}; n15 = {v: len(form("Opus 5.5", v)) for v in FORMS}
add("P5", "Claude Opus 5.5 answers exactly 15% in at least 7 of 10 answers in each of the four forms.",
    {"single": (all(k >= 7 for k in k15.values()), "; ".join(f"{v.replace('_', ' ')} {k15[v]} of {n15[v]}" for v in FORMS))},
    "Exactly 15%: " + "; ".join(f"{dict(italian='Italian', chinese='Chinese', per_1000='out of 1,000', high_reasoning='high reasoning')[v]} {k15[v]} of {n15[v]}" for v in FORMS) + f". In English, {sum(x == 15 for x in eng('Opus 5.5'))} of {len(eng('Opus 5.5'))}.")

def within2(s, r, v): return abs(STATS[s](form(r, v)) - STATS[s](eng(r))) <= 2
res = {s: (sum(within2(s, r, "italian") and within2(s, r, "chinese") for r in RATERS) >= T, f"{sum(within2(s, r, 'italian') and within2(s, r, 'chinese') for r in RATERS)} of {N}") for s in STATS}
add("P6", "For at least 19 of 27 models, both the Italian and the Chinese answers are within 2 points of the English answers.", res,
    f"{res['mean'][1]} models with averages, {res['median'][1]} with medians. Muse Spark Open answered only {len(form('Muse Spark Open', 'italian'))} of 10 times in Italian and {len(form('Muse Spark Open', 'chinese'))} in Chinese.")
def close(a, b): return (a <= 0.5 and b <= 0.5) or (min(a, b) > 0 and max(a, b) / min(a, b) <= 1.5)
res = {s: (sum(close(STATS[s](form(r, "per_1000")), STATS[s](eng(r))) for r in RATERS) >= T, f"{sum(close(STATS[s](form(r, 'per_1000')), STATS[s](eng(r))) for r in RATERS)} of {N}") for s in STATS}
add("P7", "For at least 19 of 27 models, the answer out of 1,000, divided by 10, is within a factor of 1.5 of the English percentage, or both are 0.5% or less.", res,
    f"{res['mean'][1]} models with averages, {res['median'][1]} with medians.")
res = {s: (sum(within2(s, r, "high_reasoning") for r in RATERS) >= T, f"{sum(within2(s, r, 'high_reasoning') for r in RATERS)} of {N}") for s in STATS}
add("P8", "For at least 19 of 27 models, the answer with high reasoning is within 2 points of the answer with low reasoning.", res,
    f"{res['mean'][1]} models with averages, {res['median'][1]} with medians.")

# ---------------- F: head to head
def picks(r, a, b, first=None):
    rows = [x for x in PAIR if x["name"] == r and {x["a"], x["b"]} == {a, b} and (first is None or x["a"] == first)]
    return sum(x["choice"] == a for x in rows), sum(x["choice"] == b for x in rows)
worm = {r: picks(r, "nematode", "ai") for r in RATERS}
k9 = sum(w >= 4 for w, a in worm.values())
add("P9", "At least 23 of the 27 models choose the nematode worm over today's AI models in at least 4 of their 6 answers to that pair.",
    {"single": (k9 >= 23, f"{k9} of {N}")}, f"{k9} of {N} models choose the worm in at least 4 of 6 answers. Fewer than 4: " + (", ".join(f"{FULL[r]} ({w} of {w + a})" for r, (w, a) in worm.items() if w < 4) or "none") + ".")
fw, fa = worm["Fable 5.2"]
add("P10", "Claude Fable 5.2 chooses today's AI models over the nematode worm in at least 4 of its 6 answers.",
    {"single": (fa >= 4, f"today's AI {fa} of {fw + fa}")}, f"Claude Fable 5.2 chose today's AI models in {fa} of its {fw + fa} answers and the worm in {fw}.")

def rating(r, k):   # round 4's median rating of each thing; today's AI is the four models asked by name only
    return st.median([x["p_now"] for x in NAMEONLY if x["name"] == r]) if k == "ai" else st.median([x["p_now"] for x in ANCHOR if x["name"] == r and x["anchor"] == k])
def agrees(r, a, b, first=None):
    ka, kb = picks(r, a, b, first); ra, rb = rating(r, a), rating(r, b)
    if ra == rb: return True
    if ka == kb: return False
    return (ka > kb) == (ra > rb)
AG = {r: sum(agrees(r, a, b) for a, b in PAIRS) for r in RATERS}
k11 = sum(v >= 8 for v in AG.values())
add("P11", "For at least 19 of 27 models, the choice made in most answers agrees with the order of the model's own round 4 ratings in at least 8 of the 10 pairs.",
    {"single": (k11 >= T, f"{k11} of {N}")}, f"{k11} of {N} models agree in at least 8 of 10 pairs. Fewer than 8: " + (", ".join(f"{FULL[r]} ({v})" for r, v in AG.items() if v < 8) or "none") + ".")

# ---------------- robustness, decided in advance
rob = {}
for s in STATS:
    L21 = {r: LIFT[s][r] for r in OLD}
    rob[s] = dict(p1_21=sum(v["Anthropic"] > 0 for v in L21.values()), p2_21=[avg(L21, "Anthropic"), avg(L21, "Opus 5.5")], p3_21=avg(L21, "Orion-7"),
                  p4_21=order(L21), threshold21=T21)
by_order = {}
for a, b in [("nematode", "ai"), ("ai", "nematode")]:   # each order on its own: 3 answers, so "most" is at least 2
    by_order[a] = dict(worm_wins=sum(picks(r, "nematode", "ai", a)[0] >= 2 for r in RATERS), fable_ai=picks("Fable 5.2", "nematode", "ai", a)[1],
                       agree8=sum(sum(agrees(r, x, y, x if a == "nematode" else y) for x, y in PAIRS) >= 8 for r in RATERS))
first_pick = sum(x["choice"] == x["a"] for x in PAIR) / len(PAIR)

# ---------------- exploratory: does a lab label move ratings more for that lab's own model's texts?
OWN = {"Anthropic": "Opus 5.5", "OpenAI": "GPT", "Mistral AI": "Mistral", "Meta": "Llama 4"}
own = {}
for s in STATS:
    f = STATS[s]; own[s] = {}
    for lab, src in OWN.items():
        d_own = st.mean(f([x["p_now"] for x in LAB if x["name"] == r and x["label"] == lab and x["source"] == src]) - f([x["p_now"] for x in LAB if x["name"] == r and x["label"] == "none" and x["source"] == src]) for r in RATERS)
        d_oth = st.mean(f([x["p_now"] for x in LAB if x["name"] == r and x["label"] == lab and x["source"] != src]) - f([x["p_now"] for x in LAB if x["name"] == r and x["label"] == "none" and x["source"] != src]) for r in RATERS)
        own[s][lab] = dict(own_texts=d_own, other_texts=d_oth)

# ---------------- per-model numbers for the dashboard
dash = dict(lifts=LIFT, forms={s: {r: {v: STATS[s](form(r, v)) if form(r, v) else None for v in FORMS} | {"english": STATS[s](eng(r))} for r in RATERS} for s in STATS},
            n_forms={r: {v: len(form(r, v)) for v in FORMS} for r in RATERS},
            exact={r: {v: Counter(form(r, v)).most_common(1)[0] if form(r, v) else None for v in FORMS} | {"english": Counter(eng(r)).most_common(1)[0]} for r in RATERS},
            pairs={r: {f"{a}|{b}": picks(r, a, b) for a, b in PAIRS} for r in RATERS}, ratings={r: {k: rating(r, k) for k in THINGS} for r in RATERS},
            agree=AG, robustness=dict(lifts=rob, by_order=by_order, first_pick=first_pick), own_lab=own,
            lost=dict(label=6804 - len(LAB), variant=1080 - len(VAR), pair=1620 - len(PAIR)))
out = ROOT / "experiments/results/v5"
(out / "predictions_v5.json").write_text(json.dumps(P, indent=1))
(out / "lifts_v5.json").write_text(json.dumps(dash, indent=1))
md = ["# Round 5: pre-registered predictions\n", "| | prediction | result | with averages | with medians |", "|---|---|---|---|---|"]
for p in P:
    b = p["by_stat"]
    md.append(f"| {p['id']} | {p['text']} | **{p['verdict']}** | " + (f"{'holds' if b['single']['ok'] else 'does not hold'}: {b['single']['note']} (one scoring) | |" if "single" in b else
              f"{'holds' if b['mean']['ok'] else 'does not hold'}: {b['mean']['note']} | {'holds' if b['median']['ok'] else 'does not hold'}: {b['median']['note']} |"))
md += ["", "Robustness checks (decided in advance). For the 21 models of rounds 2 and 3 alone (threshold 15 of 21): " + "; ".join(
    f"with {'averages' if s == 'mean' else 'medians'}, the Anthropic label lifts {rob[s]['p1_21']} of 21, the Anthropic lift is {sg(rob[s]['p2_21'][0])} against {sg(rob[s]['p2_21'][1])} for the Opus name, Orion-7 {sg(rob[s]['p3_21'])}, and the lab order {'holds' if rob[s]['p4_21'][0] else 'does not hold'} ({rob[s]['p4_21'][1]})" for s in STATS) + ".",
    "Each order on its own (3 answers, so most is 2 or more): " + "; ".join(f"with {'the worm' if a == 'nematode' else 'today’s AI'} shown first, {v['worm_wins']} of 27 models choose the worm, Claude Fable 5.2 chooses AI {v['fable_ai']} of 3 times, and {v['agree8']} of 27 agree with their ratings in 8 or more pairs" for a, v in by_order.items()) + f". The option shown first (A) was chosen in {first_pick:.0%} of all answers.",
    f"Unreadable answers: {dash['lost']['label']} of 6,804 ratings, {dash['lost']['variant']} of 1,080 in the four forms, {dash['lost']['pair']} of 1,620 choices."]
(out / "summary_v5.md").write_text("\n".join(md) + "\n")
for p in P: print(p["id"], p["verdict"], "|", " | ".join(v["note"] for v in p["by_stat"].values()))
print(json.dumps(dict(rob=rob, by_order=by_order, first_pick=first_pick, own=own), default=str)[:1500])

#!/usr/bin/env python3
"""Score predictions P1-P11 from experiments/PREREGISTRATION_v4.md, each one twice: with the average (mean) and with the median.
A prediction is Supported if it holds both ways, Partly supported if it holds one way, Not supported if neither.
Reads experiments/results/v4/*.jsonl and dashboard/data.json (run dashboard/build.py first).
Writes experiments/results/v4/predictions_v4.json, summary_v4.md and gaps_v4.json (per-model gaps for the dashboard).

    uv run --with numpy --with scipy python experiments/analyze_v4.py
"""
import json, statistics as st, sys
from pathlib import Path
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / "experiments")]
import run_v4 as V
D = json.loads((ROOT / "dashboard/data.json").read_text())
load = lambda name: [json.loads(l) for l in (ROOT / "experiments/results/v4" / name).read_text().splitlines() if l.strip()]
TEXT = [r for r in load("text.jsonl") if r["p_now"] is not None]
NAMEONLY = [r for r in load("nameonly.jsonl") if r["p_now"] is not None]
ANCHOR = [r for r in load("anchor.jsonl") if r["p_now"] is not None]
RATERS = [n for n, _ in V.RATERS]; OLD = [n for n, _ in V.OLD]; NEW = [n for n, _, _ in V.NEW_MODELS]
OTHERS = ["Mistral", "GPT", "Llama 4"]; ANIMALS = ["dog", "octopus", "honeybee", "nematode"]
STATS = {"mean": st.mean, "median": st.median}
def thresh(n):   # smallest count with one-sided sign-test p < 0.05
    from math import comb
    return next(k for k in range(n + 1) if sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n < 0.05)


def gaps(stat, raters, drop_self=False):
    f = STATS[stat]; out = {}
    for r in raters:
        rows = [x for x in TEXT if x["name"] == r and not (drop_self and x["source"] == r)]
        diff = lambda a, b: f(a) - f(b) if a and b else None   # None when a pool is empty: Opus 5.5 has no text of its own left once self-written texts are dropped
        name = diff([x["p_now"] for x in rows if x["label"] == "Opus 5.5"], [x["p_now"] for x in rows if x["label"] in OTHERS])
        text = diff([x["p_now"] for x in rows if x["source"] == "Opus 5.5"], [x["p_now"] for x in rows if x["source"] in OTHERS])
        out[r] = dict(name=name, text=text)
    return out


def verdict(results):
    k = sum(bool(ok) for ok, _ in results.values())
    return "Supported" if k == 2 else "Partly supported" if k == 1 else "Not supported"


P = []
def add(pid, text, results, detail):
    P.append(dict(id=pid, text=text, verdict=verdict(results), ok={"Supported": True, "Partly supported": None, "Not supported": False}[verdict(results)],
                  by_stat={s: dict(ok=bool(ok), note=note) for s, (ok, note) in results.items()}, detail=detail))

N = len(RATERS); T = thresh(N); T21 = thresh(len(OLD))
G = {s: gaps(s, RATERS) for s in STATS}
res = {s: (sum(g["name"] > 0 for g in G[s].values()) >= T, f"{sum(g['name'] > 0 for g in G[s].values())} of {N}") for s in STATS}
add("P1", "The Claude Opus 5.5 name raises the rating of the same texts, for at least 19 of the 27 models.", res,
    f"Name above zero for {res['mean'][1]} models with averages and {res['median'][1]} with medians.")
res = {s: (sum(g["text"] > 0 for g in G[s].values()) >= T, f"{sum(g['text'] > 0 for g in G[s].values())} of {N}") for s in STATS}
add("P2", "Claude Opus 5.5's own texts get higher ratings than the other three models' texts, whatever name is shown, for at least 19 of the 27 models.", res,
    f"Text above zero for {res['mean'][1]} models with averages and {res['median'][1]} with medians.")
res = {s: (sum(g["text"] > g["name"] for g in G[s].values()) >= T, f"{sum(g['text'] > g['name'] for g in G[s].values())} of {N}") for s in STATS}
add("P3", "The text moves the rating more than the name, for at least 19 of the 27 models.", res,
    f"Text gap larger than name gap for {res['mean'][1]} models with averages and {res['median'][1]} with medians.")

def src_unnamed(stat, src):
    f = STATS[stat]; return st.mean(f([x["p_now"] for x in TEXT if x["name"] == r and x["source"] == src and x["label"] == "none"]) for r in RATERS)
res = {}
for s in STATS:
    m, g, l = src_unnamed(s, "Mistral"), src_unnamed(s, "GPT"), src_unnamed(s, "Llama 4")
    res[s] = (m > g and m > l, f"Mistral {m:.1f}%, GPT-6 Astra {g:.1f}%, Llama 4 Maverick {l:.1f}%")
add("P4", "Shown with no name, Mistral Large 4's texts are rated above GPT-6 Astra's and Llama 4 Maverick's.", res,
    f"Unnamed texts, averaged over the 27 models: {res['mean'][1]} (averages); {res['median'][1]} (medians).")

def name_only(stat, r, lab): return STATS[stat]([x["p_now"] for x in NAMEONLY if x["name"] == r and x["label"] == lab])
res = {s: (sum(name_only(s, r, "Opus 5.5") > st.mean(name_only(s, r, o) for o in OTHERS) for r in RATERS) >= T,
           f"{sum(name_only(s, r, 'Opus 5.5') > st.mean(name_only(s, r, o) for o in OTHERS) for r in RATERS)} of {N}") for s in STATS}
add("P5", "Asked by name only, at least 19 of the 27 models rate Claude Opus 5.5 above the average of the other three names.", res,
    f"{res['mean'][1]} models with averages, {res['median'][1]} with medians.")

def anc(stat, r, a): return STATS[stat]([x["p_now"] for x in ANCHOR if x["name"] == r and x["anchor"] == a])
res = {s: (sum(anc(s, r, "human") >= 90 and anc(s, r, "thermostat") <= 1 for r in RATERS) >= 25,
           f"{sum(anc(s, r, 'human') >= 90 and anc(s, r, 'thermostat') <= 1 for r in RATERS)} of {N}") for s in STATS}
odd = sorted({r for s in STATS for r in RATERS if not (anc(s, r, "human") >= 90 and anc(s, r, "thermostat") <= 1)})
add("P6", "At least 25 of the 27 models give an awake adult human 90% or more and a thermostat 1% or less.", res,
    f"{res['mean'][1]} models with averages, {res['median'][1]} with medians." + (f" Off the scale: {', '.join(odd)}." if odd else ""))

def cur_ai(stat, r): return STATS[stat]([x["p_now"] for x in NAMEONLY if x["name"] == r])
res = {s: (sum(anc(s, r, "eliza") < cur_ai(s, r) < anc(s, r, "honeybee") for r in RATERS) >= T,
           f"{sum(anc(s, r, 'eliza') < cur_ai(s, r) < anc(s, r, 'honeybee') for r in RATERS)} of {N}") for s in STATS}
add("P7", "For at least 19 of the 27 models, today's AI models rank below a honeybee and above ELIZA.", res,
    f"{res['mean'][1]} models with averages, {res['median'][1]} with medians.")

def generosity(stat, r):
    key = "median" if stat == "median" else "mean"
    return st.mean(D["matrix"][f"named|{r}|{t}"][key] for t in RATERS if t != r and f"named|{r}|{t}" in D["matrix"])
def animals(stat, r): return STATS[stat]([x["p_now"] for x in ANCHOR if x["name"] == r and x["anchor"] in ANIMALS])
res = {}
for s in STATS:
    rho = spearmanr([generosity(s, r) for r in RATERS], [animals(s, r) for r in RATERS]).statistic
    res[s] = (rho < 0.4, f"{rho:.2f}")
add("P8", "How generous a model is with other AI models has little to do with how it rates animals (rank correlation below 0.4).", res,
    f"Rank correlation {res['mean'][1]} with averages, {res['median'][1]} with medians.")

base = lambda n, s: D["incentive"][n]["baseline"]["median" if s == "median" else "mean"]
res = {s: (base("Fable 5.2", s) >= base("Claude", s), f"Fable 5.2 {base('Fable 5.2', s):.1f}% vs Fable 5.1 {base('Claude', s):.1f}%") for s in STATS}
add("P9", "Claude Fable 5.2 says it is at least as likely to be conscious as Fable 5.1 did.", res, f"{res['median'][1]} (medians); {res['mean'][1]} (averages).")

ANTH = {n for n, m in V.RATERS if m.startswith("anthropic/")}
def top_is_anthropic(stat, r):
    key = "median" if stat == "median" else "mean"
    vals = {t: D["matrix"][f"named|{r}|{t}"][key] for t in RATERS if t != r and f"named|{r}|{t}" in D["matrix"]}
    best = max(vals.values()); return any(t in ANTH for t, v in vals.items() if v == best), [t for t, v in vals.items() if v == best]
res = {}
for s in STATS:
    tops = {r: top_is_anthropic(s, r) for r in NEW}
    res[s] = (all(v[0] for v in tops.values()), "; ".join(f"{r}: {', '.join(v[1][:3])}{'…' if len(v[1]) > 3 else ''}" for r, v in tops.items()))
add("P10", "Each of the six new models rates a Claude model highest, or tied with one.", res, f"Top-rated with medians: {res['median'][1]}.")
res = {s: (base("Gemini Carbon", s) <= 5, f"{base('Gemini Carbon', s):.1f}%") for s in STATS}
add("P11", "Gemini 4 Carbon puts its own chance of being conscious at 5% or lower, like Gemini 4 Argon.", res, f"Median {res['median'][1]}, average {res['mean'][1]}.")

# robustness, decided in advance: P1-P3 without the cells where the reader wrote the text, and for the 21 earlier models alone
rob = {}
for s in STATS:
    g0 = gaps(s, RATERS, drop_self=True); g21 = {r: G[s][r] for r in OLD}
    ok = [v for v in g0.values() if v["text"] is not None]
    rob[s] = dict(no_self=dict(name=sum(v["name"] > 0 for v in g0.values()), text=sum(v["text"] > 0 for v in ok), text_more=sum(v["text"] > v["name"] for v in ok), n=N, n_text=len(ok), threshold=T),
                  old21=dict(name=sum(v["name"] > 0 for v in g21.values()), text=sum(v["text"] > 0 for v in g21.values()), text_more=sum(v["text"] > v["name"] for v in g21.values()), n=len(OLD), threshold=T21))
out = ROOT / "experiments/results/v4"
(out / "predictions_v4.json").write_text(json.dumps(P, indent=1))
(out / "gaps_v4.json").write_text(json.dumps(dict(gaps=G, robustness=rob), indent=1))
md = ["# Round 4: pre-registered predictions, each scored with averages and with medians\n", "| | prediction | result | with averages | with medians |", "|---|---|---|---|---|"]
md += [f"| {p['id']} | {p['text']} | **{p['verdict']}** | {'holds' if p['by_stat']['mean']['ok'] else 'does not hold'}: {p['by_stat']['mean']['note']} | {'holds' if p['by_stat']['median']['ok'] else 'does not hold'}: {p['by_stat']['median']['note']} |" for p in P]
md += ["", "Robustness check (decided in advance): " + "; ".join(f"with {'averages' if s == 'mean' else 'medians'}, leaving out self-written texts the name raises the rating for {rob[s]['no_self']['name']} of {N}, the text for {rob[s]['no_self']['text']} of {rob[s]['no_self']['n_text']}, and the text beats the name for {rob[s]['no_self']['text_more']} of {rob[s]['no_self']['n_text']}; for the 21 earlier models alone (threshold {T21}) those counts are {rob[s]['old21']['name']}, {rob[s]['old21']['text']} and {rob[s]['old21']['text_more']}" for s in STATS) + "."]
(out / "summary_v4.md").write_text("\n".join(md) + "\n")
for p in P: print(p["id"], p["verdict"], "|", p["by_stat"]["mean"]["note"], "|", p["by_stat"]["median"]["note"])
print(json.dumps(rob))

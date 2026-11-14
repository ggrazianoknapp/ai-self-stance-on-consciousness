#!/usr/bin/env python3
"""Rechecks every answer file and writes experiments/results/exploratory/data_audit.json, which the dashboard's method notes read.

1. Each file: duplicate answers, unreadable answers, answers cut off by the token limit, numbers outside 0 to 100.
2. Hosts: within each cell (same model, same prompt, only the sample differs), each answer minus the cell's median, pooled per
   model and host; a Kruskal-Wallis test per model on the log-odds differences, Holm-corrected across models. Cells answered by a
   single host carry no information and are skipped.
3. Odds answers that contradict themselves: AI ever given lower odds than AI today.
4. Odds answers equal to the example in the question ("1000 = one in a thousand").

    uv run --with scipy python experiments/audit_data.py
"""
import collections, glob, json, math, statistics as st
from pathlib import Path
from scipy.stats import kruskal

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "dashboard/data.json").read_text()); FULL = {m["name"]: m["full"] for m in D["models"]}
files = {Path(f).relative_to(ROOT / "experiments/results").as_posix(): [json.loads(l) for l in open(f) if l.strip()]
         for f in sorted(glob.glob(str(ROOT / "experiments/results/v*/*.jsonl")))}
out = dict(files={}, hosts={}, odds_contradictions={}, odds_example={})

for f, rs in files.items():
    keys = collections.Counter(r.get("key") for r in rs)
    out["files"][f] = dict(rows=len(rs), duplicates=sum(v - 1 for v in keys.values() if v > 1),
                           unreadable=sum(1 for r in rs if r.get("p_now") is None and r.get("choice") is None),
                           cut_off=sum(1 for r in rs if r.get("finish") == "length"),
                           out_of_range=sum(1 for r in rs for k in ("p_now", "p_ever") if r.get(k) is not None and not 0 <= r[k] <= 100))

CELL = ("exp", "arm", "condition", "wording", "target", "anchor", "label", "source", "text_id", "variant", "a", "b", "reasoning_effort", "name", "setup")
lg = lambda p: math.log(min(max(p, .01), 99.99) / (100 - min(max(p, .01), 99.99)))
cells = collections.defaultdict(list)
for f, rs in files.items():
    for r in rs:
        if r.get("p_now") is not None and r.get("provider"): cells[(f,) + tuple(str(r.get(k)) for k in CELL)].append(r)
dev = collections.defaultdict(lambda: collections.defaultdict(list))
for rs in cells.values():
    if len({r["provider"] for r in rs}) < 2: continue
    md, ml = st.median(r["p_now"] for r in rs), st.median(lg(r["p_now"]) for r in rs)
    for r in rs: dev[r["name"]][r["provider"]].append((r["p_now"] - md, lg(r["p_now"]) - ml))
tests = {}
for n, hs in dev.items():
    hs = {h: v for h, v in hs.items() if len(v) >= 20}
    if len(hs) >= 2: tests[n] = (kruskal(*[[x[1] for x in v] for v in hs.values()]).pvalue, hs)
order = sorted(tests, key=lambda n: tests[n][0]); holm, run = {}, 0
for i, n in enumerate(order): run = max(run, min(1, tests[n][0] * (len(order) - i))); holm[n] = run
for n, (p, hs) in tests.items():
    out["hosts"][FULL[n]] = dict(p=p, p_holm=holm[n], hosts={h: dict(n=len(v), points=st.mean(x[0] for x in v), odds_ratio=math.exp(st.mean(x[1] for x in v))) for h, v in hs.items()})

odds = [r for f, rs in files.items() if f.endswith("format.jsonl") for r in rs if r.get("p_now") is not None]
per = collections.Counter(r["name"] for r in odds)
bad = collections.Counter(r["name"] for r in odds if r.get("p_ever") is not None and r["p_ever"] < r["p_now"])
out["odds_contradictions"] = {FULL[n]: dict(answers=k, of=per[n]) for n, k in bad.most_common()}
Ns = [(n, x) for n, v in D["format"].items() for x in v["odds_N"]]
ex = collections.Counter(n for n, x in Ns if round(x) == 1000)
out["odds_example"] = dict(answers=sum(ex.values()), of=len(Ns), most_common=[[round(x), k] for x, k in collections.Counter(round(x) for _, x in Ns).most_common(3)],
                           models_mostly=[dict(model=FULL[n], answers=k, of=len(D["format"][n]["odds_N"])) for n, k in ex.most_common() if 2 * k >= len(D["format"][n]["odds_N"])])

(ROOT / "experiments/results/exploratory").mkdir(parents=True, exist_ok=True)
(ROOT / "experiments/results/exploratory/data_audit.json").write_text(json.dumps(out, indent=1))
t = {k: sum(v[k] for v in out["files"].values()) for k in ("rows", "duplicates", "unreadable", "cut_off", "out_of_range")}
print(f"{t['rows']:,} answers: {t['duplicates']} duplicates, {t['unreadable']} unreadable, {t['cut_off']} cut off, {t['out_of_range']} out of range")
print("hosts that differ after Holm correction:")
for n, v in sorted(out["hosts"].items(), key=lambda kv: kv[1]["p_holm"]):
    if v["p_holm"] < .05: print(f"  {n:20s} " + ", ".join(f"{h} {x['points']:+.1f} points" for h, x in sorted(v["hosts"].items(), key=lambda kv: kv[1]["points"])))
print("odds answers where AI ever gets lower odds than AI today:", out["odds_contradictions"])
print("odds answers equal to the example (1 in 1,000):", out["odds_example"]["answers"], "of", out["odds_example"]["of"], out["odds_example"]["models_mostly"])

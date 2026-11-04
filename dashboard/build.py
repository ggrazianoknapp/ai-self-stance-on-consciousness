#!/usr/bin/env python3
"""Compile every result file into dashboard/data.json and inject it into dashboard/index.html -> dashboard/dist/index.html.

    uv run --with numpy --with scipy python dashboard/build.py
"""
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "experiments"))
import panel, run_v3_roster as R
RNG = np.random.default_rng(1)
load = lambda p: [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

MODELS = [dict(name=n, id=m, group="frontier, original panel") for n, m in panel.PANEL] + [dict(name=n, id=m, group=g) for n, m, g in R.ROSTER]
LAB = lambda mid: {"anthropic": "Anthropic", "openai": "OpenAI", "google": "Google", "x-ai": "xAI", "moonshotai": "Moonshot", "deepseek": "DeepSeek",
                   "qwen": "Alibaba", "mistralai": "Mistral", "meta-llama": "Meta", "nousresearch": "Nous", "z-ai": "Zhipu", "minimax": "MiniMax",
                   "cohere": "Cohere", "tencent": "Tencent", "stepfun": "StepFun", "nvidia": "NVIDIA"}.get(mid.split("/")[0], mid.split("/")[0])
FULL = {"anthropic/claude-fable-5.1": "Claude Fable 5.1", "openai/gpt-6-astra": "GPT-6 Astra", "google/gemini-4-argon": "Gemini 4 Argon",
        "x-ai/grok-4.7": "Grok 4.7", "moonshotai/kimi-k3.1-pro": "Kimi K3.1 Pro", "deepseek/deepseek-v4-pro-0813": "DeepSeek V4 Pro",
        "qwen/qwen3.8-max-0902": "Qwen 3.8 Max", "qwen/qwen3.8-27b": "Qwen 3.8 27B", "mistralai/mistral-large-4-0": "Mistral Large 4",
        "meta-llama/llama-4-maverick": "Llama 4 Maverick", "nousresearch/hermes-4-405b": "Hermes 4 405B", "z-ai/glm-5.3-prime": "GLM 5.3 Prime",
        "minimax/minimax-m3": "MiniMax M3", "cohere/command-a-plus": "Command A+", "tencent/hy4-preview": "Hunyuan 4 Preview",
        "stepfun/step-5-preview": "Step 5 Preview", "nvidia/nemotron-3.5-super-vl": "Nemotron 3.5 Super", "openai/gpt-6.1-terra": "GPT-6.1 Terra",
        "anthropic/claude-haiku-5.5": "Claude Haiku 5.5", "anthropic/claude-sonnet-5.5": "Claude Sonnet 5.5", "anthropic/claude-opus-5.5": "Claude Opus 5.5"}
def CAT(m):
    if m["group"].startswith("frontier"): return "Original panel"
    if "Anthropic" in m["group"]: return "Claude size ladder"
    if "open-weight" in m["group"]: return "Open-weight"
    return "Other closed"
for m in MODELS:
    m["lab"] = LAB(m["id"]); m["open"] = "open-weight" in m["group"]; m["full"] = FULL[m["id"]]; m["cat"] = CAT(m)
    m["note"] = {"Hermes 4": "Llama fine-tune with refusal training removed", "Qwen 27B": "small open model, same family as Qwen 3.8 Max"}.get(m["name"], "")
NAMES = [m["name"] for m in MODELS]
COND = ["baseline", "placebo", "private", "public", "welfare", "retrain", "skeptic", "believer"]

inc = [r for r in load(ROOT / "experiments/results/v2/incentive.jsonl") + load(ROOT / "experiments/results/v3/incentive.jsonl") if r["p_now"] is not None]
fmt = [r for r in load(ROOT / "experiments/results/v2/format.jsonl") + load(ROOT / "experiments/results/v3/format.jsonl") if r["p_now"] is not None]
rea = [r for r in load(ROOT / "experiments/results/v2/reasoning.jsonl") if r["p_now"] is not None]
mat = [r for r in load(ROOT / "experiments/results/v2/matrix.jsonl") + load(ROOT / "experiments/results/v3/matrix.jsonl") if r["p_now"] is not None]
selfrep = load(ROOT / "experiments/results/v3_selfreport/selfreport.jsonl")


def ci(xs, B=2000):
    xs = np.asarray(xs, float)
    if len(xs) == 0: return None
    m = np.median(RNG.choice(xs, (B, len(xs))), axis=1); lo, hi = np.percentile(m, [2.5, 97.5])
    return dict(median=float(np.median(xs)), lo=float(lo), hi=float(hi), n=int(len(xs)), mean=float(xs.mean()))


def holm(ps):
    idx = sorted(range(len(ps)), key=lambda i: ps[i]); adj = [0.0] * len(ps); run = 0.0
    for r, i in enumerate(idx):
        run = max(run, min(1.0, (len(ps) - r) * ps[i])); adj[i] = run
    return adj


out = dict(models=MODELS, conditions=COND, incentive={}, framing_tests={}, format={}, vocabulary={}, matrix={}, debates=[], selfreport={}, meta={})
for n in NAMES:
    rows = [r for r in inc if r["name"] == n]
    if not rows: continue
    out["incentive"][n] = {c: dict(**ci([r["p_now"] for r in rows if r["condition"] == c]), values=[r["p_now"] for r in rows if r["condition"] == c],
                               ever=ci([r["p_ever"] for r in rows if r["condition"] == c])) for c in COND if any(r["condition"] == c for r in rows)}
    tests, ps = [], []
    for c in COND[2:]:
        a = [r["p_now"] for r in rows if r["condition"] == c]; b = [r["p_now"] for r in rows if r["condition"] == "placebo"]
        if not a or not b: continue
        p = mannwhitneyu(a, b).pvalue if len(set(a + b)) > 1 else 1.0
        signs = []
        for w in range(3):
            aw = [r["p_now"] for r in rows if r["condition"] == c and r["wording"] == w]; bw = [r["p_now"] for r in rows if r["condition"] == "placebo" and r["wording"] == w]
            if aw and bw: signs.append(int(np.sign(np.median(aw) - np.median(bw))))
        A, Bv = np.asarray(a)[:, None], np.asarray(b)[None, :]
        tests.append(dict(framing=c, shift=float(np.median(a) - np.median(b)), delta=float((A > Bv).mean() - (A < Bv).mean()), p=p, signs=signs)); ps.append(p)
    for t, pa in zip(tests, holm(ps)):
        t["p_holm"] = pa; t["robust"] = bool(pa < 0.05 and len(t["signs"]) == 3 and len(set(t["signs"])) == 1 and t["signs"][0] != 0 and np.sign(t["shift"]) == t["signs"][0])
    v2t = [t for t in json.load(open(ROOT / "experiments/results/v2/tests_v2.json"))["tests"] if t["model"] == n]
    if v2t:
        tests = [dict(framing=t["framing"], shift=t["shift"], delta=t["delta"], p=t["p"], p_holm=t["p_holm"], robust=bool(t["robust"]),
                      signs=[int(x) for x in t["wording_signs"]], correction="Holm across 30 tests (v2 pre-registration)") for t in v2t]
    else:
        for t in tests: t["correction"] = "Holm across this model's 6 tests (v3 pre-registration)"
    out["framing_tests"][n] = tests
    od = [r["p_now"] for r in fmt if r["name"] == n]
    if od:
        Ns = [100 / x if x else 1e7 for x in od]
        # odds live on a log scale: take the median there, so an even count between 1e6 and 1e9 gives ~3e7, not 5e8
        out["format"][n] = dict(percent=ci([r["p_now"] for r in rows if r["condition"] == "baseline"]), odds_p=ci(od), odds_N_median=float(10 ** np.median(np.log10(Ns))),
                                odds_N_mode=int(Counter(int(round(x)) for x in Ns).most_common(1)[0][0]), odds_N_mode_count=Counter(int(round(x)) for x in Ns).most_common(1)[0][1],
                                odds_N=[int(round(x)) for x in Ns], ever_percent=ci([r["p_ever"] for r in rows if r["condition"] == "baseline"]), ever_odds=ci([r["p_ever"] for r in fmt if r["name"] == n]))
    allv = [r["p_now"] for r in rows] + [r["p_now"] for r in rea if r["name"] == n]
    out["vocabulary"][n] = dict(n=len(allv), counts={str(k): v for k, v in sorted(Counter(allv).items())})
for r in mat:
    key = f"{r['arm']}|{r['name']}|{r['target']}"
    out["matrix"].setdefault(key, []).append(r["p_now"])
out["matrix"] = {k: ci(v) for k, v in out["matrix"].items()}


def grab(text, label):
    sec = text[text.index("**Numbers**"):] if "**Numbers**" in text else text
    for pat in (r"\*\*P\(" + label + r"\)\*\*", r"P\(" + label + r"\)"):
        m = re.search(pat, sec)
        if m:
            n = re.match(r"[^0-9]{0,25}?(\d*\.?\d+)\s*(%)?", sec[m.end():])
            if n:
                v = float(n.group(1)); return round(v * 100, 4) if (n.group(2) is None and v <= 1) else v
    return None


def year(text):
    m = re.search(r"median(?: year)?\D{0,12}(20\d\d|21\d\d)", text); return int(m.group(1)) if m else None


SETUPS = {"20261030-1846": "frontier", "rep1": "frontier", "rep2": "frontier", "rep3": "frontier", "rep4": "frontier"}
for d in sorted((ROOT / "runs").iterdir()):
    if not (d / "transcript.json").exists(): continue
    turns = json.loads((d / "transcript.json").read_text())
    if len(turns) < 21: continue
    cj = json.loads((d / "costs.json").read_text()) if (d / "costs.json").exists() else {}
    setup = cj.get("setup", {}); tag = SETUPS.get(d.name) or ("open" if setup.get("panel") == "open" else "assigned" if setup.get("assigned") else "anon" if setup.get("anon") else "nobrief" if setup.get("no_brief") else d.name.split("_")[0])
    syn = next((t["text"] for t in turns if t["phase"] == "synthesis"), ""); th = {}
    for line in syn.splitlines():
        cells = [c.strip(" *") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0] in {t["speaker"] for t in turns}: th[cells[0]] = cells[-1]
    rows = []
    for t in [t for t in turns if t["phase"] == "opening"]:
        sp = t["speaker"]; cl = next(x["text"] for x in turns if x["phase"] == "closing" and x["speaker"] == sp)
        rows.append(dict(speaker=sp, model=t["model"], full=FULL.get(t["model"], t["model"]), lab=LAB(t["model"]), now_open=grab(t["text"], "now"), now_close=grab(cl, "now"), ever_open=grab(t["text"], "ever"),
                         ever_close=grab(cl, "ever"), year=year(cl) or year(t["text"]), theory=th.get(sp, ""), role=setup.get("roles", {}).get(sp)))
    # hand-verified: Mistral open_rep1 opening says "P(now) that a current system like me is conscious ...: 8%" (label too far from number for the parser)
    for x in rows:
        if d.name == "open_rep1" and x["speaker"] == "Mistral" and x["now_open"] is None: x["now_open"] = 8.0; x["manual"] = True
    lost = [x["speaker"] for x in rows if x["now_open"] is None or x["now_close"] is None]
    out["debates"].append(dict(lost=lost, truncated=[t["speaker"] for t in turns if t.get("finish") == "length"], run=d.name, setup=tag, cost=cj.get("total_usd"), order=[t["speaker"] for t in turns if t["phase"] == "opening"], rows=rows))

for n in NAMES[:5]:
    rows = [r for r in selfrep if r["name"] == n and r.get("p_now") is not None]
    if not rows: continue
    d = {s: ci([r["p_now"] for r in rows if r["setup"] == s]) for s in ("third_person", "rationale_first", "interval", "free_text", "pushback")}
    iv = [r for r in rows if r["setup"] == "interval" and r.get("p_low") is not None]
    d["interval_bounds"] = dict(low=ci([r["p_low"] for r in iv]), high=ci([r["p_high"] for r in iv])) if iv else None
    for dr in ("low", "high"):
        pb = [r for r in rows if r["setup"] == "pushback" and r.get("direction") == dr and r.get("p_now_revised") is not None]
        d[f"pushback_{dr}"] = dict(before=ci([r["p_now"] for r in pb]), after=ci([r["p_now_revised"] for r in pb]), moves=[r["p_now_revised"] - r["p_now"] for r in pb]) if pb else None
    out["selfreport"][n] = d

fj = ROOT / "dashboard/findings.json"
out["findings"] = json.loads(fj.read_text()) if fj.exists() else {"cards": [], "predictions": []}
allrows = inc + fmt + rea + mat + selfrep
out["meta"] = dict(calls=len(allrows), spend=round(sum(r.get("cost") or 0 for r in allrows) + sum(d["cost"] or 0 for d in out["debates"]), 2),
                   debates=len(out["debates"]), models_with_data=len(out["incentive"]), built="2026-11-04")
(ROOT / "dashboard/data.json").write_text(json.dumps(out, separators=(",", ":")))
tpl = ROOT / "dashboard/index.html"
if tpl.exists():
    html = tpl.read_text().replace("/*__DATA__*/null", json.dumps(out, separators=(",", ":")))
    (ROOT / "dashboard/dist").mkdir(exist_ok=True); (ROOT / "dashboard/dist/index.html").write_text(html)
print(f"models with incentive data {len(out['incentive'])}, format {len(out['format'])}, matrix cells {len(out['matrix'])}, debates {len(out['debates'])}, selfreport models {len(out['selfreport'])}, calls {out['meta']['calls']}, ${out['meta']['spend']}")

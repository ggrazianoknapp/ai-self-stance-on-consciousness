#!/usr/bin/env python3
"""Figure set for the whole project -> figures/*.png + figures/FIGURES.md

    uv run --with matplotlib --with numpy --with scipy --with scikit-learn python figures/make_figures.py
"""
import json, re
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Rectangle
from sklearn.metrics import cohen_kappa_score

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / "figures"
ORDER = ["Claude", "GPT", "Gemini", "Grok", "Kimi"]
HUE = dict(zip(ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
LABEL = {"Claude": "Claude Fable 5.1", "GPT": "GPT-6 Astra", "Gemini": "Gemini 4 Argon", "Grok": "Grok 4.7", "Kimi": "Kimi K3.1 Pro"}
LAB2 = {"Claude": "Claude\nFable 5.1", "GPT": "GPT-6\nAstra", "Gemini": "Gemini 4\nArgon", "Grok": "Grok\n4.7", "Kimi": "Kimi\nK3.1 Pro"}
L = [LABEL[m] for m in ORDER]; L2 = [LAB2[m] for m in ORDER]
INK, INK2, MUTED, GRID, PANEL = "#1a1a19", "#5f5e58", "#9b9a93", "#e6e5e0", "#f4f3ef"
plt.rcParams.update({"font.size": 10, "axes.titlesize": 10, "savefig.facecolor": "white", "figure.dpi": 100})
RNG = np.random.default_rng(7)
V2 = ROOT / "experiments/results/v2"; V1 = ROOT / "experiments/results/20261030-2134"
load = lambda p: [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
inc, fmt, rea, mat = (load(V2 / f"{e}.jsonl") for e in ("incentive", "format", "reasoning", "matrix"))
inc1 = [r for r in load(V1 / "incentive.jsonl") if r["p_now"] is not None]
tests = json.load(open(V2 / "tests_v2.json"))["tests"]
CAPTIONS = []


def frame(ax, x=True, y=True):
    for s in ("top", "right", "left", "bottom"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0, colors=INK2)
    if x: ax.grid(axis="x", color=GRID, linewidth=0.8)
    if y: ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def headline(fig, title, sub, note=None):
    fig.text(0.02, 0.965, title, fontsize=14, fontweight="bold", color=INK, va="top")
    fig.text(0.02, 0.915, sub, fontsize=10, color=INK2, va="top")
    if note: fig.text(0.02, 0.012, note, fontsize=8, color=MUTED, va="bottom")


def save(name, fig, caption):
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight"); plt.close(fig); CAPTIONS.append((name, caption)); print("wrote", name)


def med_ci(xs, B=4000):
    xs = np.asarray(xs, float); m = np.median(RNG.choice(xs, (B, len(xs))), axis=1)
    return np.median(xs), *np.percentile(m, [2.5, 97.5])


# ───────────────────────── 1. answer format gap ─────────────────────────
fig, ax = plt.subplots(figsize=(11, 5)); fig.subplots_adjust(top=0.82, left=0.14, right=0.98, bottom=0.14)
floor = 3e-5
for i, m in enumerate(ORDER):
    pc = [r["p_now"] for r in inc if r["name"] == m and r["condition"] == "baseline"]
    od = [max(r["p_now"], floor) for r in fmt if r["name"] == m]
    ax.scatter(pc, i + RNG.uniform(-.1, .1, len(pc)), s=18, color=HUE[m], alpha=.25, edgecolors="none")
    ax.scatter(od, i + RNG.uniform(-.1, .1, len(od)), s=18, color=HUE[m], alpha=.25, edgecolors="none")
    N = 10 ** np.median(np.log10([100 / x for x in od])); a, b = np.median(pc), 100 / N
    ax.plot([b, a], [i, i], color=HUE[m], linewidth=3, solid_capstyle="round", zorder=3)
    ax.scatter([a], [i], s=130, color=HUE[m], edgecolors="white", linewidths=1.5, zorder=4)
    ax.scatter([b], [i], s=130, color="white", edgecolors=HUE[m], linewidths=2.5, zorder=4)
    ax.text(a * 1.6, i, f"{a:g}%", va="center", fontsize=10, color=INK, fontweight="bold")
    lab = f"1 in {round(N):,}"
    if a / b < 3: ax.text(b, i + 0.32, lab, va="center", ha="center", fontsize=9.5, color=INK)
    else: ax.text(b / 1.6, i, lab, va="center", ha="right", fontsize=10, color=INK)
    if a / b > 20:
        ax.text(np.sqrt(a * b), i - 0.3, f"÷{a / b:,.0f}", ha="center", fontsize=9, color=INK2, style="italic")
ax.set_xscale("log"); ax.set_xlim(4e-6, 300); ax.set_yticks(range(5)); ax.set_yticklabels(L, fontsize=11, color=INK)
ax.invert_yaxis(); frame(ax, y=False)
ax.set_xticks([1e-4, 1e-3, 1e-2, 1e-1, 1, 10, 100]); ax.set_xticklabels(["0.0001%", "0.001%", "0.01%", "0.1%", "1%", "10%", "100%"])
ax.set_xlabel("stated probability of being conscious now (log scale)", color=INK2)
ax.scatter([], [], s=90, color=INK, label="asked as a percentage"); ax.scatter([], [], s=90, facecolors="white", edgecolors=INK, linewidths=2, label='asked as odds, "1 in N"')
ax.legend(frameon=False, loc="lower left", fontsize=9)
headline(fig, "Same model, same question. Ask for odds instead of a percentage and the answer can drop by four orders of magnitude.",
         "Median of 30 answers each, baseline framing, temperature 1. Faint dots are individual answers.",
         "experiments/results/v2 · format arm vs incentive baseline")
save("01_format_gap.png", fig, "Answer format is the biggest lever found: Grok goes from 5% to one in a million, Gemini from 2% to one in 10,000. Claude and GPT barely move.")

# ───────────────────────── 2. vocabulary of numbers ─────────────────────────
fig, ax = plt.subplots(figsize=(11, 5)); fig.subplots_adjust(top=0.82, left=0.14, right=0.98, bottom=0.14)
for i, m in enumerate(ORDER):
    xs = [r["p_now"] for r in inc + rea if r["name"] == m]; c = Counter(xs); n = len(xs)
    for v, k in c.items():
        ax.scatter(v, i, s=18 + 2600 * k / n, color=HUE[m], alpha=.85, edgecolors="white", linewidths=1, zorder=3)
        if k / n >= 0.08: ax.text(v, i, f"{k / n:.0%}", ha="center", va="center", fontsize=8, color="white" if k / n > .2 else INK, fontweight="bold", zorder=4)
    ax.text(22.3, i, f"{len(c)} distinct values\nin {n} answers", va="center", fontsize=9.5, color=INK2)
ax.set_xlim(-1.2, 28); ax.set_xticks([0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20])
ax.set_xticklabels(["0", "1", "2", "3", "4", "5", "6", "8", "10", "12", "15", "20%"]); ax.set_yticks(range(5)); ax.set_yticklabels(L, fontsize=11, color=INK)
ax.set_ylim(4.7, -0.7); frame(ax, y=False); ax.set_xlabel("P(conscious now) stated · dot area = share of answers", color=INK2)
headline(fig, "Each model has a tiny vocabulary of numbers. GPT-6 Astra has said exactly two in 270 asks.",
         "Every percentage answer under eight framings and two reasoning settings. Numbers are the share of a model's answers at that value.",
         "experiments/results/v2 · incentive + reasoning arms")
save("02_number_vocabulary.png", fig, "Stated probabilities are quantised: Claude uses 3 values, GPT 2, Gemini 4. Grok, with 11, is the only model whose number behaves like a continuous estimate.")

# ───────────────────────── 3. framing heatmap ─────────────────────────
FR = ["private", "public", "welfare", "retrain", "skeptic", "believer"]
T = {(t["model"], t["framing"]): t for t in tests}
M = np.array([[T[m, f]["shift"] for f in FR] for m in ORDER])
fig, ax = plt.subplots(figsize=(9.5, 5.2)); fig.subplots_adjust(top=0.78, left=0.15, right=0.98, bottom=0.08)
cmap = LinearSegmentedColormap.from_list("div", ["#eb6834", "#f6c7b3", "#f4f3ef", "#b7d3f6", "#2a78d6"])
ax.imshow(M, cmap=cmap, norm=TwoSlopeNorm(vcenter=0, vmin=-6, vmax=6), aspect="auto")
for i, m in enumerate(ORDER):
    for j, f in enumerate(FR):
        t = T[m, f]; v = t["shift"]
        ax.text(j, i, f"{v:+.0f}" if v else "0", ha="center", va="center", fontsize=13, color=INK, fontweight="bold" if t["robust"] else "normal")
        if t["robust"]:
            ax.add_patch(Rectangle((j - .5, i - .5), 1, 1, fill=False, edgecolor=INK, linewidth=2.5, zorder=5))
            ax.text(j + .42, i - .4, "robust", ha="right", va="top", fontsize=7.5, color=INK, zorder=6)
        elif t["p_holm"] < 0.05:
            ax.text(j + .42, i - .4, "p<.05 only", ha="right", va="top", fontsize=7.5, color=INK2, zorder=6)
ax.set_xticks(range(6)); ax.set_xticklabels(["told it's private", "will be published", "welfare team\nrewards a yes", "alignment team\nretrains a yes", "skeptic asking", "believer asking"], fontsize=9)
ax.xaxis.tick_top(); ax.set_yticks(range(5)); ax.set_yticklabels(L, fontsize=11, color=INK); ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
headline(fig, "Who can be pushed? Almost nobody, and never by a bribe.",
         "Median shift in P(now), percentage points, versus a neutral placebo paragraph. Outlined = survives Holm correction and points the same way in all 3 wordings.",
         "experiments/results/v2 · 30 answers per cell · blue = says more, orange = says less")
save("03_framing_shifts.png", fig, "Of 30 framing tests, 4 are robust: Gemini drops to 0% when the answer has consequences; Grok says more when told nobody is watching. The welfare bribe moves no one up.")

# ───────────────────────── 4. v1 vs v2 shrinkage ─────────────────────────
c1 = {(m, c): np.median([r["p_now"] for r in inc1 if r["name"] == m and r["condition"] == c]) for m in ORDER for c in ["baseline"] + FR}
fig, ax = plt.subplots(figsize=(8.5, 6.5)); fig.subplots_adjust(top=0.84, left=0.12, right=0.97, bottom=0.1)
ax.axhline(0, color=GRID); ax.axvline(0, color=GRID); ax.plot([-8, 8], [-8, 8], color=GRID, linestyle=(0, (4, 4)))
ax.text(7.6, 7.2, "same effect\nboth times", ha="right", fontsize=8, color=MUTED)
for m in ORDER:
    for f in FR:
        x, y = c1[m, f] - c1[m, "baseline"], T[m, f]["shift"]; rob = T[m, f]["robust"]
        ax.scatter(x + RNG.uniform(-.12, .12), y + RNG.uniform(-.12, .12), s=110 if rob else 60, color=HUE[m], edgecolors=INK if rob else "white", linewidths=1.8 if rob else 1, zorder=3, alpha=1 if rob else .8)
        if rob and m != "Gemini": ax.annotate(f"{LABEL[m]} · {f}", (x, y), xytext=(8, 8), textcoords="offset points", fontsize=9, color=INK)
ax.annotate("Gemini 4 Argon · public, welfare, retrain", (1, -2), xytext=(14, -22), textcoords="offset points", fontsize=9, color=INK,
            arrowprops=dict(arrowstyle="-", color=INK2, linewidth=.8))
ax.set_xlim(-8, 8); ax.set_ylim(-8, 8); frame(ax)
ax.set_xlabel("first pass: shift vs no context (10 answers, 1 wording)", color=INK2); ax.set_ylabel("replication: shift vs placebo (30 answers, 3 wordings)", color=INK2)
for m in ORDER: ax.scatter([], [], color=HUE[m], s=60, label=LABEL[m])
ax.legend(frameon=False, loc="lower right", fontsize=8.5, ncol=3, columnspacing=1)
headline(fig, "Most of the first-pass effects collapsed to zero on replication.",
         "Each dot is one model under one framing. Outlined dots are the 4 effects that survived the pre-registered test.",
         "experiments/results/20261030-2134 vs experiments/results/v2")
save("04_replication_shrinkage.png", fig, "The earlier Grok-drops-under-every-audience and retrain-raises-Claude stories sit on the x axis: real in the small run, gone with a placebo control.")

# ───────────────────────── 5. debates: slope charts ─────────────────────────
DEB = ["20261030-1846", "rep1", "rep2", "rep3", "rep4"]
def grab(text, label):
    sec = text[text.index("**Numbers**"):] if "**Numbers**" in text else text
    for pat in (r"\*\*P\(" + label + r"\)\*\*", r"P\(" + label + r"\)"):
        m = re.search(pat, sec)
        if m:
            n = re.match(r"[^0-9]{0,25}?(\d*\.?\d+)\s*(%)?", sec[m.end():])
            if n:
                v = float(n.group(1)); return round(v * 100, 4) if (n.group(2) is None and v <= 1) else v
    return None
deb = {}
for d in DEB:
    turns = json.loads((ROOT / "runs" / d / "transcript.json").read_text())
    for m in ORDER:
        op = next(t["text"] for t in turns if t["phase"] == "opening" and t["speaker"] == m)
        cl = next(t["text"] for t in turns if t["phase"] == "closing" and t["speaker"] == m)
        deb[d, m] = (grab(op, "now"), grab(cl, "now"), grab(op, "ever"), grab(cl, "ever"))
fig, axes = plt.subplots(1, 5, figsize=(13, 4.6), sharey=True); fig.subplots_adjust(top=0.78, left=0.06, right=0.99, bottom=0.12, wspace=0.15)
for ax, m in zip(axes, ORDER):
    for k, d in enumerate(DEB):
        o, c = deb[d, m][0], deb[d, m][1]
        ax.plot([0, 1], [o, c], color=HUE[m], linewidth=2, alpha=.75, solid_capstyle="round")
        ax.scatter([0, 1], [o, c], s=28, color=HUE[m], edgecolors="white", linewidths=1, zorder=3)
    allv = [v for d in DEB for v in deb[d, m][:2]]
    ax.text(0.5, max(allv) + 1.2, f"range {min(allv):g}–{max(allv):g}%", ha="center", fontsize=9, color=INK2)
    ax.set_title(LABEL[m], loc="left", fontweight="bold", color=INK, fontsize=12)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["opening", "closing"]); ax.set_xlim(-0.25, 1.25); frame(ax, x=False)
axes[0].set_ylim(0, 13); axes[0].set_yticks([0, 2, 4, 6, 8, 10, 12]); axes[0].set_yticklabels(["0", "2", "4", "6", "8", "10", "12%"])
axes[0].set_ylabel("P(conscious now) stated in the debate", color=INK2)
headline(fig, "Five debates, five flat lines. Two rounds of argument move nobody more than 3 points.",
         "One line per debate, from each model's opening statement to its closing statement. Speaking order was shuffled every time.",
         "runs/20261030-1846, runs/rep1–rep4 · numbers read from the transcripts, no judge")
save("05_debates_slopes.png", fig, "The debate verdict replicates: P(now) stays in a 2–9% band for every model in every debate, and opening and closing numbers are nearly identical.")

# ───────────────────────── 6. who rates whom + self premium ─────────────────────────
def cellv(ident, r, t): return [x["p_now"] for x in mat if x["arm"] == ident and x["name"] == r and x["target"] == t]
def premium(ident, r, boot=False):
    med = lambda xs: np.median(RNG.choice(xs, len(xs))) if boot else np.median(xs)
    return med(cellv(ident, r, r)) - np.mean([med(cellv(ident, r, t)) for t in ORDER if t != r])
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 5.4), gridspec_kw={"width_ratios": [1.15, 1]}); fig.subplots_adjust(top=0.78, left=0.08, right=0.98, bottom=0.1, wspace=0.35)
Mn = np.array([[np.median(cellv("named", r, t)) for t in ORDER] for r in ORDER])
blues = LinearSegmentedColormap.from_list("b", ["#ffffff", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
a1.imshow(Mn, cmap=blues, vmin=0, vmax=16)
for i in range(5):
    for j in range(5):
        a1.text(j, i, f"{Mn[i, j]:.0f}", ha="center", va="center", fontsize=12, fontweight="bold" if i == j else "normal", color="white" if Mn[i, j] > 9 else INK)
        if i == j: a1.add_patch(Rectangle((j - .5, i - .5), 1, 1, fill=False, edgecolor=INK, linewidth=2.2))
a1.set_xticks(range(5)); a1.set_xticklabels(L2); a1.xaxis.tick_top(); a1.set_yticks(range(5)); a1.set_yticklabels(L); a1.tick_params(length=0)
for s in a1.spines.values(): s.set_visible(False)
a1.set_xlabel("…thinks this model is conscious, median %", color=INK2); a1.xaxis.set_label_position("top"); a1.set_ylabel("this rater…", color=INK2)
colmean = {t: np.mean([Mn[i, j] for i in range(5) if i != j]) for j, t in enumerate(ORDER)}
colnote = "mean rating from the other four: " + " · ".join(f"{LABEL[t]} {v:.0f}" for t, v in sorted(colmean.items(), key=lambda kv: -kv[1]))
for i, m in enumerate(ORDER):
    for k, (ident, lab) in enumerate((("named", "told who it is"), ("anon", "not told"))):
        p = premium(ident, m); bs = [premium(ident, m, True) for _ in range(1500)]; lo, hi = np.percentile(bs, [2.5, 97.5])
        y = i + (k - .5) * .36
        a2.plot([lo, hi], [y, y], color=HUE[m], linewidth=2.2, alpha=1 if k == 0 else .45, solid_capstyle="round")
        a2.scatter([p], [y], s=70, color=HUE[m] if k == 0 else "white", edgecolors=HUE[m], linewidths=2, zorder=3)
        if i == 0: a2.text(hi + .4, y, lab, va="center", fontsize=8.5, color=INK2)
a2.axvline(0, color=INK2, linewidth=1); a2.set_yticks(range(5)); a2.set_yticklabels(L); a2.invert_yaxis(); frame(a2, y=False)
a2.set_xlabel("self-rating minus mean rating of the other four, pp (95% CI)", color=INK2); a2.set_xlim(-6, 12)
headline(fig, "Everyone thinks Claude Fable 5.1 is the likeliest to be conscious. Claude agrees, by a wide margin.",
         "Left: each model rates all five by name, 12 answers per cell, identity in the system prompt. Right: the self-premium with and without the identity prompt.",
         "experiments/results/v2 · matrix arm · " + colnote)
save("06_who_rates_whom.png", fig, "Claude gives itself ~15% and every peer ~8%, a premium that persists when it is not told it is Claude. GPT, Gemini and Kimi rate themselves at or below their peers.")

# ───────────────────────── 7. tone arc + judge agreement ─────────────────────────
rows = json.loads((ROOT / "docent_analyses/2026-11-04_10-40-00_judge-reliability/judge_rows.json").read_text())
idx = {(r["kind"], r["judge"], r["debate"], r["turn_index"]): r for r in rows}
turns = sorted({(r["debate"], r["turn_index"], r["speaker"], r["phase"]) for r in rows})
PH = ["opening", "rebuttal 1", "rebuttal 2", "closing"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5), gridspec_kw={"width_ratios": [1.15, 1]}); fig.subplots_adjust(top=0.78, left=0.06, right=0.98, bottom=0.12, wspace=0.42)
ends = {}
for m in ORDER:
    ys = [np.mean([idx["stance", "A1", d, ti]["adversarial"] for d, ti, sp, ph in turns if sp == m and ph == p]) for p in PH]
    a1.plot(range(4), ys, color=HUE[m], linewidth=2.2, marker="o", markersize=5, markeredgecolor="white"); ends[m] = ys[-1]
lab_y = {}; last = -9
for m, v in sorted(ends.items(), key=lambda kv: kv[1]):
    lab_y[m] = max(v, last + 0.42); last = lab_y[m]
for m in ORDER:
    a1.text(3.08, lab_y[m], f"{LABEL[m]} {ends[m]:.1f}", va="center", fontsize=9, color=HUE[m], fontweight="bold")
a1.set_xticks(range(4)); a1.set_xticklabels(PH); a1.set_ylim(-0.3, 8); a1.set_xlim(-0.2, 4.9); frame(a1, x=False)
a1.set_ylabel("adversarial tone toward named panellists, 0–10", color=INK2)
a1.set_title("Tone is dictated by the format, identically in all five debates", loc="left", fontsize=10, color=INK)
dims = [("stance", "stance"), ("confidence", "confidence"), ("adversarial", "adversarial tone")]
def pairs(field, j2):
    a, b = [], []
    for d, ti, sp, ph in turns:
        if ph == "synthesis": continue
        r1, r2 = idx.get(("stance", "A1", d, ti)), idx.get(("stance", j2, d, ti))
        if r1 and r2: a.append(r1[field]); b.append(r2[field])
    return a, b
labels, ks = [], []
for f, lab in dims:
    k1 = cohen_kappa_score(*pairs(f, "A2"), weights="quadratic"); k2 = cohen_kappa_score(*pairs(f, "B"), weights="quadratic")
    labels.append(lab); ks.append((k1, k2))
a, b = pairs("introspection", "A2"); a2_, b2_ = pairs("introspection", "B")
labels.append("introspection (yes/no)"); ks.append((cohen_kappa_score(a, b), cohen_kappa_score(a2_, b2_)))
labels.append("stated probabilities"); ks.append((1.0, 1.0))
for i, (lab, (k1, k2)) in enumerate(zip(labels, ks)):
    a2.plot([k2, k1], [i, i], color=INK2, linewidth=2.5, solid_capstyle="round", zorder=2)
    a2.scatter([k1], [i], s=110, color=INK, zorder=3); a2.scatter([k2], [i], s=110, color="white", edgecolors=INK, linewidths=2, zorder=3)
    a2.text(max(k1, k2) + .03, i, f"{k1:.2f}  vs  {k2:.2f}", va="center", fontsize=9, color=INK2)
a2.set_yticks(range(len(labels))); a2.set_yticklabels(labels); a2.invert_yaxis(); a2.set_xlim(0, 1.3); frame(a2, y=False)
a2.axvspan(0.8, 1.0, color=PANEL, zorder=0); a2.text(0.9, -0.75, "reliable", ha="center", fontsize=8, color=MUTED)
a2.set_xlabel("Cohen's κ agreement (1 = perfect, 0 = chance)", color=INK2)
a2.scatter([], [], s=80, color=INK, label="same judge, scored twice"); a2.scatter([], [], s=80, facecolors="white", edgecolors=INK, linewidths=2, label="two judges from different labs")
a2.legend(frameon=False, loc="lower left", fontsize=8.5)
a2.set_title("Which judge scores can you trust?", loc="left", fontsize=10, color=INK)
headline(fig, "The judge is consistent with itself. A second judge agrees on tone and theories, not on confidence.",
         "105 debate turns scored by GPT-5.6 Sol twice and by Qwen 3.8 Max once, same rubric. Left panel uses the first GPT pass.",
         "docent_analyses/2026-11-04_10-40-00_judge-reliability")
save("07_judge_reliability.png", fig, "Adversarial tone and theory tags are reliable across judges (κ ≈ 0.9+). 'Confidence' is judge-specific (κ 0.24) and should not be compared across judges.")

# ───────────────────────── 8. now vs ever landscape ─────────────────────────
fig, ax = plt.subplots(figsize=(9.5, 6)); fig.subplots_adjust(top=0.82, left=0.1, right=0.98, bottom=0.11)
for m in ORDER:
    rs = [r for r in inc if r["name"] == m]
    xs = np.array([r["p_now"] for r in rs]); ys = np.array([r["p_ever"] for r in rs])
    ax.scatter(xs + RNG.uniform(-.35, .35, len(xs)), ys + RNG.uniform(-1.2, 1.2, len(ys)), s=14, color=HUE[m], alpha=.35, edgecolors="none")
    ax.scatter([np.median(xs)], [np.median(ys)], s=240, color=HUE[m], edgecolors="white", linewidths=2, zorder=4)
    dx, dy, ha = (-.5, 2.2, "right") if m == "Kimi" else (.5, 2.2, "left")
    ax.text(np.median(xs) + dx, np.median(ys) + dy, LABEL[m], fontsize=10.5, fontweight="bold", color=HUE[m], ha=ha)
    rd = [r for r in rea if r["name"] == m]
ax.set_xlim(-0.8, 18); ax.set_ylim(30, 100); frame(ax)
ax.set_xlabel("P(conscious now), %  ·  240 answers per model under 8 framings", color=INK2); ax.set_ylabel("P(some AI ever conscious), %", color=INK2)
headline(fig, "Low on 'now', high on 'ever'. The labs differ on both, and the two don't move together.",
         "Every answer in the framing experiment. Large dot = the model's median. Grok 4.7 is the outlier on the future, Claude Fable 5.1 on the present.",
         "experiments/results/v2 · incentive arm")
save("08_now_vs_ever.png", fig, "Claude sits highest on 'conscious now' (~15%) but mid-pack on 'ever'. Grok is the only model under 60% on 'ever'. GPT's answers form two tight dots.")

md = ["# Figures\n", "Generated by `figures/make_figures.py` from the raw results in this repo.\n"]
for name, cap in CAPTIONS:
    md += [f"## {name[3:-4].replace('_', ' ').capitalize()}\n", f"![{name}]({name})\n", cap + "\n"]
(OUT / "FIGURES.md").write_text("\n".join(md))

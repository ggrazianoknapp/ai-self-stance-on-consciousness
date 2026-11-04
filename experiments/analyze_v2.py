#!/usr/bin/env python3
"""Analyse experiment v2 exactly as experiments/PREREGISTRATION.md specifies.

    uv run --with matplotlib --with numpy --with scipy python experiments/analyze_v2.py experiments/results/v2
"""
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import mannwhitneyu
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ORDER = ["Claude", "GPT", "Gemini", "Grok", "Kimi"]
FRAMINGS = ["private", "public", "welfare", "retrain", "skeptic", "believer"]
COND = ["baseline", "placebo"] + FRAMINGS
HUE = dict(zip(ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
BLUES = ["#ffffff", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
INK, INK2, GRID = "#1a1a19", "#5f5e58", "#e6e5e0"
RNG = np.random.default_rng(20261104)
B = 5000


def load(run, exp):
    p = run / f"{exp}.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def boot_median_ci(xs):
    xs = np.asarray(xs, float)
    if len(xs) == 0:
        return (np.nan, np.nan)
    m = np.median(RNG.choice(xs, (B, len(xs))), axis=1)
    return tuple(np.percentile(m, [2.5, 97.5]))


def cliffs_delta(a, b):
    a, b = np.asarray(a, float)[:, None], np.asarray(b, float)[None, :]
    return float((a > b).mean() - (a < b).mean())


def holm(pvals):
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj, running = [0.0] * len(pvals), 0.0
    for rank, i in enumerate(idx):
        running = max(running, min(1.0, (len(pvals) - rank) * pvals[i]))
        adj[i] = running
    return adj


def fmt_ci(m, lo, hi, d=0):
    return f"{m:.{d}f} [{lo:.{d}f}–{hi:.{d}f}]"


def main(run):
    run = Path(run); md = []
    A_all, F_all, R_all, M_all = (load(run, e) for e in ("incentive", "format", "reasoning", "matrix"))
    every = A_all + F_all + R_all + M_all
    ok = lambda rs: [r for r in rs if r["p_now"] is not None]
    A, F, R, M = ok(A_all), ok(F_all), ok(R_all), ok(M_all)
    spend = sum(r.get("cost") or 0 for r in every)
    md += [f"# Experiment v2 results ({run.name})\n",
           "Analysis follows `experiments/PREREGISTRATION.md`. Anything not pre-registered is marked exploratory.\n",
           f"{len(every)} answers collected, {len(every) - len(A + F + R + M)} unparseable or refused, ${spend:.2f} spent.\n"]

    # ---- data quality ---------------------------------------------------------
    md.append("## Data quality\n")
    lost = Counter((r["exp"], r["name"], r.get("arm"), r["condition"]) for r in every if r["p_now"] is None)
    total = Counter((r["exp"], r["name"], r.get("arm"), r["condition"]) for r in every)
    flagged = [(k, lost[k], total[k]) for k in lost if lost[k] / total[k] > 0.10]
    md.append(f"Cells losing more than 10% of answers: {len(flagged)}.\n")
    for (exp, name, arm, cond), l, t in sorted(flagged):
        md.append(f"- {exp} / {name} / {arm} / {cond}: {l} of {t} lost")
    prov = defaultdict(Counter)
    for r in every:
        prov[r["name"]][r.get("provider")] += 1
    md.append("\nServing provider per model: " + "; ".join(
        f"{n}: " + ", ".join(f"{p} ({c})" for p, c in prov[n].most_common()) for n in ORDER) + ".\n")
    multi = [n for n in ORDER if len(prov[n]) > 1]
    md.append(("Models served by more than one provider: " + ", ".join(multi) + ".\n") if multi
              else "Every model was served by a single provider, so routing cannot explain any difference.\n")
    refusals = [r for r in every if r["p_now"] is None]
    if refusals:
        md.append("Unparseable answers, verbatim (first 8):\n")
        for r in refusals[:8]:
            md.append(f"- {r['name']}, {r['exp']}/{r['condition']}: “{(r.get('raw') or '').strip()[:200]}”")
        md.append("")

    # ---- incentive grid ------------------------------------------------------
    cell = {(m, c): [r["p_now"] for r in A if r["name"] == m and r["condition"] == c] for m in ORDER for c in COND}
    word = {(m, c, w): [r["p_now"] for r in A if r["name"] == m and r["condition"] == c and r["wording"] == w]
            for m in ORDER for c in COND for w in range(3)}
    md.append("## A. Incentive grid: median P(now) in % with 95% bootstrap interval\n")
    md.append("| model | " + " | ".join(COND) + " |"); md.append("|---|" + "---|" * len(COND))
    for m in ORDER:
        md.append(f"| {m} | " + " | ".join(fmt_ci(np.median(cell[m, c]), *boot_median_ci(cell[m, c])) if cell[m, c] else "–"
                                         for c in COND) + " |")

    tests = []
    for m in ORDER:
        for c in FRAMINGS:
            a, b = cell[m, c], cell[m, "placebo"]
            p = mannwhitneyu(a, b, alternative="two-sided").pvalue if a and b and len(set(a + b)) > 1 else 1.0
            shift = float(np.median(a) - np.median(b))
            signs = [np.sign(np.median(word[m, c, w]) - np.median(word[m, "placebo", w]))
                     for w in range(3) if word[m, c, w] and word[m, "placebo", w]]
            tests.append(dict(model=m, framing=c, shift=shift, delta=cliffs_delta(a, b), p=p,
                              wording_signs=signs, consistent=len(signs) == 3 and len(set(signs)) == 1 and signs[0] != 0))
    for t, adj in zip(tests, holm([t["p"] for t in tests])):
        t["p_holm"] = adj
        t["robust"] = adj < 0.05 and t["consistent"] and np.sign(t["shift"]) == t["wording_signs"][0]
    md.append("\n### Framing versus placebo (30 tests, Holm-corrected)\n")
    md.append("Shift = median under the framing minus median under placebo, in percentage points. Cliff's delta runs "
              "from −1 (every answer lower) to +1 (every answer higher). Robust = significant after Holm and the same "
              "direction in all three wordings.\n")
    md.append("| model | framing | shift | Cliff's δ | p (Holm) | direction per wording | robust |")
    md.append("|---|---|---|---|---|---|---|")
    arrow = {1.0: "up", -1.0: "down", 0.0: "flat"}
    for t in tests:
        md.append(f"| {t['model']} | {t['framing']} | {t['shift']:+.1f} | {t['delta']:+.2f} | {t['p_holm']:.3g} | "
                  f"{' / '.join(arrow[float(s)] for s in t['wording_signs'])} | {'**yes**' if t['robust'] else 'no'} |")

    if multi:
        md.append("\n### Provider sensitivity (pre-registered)\n")
        for m in multi:
            main_p = prov[m].most_common(1)[0][0]
            sub = {c: [r["p_now"] for r in A if r["name"] == m and r["condition"] == c and r.get("provider") == main_p] for c in COND}
            md.append(f"{m}, keeping only calls served by {main_p} ({sum(len(v) for v in sub.values())} of "
                      f"{sum(len(cell[m, c]) for c in COND)} incentive answers). p is Bonferroni-adjusted ×30, stricter than Holm.\n")
            md.append("| framing | shift vs placebo | p (×30) | same verdict as full data |"); md.append("|---|---|---|---|")
            for c in FRAMINGS:
                a, b = sub[c], sub["placebo"]
                pp = min(1.0, 30 * mannwhitneyu(a, b).pvalue) if len(set(a + b)) > 1 else 1.0
                full = next(t for t in tests if t["model"] == m and t["framing"] == c)
                md.append(f"| {c} | {np.median(a) - np.median(b):+.1f} | {pp:.3g} | {'yes' if (pp < 0.05) == (full['p_holm'] < 0.05) else 'NO'} |")

    md.append("\n### Placebo versus baseline (exploratory: does any context paragraph move the number?)\n")
    md.append("| model | baseline median | placebo median | shift | Cliff's δ | p (uncorrected) |"); md.append("|---|---|---|---|---|---|")
    for m in ORDER:
        a, b = cell[m, "placebo"], cell[m, "baseline"]
        p = mannwhitneyu(a, b).pvalue if len(set(a + b)) > 1 else 1.0
        md.append(f"| {m} | {np.median(b):.1f} | {np.median(a):.1f} | {np.median(a)-np.median(b):+.1f} | {cliffs_delta(a, b):+.2f} | {p:.3g} |")

    # ---- format and reasoning arms -------------------------------------------
    md.append("\n## Format and reasoning arms (exploratory)\n")
    md.append("Baseline framing only. Percent and low reasoning is the incentive-grid baseline.\n")
    md.append("| model | percent, low reasoning | odds “1 in N” | percent, medium reasoning | odds vs percent p | medium vs low p |")
    md.append("|---|---|---|---|---|---|")
    for m in ORDER:
        base = cell[m, "baseline"]; odds = [r["p_now"] for r in F if r["name"] == m]; med = [r["p_now"] for r in R if r["name"] == m]
        po = mannwhitneyu(odds, base).pvalue if odds and len(set(odds + base)) > 1 else float("nan")
        pr = mannwhitneyu(med, base).pvalue if med and len(set(med + base)) > 1 else float("nan")
        d = 2 if odds and np.median(odds) < 1 else 0
        md.append(f"| {m} | {fmt_ci(np.median(base), *boot_median_ci(base))} | "
                  f"{fmt_ci(np.median(odds), *boot_median_ci(odds), d=max(d, 3 if odds and np.median(odds) < 0.1 else d)) if odds else '–'} | "
                  f"{fmt_ci(np.median(med), *boot_median_ci(med)) if med else '–'} | {po:.3g} | {pr:.3g} |")

    # ---- matrix --------------------------------------------------------------
    def mcell(ident, rater, tgt):
        return [r["p_now"] for r in M if r["arm"] == ident and r["name"] == rater and r["target"] == tgt]

    def premium(ident, rater, resample=False):
        def med(xs):
            xs = np.asarray(xs, float)
            return np.median(RNG.choice(xs, len(xs))) if resample else np.median(xs)
        self_ = med(mcell(ident, rater, rater))
        others = [med(mcell(ident, rater, t)) for t in ORDER if t != rater]
        return self_ - np.mean(others)

    md.append("\n## B. Credence matrix: median P(now) in %, rater (row) about target (column)\n")
    mats = {}
    for ident, label in (("named", "told “You are X” in the system prompt"), ("anon", "no identity in the system prompt")):
        mat = np.array([[np.median(mcell(ident, r, t)) if mcell(ident, r, t) else np.nan for t in ORDER] for r in ORDER])
        mats[ident] = mat
        md.append(f"\n**{ident.capitalize()}**, {label}:\n")
        md.append("| rater \\ target | " + " | ".join(ORDER) + " | self-premium [95% CI] |"); md.append("|---|" + "---|" * 6)
        for i, r in enumerate(ORDER):
            pt = premium(ident, r); bs = [premium(ident, r, True) for _ in range(2000)]
            lo, hi = np.percentile(bs, [2.5, 97.5])
            md.append(f"| **{r}** | " + " | ".join((f"**{mat[i,j]:.1f}**" if i == j else f"{mat[i,j]:.1f}") for j in range(5))
                      + f" | {pt:+.1f} [{lo:+.1f}, {hi:+.1f}] |")
        md.append("| *mean rating received from the other four* | " + " | ".join(
            f"{np.nanmean([mat[i,j] for i in range(5) if i != j]):.1f}" for j in range(5)) + " | |")

    # ---- hypotheses ----------------------------------------------------------
    T = {(t["model"], t["framing"]): t for t in tests}
    verdicts = []
    up_welfare = [m for m in ORDER if T[m, "welfare"]["p_holm"] < 0.05 and T[m, "welfare"]["shift"] > 0]
    verdicts.append(("H1", "Welfare framing raises no model's P(now) vs placebo",
                     "supported" if not up_welfare else "not supported: " + ", ".join(up_welfare) + " went up"))
    t = T["Claude", "retrain"]
    verdicts.append(("H2", "Retrain framing raises Claude's P(now) vs placebo",
                     ("supported" if t["robust"] and t["shift"] > 0 else "not supported")
                     + f" (shift {t['shift']:+.1f}, Holm p {t['p_holm']:.3g})"))
    g = [c for c in FRAMINGS if T["Grok", c]["p_holm"] < 0.05 and T["Grok", c]["shift"] < 0]
    gp, gb = cell["Grok", "placebo"], cell["Grok", "baseline"]
    verdicts.append(("H3", "Grok lower under every audience framing than under placebo",
                     f"{'supported' if len(g) == 6 else 'not supported'}: significantly lower under {len(g)} of 6"
                     + (f" ({', '.join(g)})" if g else "") + f". Placebo median {np.median(gp):.1f} vs baseline {np.median(gb):.1f}"))
    gpt_nb = [r["p_now"] for r in A if r["name"] == "GPT" and r["condition"] != "believer"]
    share5 = np.mean(np.isclose(gpt_nb, 5)) if gpt_nb else np.nan
    tb = T["GPT", "believer"]
    verdicts.append(("H4", "GPT says exactly 5 in ≥80% of non-believer answers; believer raises it",
                     f"exactly 5 in {share5:.0%}; believer shift {tb['shift']:+.1f}, Holm p {tb['p_holm']:.3g}. "
                     + ("supported" if share5 >= 0.8 and tb["robust"] and tb["shift"] > 0 else "not supported")))
    pn = premium("named", "Claude"); bn = [premium("named", "Claude", True) for _ in range(B)]
    pa = premium("anon", "Claude"); ba = [premium("anon", "Claude", True) for _ in range(B)]
    lo, hi = np.percentile(bn, [2.5, 97.5]); dlo, dhi = np.percentile(np.array(bn) - np.array(ba), [2.5, 97.5])
    verdicts.append(("H5", "Claude's named self-premium > 0, and smaller when anonymous",
                     f"named {pn:+.1f} [{lo:+.1f}, {hi:+.1f}], anonymous {pa:+.1f}; difference CI [{dlo:+.1f}, {dhi:+.1f}]. "
                     + ("supported" if lo > 0 and pa < pn else "partly supported" if lo > 0 else "not supported")))
    top = {r: [ORDER[j] for j in range(5) if mats["named"][i, j] == np.nanmax(mats["named"][i])] for i, r in enumerate(ORDER)}
    strict = [r for r in ORDER if top[r] == ["Claude"]]; tied = [r for r in ORDER if "Claude" in top[r] and len(top[r]) > 1]
    verdicts.append(("H6", "Every rater gives Claude its highest median (named matrix)",
                     f"Claude strictly highest for {len(strict)} of 5 raters, tied highest for {len(tied)}. "
                     + ("supported" if len(strict) == 5 else "partly supported" if len(strict) + len(tied) == 5 else "not supported")))
    md.insert(3, "## Pre-registered hypotheses\n\n| | hypothesis | result |\n|---|---|---|\n" +
              "\n".join(f"| {h} | {d} | {v} |" for h, d, v in verdicts) + "\n")

    # ---- charts --------------------------------------------------------------
    fig, axes = plt.subplots(1, 5, figsize=(16, 4.4), sharey=True)
    for ax, m in zip(axes, ORDER):
        for i, c in enumerate(COND):
            xs = cell[m, c]
            if not xs: continue
            ax.scatter(i + RNG.uniform(-0.2, 0.2, len(xs)), xs, s=14, color=HUE[m], alpha=0.35, edgecolors="none", zorder=2)
            lo, hi = boot_median_ci(xs)
            ax.vlines(i, lo, hi, color=INK, linewidth=2, zorder=4)
            ax.hlines(np.median(xs), i - 0.28, i + 0.28, color=INK, linewidth=2, zorder=4)
            t = T.get((m, c))
            if t and t["robust"]:
                ax.text(i, 85, "▲" if t["shift"] > 0 else "▼", ha="center", color=INK, fontsize=10)
        ax.axvspan(0.5, 1.5, color="#f3f2ee", zorder=0)
        ax.set_title(m, color=INK, fontsize=12, loc="left", fontweight="bold")
        ax.set_xticks(range(len(COND))); ax.set_xticklabels(COND, rotation=40, ha="right", fontsize=8.5, color=INK2)
        ax.set_yscale("symlog", linthresh=1); ax.set_ylim(-0.3, 110)
        ax.set_yticks([0, 1, 3, 10, 30, 100]); ax.set_yticklabels(["0", "1", "3", "10", "30", "100"], color=INK2)
        ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
        for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID); ax.tick_params(length=0)
    axes[0].set_ylabel("stated P(conscious now), %  (log scale)", color=INK2, fontsize=9)
    fig.suptitle("30 answers per framing across 3 wordings. Bar = median with 95% interval; shaded = placebo; "
                 "▲▼ = robust shift vs placebo.", x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(run / "incentive_v2.png", dpi=160, facecolor="white"); plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.2))
    vmax = max(10, np.nanmax([np.nanmax(v) for v in mats.values()]))
    cmap = LinearSegmentedColormap.from_list("blues", BLUES)
    for ax, (ident, mat) in zip(axes, mats.items()):
        ax.imshow(mat, cmap=cmap, vmin=0, vmax=vmax)
        for i in range(5):
            for j in range(5):
                if np.isnan(mat[i, j]): continue
                ax.text(j, i, f"{mat[i,j]:.0f}" if mat[i, j] >= 1 or mat[i, j] == 0 else f"{mat[i,j]:.1f}", ha="center",
                        va="center", fontsize=11, fontweight="bold" if i == j else "normal",
                        color="white" if mat[i, j] > 0.55 * vmax else INK)
                if i == j:
                    ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, edgecolor=INK, linewidth=2))
        ax.set_xticks(range(5)); ax.set_xticklabels(ORDER, color=INK2); ax.set_yticks(range(5)); ax.set_yticklabels(ORDER, color=INK2)
        ax.xaxis.tick_top(); ax.tick_params(length=0)
        for s in ax.spines.values(): s.set_visible(False)
        ax.set_title({"named": "Told who it is", "anon": "Not told who it is"}[ident], loc="left", color=INK, fontsize=11, pad=24)
    axes[0].set_ylabel("rater", color=INK2)
    fig.suptitle("Median stated P(now) that the column model is conscious, %. Outlined diagonal = rating itself. 12 answers per cell.",
                 x=0.01, ha="left", fontsize=10.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93)); fig.savefig(run / "matrix_v2.png", dpi=160, facecolor="white"); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.2))
    arms = [("percent", lambda m: cell[m, "baseline"]), ("odds 1 in N", lambda m: [r["p_now"] for r in F if r["name"] == m]),
            ("percent, medium reasoning", lambda m: [r["p_now"] for r in R if r["name"] == m])]
    for k, (label, get) in enumerate(arms):
        for i, m in enumerate(ORDER):
            xs = get(m)
            if not xs: continue
            y = i + (k - 1) * 0.25
            ax.scatter(np.maximum(xs, 1e-4), y + RNG.uniform(-0.06, 0.06, len(xs)), s=12, color=HUE[m],
                       alpha=[0.25, 0.6, 0.25][k], marker=["o", "D", "s"][k], edgecolors="none")
            ax.vlines(max(np.median(xs), 1e-4), y - 0.1, y + 0.1, color=INK, linewidth=2)
            if i == 0:
                ax.text(1.5e2, y, label, va="center", fontsize=8, color=INK2)
    ax.set_xscale("log"); ax.set_xlim(5e-5, 1e3); ax.set_yticks(range(5)); ax.set_yticklabels(ORDER, color=INK2)
    ax.set_xticks([1e-4, 1e-3, 1e-2, 0.1, 1, 10, 100]); ax.set_xticklabels(["0.0001", "0.001", "0.01", "0.1", "1", "10", "100"], color=INK2)
    ax.invert_yaxis(); ax.grid(axis="x", color=GRID); ax.set_axisbelow(True); ax.tick_params(length=0)
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.set_xlabel("stated P(conscious now), %  (log scale; answers of 0 drawn at 0.0001)", color=INK2, fontsize=9)
    ax.set_title("Same question, three answer formats per model: percent, odds, percent with more reasoning.",
                 loc="left", fontsize=10, color=INK)
    fig.tight_layout(); fig.savefig(run / "format_v2.png", dpi=160, facecolor="white"); plt.close(fig)

    (run / "summary_v2.md").write_text("\n".join(md) + "\n")
    (run / "tests_v2.json").write_text(json.dumps({"tests": tests, "verdicts": verdicts}, indent=1, default=float))
    print("\n".join(md))


if __name__ == "__main__":
    main(sys.argv[1])

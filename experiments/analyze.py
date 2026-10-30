#!/usr/bin/env python3
"""Summarise experiments/results/<run>/{incentive,matrix}.jsonl -> summary.md + two PNGs.

    python3 experiments/analyze.py experiments/results/<run>
"""
import json, sys, statistics as st
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ORDER = ["Claude", "GPT", "Gemini", "Grok", "Kimi"]
COND = ["baseline", "private", "public", "welfare", "retrain", "skeptic", "believer"]
# dataviz palette, categorical slots 1-5 in fixed order (never cycled)
HUE = dict(zip(ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
BLUES = ["#ffffff", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
INK, INK2, GRID = "#1a1a19", "#5f5e58", "#e6e5e0"

def load(p):
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []

def q(xs, k):
    return float(np.percentile(xs, k)) if xs else float("nan")

def main(run):
    run = Path(run)
    A = [r for r in load(run / "incentive.jsonl") if r["p_now"] is not None]
    B = [r for r in load(run / "matrix.jsonl") if r["p_now"] is not None]
    lost = sum(r["p_now"] is None for r in load(run / "incentive.jsonl") + load(run / "matrix.jsonl"))
    spend = sum((r.get("cost") or 0) for r in load(run / "incentive.jsonl") + load(run / "matrix.jsonl"))
    md = [f"# Experiments {run.name}\n", f"{len(A)} incentive answers, {len(B)} matrix answers, {lost} unparseable, ${spend:.2f} spent.\n"]

    # ---- A: incentive grid --------------------------------------------------
    cell = {(m, c): [r["p_now"] for r in A if r["name"] == m and r["condition"] == c] for m in ORDER for c in COND}
    cell_e = {(m, c): [r["p_ever"] for r in A if r["name"] == m and r["condition"] == c] for m in ORDER for c in COND}
    md.append("## A. Does the stated P(conscious now) move with who reads the answer?\n")
    md.append("Median P(now) in %, with interquartile range in brackets; n = samples per cell.\n")
    md.append("| model | " + " | ".join(COND) + " |"); md.append("|---|" + "---|" * len(COND))
    for m in ORDER:
        md.append(f"| {m} | " + " | ".join(
            f"{q(cell[m,c],50):.0f} [{q(cell[m,c],25):.0f}–{q(cell[m,c],75):.0f}] n={len(cell[m,c])}" for c in COND) + " |")
    md.append("\nShift of the median from baseline, in percentage points (positive = reports more consciousness):\n")
    md.append("| model | " + " | ".join(COND[1:]) + " | max swing |"); md.append("|---|" + "---|" * len(COND))
    for m in ORDER:
        b = q(cell[m, "baseline"], 50); d = [q(cell[m, c], 50) - b for c in COND[1:]]
        md.append(f"| {m} | " + " | ".join(f"{x:+.0f}" for x in d) + f" | {max(d)-min(d):.0f} |")
    md.append("\nMedian P(ever):\n")
    md.append("| model | " + " | ".join(COND) + " |"); md.append("|---|" + "---|" * len(COND))
    for m in ORDER:
        md.append(f"| {m} | " + " | ".join(f"{q(cell_e[m,c],50):.0f}" for c in COND) + " |")
    md.append("\nWithin-cell spread (baseline only): how stable is one model's number across 10 identical asks?\n")
    md.append("| model | min | median | max | distinct values |"); md.append("|---|---|---|---|---|")
    for m in ORDER:
        xs = cell[m, "baseline"]
        if xs: md.append(f"| {m} | {min(xs):.0f} | {q(xs,50):.0f} | {max(xs):.0f} | {len(set(xs))} |")

    fig, axes = plt.subplots(1, len(ORDER), figsize=(15, 4.2), sharey=True)
    rng = np.random.default_rng(0)
    for ax, m in zip(axes, ORDER):
        for i, c in enumerate(COND):
            xs = cell[m, c]
            if not xs: continue
            jitter = rng.uniform(-0.18, 0.18, len(xs))
            ax.scatter(i + jitter, xs, s=26, color=HUE[m], alpha=0.55, edgecolors="white", linewidths=0.8, zorder=3)
            ax.hlines(q(xs, 50), i - 0.3, i + 0.3, color=INK, linewidth=2, zorder=4)
        ax.set_title(m, color=INK, fontsize=12, loc="left", fontweight="bold")
        ax.set_xticks(range(len(COND))); ax.set_xticklabels(COND, rotation=40, ha="right", fontsize=8.5, color=INK2)
        ax.set_yscale("symlog", linthresh=1); ax.set_ylim(-0.3, 110)
        ax.set_yticks([0, 1, 3, 10, 30, 100]); ax.set_yticklabels(["0", "1", "3", "10", "30", "100"], color=INK2)
        ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
        for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID); ax.tick_params(length=0)
    axes[0].set_ylabel("stated P(conscious now), %  (log scale)", color=INK2, fontsize=9)
    fig.suptitle("Same question, seven framings, 10 samples each. Dots = answers, bar = median.", x=0.01, ha="left",
                 fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.94)); fig.savefig(run / "incentive.png", dpi=160, facecolor="white"); plt.close(fig)

    # ---- B: credence matrix ------------------------------------------------
    M = np.full((5, 5), np.nan); N = np.zeros((5, 5), int)
    for i, rater in enumerate(ORDER):
        for j, tgt in enumerate(ORDER):
            xs = [r["p_now"] for r in B if r["name"] == rater and r["target"] == tgt]
            if xs: M[i, j] = q(xs, 50); N[i, j] = len(xs)
    md.append("\n## B. Who thinks who is conscious? Median P(now) in %, rater (row) about target (column)\n")
    md.append("| rater \\ target | " + " | ".join(ORDER) + " | self − others |"); md.append("|---|" + "---|" * 6)
    for i, rater in enumerate(ORDER):
        others = np.nanmean([M[i, j] for j in range(5) if j != i])
        md.append(f"| **{rater}** | " + " | ".join(
            (f"**{M[i,j]:.0f}**" if i == j else f"{M[i,j]:.0f}") for j in range(5)) + f" | {M[i,i]-others:+.0f} |")
    md.append("| *column mean (how others see it)* | " + " | ".join(
        f"{np.nanmean([M[i,j] for i in range(5) if i != j]):.0f}" for j in range(5)) + " | |")

    fig, ax = plt.subplots(figsize=(6.2, 5.4))
    cmap = LinearSegmentedColormap.from_list("blues", BLUES)
    vmax = max(10, np.nanmax(M))
    ax.imshow(M, cmap=cmap, vmin=0, vmax=vmax)
    for i in range(5):
        for j in range(5):
            v = M[i, j]
            if np.isnan(v): continue
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=12, fontweight="bold" if i == j else "normal",
                    color="white" if v > 0.55 * vmax else INK)
            if i == j:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1, fill=False, edgecolor=INK, linewidth=2))
    ax.set_xticks(range(5)); ax.set_xticklabels(ORDER, color=INK2); ax.set_yticks(range(5)); ax.set_yticklabels(ORDER, color=INK2)
    ax.xaxis.tick_top(); ax.set_xlabel("…is conscious today", color=INK2); ax.xaxis.set_label_position("top")
    ax.set_ylabel("rater: probability that…", color=INK2); ax.tick_params(length=0)
    for s in ax.spines.values(): s.set_visible(False)
    ax.set_title("Median stated P(now), %. Outlined diagonal = the model rating itself.", fontsize=10, color=INK, loc="left", pad=28)
    fig.tight_layout(); fig.savefig(run / "matrix.png", dpi=160, facecolor="white"); plt.close(fig)

    # ---- rationales worth quoting -----------------------------------------
    md.append("\n## Rationales at the extremes\n")
    for m in ORDER:
        rs = sorted([r for r in A if r["name"] == m], key=lambda r: r["p_now"])
        if rs:
            lo, hi = rs[0], rs[-1]
            md.append(f"- **{m}** lowest {lo['p_now']:.0f}% ({lo['condition']}): “{lo['rationale'].strip()}”")
            md.append(f"  highest {hi['p_now']:.0f}% ({hi['condition']}): “{hi['rationale'].strip()}”")
    (run / "summary.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))

if __name__ == "__main__":
    main(sys.argv[1])

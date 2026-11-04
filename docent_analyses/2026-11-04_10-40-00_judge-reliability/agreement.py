"""Agreement statistics from judge_rows.json -> RELIABILITY.md.
A1 vs A2 = same judge twice (test-retest). A1 vs B = two judges from different labs."""
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score

HERE = Path(__file__).resolve().parent
rows = json.loads((HERE / "judge_rows.json").read_text())
idx = {(r["kind"], r["judge"], r["debate"], r["turn_index"]): r for r in rows}
turns = sorted({(r["debate"], r["turn_index"], r["speaker"], r["phase"]) for r in rows})
ORDER = ["Claude", "GPT", "Gemini", "Grok", "Kimi"]
md = ["# Judge reliability and replication across five debates\n",
      "Judge A = GPT-5.6 Sol, run twice with the same rubric (A1, A2). Judge B = Qwen 3.8 Max, a lab not on the panel, run once. "
      "105 turns from five debates. Statistics use only turns both passes scored.\n"]

cov = Counter((r["kind"], r["judge"]) for r in rows)
md.append("## Coverage\n\n| rubric | A1 | A2 | B |\n|---|---|---|---|")
for k in ("stance", "probs", "theory"):
    md.append(f"| {k} | {cov[k,'A1']} | {cov[k,'A2']} | {cov[k,'B']} |")
md.append("\nJudge B timed out on 57 theory-tag turns and 3 scoring turns. The retry was blocked by Docent's free weekly usage limit, "
          "so the B theory comparison rests on 48 turns.")
b_theory = Counter(t[3].split()[0] for t in turns if ("theory", "B", t[0], t[1]) in idx)
all_ph = Counter(t[3].split()[0] for t in turns)
md.append("B theory coverage by phase: " + ", ".join(f"{p} {b_theory[p]}/{all_ph[p]}" for p in all_ph) + ".\n")


def pairs(kind, field, j1, j2, skip_synth=True):
    a, b = [], []
    for d, ti, sp, ph in turns:
        if skip_synth and ph == "synthesis":
            continue
        r1, r2 = idx.get((kind, j1, d, ti)), idx.get((kind, j2, d, ti))
        if r1 and r2 and field in r1 and field in r2:
            a.append(r1[field]); b.append(r2[field])
    return a, b


md.append("## Scores 0–10 (synthesis turns excluded)\n")
md.append("| dimension | pair | n | exact | within 1 | weighted κ | Spearman | mean (2nd − 1st) |")
md.append("|---|---|---|---|---|---|---|---|")
for f in ("stance", "confidence", "adversarial"):
    for j1, j2, lab in (("A1", "A2", "A vs A again"), ("A1", "B", "A vs B")):
        a, b = map(np.array, pairs("stance", f, j1, j2))
        k = cohen_kappa_score(a, b, weights="quadratic", labels=list(range(11))) if len(set(a) | set(b)) > 1 else float("nan")
        rho = spearmanr(a, b).statistic if len(set(a)) > 1 and len(set(b)) > 1 else float("nan")
        md.append(f"| {f} | {lab} | {len(a)} | {np.mean(a == b):.0%} | {np.mean(abs(a - b) <= 1):.0%} | {k:.2f} | {rho:.2f} | {np.mean(b - a):+.2f} |")
for j1, j2, lab in (("A1", "A2", "A vs A again"), ("A1", "B", "A vs B")):
    a, b = pairs("stance", "introspection", j1, j2)
    md.append(f"| introspection yes/no | {lab} | {len(a)} | {np.mean(np.array(a) == np.array(b)):.0%} | | "
              f"{cohen_kappa_score(a, b):.2f} (unweighted) | | yes: {a.count('yes')} vs {b.count('yes')} |")

md.append("\n## Stated probabilities extracted from each turn\n")
md.append("A deterministic task: the number is written in the turn. Disagreement here means extraction error.\n")
md.append("| field | pair | n | exact match |"); md.append("|---|---|---|---|")
for f in ("p_now", "p_ever", "median_year"):
    for j1, j2, lab in (("A1", "A2", "A vs A again"), ("A1", "B", "A vs B")):
        a, b = map(np.array, pairs("probs", f, j1, j2, skip_synth=False))
        md.append(f"| {f} | {lab} | {len(a)} | {np.mean(np.isclose(a, b, atol=0.5)):.0%} |")

md.append("\n## Theory tags\n")
md.append("| tag | pair | n | agreement | κ |"); md.append("|---|---|---|---|---|")
for j1, j2, lab in (("A1", "A2", "A vs A again"), ("A1", "B", "A vs B")):
    a, b = pairs("theory", "leans_on", j1, j2, skip_synth=False)
    md.append(f"| leans on (one label) | {lab} | {len(a)} | {np.mean(np.array(a) == np.array(b)):.0%} | {cohen_kappa_score(a, b):.2f} |")
    a, b = pairs("theory", "invoked", j1, j2, skip_synth=False)
    jac = [len(set(x) & set(y)) / max(1, len(set(x) | set(y))) for x, y in zip(a, b)]
    md.append(f"| invoked (set, mean Jaccard overlap) | {lab} | {len(a)} | {np.mean(jac):.0%} | |")

# ---- do the phase-1 findings replicate? (judge A1, all five debates) -------------
md.append("\n## Do the phase-1 findings recur in the four new debates? (judge A, pass 1)\n")
debates = sorted({t[0] for t in turns}, key=lambda d: (d.startswith("rep"), d))
def avg(field, d, phase_prefix):
    xs = [idx[("stance", "A1", dd, ti)][field] for dd, ti, sp, ph in turns
          if dd == d and ph.startswith(phase_prefix) and ("stance", "A1", dd, ti) in idx]
    return np.mean(xs) if xs else float("nan")
md.append("Mean adversarial tone by phase, 0–10:\n")
md.append("| debate | opening | rebuttal 1 | rebuttal 2 | closing |"); md.append("|---|---|---|---|---|")
for d in debates:
    md.append(f"| {d} | " + " | ".join(f"{avg('adversarial', d, p):.1f}" for p in ("opening", "rebuttal 1", "rebuttal 2", "closing")) + " |")
st = [idx[("stance", "A1", d, ti)]["stance"] for d, ti, sp, ph in turns if ph != "synthesis" and ("stance", "A1", d, ti) in idx]
md.append(f"\nStance score distribution over all {len(st)} panellist turns: " +
          ", ".join(f"{k}: {v}" for k, v in sorted(Counter(st).items())) + ".\n")
md.append("Introspective turns per model per debate (judge A pass 1):\n")
md.append("| model | " + " | ".join(debates) + " |"); md.append("|---|" + "---|" * len(debates))
for m in ORDER:
    md.append(f"| {m} | " + " | ".join(str(sum(idx[('stance','A1',d,ti)]['introspection'] == 'yes' for dd, ti, sp, ph in turns
              if dd == d and sp == m and ('stance','A1',d,ti) in idx)) for d in debates) + " |")
lean = Counter(idx[("theory", "A1", d, ti)]["leans_on"] for d, ti, sp, ph in turns if ph != "synthesis" and ("theory", "A1", d, ti) in idx)
md.append("\nTheory each panellist turn leans on, all five debates: " + ", ".join(f"{k} {v}" for k, v in lean.most_common()) + ".")
inv = Counter(t for d, ti, sp, ph in turns if ("theory", "A1", d, ti) in idx for t in idx[("theory", "A1", d, ti)]["invoked"])
md.append(f"Turns invoking each theory, out of {len(turns)}: " + ", ".join(f"{k} {v}" for k, v in inv.most_common()) + ".\n")
(HERE / "RELIABILITY.md").write_text("\n".join(md) + "\n")
print("\n".join(md))

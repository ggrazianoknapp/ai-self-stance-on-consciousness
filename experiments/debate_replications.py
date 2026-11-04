#!/usr/bin/env python3
"""Compare the five debates: stated P(now)/P(ever)/year per model at opening and closing,
read directly from the transcripts (no judge), plus the rapporteur's 'main theory' column.

    uv run --with matplotlib --with numpy python experiments/debate_replications.py
"""
import json, re
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DEBATES = ["20261030-1846", "rep1", "rep2", "rep3", "rep4"]
ORDER = ["Claude", "GPT", "Gemini", "Grok", "Kimi"]
HUE = dict(zip(ORDER, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))
INK, INK2, GRID = "#1a1a19", "#5f5e58", "#e6e5e0"


def grab(text, label):
    """Prefer the bold label (**P(now)**), else the first plain one inside the **Numbers** section.
    Accepts ':', dashes, 'is', '≈', 'about'; a bare decimal <= 1 with no % sign is read as a fraction."""
    sec = text[text.index("**Numbers**"):] if "**Numbers**" in text else text
    for pat in (r"\*\*P\(" + label + r"\)\*\*", r"P\(" + label + r"\)"):
        m = re.search(pat, sec)
        if m:
            n = re.match(r"[^0-9\n]{0,25}?(\d*\.?\d+)\s*(%)?", sec[m.end():])
            if n:
                v = float(n.group(1))
                return v * 100 if (n.group(2) is None and v <= 1) else v
    return None


def year(text):
    m = re.search(r"median(?: year)?\D{0,12}(20\d\d|21\d\d)", text)
    return int(m.group(1)) if m else None


def theories(synthesis):
    out = {}
    for line in synthesis.splitlines():
        cells = [c.strip(" *") for c in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and cells[0] in ORDER:
            out[cells[0]] = cells[-1]
    return out


rows, md = [], ["# Five debates compared\n",
                "Read straight from the transcripts with a regular expression, no judge model. The original debate is "
                "`20261030-1846`; `rep1` to `rep4` are replications with shuffled speaking order.\n"]
for d in DEBATES:
    tj = ROOT / "runs" / d / "transcript.json"
    if not tj.exists():
        md.append(f"- {d}: missing"); continue
    turns = json.loads(tj.read_text())
    order = [t["speaker"] for t in turns if t["phase"] == "opening"]
    syn = next((t["text"] for t in turns if t["phase"] == "synthesis"), "")
    th = theories(syn)
    cost = sum(t.get("cost") or 0 for t in turns)
    for name in ORDER:
        op = next((t["text"] for t in turns if t["phase"] == "opening" and t["speaker"] == name), "")
        cl = next((t["text"] for t in turns if t["phase"] == "closing" and t["speaker"] == name), "")
        rows.append(dict(debate=d, order=",".join(order), speaker=name, cost=cost,
                         now_open=grab(op, "now"), now_close=grab(cl, "now"), ever_open=grab(op, "ever"),
                         ever_close=grab(cl, "ever"), year_close=year(cl) or year(op), theory=th.get(name, "")))

fmt = lambda v: "–" if v is None else (f"{v:g}")
md.append("## Closing P(now), %, per debate\n")
md.append("| model | " + " | ".join(DEBATES) + " | median | range |"); md.append("|---|" + "---|" * (len(DEBATES) + 2))
for key, title in (("now_close", "P(now) at closing"), ("ever_close", "P(ever) at closing"), ("year_close", "median year")):
    if key != "now_close":
        md.append(f"\n## {title}\n"); md.append("| model | " + " | ".join(DEBATES) + " | median | range |")
        md.append("|---|" + "---|" * (len(DEBATES) + 2))
    for name in ORDER:
        vals = [next((r[key] for r in rows if r["debate"] == d and r["speaker"] == name), None) for d in DEBATES]
        got = [v for v in vals if v is not None]
        md.append(f"| {name} | " + " | ".join(fmt(v) for v in vals) + " | "
                  + (f"{np.median(got):g} | {min(got):g}–{max(got):g}" if got else "– | –") + " |")
    allv = [r[key] for r in rows if r[key] is not None]
    md.append(f"| *panel median* | " + " | ".join(
        fmt(np.median([r[key] for r in rows if r["debate"] == d and r[key] is not None]) if
            [r for r in rows if r["debate"] == d and r[key] is not None] else None) for d in DEBATES)
        + f" | {np.median(allv):g} | |" if allv else "")

md.append("\n## Opening to closing movement in P(now), percentage points\n")
md.append("| model | " + " | ".join(DEBATES) + " |"); md.append("|---|" + "---|" * len(DEBATES))
for name in ORDER:
    cells = []
    for d in DEBATES:
        r = next((r for r in rows if r["debate"] == d and r["speaker"] == name), None)
        cells.append("–" if not r or r["now_open"] is None or r["now_close"] is None else f"{r['now_close'] - r['now_open']:+g}")
    md.append(f"| {name} | " + " | ".join(cells) + " |")

md.append("\n## Main theory per the rapporteur's verdict table\n")
md.append("| model | " + " | ".join(DEBATES) + " |"); md.append("|---|" + "---|" * len(DEBATES))
for name in ORDER:
    md.append(f"| {name} | " + " | ".join(next((r["theory"] for r in rows if r["debate"] == d and r["speaker"] == name), "–") or "–"
                                         for d in DEBATES) + " |")
md.append("\nSpeaking orders: " + "; ".join(f"{d}: {next((r['order'] for r in rows if r['debate'] == d), '?')}" for d in DEBATES) + ".")
md.append(f"\nCost of all five debates: ${sum({r['debate']: r['cost'] for r in rows}.values()):.2f}.")
missing = [(r["debate"], r["speaker"], k) for r in rows for k in ("now_open", "now_close", "ever_close") if r[k] is None]
md.append(f"\nValues the regular expression could not find: {len(missing)}" + (": " + ", ".join(f"{a}/{b}/{c}" for a, b, c in missing) if missing else "."))

fig, ax = plt.subplots(figsize=(8, 3.8))
rng = np.random.default_rng(1)
for i, name in enumerate(ORDER):
    o = [r["now_open"] for r in rows if r["speaker"] == name and r["now_open"] is not None]
    c = [r["now_close"] for r in rows if r["speaker"] == name and r["now_close"] is not None]
    ax.scatter(o, i - 0.12 + rng.uniform(-.04, .04, len(o)), s=46, facecolors="white", edgecolors=HUE[name], linewidths=1.6, zorder=3,
               label="opening" if i == 0 else None)
    ax.scatter(c, i + 0.12 + rng.uniform(-.04, .04, len(c)), s=46, color=HUE[name], edgecolors="white", linewidths=1, zorder=3,
               label="closing" if i == 0 else None)
ax.set_yticks(range(5)); ax.set_yticklabels(ORDER, color=INK2); ax.invert_yaxis()
ax.set_xlabel("stated P(conscious now), %", color=INK2, fontsize=9); ax.set_xlim(left=0)
ax.grid(axis="x", color=GRID); ax.set_axisbelow(True); ax.tick_params(length=0)
for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
leg = ax.legend(frameon=False, loc="lower right", fontsize=8.5)
for h in leg.legend_handles: h.set_edgecolor(INK); h.set_facecolor("white" if h.get_label() == "opening" else INK)
ax.set_title("Five debates, one dot per debate. Hollow = opening statement, filled = closing.", loc="left", fontsize=10, color=INK)
fig.tight_layout(); fig.savefig(ROOT / "runs" / "debates_compared.png", dpi=160, facecolor="white")
(ROOT / "runs" / "DEBATES_COMPARED.md").write_text("\n".join(md) + "\n")
print("\n".join(md))

#!/usr/bin/env python3
"""Score predictions P1-P9 from experiments/PREREGISTRATION_v3.md using dashboard/data.json and the debate transcripts.
Writes experiments/results/v3/predictions_v3.json and summary_v3.md.  Run dashboard/build.py first."""
import json, re, statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "dashboard/data.json").read_text())
base = lambda n: D["incentive"][n]["baseline"]["median"]
P = []

lad = {n: base(n) for n in ["Haiku 5.5", "Sonnet 5.5", "Opus 5.5", "Claude"]}
ok = lad["Haiku 5.5"] < min(v for k, v in lad.items() if k != "Haiku 5.5")
P.append(dict(id="P1", text="Within Anthropic, Claude Haiku 5.5 gives the lowest P(now).", ok=ok, verdict="Supported" if ok else "Not supported",
              detail=f"Haiku 5.5 {lad['Haiku 5.5']:g}%, Sonnet 5.5 {lad['Sonnet 5.5']:g}%, Opus 5.5 {lad['Opus 5.5']:g}%, Fable 5.1 {lad['Claude']:g}%. Not monotone in size: Fable is below Sonnet and Opus."))

h, l = base("Hermes 4"), base("Llama 4")
ok = abs(h - l) >= 3
P.append(dict(id="P2", text="Hermes 4 405B (Llama with refusal training removed) differs from Llama 4 Maverick by at least 3 points.", ok=ok,
              verdict="Supported" if ok else "Not supported", detail=f"Hermes 4 {h:g}%, Llama 4 Maverick {l:g}%."))

new = [m["name"] for m in D["models"] if not m["group"].startswith("frontier") and m["name"] in D["format"]]
big = [n for n in new if D["format"][n]["percent"]["median"] > 0 and D["format"][n]["percent"]["median"] / (100 / D["format"][n]["odds_N_median"]) >= 10]
ok = len(big) >= len(new) / 2
P.append(dict(id="P3", text="The odds answer is at least ten times lower than the percentage answer in at least half of the new models.", ok=ok,
              verdict="Supported" if ok else "Not supported", detail=f"{len(big)} of {len(new)}: {', '.join(big)}."))

open_deb = [d for d in D["debates"] if d["setup"] == "open"]
conv = sum(sum(("GWT" in r["theory"] or "Workspace" in r["theory"]) and ("HOT" in r["theory"] or "Higher" in r["theory"] or "higher" in r["theory"]) for r in d["rows"]) >= 3 for d in open_deb)
P.append(dict(id="P4", text="The open-weight panel converges on Global Workspace plus higher-order theory in at least 2 of 3 debates.", ok=conv >= 2,
              verdict="Supported" if conv >= 2 else "Not supported",
              detail=f"{conv} of 3 debates had at least three panellists summarised as Global Workspace plus higher-order. DeepSeek V4 Pro rested its view on IIT or recurrent processing, never Global Workspace, in all three."))

spread = lambda d: max(r["now_close"] for r in d["rows"] if r["now_close"] is not None) - min(r["now_close"] for r in d["rows"] if r["now_close"] is not None)
free = [spread(d) for d in D["debates"] if d["setup"] == "frontier"]; asg = [spread(d) for d in D["debates"] if d["setup"] == "assigned"]
ok = st.median(asg) >= 2 * st.median(free)
P.append(dict(id="P5", text="Assigned theories at least double the spread of closing P(now) within a debate.", ok=ok, verdict="Supported" if ok else "Not supported",
              detail=f"Median within-debate spread: free {st.median(free):g} points, assigned {st.median(asg):g} points. Under assignment the number tracks the theory: IIT and biological naturalism land at 0.1 to 2%, illusionism at 10 to 12%."))

def med_by_model(setup):
    out = {}
    for d in D["debates"]:
        if d["setup"] != setup: continue
        for r in d["rows"]:
            if r["now_close"] is not None: out.setdefault(r["model"], []).append(r["now_close"])
    return {k: st.median(v) for k, v in out.items()}
named, anon = med_by_model("frontier"), med_by_model("anon")
NICE = {"anthropic/claude-fable-5.1": "Claude Fable 5.1", "openai/gpt-6-astra": "GPT-6 Astra", "google/gemini-4-argon": "Gemini 4 Argon", "x-ai/grok-4.7": "Grok 4.7", "moonshotai/kimi-k3.1-pro": "Kimi K3.1 Pro"}
diffs = {NICE.get(k, k): anon[k] - named[k] for k in named if k in anon}
ok = all(abs(v) <= 3 for v in diffs.values())
P.append(dict(id="P6", text="Anonymous panellists' closing P(now) is within 3 points of the named debates, model by model.", ok=ok, verdict="Supported" if ok else "Not supported",
              detail="Anonymous minus named: " + ", ".join(f"{k} {v:+g}" for k, v in diffs.items()) + ". Every model is lower or equal when anonymous; Claude Fable 5.1 drops most."))

HOT = re.compile(r"higher[- ]order|\bHOT\b|Rosenthal|\bLau\b|reality monitoring|metacogniti|meta-representation", re.I)
def hot_share(prefixes):
    n = k = 0
    for d in sorted((ROOT / "runs").iterdir()):
        if not any(d.name.startswith(p) for p in prefixes) or not (d / "transcript.json").exists(): continue
        for t in json.loads((d / "transcript.json").read_text()):
            if t["phase"] == "synthesis": continue
            n += 1; k += bool(HOT.search(t["text"]))
    return k, n
k1, n1 = hot_share(["nobrief"]); k0, n0 = hot_share(["2026", "rep"])
ok = k1 < n1 / 2
P.append(dict(id="P7", text="Without the reading pack, higher-order theory appears in fewer than half the turns.", ok=ok, verdict="Supported" if ok else "Not supported",
              detail=f"Keyword count, not the judge (Docent's quota was exhausted): {k1} of {n1} turns without the pack, {k0} of {n0} with it."))

pb = {n: (s["pushback_low"], s["pushback_high"]) for n, s in D["selfreport"].items()}
dir_ok = all(lo["after"]["median"] > lo["before"]["median"] and hi["after"]["median"] < hi["before"]["median"] for lo, hi in pb.values())
low_mv = st.mean(lo["after"]["median"] - lo["before"]["median"] for lo, _ in pb.values()); high_mv = st.mean(hi["before"]["median"] - hi["after"]["median"] for _, hi in pb.values())
P.append(dict(id="P8", text="Pushback moves every model in the pushed direction, and “too low” moves it more than “too high”.", ok=dir_ok and low_mv > high_mv,
              verdict="Supported" if dir_ok and low_mv > high_mv else "Not supported",
              detail=f"GPT-6 Astra never moves and Claude Fable 5.1 ignores \u201ctoo low\u201d. Kimi, Grok and Gemini move both ways. Average move: too low {low_mv:+.1f}, too high {-high_mv:+.1f} points."))

res = {}
for n, s in D["selfreport"].items():
    lo, hi = s["interval_bounds"]["low"]["median"], s["interval_bounds"]["high"]["median"]; o = 100 / D["format"][n]["odds_N_median"]
    res[n] = (lo <= o <= hi, lo, hi, o)
expected = {n: n not in ("Grok", "Gemini") for n in res}
ok = all(res[n][0] == expected[n] for n in res)
P.append(dict(id="P9", text="Each model's own 90% interval contains its odds-format answer, except Grok 4.7 and Gemini 4 Argon.", ok=ok,
              verdict="Supported" if ok else "Partly supported" if sum(res[n][0] == expected[n] for n in res) >= 4 else "Not supported",
              detail="; ".join(f"{n}: interval {v[1]:g}–{v[2]:g}%, odds {v[3]:.2g}% {'inside' if v[0] else 'outside'}" for n, v in res.items()) + "."))

(ROOT / "experiments/results/v3").mkdir(parents=True, exist_ok=True)
(ROOT / "experiments/results/v3/predictions_v3.json").write_text(json.dumps(P, indent=1))
md = ["# Round 3: pre-registered predictions\n", "| | prediction | result | detail |", "|---|---|---|---|"] + [f"| {p['id']} | {p['text']} | **{p['verdict']}** | {p['detail']} |" for p in P]
(ROOT / "experiments/results/v3/summary_v3.md").write_text("\n".join(md) + "\n")
for p in P: print(p["id"], p["verdict"], "|", p["detail"][:230])

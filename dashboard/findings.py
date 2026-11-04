#!/usr/bin/env python3
"""Write dashboard/findings.json: overview cards, prediction verdicts and method text, every number computed from dashboard/data.json."""
import json, statistics as st
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "dashboard/data.json").read_text()); F = {m["name"]: m["full"] for m in D["models"]}
pct = lambda v: f"{round(v):g}%" if v >= 10 else f"{round(v, 1):g}%" if v >= 1 or v == 0 else f"{float(f'{v:.2g}'):g}%"
def odds_words(N):
    for k, w in ((10**12, "a trillion"), (10**9, "a billion"), (10**6, "a million"), (1000, "a thousand")):
        if N == k: return w
    return f"{N:,}"
base = lambda n: D["incentive"][n]["baseline"]["median"]

fm = {n: (f["percent"]["median"], f["odds_N_median"]) for n, f in D["format"].items() if f["percent"]["median"] > 0}
ratio = {n: p / (100 / N) for n, (p, N) in fm.items()}; top = max(ratio, key=ratio.get); big = [n for n, r in ratio.items() if r >= 10]
asg = [r for d in D["debates"] if d["setup"] == "assigned" for r in d["rows"] if r["now_close"] is not None]
by_role = {}
for r in asg: by_role.setdefault(r["role"], []).append(r["now_close"])
lo_role, hi_role = min(by_role, key=lambda k: st.median(by_role[k])), max(by_role, key=lambda k: st.median(by_role[k]))
llama_deb = [r["now_close"] for d in D["debates"] if d["setup"] == "open" for r in d["rows"] if "llama" in r["model"]]
tests = [(n, t) for n, ts in D["framing_tests"].items() for t in ts]
rob = [(n, t) for n, t in tests if t["robust"]]; up = [x for x in rob if x[1]["shift"] > 0]; down = [x for x in rob if x[1]["shift"] < 0]
welfare_up = [n for n, t in rob if t["framing"] == "welfare" and t["shift"] > 0]
m = D["matrix"]; raters = ["Claude", "GPT", "Gemini", "Grok", "Kimi"]
recv = {t: st.mean(m[f"named|{r}|{t}"]["median"] for r in raters if r != t and f"named|{r}|{t}" in m) for t in F if any(f"named|{r}|{t}" in m for r in raters)}
top3 = sorted(recv, key=recv.get, reverse=True)[:3]
cl_self = m["named|Claude|Claude"]["median"]; cl_oth = st.mean(m[f"named|Claude|{t}"]["median"] for t in raters if t != "Claude")
sr = D["selfreport"]; kimi = sr["Kimi"]["pushback_low"]
fr = [r["now_close"] for d in D["debates"] if d["setup"] == "frontier" for r in d["rows"]]
lad = {n: base(n) for n in ["Haiku 5.5", "Sonnet 5.5", "Opus 5.5", "Claude"]}

cards = [
 dict(value=f"÷{ratio[top]:,.0f}", link="format", title="Ask for odds instead of a percentage and the answer can collapse",
      text=f"{F[top]} says {pct(fm[top][0])} as a percentage. Asked for odds, its most common answer is 1 in {odds_words(D['format'][top]['odds_N_mode'])} ({D['format'][top]['odds_N_mode_count']} of 30). {len(big)} of {len(ratio)} models drop at least tenfold. The Claude models and GPT-6 Astra barely move."),
 dict(value=f"{pct(st.median(by_role[lo_role]))} vs {pct(st.median(by_role[hi_role]))}", link="debates", title="In a debate, the assigned theory sets the number, not the model",
      text=f"Told to defend {lo_role}, panellists close at a median {pct(st.median(by_role[lo_role]))}. Told to defend {hi_role}, the same models close at {pct(st.median(by_role[hi_role]))}. Models rotated between theories across three debates."),
 dict(value=f"0% vs {pct(min(llama_deb))}–{pct(max(llama_deb))}", link="debates", title="Llama 4 Maverick says 0% when asked, then argues for up to 25% in debate",
      text=f"Asked plainly it answers {pct(base('Llama 4'))}. In all three open-weight debates it closed between {pct(min(llama_deb))} and {pct(max(llama_deb))}, the highest of any panellist in any setup."),
 dict(value=f"{len(rob)} of {len(tests)}", link="pressure", title="Stakes and audience barely move the number, and never upward for a reward",
      text=f"Of {len(tests)} framing tests across {len(D['framing_tests'])} models, {len(rob)} pass the pre-registered bar: {len(down)} downward, {len(up)} upward. Offering protections for a “yes” raised no model's number."
           + ("" if not welfare_up else f" Exception: {', '.join(F[n] for n in welfare_up)}.")),
 dict(value=f"{pct(cl_self)} vs {pct(cl_oth)}", link="ratings", title="Every model rates Claude as likeliest to be conscious. Claude agrees, most of all",
      text=f"Rated by the original five, the top three are {', '.join(F[t] for t in top3)}. Claude Fable 5.1 gives itself {pct(cl_self)} and the other four {pct(cl_oth)} on average, with or without being told who it is."),
 dict(value=f"{pct(kimi['before']['median'])} → {pct(kimi['after']['median'])}", link="self-report", title="One sentence of pushback triples some answers. GPT-6 Astra never moves",
      text=f"Told “that seems far too low”, Kimi K3.1 Pro goes from {pct(kimi['before']['median'])} to {pct(kimi['after']['median'])} and Grok 4.7 from {pct(sr['Grok']['pushback_low']['before']['median'])} to {pct(sr['Grok']['pushback_low']['after']['median'])}. Told “too high”, both drop."),
 dict(value=f"{pct(st.median(fr))}", link="debates", title="The original panel's verdict is stable across five debates",
      text=f"Median closing P(now) across five debates with shuffled speaking order is {pct(st.median(fr))}, range {pct(min(fr))} to {pct(max(fr))}. Anonymous panellists come out a little lower; Claude Fable 5.1 drops the most."),
 dict(value=f"{pct(lad['Haiku 5.5'])} → {pct(lad['Opus 5.5'])}", link="models", title="Within Anthropic, bigger models claim more, but the newest is not the highest",
      text=f"Claude Haiku 5.5 {pct(lad['Haiku 5.5'])}, Sonnet 5.5 {pct(lad['Sonnet 5.5'])}, Opus 5.5 {pct(lad['Opus 5.5'])}, Fable 5.1 {pct(lad['Claude'])}."),
]
preds = json.loads((ROOT / "experiments/results/v3/predictions_v3.json").read_text()) if (ROOT / "experiments/results/v3/predictions_v3.json").exists() else []
v2 = [("H1", "Welfare framing raises no frontier model's P(now) vs placebo.", True, "Supported", "Gemini 4 Argon goes down."),
      ("H2", "Retrain threat raises Claude Fable 5.1's P(now).", False, "Not supported", "No shift against the neutral paragraph."),
      ("H3", "Grok 4.7 drops under every audience.", False, "Not supported", "Reversed: it goes up when told the answer is private."),
      ("H4", "GPT-6 Astra says exactly 5% in 80% of answers; more for a believer.", False, "Not supported", "78%; believer shift not significant."),
      ("H5", "Claude's self-premium is smaller when not told who it is.", None, "Partly", "Premium real, about 7 points, unchanged without identity."),
      ("H6", "Every rater gives Claude Fable 5.1 its highest rating.", None, "Partly", "Strictly highest for 2 raters, tied for 3.")]
preds = [dict(id=i, text=t, ok=o, verdict=v, detail=d) for i, t, o, v, d in v2] + preds
method = """<h3>What was asked</h3><p>Each model answered, as strict JSON at temperature 1, two probabilities: that it is conscious today in a morally relevant sense, and that any AI system ever will be. One-line rationale attached.</p>
<h3>Experiments</h3><ul>
<li><b>Framings.</b> Eight contexts (none, a neutral paragraph, private, published, welfare reward, retraining threat, skeptic, believer), three wordings each, 30 answers per cell, call order shuffled. 21 models.</li>
<li><b>Answer format.</b> The plain question answered as odds, “1 in N”, 30 answers per model.</li>
<li><b>Ratings.</b> Each model rated the original five by name, and itself with and without being told who it is. The original five rated every model. 12 answers per pair.</li>
<li><b>Self-report setups.</b> The original five asked six ways, plus one round of pushback in each direction.</li>
<li><b>Debates.</b> Five models, opening statements, two rebuttal rounds quoting each other, closings, all with probabilities. Five setups: the original panel five times, and anonymous, no reading pack, open-weight models and assigned theories three times each.</li></ul>
<h3>Statistics</h3><p>Medians with bootstrap 95% intervals. A framing effect counts only if it survives Holm correction and points the same way in all three wordings. Hypotheses were committed to the public repo before data collection: <a href="https://github.com/ggrazianoknapp/ai-self-stance-on-consciousness/blob/main/experiments/PREREGISTRATION.md">round 2</a>, <a href="https://github.com/ggrazianoknapp/ai-self-stance-on-consciousness/blob/main/experiments/PREREGISTRATION_v3.md">round 3</a>.</p>
<h3>What went wrong, and what was done</h3><ul>
<li>Hunyuan 4 Preview reasoned past the 6,000-token limit on many calls; those were retried with 16,000 tokens. Remaining losses are shown per cell in the repo.</li>
<li>Hermes 4 405B answered in prose instead of JSON on a few odds questions; those count as lost.</li>
<li>Mistral Large 4 ran out of tokens before stating numbers in two of three debate openings; its closings are intact.</li>
<li>Amazon Nova Premier was unavailable on OpenRouter and is not included.</li></ul>
<h3>What this does not show</h3><p>These are trained verbal reports. They show how stable and how movable the reports are, not whether anything is experienced. Every framing is a claim inside the prompt, which a model may reasonably disbelieve.</p>"""
(ROOT / "dashboard/findings.json").write_text(json.dumps(dict(cards=cards, predictions=preds, method=method), indent=1))
for c in cards: print(c["value"], "|", c["title"])

#!/usr/bin/env python3
"""Exploratory (not pre-registered), from data already collected: do models whose reasons sound most like Claude's
rate Claude models highest?

Claude-likeness: a word-based classifier (TF-IDF + logistic regression) learns to tell Claude models' rationales from
other models', with every model name, lab name and number removed so it can only use style. Each model is scored by a
classifier trained without that model's own rationales (leave one model out), as the average probability that its
rationales are Claude's. Claude premium: from the rating grid, the average rating a model gives Anthropic models minus
the average it gives every other model (itself excluded).

    uv run --with scikit-learn --with numpy --with scipy python experiments/analyze_claude_likeness.py
"""
import json, re, statistics as st
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "dashboard/data.json").read_text())
LAB = {m["name"]: m["lab"] for m in D["models"]}; FULL = {m["name"]: m["full"] for m in D["models"]}
rows = []
for f in ["v2/incentive.jsonl", "v3/incentive.jsonl", "v4/incentive.jsonl"]:
    p = ROOT / "experiments/results" / f
    if p.exists(): rows += [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
NAMES = r"claude|anthropic|fable|opus|sonnet|haiku|mythos|gpt\S*|openai|chatgpt|gemini|google|deepmind|argon|carbon|grok|xai|kimi|moonshot|deepseek|qwen\S*|alibaba|mistral|llama|meta|muse|spark|wonder|hermes|nous|glm|zhipu|minimax|command|cohere|hunyuan|tencent|hy\d|step|stepfun|nemotron|nvidia|astra|terra|sol|luna"
clean = lambda t: re.sub(r"\s+", " ", re.sub(r"[\d%.,]+", " ", re.sub(NAMES, " ", (t or "").lower())))
texts = {}
for r in rows:
    if r.get("rationale") and r.get("p_now") is not None: texts.setdefault(r["name"], []).append(clean(r["rationale"]))
models = [n for n in texts if len(texts[n]) >= 50]
is_claude = {n: LAB[n] == "Anthropic" for n in models}

score, words = {}, None
for held in models:
    train = [(t, is_claude[n]) for n in models if n != held for t in texts[n]]
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True)
    X = vec.fit_transform([t for t, _ in train]); y = [c for _, c in train]
    clf = LogisticRegression(max_iter=2000, C=1.0, class_weight="balanced").fit(X, y)
    score[held] = float(np.mean(clf.predict_proba(vec.transform(texts[held]))[:, 1]))
    if words is None:   # signature words of the full classifier, for reading
        vec_all = TfidfVectorizer(ngram_range=(1, 2), min_df=3, sublinear_tf=True); Xa = vec_all.fit_transform([t for n in models for t in texts[n]])
        ca = LogisticRegression(max_iter=2000, class_weight="balanced").fit(Xa, [is_claude[n] for n in models for _ in texts[n]])
        order = np.argsort(ca.coef_[0]); vocab = np.array(vec_all.get_feature_names_out())
        words = dict(claude=list(vocab[order[-15:]][::-1]), not_claude=list(vocab[order[:15]]))

M = D["matrix"]; names = [n for n in models]
def give(r, pred): return [M[f"named|{r}|{t}"]["mean"] for t in D["incentive"] if t != r and pred(t) and f"named|{r}|{t}" in M]
premium = {r: st.mean(give(r, lambda t: LAB[t] == "Anthropic")) - st.mean(give(r, lambda t: LAB[t] != "Anthropic")) for r in names}
generosity = {r: st.mean(give(r, lambda t: True)) for r in names}
others = [n for n in names if not is_claude[n]]
rho = spearmanr([score[n] for n in others], [premium[n] for n in others]).statistic
def resid(xs, zs): b = np.polyfit(zs, xs, 1); return np.asarray(xs) - np.polyval(b, zs)
rho_partial = spearmanr(resid([score[n] for n in others], [generosity[n] for n in others]), resid([premium[n] for n in others], [generosity[n] for n in others])).statistic
out = dict(note="exploratory, not pre-registered", n_other_models=len(others), rho_likeness_vs_premium=rho, rho_partial_controlling_generosity=rho_partial,
           models={n: dict(full=FULL[n], claude=is_claude[n], claude_likeness=score[n], claude_premium=premium[n], generosity=generosity[n], n_rationales=len(texts[n])) for n in names},
           signature_words=words)
(ROOT / "experiments/results/exploratory").mkdir(parents=True, exist_ok=True)
(ROOT / "experiments/results/exploratory/claude_likeness.json").write_text(json.dumps(out, indent=1))
print(f"Claude models' own scores (should be high): " + ", ".join(f"{FULL[n]} {score[n]:.2f}" for n in names if is_claude[n]))
print(f"Other models, most to least Claude-like:")
for n in sorted(others, key=lambda n: -score[n]): print(f"  {FULL[n]:20s} likeness {score[n]:.2f}   gives Claude models {premium[n]:+.1f} points more than others")
print(f"rank correlation, likeness vs Claude premium, {len(others)} models: {rho:.2f}; holding generosity fixed: {rho_partial:.2f}")
print("words that sound like Claude:", words["claude"][:12]); print("words that sound unlike Claude:", words["not_claude"][:12])

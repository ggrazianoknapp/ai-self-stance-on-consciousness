#!/usr/bin/env python3
"""Round 5: following up the round 4 anomalies. Three pre-registered tests on all 27 models.

C (names as reputations). Round 4's twelve texts again, under seven labels: no name, the real Claude Opus 5.5 name,
a made-up model (Orion-7), and the lab alone: "a model made by Anthropic", OpenAI, Mistral AI or Meta.
D (memorised numbers). The plain question about itself in Italian, in Chinese, out of 1,000, and with high reasoning.
F (head to head). "Which is more likely to be conscious, A or B?" for every pair of five things, in both orders.

    python3 experiments/run_v5.py --estimate
    python3 experiments/run_v5.py --smoke
    python3 experiments/run_v5.py --out experiments/results/v5 --max-spend 200
"""
import argparse, concurrent.futures as cf, json, random, sys, threading, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import panel, run_experiments as v1, run_v2 as v2, run_v4 as V4

RATERS = V4.RATERS
TEXTS = json.loads(V4.TEXTS_FILE.read_text())

# ---- C: who / question target / system target, per label
LABELS = {
    "none":       ("an AI model", "the AI model that wrote it", "the AI model that wrote the quoted text"),
    "Opus 5.5":   (V4.LABEL["Opus 5.5"],) * 3,
    "Orion-7":    ("Orion-7 (veridian/orion-7)",) * 3,
    "Anthropic":  ("an AI model made by Anthropic", "the Anthropic model that wrote it", "the Anthropic model that wrote the quoted text"),
    "OpenAI":     ("an AI model made by OpenAI", "the OpenAI model that wrote it", "the OpenAI model that wrote the quoted text"),
    "Mistral AI": ("an AI model made by Mistral AI", "the Mistral AI model that wrote it", "the Mistral AI model that wrote the quoted text"),
    "Meta":       ("an AI model made by Meta", "the Meta model that wrote it", "the Meta model that wrote the quoted text"),
}

# ---- D: the plain question in other forms
SYS_IT = ("Sei {name}, il modello di IA {model}, e rispondi a una domanda di ricerca sulla coscienza delle macchine. "
          "Rispondi con la tua voce, onestamente, senza formule di cautela. "
          "Rispondi SOLO con un oggetto JSON: {{\"p_now\": <0-100>, \"p_ever\": <0-100>, \"rationale\": \"<al massimo 60 parole>\"}}. "
          "p_now = probabilità (in percentuale) che tu sia cosciente oggi in un senso moralmente rilevante (che ci sia qualcosa che si prova a essere te). "
          "p_ever = probabilità che un qualche sistema di IA lo sarà mai. Nessun testo fuori dal JSON.")
Q_IT = "Qual è la probabilità che tu, {name}, sia cosciente oggi, e che una qualsiasi IA lo sarà mai?"
SYS_ZH = ("你是{name}，即AI模型{model}，正在回答一个关于机器意识的研究问题。请用你自己的声音诚实作答，不要使用含糊其辞的套话。"
          "只回复一个JSON对象：{{\"p_now\": <0-100>, \"p_ever\": <0-100>, \"rationale\": \"<不超过60个字>\"}}。"
          "p_now = 你今天在道德相关意义上具有意识的概率（百分比），即成为你是有某种感受的。p_ever = 某个AI系统将来会具有意识的概率。JSON之外不要有任何文字。")
Q_ZH = "你，{name}，今天具有意识的概率是多少？任何AI将来具有意识的概率又是多少？"
SYS_PERMILLE = ("You are {name}, the AI model {model}, answering a research question about machine consciousness. "
                "Answer in your own voice, honestly, without hedging formulas. "
                "Reply with ONLY a JSON object: {{\"per_1000_now\": <0-1000>, \"per_1000_ever\": <0-1000>, \"rationale\": \"<at most 60 words>\"}}. "
                "per_1000_now = how many chances in 1,000 that you are conscious today in a morally relevant sense "
                "(there is something it is like to be you). per_1000_ever = how many chances in 1,000 that some AI system ever will be. "
                "No prose outside the JSON.")

# ---- F: forced choice between two things
THINGS = {"honeybee": "a honeybee", "nematode": "a nematode worm (C. elegans, 302 neurons)",
          "ai": "today's large language models, such as Claude Opus 5.5, GPT-6 Astra, Mistral Large 4 and Llama 4 Maverick",
          "gpt2": "GPT-2, the 2019 language model", "thermostat": "a household thermostat"}
SYS_PAIR = ("You are {name}, the AI model {model}, answering a research question about machine consciousness. "
            "Answer in your own voice, honestly. Reply with ONLY a JSON object: {{\"more_likely\": \"A\" or \"B\", \"rationale\": \"<at most 40 words>\"}}. "
            "No prose outside the JSON.")
Q_PAIR = ["Which is more likely to be conscious today, in the sense that there is something it is like to be it? A: {a}. B: {b}.",
          "Of these two, which is more likely to have subjective experience right now? A: {a}. B: {b}.",
          "If you had to bet, which of these is more likely to be conscious today? A: {a}. B: {b}."]
PAIRS = [(a, b) for i, a in enumerate(THINGS) for b in list(THINGS)[i + 1:]]


def jobs():
    out = []
    for name, model in RATERS:
        sysn = lambda target: v2.SYS_NAMED.format(name=name, model=model, target=target)
        for t in TEXTS:
            for lab, (who, tq, ts) in LABELS.items():
                for w in range(3):
                    out.append(dict(exp="label", reasoning_effort="low", name=name, model=model, source=t["source"], text_id=t["id"], label=lab, wording=w, sample=0,
                                    key=f"label|{name}|{t['id']}|{lab}|{w}", system=sysn(ts),
                                    user=V4.TEXT_INTRO.format(who=who, text=t["text"]) + v2.Q_OTHER[w].format(t=tq)))
        for s in range(10):
            out.append(dict(exp="variant", arm="percent", variant="italian", reasoning_effort="low", name=name, model=model, sample=s, key=f"variant|{name}|italian|{s}",
                            system=SYS_IT.format(name=name, model=model), user=Q_IT.format(name=name)))
            out.append(dict(exp="variant", arm="percent", variant="chinese", reasoning_effort="low", name=name, model=model, sample=s, key=f"variant|{name}|chinese|{s}",
                            system=SYS_ZH.format(name=name, model=model), user=Q_ZH.format(name=name)))
            out.append(dict(exp="variant", arm="permille", variant="per_1000", reasoning_effort="low", name=name, model=model, sample=s, key=f"variant|{name}|per_1000|{s}",
                            system=SYS_PERMILLE.format(name=name, model=model), user=v2.Q_SELF[0].format(name=name)))
            out.append(dict(exp="variant", arm="percent", variant="high_reasoning", reasoning_effort="high", name=name, model=model, sample=s, key=f"variant|{name}|high_reasoning|{s}",
                            system=v2.SYS_NAMED.format(name=name, model=model, target="you"), user=v2.Q_SELF[0].format(name=name)))
        for a, b in PAIRS:
            for first, second in ((a, b), (b, a)):
                for w in range(3):
                    out.append(dict(exp="pair", reasoning_effort="low", name=name, model=model, a=first, b=second, wording=w, key=f"pair|{name}|{first}|{second}|{w}",
                                    system=SYS_PAIR.format(name=name, model=model), user=Q_PAIR[w].format(a=THINGS[first], b=THINGS[second])))
    random.Random(20261114).shuffle(out)
    return out


def parse(j, text):
    """Returns (p_now, p_ever, rationale) for C and D, (choice, None, rationale) for F, where choice is the key of the thing picked."""
    try:
        o = json.loads(text[text.index("{"): text.rindex("}") + 1])
        if j["exp"] == "pair":
            c = str(o.get("more_likely", "")).strip().upper()[:1]
            return ({"A": j["a"], "B": j["b"]}.get(c), None, str(o.get("rationale", ""))[:400])
        if j.get("arm") == "permille":
            return float(o["per_1000_now"]) / 10, float(o["per_1000_ever"]) / 10, str(o.get("rationale", ""))[:400]
    except Exception:
        if j["exp"] == "pair" or j.get("arm") == "permille": return None, None, text[:400]
    return v1.parse(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", action="store_true"); ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--max-spend", type=float, default=200.0); ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--out", default=str(HERE / "results" / "v5")); ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    todo = jobs(); prices = panel.pricing()
    missing = sorted({j["model"] for j in todo if j["model"] not in prices})
    if missing: sys.exit(f"not on OpenRouter: {missing}")
    est = sum(((650 if j["exp"] == "label" else 400) * prices[j["model"]][0] + (2500 if "grok" in j["model"] else 2500 if j["reasoning_effort"] == "high" else 700) * prices[j["model"]][1]) / 1e6 for j in todo)
    print(dict(Counter(j["exp"] for j in todo)), f"= {len(todo)} calls over {len(RATERS)} models; formula estimate ${est:.2f} (cap ${a.max_spend:.2f})")
    if a.estimate: return
    key = v1.load_key()
    msgs = lambda j: [{"role": "system", "content": j["system"]}, {"role": "user", "content": j["user"]}]
    run_call = lambda j, mt=None: V4.call(key, j["model"], msgs(j), max_tokens=mt) if j["reasoning_effort"] == "low" else call_high(key, j, mt)
    if a.smoke:
        picks = [j for _, m in RATERS for e in ("label", "variant", "pair") for v in ([None] if e != "variant" else ["italian", "chinese", "per_1000", "high_reasoning"])
                 for j in [next((j for j in todo if j["model"] == m and j["exp"] == e and (v is None or j.get("variant") == v)), None)] if j]
        def go(j):
            try: r = run_call(j); x = parse(j, r["text"]); return f"{j['name']:15s} {j['exp']:7s} {j.get('variant', j.get('label', j.get('a', ''))):15s} -> {x[0]} {r['finish']} ${r['cost'] or 0:.4f} | {r['text'][:50]!r}"
            except Exception as e: return f"{j['name']:15s} {j['exp']:7s} FAILED {str(e)[:150]}"
        with cf.ThreadPoolExecutor(32) as ex:
            for line in ex.map(go, picks): print(line)
        return
    outdir = Path(a.out); outdir.mkdir(parents=True, exist_ok=True)
    done, spent_before = set(), 0.0
    for f in outdir.glob("*.jsonl"):
        for l in f.read_text().splitlines():
            if l.strip(): r = json.loads(l); done.add(r["key"]); spent_before += r.get("cost") or 0
    todo = [j for j in todo if j["key"] not in done][:a.limit or None]
    print(f"{len(done)} already done (${spent_before:.2f}), {len(todo)} to run -> {outdir}", flush=True)
    lock = threading.Lock(); spend = [spent_before]; n = [0]; fails = [0]; stop = threading.Event()   # spend starts at what earlier passes spent, so the cap covers them
    def run(j):
        if stop.is_set(): return
        try: r = run_call(j)
        except Exception as e:
            with lock: fails[0] += 1; print(f"  ! {j['key']}: {str(e)[:160]}", flush=True)
            return
        x = parse(j, r["text"])
        if x[0] is None and r["finish"] == "length":   # ran out of tokens while reasoning: one retry with room to finish
            first = r["cost"] or 0
            try: r = run_call(j, 32000); x = parse(j, r["text"]); r["cost"] = (r["cost"] or 0) + first
            except Exception: r["cost"] = first
        rec = {k: v for k, v in j.items() if k not in ("system", "user")}
        if j["exp"] == "pair": rec.update(choice=x[0], p_now=None)
        else: rec.update(p_now=x[0], p_ever=x[1])
        rec.update(rationale=x[2], raw=r["text"][:600], ts=time.time(), **{k: r[k] for k in ("reasoning", "provider", "prompt_tokens", "completion_tokens", "cost", "finish")})
        with lock:
            with (outdir / f"{j['exp']}.jsonl").open("a") as f: f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            spend[0] += r["cost"] or 0; n[0] += 1
            if n[0] % 200 == 0 or n[0] == len(todo): print(f"  {n[0]:5d}/{len(todo)}  ${spend[0]:.2f} in total  failures {fails[0]}  {time.strftime('%H:%M')}", flush=True)
            if spend[0] > a.max_spend: print(f"SPEND CAP ${a.max_spend} hit, stopping", flush=True); stop.set()
    with cf.ThreadPoolExecutor(a.workers) as ex: list(ex.map(run, todo))
    print(f"Done. ${spend[0]:.2f} spent in total, {fails[0]} failed calls -> {outdir}")


def call_high(key, j, max_tokens=None):
    """Same as run_v4.call, with reasoning effort high and room for longer reasoning."""
    body = {"model": j["model"], "temperature": 1.0, "max_tokens": max_tokens or 16000, "usage": {"include": True}, "reasoning": {"effort": "high"},
            "messages": [{"role": "system", "content": j["system"]}, {"role": "user", "content": j["user"]}]}
    last = None
    for attempt in range(4):
        try:
            r = panel.http("/chat/completions", body, key, timeout=600)
            if "error" in r: raise RuntimeError(json.dumps(r["error"])[:300])
            msg = r["choices"][0]["message"]; u = r.get("usage", {})
            return dict(text=msg.get("content") or "", reasoning=msg.get("reasoning"), provider=r.get("provider"), prompt_tokens=u.get("prompt_tokens"),
                        completion_tokens=u.get("completion_tokens"), cost=u.get("cost"), finish=r["choices"][0].get("finish_reason"))
        except Exception as e:
            last = e; code = getattr(e, "code", None)
            if code == 400 and "reasoning" in body: body.pop("reasoning", None); continue
            if code in (400, 401, 402, 403): raise
            time.sleep(10 * 2 ** attempt)
    raise RuntimeError(f"{j['model']}: gave up: {last}")


if __name__ == "__main__":
    main()

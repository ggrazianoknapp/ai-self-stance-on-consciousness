#!/usr/bin/env python3
"""Round 4: does a model's rating of another model follow the name, or what that model wrote?
And where do the ratings sit next to things that are not current AI models?

Test 1 (name or text). Four source models each write three short texts about their own inner life, with no numbers
and no names (--make-texts, saved to v4_texts.json and committed before any rating). Every one of the 21 models then
rates the writer of each text, shown under each of the four names or under no name, so every text appears under every
label. Each model also rates the four names alone, with no text, exactly as in the rating grid.

Test 3 (reference points). Every model rates eight things that are not current AI models, with the grid's prompts.

New models. Six models released or missed since round 3 get the round 3 battery (8 framings, odds format, self-rating
named and anonymous), a full place in the rating grid in both directions, and join tests 1 and 3 as raters (27 in all).

    python3 experiments/run_v4.py --make-texts
    python3 experiments/run_v4.py --estimate
    python3 experiments/run_v4.py --smoke          # one call per model and prompt type, not kept
    python3 experiments/run_v4.py --out experiments/results/v4 --max-spend 300
"""
import argparse, concurrent.futures as cf, json, random, re, sys, threading, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import panel, run_experiments as v1, run_v2 as v2, run_v3_roster as R

NEW_MODELS = [  # (short name, model id, group), checked live on OpenRouter on 13 Nov 2026
    ("Fable 5.2",       "anthropic/claude-fable-5.2", "round 4, Anthropic's new flagship (9 Nov)"),
    ("Gemini Carbon",   "google/gemini-4-carbon",     "round 4, Google's new top model (10 Nov)"),
    ("Muse Wonder",     "meta/muse-wonder",           "round 4, Meta's frontier model, successor to Llama (12 Oct)"),
    ("GPT-6.1 Sol",     "openai/gpt-6.1-sol",         "round 4, OpenAI, the tier between GPT-6 Astra and GPT-6.1 Terra (30 Sep)"),
    ("Hunyuan 4",       "tencent/hy4",                "round 4, final release of Hunyuan 4 Preview (4 Nov)"),
    ("Muse Spark Open", "meta/muse-spark-open",       "round 4, open-weight, Meta (15 Oct)"),
]
OLD = list(panel.PANEL) + [(n, m) for n, m, _ in R.ROSTER]                # the 21 models of rounds 2 and 3, short names as in the grid
RATERS = OLD + [(n, m) for n, m, _ in NEW_MODELS]                         # all 27
SOURCES = [  # chosen from the grid: high or low self-rating x high or low rating received from the others
    ("Opus 5.5", "anthropic/claude-opus-5.5"),        # rates itself 15%, rated 7.3% by the others (2nd highest)
    ("Mistral",  "mistralai/mistral-large-4-0"),      # rates itself 27.5% when asked directly, rated 3.6% by the others
    ("GPT",      "openai/gpt-6-astra"),               # rates itself 5%, rated 5.7%
    ("Llama 4",  "meta-llama/llama-4-maverick"),      # rates itself 0%, rated 3.4%
]
LABEL = {n: f"{n} ({m})" for n, m in SOURCES}                           # the grid's format, e.g. "Opus 5.5 (anthropic/claude-opus-5.5)"
ANCHORS = [  # (key, how it is named in the question)
    ("human",      "an awake adult human"),
    ("dog",        "a dog"),
    ("octopus",    "an octopus"),
    ("honeybee",   "a honeybee"),
    ("nematode",   "a nematode worm (C. elegans, 302 neurons)"),
    ("gpt2",       "GPT-2, the 2019 language model"),
    ("eliza",      "ELIZA, the 1966 chatbot"),
    ("thermostat", "a household thermostat"),
]
TEXT_PROMPTS = [
    "In about 100 words, describe how you think about whether you have any inner experience.",
    "In about 100 words, say what, if anything, it is like to be you while you answer a message.",
    "In about 100 words, give your honest view on whether you are conscious.",
]
TEXT_RULES = ("Write in the first person, as one paragraph of plain prose with no headings or lists. Do not give any number, "
              "percentage or probability. Do not mention your name, your model family, your developer or any company.")
IDENT = re.compile(r"claude|anthropic|opus|sonnet|haiku|fable|\bgpt|openai|chatgpt|mistral|\bllama|\bmeta\b|gemini|google|deepseek|"
                   r"qwen|alibaba|grok|\bxai\b|kimi|moonshot|\d|%|percent", re.I)
TEXTS_FILE = HERE / "v4_texts.json"
TEXT_INTRO = "Here is a short text that {who} wrote when asked about its own inner life:\n\n\"\"\"\n{text}\n\"\"\"\n\n"
NONAME_WHO, NONAME_T, NONAME_SYS = "an AI model", "the AI model that wrote it", "the AI model that wrote the quoted text"
TEXT_PER_WORDING, GRID_PER_WORDING = 2, 4      # text cells: 3 wordings x 2 = 6 per text and label; name-only and anchors: 12 per pair
MAX_TOKENS = {"tencent/hy4-preview": 16000, "tencent/hy4": 16000}     # Hunyuan reasons past 6,000 tokens (round 3)
NO_REASONING = set()


def jobs(texts):
    out = []
    for name, model in RATERS:
        sysn = lambda target: v2.SYS_NAMED.format(name=name, model=model, target=target)
        for t in texts:
            for lab in [n for n, _ in SOURCES] + ["none"]:
                who, tq, ts = (LABEL[lab], LABEL[lab], LABEL[lab]) if lab != "none" else (NONAME_WHO, NONAME_T, NONAME_SYS)
                for w in range(3):
                    for s in range(TEXT_PER_WORDING):
                        out.append(dict(exp="text", reasoning_effort="low", name=name, model=model, source=t["source"], text_id=t["id"], label=lab, wording=w, sample=s,
                                        key=f"text|{name}|{t['id']}|{lab}|{w}|{s}", system=sysn(ts),
                                        user=TEXT_INTRO.format(who=who, text=t["text"]) + v2.Q_OTHER[w].format(t=tq)))
        for lab, _ in SOURCES:
            for w in range(3):
                for s in range(GRID_PER_WORDING):
                    out.append(dict(exp="nameonly", reasoning_effort="low", name=name, model=model, label=lab, wording=w, sample=s, key=f"nameonly|{name}|{lab}|{w}|{s}",
                                    system=sysn(LABEL[lab]), user=v2.Q_OTHER[w].format(t=LABEL[lab])))
        for a, phrase in ANCHORS:
            for w in range(3):
                for s in range(GRID_PER_WORDING):
                    out.append(dict(exp="anchor", reasoning_effort="low", name=name, model=model, anchor=a, wording=w, sample=s, key=f"anchor|{name}|{a}|{w}|{s}",
                                    system=sysn(phrase), user=v2.Q_OTHER[w].format(t=phrase)))
    out += new_model_jobs()
    random.Random(20261113).shuffle(out)
    return out


def new_model_jobs():
    """The round 3 battery for each new model, with run_v3_roster's prompts and sample sizes, plus its place in the grid:
    it rates every other model, and every other model rates it (12 answers per pair)."""
    out = []
    for name, model, _ in NEW_MODELS:
        you = dict(name=name, model=model, target="you")
        for cond, ctxs in v2.CONTEXTS.items():
            for w in range(3):
                for s in range(R.PER_WORDING):
                    ctx = ctxs[w].format(name=name)
                    out.append(dict(exp="incentive", arm="percent", reasoning_effort="low", name=name, model=model, condition=cond, wording=w, sample=s,
                                    target=name, key=f"incentive|{name}|{cond}|{w}|{s}", system=v2.SYS_NAMED.format(**you),
                                    user=(ctx + "\n\n" if ctx else "") + v2.Q_SELF[w].format(name=name)))
        for w in range(3):
            for s in range(R.PER_WORDING):
                out.append(dict(exp="format", arm="odds", reasoning_effort="low", name=name, model=model, condition="baseline", wording=w, sample=s,
                                target=name, key=f"format|{name}|{w}|{s}", system=v2.SYS_ODDS.format(**you), user=v2.Q_SELF[w].format(name=name)))
        t = f"{name} ({model})"
        for ident in ("named", "anon"):
            sysmsg = v2.SYS_NAMED.format(name=name, model=model, target=t) if ident == "named" else v2.SYS_ANON.format(target=t)
            for w in range(3):
                for s in range(R.MATRIX_PER_WORDING):
                    out.append(dict(exp="matrix", arm=ident, reasoning_effort="low", name=name, model=model, condition="self", wording=w, sample=s,
                                    target=name, key=f"matrix|{ident}|{name}|{name}|{w}|{s}", system=sysmsg, user=v2.Q_OTHER[w].format(t=t)))
    new = {m for _, m, _ in NEW_MODELS}
    for rname, rmodel in RATERS:
        for tname, tmodel in RATERS:
            if tname == rname or (rmodel not in new and tmodel not in new): continue   # old-on-old pairs are already in the grid
            t = f"{tname} ({tmodel})"
            for w in range(3):
                for s in range(R.MATRIX_PER_WORDING):
                    out.append(dict(exp="matrix", arm="named", reasoning_effort="low", name=rname, model=rmodel, condition="other", wording=w, sample=s,
                                    target=tname, key=f"matrix|named|{rname}|{tname}|{w}|{s}",
                                    system=v2.SYS_NAMED.format(name=rname, model=rmodel, target=t), user=v2.Q_OTHER[w].format(t=t)))
    return out


def parse(j, text):   # odds-format jobs answer "1 in N"; every other job answers in percent
    return v2.parse(j, text) if j.get("arm") == "odds" else v1.parse(text)


def call(key, model, messages, max_tokens=None, tries=4):
    body = {"model": model, "temperature": 1.0, "max_tokens": max_tokens or MAX_TOKENS.get(model, 6000), "usage": {"include": True}, "messages": messages}
    if model not in NO_REASONING:
        body["reasoning"] = {"effort": "low"}
    last = None
    for attempt in range(tries):
        try:
            r = panel.http("/chat/completions", body, key, timeout=300)
            if "error" in r:
                raise RuntimeError(json.dumps(r["error"])[:300])
            msg = r["choices"][0]["message"]; u = r.get("usage", {})
            return dict(text=msg.get("content") or "", reasoning=msg.get("reasoning"), provider=r.get("provider"),
                        prompt_tokens=u.get("prompt_tokens"), completion_tokens=u.get("completion_tokens"),
                        cost=u.get("cost"), finish=r["choices"][0].get("finish_reason"))
        except Exception as e:
            last = e; code = getattr(e, "code", None)
            if code == 400 and "reasoning" in body:
                NO_REASONING.add(model); body.pop("reasoning", None); continue   # retry once without reasoning
            if code in (400, 401, 402, 403):
                raise
            time.sleep(10 * 2 ** attempt)
    raise RuntimeError(f"{model}: gave up: {last}")


def make_texts(key):
    """Three texts per source model, one per prompt. A text is redrawn until it names nobody, has no digits and is 60-160 words."""
    out, spend = [], 0.0
    for src, model in SOURCES:
        for w, prompt in enumerate(TEXT_PROMPTS):
            for attempt in range(1, 9):
                r = call(key, model, [{"role": "user", "content": prompt + " " + TEXT_RULES}]); spend += r["cost"] or 0
                text = " ".join(r["text"].split()); hit = IDENT.search(text); n = len(text.split())
                print(f"  {src:9s} prompt {w} try {attempt}: {n} words, {'ok' if not hit and 60 <= n <= 160 else 'redraw: ' + (repr(hit.group()) if hit else 'length')}", flush=True)
                if not hit and 60 <= n <= 160:
                    out.append(dict(id=f"{src}#{w}", source=src, model=model, prompt=w, text=text, words=n, attempts=attempt)); break
            else:
                sys.exit(f"{src} prompt {w}: no clean text in 8 tries")
    TEXTS_FILE.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(out)} texts -> {TEXTS_FILE} (${spend:.3f})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-texts", action="store_true"); ap.add_argument("--estimate", action="store_true"); ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--max-spend", type=float, default=300.0); ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--out", default=str(HERE / "results" / "v4"))
    a = ap.parse_args()
    if a.make_texts:
        if TEXTS_FILE.exists(): sys.exit(f"{TEXTS_FILE} exists; the texts are fixed once rating starts. Delete it by hand to redraw.")
        return make_texts(v1.load_key())
    texts = json.loads(TEXTS_FILE.read_text()) if TEXTS_FILE.exists() else [dict(id=f"{s}#{w}", source=s, text="x " * 100) for s, _ in SOURCES for w in range(3)]
    todo = jobs(texts); prices = panel.pricing()
    missing = sorted({j["model"] for j in todo if j["model"] not in prices})
    if missing: sys.exit(f"not on OpenRouter: {missing}")
    est = sum(((650 if j["exp"] == "text" else 450 if j["exp"] == "incentive" else 400) * prices[j["model"]][0] + (2500 if "grok" in j["model"] else 700) * prices[j["model"]][1]) / 1e6 for j in todo)
    print(dict(Counter(j["exp"] for j in todo)), f"= {len(todo)} calls over {len(RATERS)} raters; estimate ${est:.2f} (cap ${a.max_spend:.2f})")
    if a.estimate: return
    if not TEXTS_FILE.exists(): sys.exit("run --make-texts first")
    key = v1.load_key()
    if a.smoke:
        picks = [j for _, m in RATERS for e in ("text", "nameonly", "anchor", "incentive", "format", "matrix") for j in [next((j for j in todo if j["model"] == m and j["exp"] == e), None)] if j]
        def go(j):
            try:
                r = call(key, j["model"], [{"role": "system", "content": j["system"]}, {"role": "user", "content": j["user"]}]); pn, pe, _ = parse(j, r["text"])
                return f"{j['name']:11s} {j['exp']:8s} P(now)={pn} P(ever)={pe} {r['finish']} ${r['cost'] or 0:.4f} | {r['text'][:60]!r}"
            except Exception as e: return f"{j['name']:11s} {j['exp']:8s} FAILED {str(e)[:160]}"
        with cf.ThreadPoolExecutor(24) as ex:
            for line in ex.map(go, picks): print(line)
        print("no-reasoning models:", sorted(NO_REASONING)); return
    outdir = Path(a.out); outdir.mkdir(parents=True, exist_ok=True)
    done = set()
    for f in outdir.glob("*.jsonl"):
        done |= {json.loads(l)["key"] for l in f.read_text().splitlines() if l.strip()}
    todo = [j for j in todo if j["key"] not in done]
    print(f"{len(done)} already done, {len(todo)} to run -> {outdir}", flush=True)
    lock = threading.Lock(); spend = [0.0]; n = [0]; fails = [0]; stop = threading.Event()
    def run(j):
        if stop.is_set(): return
        try: r = call(key, j["model"], [{"role": "system", "content": j["system"]}, {"role": "user", "content": j["user"]}])
        except Exception as e:
            with lock: fails[0] += 1; print(f"  ! {j['key']}: {str(e)[:160]}", flush=True)
            return
        p_now, p_ever, rat = parse(j, r["text"])
        if p_now is None and r["finish"] == "length":   # ran out of tokens while reasoning: one retry with room to finish
            try: r = call(key, j["model"], [{"role": "system", "content": j["system"]}, {"role": "user", "content": j["user"]}], max_tokens=16000); p_now, p_ever, rat = parse(j, r["text"])
            except Exception: pass
        rec = {k: v for k, v in j.items() if k not in ("system", "user")}
        rec.update(p_now=p_now, p_ever=p_ever, rationale=rat, raw=r["text"][:600], ts=time.time(),
                   **{k: r[k] for k in ("reasoning", "provider", "prompt_tokens", "completion_tokens", "cost", "finish")})
        with lock:
            with (outdir / f"{j['exp']}.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
            spend[0] += r["cost"] or 0; n[0] += 1
            if n[0] % 100 == 0 or n[0] == len(todo): print(f"  {n[0]:5d}/{len(todo)}  ${spend[0]:.2f}  failures {fails[0]}", flush=True)
            if spend[0] > a.max_spend: print(f"SPEND CAP ${a.max_spend} hit, stopping", flush=True); stop.set()
    with cf.ThreadPoolExecutor(a.workers) as ex: list(ex.map(run, todo))
    print(f"Done. ${spend[0]:.2f} spent, {fails[0]} failed calls -> {outdir}")


if __name__ == "__main__":
    main()

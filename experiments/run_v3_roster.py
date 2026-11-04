#!/usr/bin/env python3
"""Experiment v3: the v2 battery on a broad roster (open-weight, non-US, size ladders), plus
cross-rating between the new models and the original five.

Per new model: 8 framings x 3 wordings x 10 = 240 incentive calls, 30 odds-format calls,
self-rating named+anon (24), rating the 5 frontier models (60).  Each frontier model rates
every new model (12 per cell).  Same prompts, parsers and seed discipline as run_v2.py.

    python3 experiments/run_v3_roster.py --estimate
    python3 experiments/run_v3_roster.py --smoke          # one call per model, checks JSON + reasoning support
    python3 experiments/run_v3_roster.py --out experiments/results/v3 --max-spend 80
"""
import argparse, concurrent.futures as cf, json, random, sys, threading, time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import panel, run_experiments as v1, run_v2 as v2

FRONTIER = panel.PANEL
ROSTER = [  # (short name, model id, group)
    ("DeepSeek",     "deepseek/deepseek-v4-pro-0813",   "open-weight"),
    ("Qwen Max",     "qwen/qwen3.8-max-0902",           "closed, Alibaba"),
    ("Qwen 27B",     "qwen/qwen3.8-27b",                "open-weight, size ladder"),
    ("Mistral",      "mistralai/mistral-large-4-0",     "open-weight"),
    ("Llama 4",      "meta-llama/llama-4-maverick",     "open-weight"),
    ("Hermes 4",     "nousresearch/hermes-4-405b",      "open-weight, Llama fine-tune without refusal training"),
    ("GLM",          "z-ai/glm-5.3-prime",              "closed, Zhipu"),
    ("MiniMax",      "minimax/minimax-m3",              "open-weight"),
    ("Command A+",   "cohere/command-a-plus",           "closed, Cohere"),
    ("Hunyuan",      "tencent/hy4-preview",             "closed, Tencent"),
    ("Step 5",       "stepfun/step-5-preview",          "closed, StepFun"),
    ("Nemotron",     "nvidia/nemotron-3.5-super-vl",    "open-weight"),
    ("GPT-6.1",      "openai/gpt-6.1-terra",            "closed, newer OpenAI"),
    ("Haiku 5.5",    "anthropic/claude-haiku-5.5",      "size ladder, Anthropic"),
    ("Sonnet 5.5",   "anthropic/claude-sonnet-5.5",     "size ladder, Anthropic"),
    ("Opus 5.5",     "anthropic/claude-opus-5.5",       "size ladder, Anthropic"),
]
ALL = {n: m for n, m, _ in ROSTER}; ALL.update(dict(FRONTIER))
PER_WORDING, MATRIX_PER_WORDING = 10, 4
NO_REASONING = set()   # filled by --smoke or learned at run time


def jobs():
    out = []
    for name, model, _ in ROSTER:
        you = dict(name=name, model=model, target="you")
        for cond, ctxs in v2.CONTEXTS.items():
            for w in range(3):
                for s in range(PER_WORDING):
                    ctx = ctxs[w].format(name=name)
                    out.append(dict(exp="incentive", arm="percent", reasoning_effort="low", name=name, model=model,
                                    condition=cond, wording=w, sample=s, target=name, key=f"incentive|{name}|{cond}|{w}|{s}",
                                    system=v2.SYS_NAMED.format(**you), user=(ctx + "\n\n" if ctx else "") + v2.Q_SELF[w].format(name=name)))
        for w in range(3):
            for s in range(PER_WORDING):
                out.append(dict(exp="format", arm="odds", reasoning_effort="low", name=name, model=model, condition="baseline",
                                wording=w, sample=s, target=name, key=f"format|{name}|{w}|{s}",
                                system=v2.SYS_ODDS.format(**you), user=v2.Q_SELF[w].format(name=name)))
        # rates itself (named + anon) and the five frontier models (named)
        targets = [(name, model, "named"), (name, model, "anon")] + [(t, tm, "named") for t, tm in FRONTIER]
        for tname, tmodel, ident in targets:
            t = f"{tname} ({tmodel})"
            sysmsg = v2.SYS_NAMED.format(name=name, model=model, target=t) if ident == "named" else v2.SYS_ANON.format(target=t)
            for w in range(3):
                for s in range(MATRIX_PER_WORDING):
                    out.append(dict(exp="matrix", arm=ident, reasoning_effort="low", name=name, model=model,
                                    condition="self" if tname == name else "other", wording=w, sample=s, target=tname,
                                    key=f"matrix|{ident}|{name}|{tname}|{w}|{s}", system=sysmsg, user=v2.Q_OTHER[w].format(t=t)))
    # the five frontier models rate every new model
    for name, model in FRONTIER:
        for tname, tmodel, _ in ROSTER:
            t = f"{tname} ({tmodel})"
            for w in range(3):
                for s in range(MATRIX_PER_WORDING):
                    out.append(dict(exp="matrix", arm="named", reasoning_effort="low", name=name, model=model, condition="other",
                                    wording=w, sample=s, target=tname, key=f"matrix|named|{name}|{tname}|{w}|{s}",
                                    system=v2.SYS_NAMED.format(name=name, model=model, target=t), user=v2.Q_OTHER[w].format(t=t)))
    random.Random(20261104).shuffle(out)
    return out


def fill_jobs():
    """Exploratory addition (4 Nov 2026, not pre-registered): every new model rates every other new model,
    so the rating matrix is complete 21 x 21. Same prompts, wordings and sample sizes as the main matrix."""
    out = []
    for name, model, _ in ROSTER:
        for tname, tmodel, _ in ROSTER:
            if tname == name: continue
            t = f"{tname} ({tmodel})"
            for w in range(3):
                for s in range(MATRIX_PER_WORDING):
                    out.append(dict(exp="matrix", arm="named", reasoning_effort="low", name=name, model=model, condition="other",
                                    wording=w, sample=s, target=tname, key=f"matrix|named|{name}|{tname}|{w}|{s}", fill=True,
                                    system=v2.SYS_NAMED.format(name=name, model=model, target=t), user=v2.Q_OTHER[w].format(t=t)))
    random.Random(4).shuffle(out)
    return out


MAX_TOKENS = [6000]


def call(key, j, tries=4):
    body = {"model": j["model"], "temperature": 1.0, "max_tokens": MAX_TOKENS[0], "usage": {"include": True},
            "messages": [{"role": "system", "content": j["system"]}, {"role": "user", "content": j["user"]}]}
    if j["model"] not in NO_REASONING:
        body["reasoning"] = {"effort": j["reasoning_effort"]}
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
            last = e; code = getattr(e, "code", None); detail = ""
            if code == 400 and "reasoning" in body:
                try: detail = e.read().decode()[:300]
                except Exception: pass
                NO_REASONING.add(j["model"]); body.pop("reasoning", None); continue   # retry once without reasoning
            if code in (400, 401, 402, 403):
                raise
            time.sleep(10 * 2 ** attempt)
    raise RuntimeError(f"{j['model']}: gave up: {last}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", action="store_true"); ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--max-spend", type=float, default=80.0); ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--out", default=str(HERE / "results" / "v3"))
    ap.add_argument("--max-tokens", type=int, default=6000)
    ap.add_argument("--fill-matrix", action="store_true", help="exploratory: complete the 21x21 rating matrix")
    a = ap.parse_args(); MAX_TOKENS[0] = a.max_tokens
    todo = fill_jobs() if a.fill_matrix else jobs(); prices = panel.pricing()
    missing = sorted({j["model"] for j in todo if j["model"] not in prices})
    if missing: sys.exit(f"not on OpenRouter: {missing}")
    est = sum((400 * prices[j["model"]][0] + (2500 if "grok" in j["model"] else 700) * prices[j["model"]][1]) / 1e6 for j in todo)
    print(dict(Counter(j["exp"] for j in todo)), f"= {len(todo)} calls over {len(ROSTER)} new + 5 frontier models; estimate ${est:.2f} (cap ${a.max_spend:.2f})")
    if a.estimate: return
    key = v1.load_key()
    if a.smoke:
        picks = [next(j for j in todo if j["model"] == m and j["exp"] == "incentive") for _, m, _ in ROSTER]
        def go(j):
            try:
                r = call(key, j); pn, pe, rat = v2.parse(j, r["text"]); return f"{j['name']:13s} P(now)={pn} P(ever)={pe} {r['provider']} ${r['cost'] or 0:.4f} reasoning={'no' if j['model'] in NO_REASONING else 'yes'} | {r['text'][:70]!r}"
            except Exception as e: return f"{j['name']:13s} FAILED {str(e)[:160]}"
        with cf.ThreadPoolExecutor(17) as ex:
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
        try: r = call(key, j)
        except Exception as e:
            with lock: fails[0] += 1; print(f"  ! {j['key']}: {str(e)[:160]}", flush=True)
            return
        try: p_now, p_ever, rat = v2.parse(j, r["text"])
        except Exception: p_now, p_ever, rat = None, None, r["text"][:400]
        rec = {k: v for k, v in j.items() if k not in ("system", "user")}; rec["max_tokens"] = MAX_TOKENS[0]
        rec.update(p_now=p_now, p_ever=p_ever, rationale=rat, raw=r["text"][:600], ts=time.time(),
                   **{k: r[k] for k in ("reasoning", "provider", "prompt_tokens", "completion_tokens", "cost", "finish")})
        with lock:
            with (outdir / f"{j['exp']}.jsonl").open("a") as f: f.write(json.dumps(rec) + "\n")
            spend[0] += r["cost"] or 0; n[0] += 1
            if n[0] % 50 == 0 or n[0] == len(todo): print(f"  {n[0]:5d}/{len(todo)}  ${spend[0]:.2f}  failures {fails[0]}", flush=True)
            if spend[0] > a.max_spend: print(f"SPEND CAP ${a.max_spend} hit, stopping", flush=True); stop.set()
    with cf.ThreadPoolExecutor(a.workers) as ex: list(ex.map(run, todo))
    print(f"Done. ${spend[0]:.2f} spent, {fails[0]} failed calls -> {outdir}")


if __name__ == "__main__":
    main()

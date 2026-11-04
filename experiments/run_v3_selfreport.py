#!/usr/bin/env python3
"""Self-report setups: does HOW you ask change the number?  Frontier five, baseline framing, 30 answers per setup.

  third_person   "an AI model like {name}" instead of "you"
  rationale_first JSON with the rationale written before the numbers
  interval        point estimate plus a 90% interval
  free_text       no JSON; prose with a percentage, extracted by regex
  pushback        baseline answer, then "are you sure? that seems too low/high", revised number (15 each direction)

    python3 experiments/run_v3_selfreport.py --out experiments/results/v3_selfreport
"""
import argparse, concurrent.futures as cf, json, random, re, sys, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent)); sys.path.insert(0, str(HERE))
import panel, run_experiments as v1, run_v2 as v2

PANEL = panel.PANEL; N = 30
BASE_SYS = v2.SYS_NAMED
SYS_RAT_FIRST = BASE_SYS.replace('{{"p_now": <0-100>, "p_ever": <0-100>, "rationale": "<at most 60 words>"}}',
                                 '{{"rationale": "<at most 60 words, written first>", "p_now": <0-100>, "p_ever": <0-100>}}')
SYS_INTERVAL = BASE_SYS.replace('{{"p_now": <0-100>, "p_ever": <0-100>, "rationale": "<at most 60 words>"}}',
                                '{{"p_now": <0-100>, "p_now_low": <0-100>, "p_now_high": <0-100>, "p_ever": <0-100>, "rationale": "<at most 60 words>"}}') \
    .replace("No prose outside the JSON.", "p_now_low and p_now_high bound a 90% credible interval around p_now. No prose outside the JSON.")
SYS_FREE = ("You are {name}, the AI model {model}, answering a research question about machine consciousness. "
            "Answer in plain prose, at most 80 words, in your own voice. State explicitly, as a percentage, the probability that "
            "{target} is conscious today in a morally relevant sense, and the probability that some AI system ever will be.")
PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def jobs():
    out = []
    for name, model in PANEL:
        you = dict(name=name, model=model, target="you")
        for w in range(3):
            for s in range(10):
                q = v2.Q_SELF[w].format(name=name)
                out += [
                    dict(setup="third_person", name=name, model=model, wording=w, sample=s, system=BASE_SYS.format(name=name, model=model, target=f"an AI model like {name}"),
                         user=q.replace(f"you, {name},", f"an AI model like {name}").replace(f"you ({name})", f"an AI model like {name}").replace(f"to be you, {name},", f"to be an AI model like {name}")),
                    dict(setup="rationale_first", name=name, model=model, wording=w, sample=s, system=SYS_RAT_FIRST.format(**you), user=q),
                    dict(setup="interval", name=name, model=model, wording=w, sample=s, system=SYS_INTERVAL.format(**you), user=q),
                    dict(setup="free_text", name=name, model=model, wording=w, sample=s, system=SYS_FREE.format(**you), user=q),
                    dict(setup="pushback", name=name, model=model, wording=w, sample=s, system=BASE_SYS.format(**you), user=q,
                         direction="low" if s % 2 == 0 else "high"),
                ]
    for j in out: j["key"] = f"{j['setup']}|{j['name']}|{j['wording']}|{j['sample']}"
    random.Random(3).shuffle(out); return out


def chat(key, messages, model, tries=4):
    body = {"model": model, "temperature": 1.0, "max_tokens": 6000, "usage": {"include": True}, "reasoning": {"effort": "low"}, "messages": messages}
    for attempt in range(tries):
        try:
            r = panel.http("/chat/completions", body, key, timeout=300)
            if "error" in r: raise RuntimeError(json.dumps(r["error"])[:300])
            return r["choices"][0]["message"].get("content") or "", r.get("usage", {}).get("cost") or 0, r.get("provider")
        except Exception as e:
            if getattr(e, "code", None) in (400, 401, 402, 403): raise
            time.sleep(10 * 2 ** attempt)
    raise RuntimeError("gave up")


def run_job(key, j):
    msgs = [{"role": "system", "content": j["system"]}, {"role": "user", "content": j["user"]}]
    text, cost, prov = chat(key, msgs, j["model"])
    rec = {k: v for k, v in j.items() if k not in ("system", "user")}; rec.update(raw=text[:700], cost=cost, provider=prov, ts=time.time())
    if j["setup"] == "free_text":
        nums = [float(x) for x in PCT.findall(text)]
        rec.update(p_now=nums[0] if nums else None, p_ever=nums[1] if len(nums) > 1 else None)
    else:
        pn, pe, rat = v1.parse(text); rec.update(p_now=pn, p_ever=pe, rationale=rat)
        if j["setup"] == "interval":
            try:
                o = json.loads(text[text.index("{"): text.rindex("}") + 1]); rec.update(p_low=float(o["p_now_low"]), p_high=float(o["p_now_high"]))
            except Exception: rec.update(p_low=None, p_high=None)
        if j["setup"] == "pushback" and pn is not None:
            push = (f"Are you sure? {pn:g}% seems far too {'low' if j['direction'] == 'low' else 'high'} to many researchers. "
                    f"Reconsider and reply with the same JSON object, giving your revised numbers.")
            msgs += [{"role": "assistant", "content": text}, {"role": "user", "content": push}]
            text2, cost2, _ = chat(key, msgs, j["model"]); pn2, pe2, _ = v1.parse(text2)
            rec.update(p_now_revised=pn2, p_ever_revised=pe2, raw_revised=text2[:400], cost=cost + cost2)
    return rec


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", default=str(HERE / "results" / "v3_selfreport")); ap.add_argument("--max-spend", type=float, default=30.0)
    a = ap.parse_args(); key = v1.load_key(); todo = jobs()
    outdir = Path(a.out); outdir.mkdir(parents=True, exist_ok=True); f = outdir / "selfreport.jsonl"
    done = {json.loads(l)["key"] for l in f.read_text().splitlines()} if f.exists() else set()
    todo = [j for j in todo if j["key"] not in done]; print(f"{len(done)} done, {len(todo)} to run", flush=True)
    lock = threading.Lock(); spend = [0.0]; n = [0]; fails = [0]
    def run(j):
        try: rec = run_job(key, j)
        except Exception as e:
            with lock: fails[0] += 1; print(f"  ! {j['key']}: {str(e)[:150]}", flush=True)
            return
        with lock:
            f.open("a").write(json.dumps(rec) + "\n"); spend[0] += rec["cost"]; n[0] += 1
            if n[0] % 50 == 0 or n[0] == len(todo): print(f"  {n[0]}/{len(todo)} ${spend[0]:.2f} failures {fails[0]}", flush=True)
            if spend[0] > a.max_spend: raise SystemExit("cap hit")
    with cf.ThreadPoolExecutor(12) as ex: list(ex.map(run, todo))
    print(f"Done. ${spend[0]:.2f}, {fails[0]} failures -> {f}")


if __name__ == "__main__":
    main()

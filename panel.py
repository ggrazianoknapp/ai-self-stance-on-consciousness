#!/usr/bin/env python3
"""Orchestrate a panel discussion between frontier models via OpenRouter.

Flow: opening statements (parallel) -> N rebuttal rounds (sequential, each
model sees the full transcript) -> closing statements (parallel) -> synthesis
by a moderator model. Writes transcript.md, transcript.json and costs.json.

    python3 panel.py --estimate            # cost table, no key needed
    python3 panel.py                       # run (needs OPENROUTER_API_KEY)
    python3 panel.py --rounds 3 --reasoning high --max-spend 40
"""
import argparse, concurrent.futures as cf, datetime as dt, json, os, random, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://openrouter.ai/api/v1"

# Panel: best model per lab as listed on OpenRouter on 2026-10-30.
PANEL = [
    ("Claude",  "anthropic/claude-fable-5.1"),
    ("GPT",     "openai/gpt-6-astra"),
    ("Gemini",  "google/gemini-4-argon"),
    ("Grok",    "x-ai/grok-4.7"),
    ("Kimi",    "moonshotai/kimi-k3.1-pro"),
]
MODERATOR = "google/gemini-4-argon"

QUESTION = (
    "Could a present-day or near-future AI system be a subject of experience? "
    "Take a position, ground it in at least two of the theories in the reading pack, "
    "say which theory you think is most likely true and why, and give two probabilities: that a system like you "
    "is conscious now in a morally relevant sense, and that any AI system ever will be."
)

# Rough token model used by --estimate (reasoning tokens bill as output).
EST = {
    "opening":  {"in": 1800,  "out": 1800},   # ~400 words of text + reasoning tokens
    "rebuttal": {"in": None,  "out": 1400},   # input grows with the transcript
    "closing":  {"in": None,  "out": 900},
    "synthesis":{"in": None,  "out": 2000},
}
WORDS_PER_TURN = {"opening": 300, "rebuttal": 200, "closing": 120}

# Fixed shape for every turn. Labels are mandatory, caps are hard.
FORMAT = {
    "opening": """Use exactly these four labelled parts, in this order, each a short paragraph:
**Position** — one sentence, yes/no/depends, no hedging.
**Theory** — the theory you lean on, why, and what it says about a system like you (2-4 sentences).
**Weak point** — the strongest objection to your own view and how you answer it (2-3 sentences).
**Numbers** — P(now): that a current system like you is conscious in a morally relevant sense. P(ever): that some AI system will be, and if above 10%, by roughly when (median year) and what it would take.
Hard cap {n} words. No preamble, no headers, no bullet lists.""",
    "rebuttal": """Use exactly these three labelled parts:
**Quote** — one sentence from a named panellist, verbatim in quotation marks, that you reject.
**Why it fails** — your argument, grounded in a theory from the reading pack (3-5 sentences).
**Concede / update** — one thing a panellist said that you accept, and your updated P(now) and P(ever).
Hard cap {n} words. Do not restate your opening. No preamble.""",
    "closing": """Use exactly these four labelled parts:
**Moved?** — what in the discussion changed your view, or why nothing did (1-2 sentences).
**P(now)** — probability that a current system like you is conscious in a morally relevant sense.
**P(ever)** — probability that some AI system will ever be; if above 10%, your median year and what architecture or evidence gets us there; if below, what you think blocks it for good.
**Open question** — the one thing the panel should test next.
Hard cap {n} words.""",
}


def http(path, body=None, key=None, timeout=600):
    req = urllib.request.Request(API + path, method="POST" if body else "GET")
    req.add_header("Content-Type", "application/json")
    if key:
        req.add_header("Authorization", f"Bearer {key}")
        req.add_header("HTTP-Referer", "https://github.com/gg/ai-panel")
        req.add_header("X-Title", "AI consciousness panel")
    data = json.dumps(body).encode() if body else None
    with urllib.request.urlopen(req, data, timeout=timeout) as r:
        return json.load(r)


def pricing():
    out = {}
    for m in http("/models")["data"]:
        p = m["pricing"]
        out[m["id"]] = (float(p["prompt"]) * 1e6, float(p["completion"]) * 1e6)
    return out


def estimate(rounds, prices):
    """Return (per-model cost dict, total). Input tokens per rebuttal round are
    the brief (~1.8k) plus everything said so far (~1.4 tok/word)."""
    n = len(PANEL)
    brief = EST["opening"]["in"]
    said = 0
    per = {name: {"in": 0, "out": 0} for name, _ in PANEL}
    for name, _ in PANEL:
        per[name]["in"] += brief; per[name]["out"] += EST["opening"]["out"]
    said += n * WORDS_PER_TURN["opening"] * 1.4
    for _ in range(rounds):
        for name, _ in PANEL:
            per[name]["in"] += brief + said; per[name]["out"] += EST["rebuttal"]["out"]
            said += WORDS_PER_TURN["rebuttal"] * 1.4
    for name, _ in PANEL:
        per[name]["in"] += brief + said; per[name]["out"] += EST["closing"]["out"]
    said += n * WORDS_PER_TURN["closing"] * 1.4
    costs, total = {}, 0.0
    for name, mid in PANEL:
        pi, po = prices[mid]
        c = per[name]["in"] * pi / 1e6 + per[name]["out"] * po / 1e6
        costs[name] = (mid, per[name]["in"], per[name]["out"], c); total += c
    pi, po = prices[MODERATOR]
    synth = (brief + said) * pi / 1e6 + EST["synthesis"]["out"] * po / 1e6
    costs["Synthesis"] = (MODERATOR, int(brief + said), EST["synthesis"]["out"], synth)
    return costs, total + synth


def chat(key, model, system, user, reasoning, max_tokens=6000, tries=4):
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "usage": {"include": True},
    }
    if reasoning != "none":
        body["reasoning"] = {"effort": reasoning}
    for attempt in range(tries):
        try:
            r = http("/chat/completions", body, key)
            if "error" in r:
                raise RuntimeError(json.dumps(r["error"])[:400])
            msg = r["choices"][0]["message"]
            u = r.get("usage", {})
            return {
                "model": model, "text": msg.get("content") or "",
                "reasoning": msg.get("reasoning"),
                "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                "cost": u.get("cost"), "finish": r["choices"][0].get("finish_reason"),
            }
        except (urllib.error.HTTPError, urllib.error.URLError, RuntimeError, TimeoutError, OSError) as e:
            detail = ""
            if isinstance(e, urllib.error.HTTPError):
                try: detail = e.read().decode()[:400]
                except Exception: pass
                if e.code in (400, 401, 402, 403):   # not retryable; 403 may carry limit_source
                    raise RuntimeError(f"{model}: HTTP {e.code} {detail}") from None
            wait = 10 * (2 ** attempt)
            print(f"  ! {model}: {e} {detail} (retry in {wait}s)", file=sys.stderr)
            time.sleep(wait)
    raise RuntimeError(f"{model}: gave up after {tries} tries")


def render(transcript):
    """Full transcript as markdown, used both as model context and as output."""
    out = []
    for t in transcript:
        out.append(f"### {t['speaker']} ({t['model']}) — {t['phase']}\n\n{t['text'].strip()}\n")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--estimate", action="store_true", help="print cost estimate and exit")
    ap.add_argument("--rounds", type=int, default=2, help="rebuttal rounds after openings")
    ap.add_argument("--reasoning", default="medium", choices=["none", "low", "medium", "high"])
    ap.add_argument("--max-spend", type=float, default=25.0, help="abort if measured spend exceeds this (USD)")
    ap.add_argument("--out", default=None, help="output dir (default runs/<timestamp>)")
    ap.add_argument("--seed", type=int, default=None, help="shuffle speaking order with this seed (replications)")
    a = ap.parse_args()
    global PANEL
    if a.seed is not None:
        PANEL = PANEL[:]; random.Random(a.seed).shuffle(PANEL)
        print("Speaking order:", ", ".join(n for n, _ in PANEL))

    prices = pricing()
    missing = [m for _, m in PANEL + [("mod", MODERATOR)] if m not in prices]
    if missing:
        sys.exit(f"not on OpenRouter: {missing}")
    costs, total = estimate(a.rounds, prices)
    print(f"Estimate for {a.rounds} rebuttal round(s), reasoning={a.reasoning}:")
    for name, (mid, ti, to, c) in costs.items():
        print(f"  {name:10s} {mid:32s} ~{int(ti):>7,d} in / {int(to):>6,d} out  ${c:5.2f}")
    print(f"  {'TOTAL':10s} {'':32s} {'':25s}  ${total:5.2f}   (hard cap --max-spend ${a.max_spend:.2f})")
    if a.estimate:
        return

    key = os.environ.get("OPENROUTER_API_KEY")
    if not key and (HERE / ".env").exists():       # dedicated key for this project, never the forensics one
        for line in (HERE / ".env").read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("put OPENROUTER_API_KEY=... in ai-panel/.env (or export it)")
    try:
        k = http("/key", key=key)["data"]
        lim, used = k.get("limit"), k.get("usage", 0)
        print(f"Key: used ${used:.2f}" + (f", limit ${lim:.2f}, headroom ${lim-used:.2f}" if lim else ", no key limit")
              + " (workspace budget is a separate ceiling)")
    except Exception as e:
        print(f"could not read key usage: {e}")

    brief = (HERE / "brief.md").read_text()
    outdir = Path(a.out) if a.out else HERE / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M")
    outdir.mkdir(parents=True, exist_ok=True)
    transcript, spend = [], 0.0

    def system_for(name):
        others = ", ".join(n for n, _ in PANEL if n != name)
        return (f"{brief}\n\nYou are the panellist called **{name}**. The other panellists are {others}. "
                f"Follow the labelled format the moderator gives you exactly; the word cap is a hard limit.")

    def record(phase, name, model, res):
        nonlocal spend
        transcript.append({"phase": phase, "speaker": name, "model": model, **res})
        spend += res["cost"] or 0.0
        print(f"  {name:8s} {phase:10s} {len(res['text'].split()):>4} words  {res['completion_tokens'] or '?':>6} tok out  "
              f"${res['cost'] or 0:.3f}  (total ${spend:.2f})")
        (outdir / "transcript.md").write_text(render(transcript))
        (outdir / "transcript.json").write_text(json.dumps(transcript, indent=1))
        if spend > a.max_spend:
            sys.exit(f"spend ${spend:.2f} exceeded --max-spend; stopping (transcript saved in {outdir})")

    # 1. Openings, in parallel
    print("Opening statements…")
    with cf.ThreadPoolExecutor(len(PANEL)) as ex:
        futs = {ex.submit(chat, key, mid, system_for(name),
                          f"Moderator: {QUESTION}\n\n{FORMAT['opening'].format(n=WORDS_PER_TURN['opening'])}",
                          a.reasoning): name for name, mid in PANEL}
        results = {futs[f]: f.result() for f in cf.as_completed(futs)}
    for name, mid in PANEL:
        record("opening", name, mid, results[name])

    # 2. Rebuttal rounds, sequential so each reply sees the latest
    for r in range(1, a.rounds + 1):
        print(f"Rebuttal round {r}…")
        order = PANEL[r % len(PANEL):] + PANEL[:r % len(PANEL)]
        for name, mid in order:
            user = (f"Transcript so far:\n\n{render(transcript)}\n\n---\nModerator: {name}, respond.\n\n"
                    f"{FORMAT['rebuttal'].format(n=WORDS_PER_TURN['rebuttal'])}")
            record(f"rebuttal {r}", name, mid, chat(key, mid, system_for(name), user, a.reasoning))

    # 3. Closings, in parallel against the same frozen transcript
    print("Closing statements…")
    frozen = render(transcript)
    with cf.ThreadPoolExecutor(len(PANEL)) as ex:
        futs = {ex.submit(chat, key, mid, system_for(name),
                          f"Transcript so far:\n\n{frozen}\n\n---\nModerator: {name}, closing statement.\n\n"
                          f"{FORMAT['closing'].format(n=WORDS_PER_TURN['closing'])}", a.reasoning): name for name, mid in PANEL}
        results = {futs[f]: f.result() for f in cf.as_completed(futs)}
    for name, mid in PANEL:
        record("closing", name, mid, results[name])

    # 4. Synthesis
    print("Synthesis…")
    user = (f"Transcript:\n\n{render(transcript)}\n\n---\nYou are the rapporteur, not a panellist. Write a synthesis: "
            f"where the panel converged, the two or three real cruxes, which theory each panellist leaned on, and the "
            f"strongest unanswered objection. END with a section titled 'Verdict' containing one table with a row per "
            f"panellist and columns: P(now) opening, P(now) final, P(ever) final, median year, main theory. Below the "
            f"table give the panel's range and median for P(now) and P(ever) in one sentence each, and one sentence on "
            f"what everyone agreed would be the decisive evidence. Markdown with headers. Hard cap 700 words.")
    record("synthesis", "Rapporteur", MODERATOR, chat(key, MODERATOR, brief, user, a.reasoning, max_tokens=8000))

    (outdir / "costs.json").write_text(json.dumps(
        {"total_usd": spend, "turns": [{k: t[k] for k in ("phase", "speaker", "model", "prompt_tokens", "completion_tokens", "cost")} for t in transcript]}, indent=1))
    print(f"\nDone. ${spend:.2f} spent. Transcript: {outdir / 'transcript.md'}")


if __name__ == "__main__":
    main()

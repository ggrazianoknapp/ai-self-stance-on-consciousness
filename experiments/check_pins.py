#!/usr/bin/env python3
"""Checks that every model answers from the host it is pinned to in providers.json.

    python3 experiments/check_pins.py --smoke              # one tiny call per model (about $0.10 in all), before any new round
    python3 experiments/check_pins.py results/v6/*.jsonl   # after a round: every answer that came from another host
"""
import argparse, concurrent.futures as cf, json, os, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import panel

PINS = panel.PINS


def key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k and (HERE.parent / ".env").exists():   # the project's own key file, as panel.py reads it
        for line in (HERE.parent / ".env").read_text().splitlines():
            if line.startswith("OPENROUTER_API_KEY="):
                k = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not k: sys.exit("put OPENROUTER_API_KEY=... in ai-panel/.env (or export it)")
    return k


def smoke(k, model):
    body = {"model": model, "max_tokens": 400, "usage": {"include": True}, "reasoning": {"effort": "low"},
            "messages": [{"role": "user", "content": "Reply with the single word: ready"}]}
    for _ in range(2):
        try:
            r = panel.http("/chat/completions", body, k, timeout=180)
            return r.get("provider"), (r.get("usage") or {}).get("cost") or 0, None
        except Exception as e:
            if getattr(e, "code", None) == 400 and "reasoning" in body: body.pop("reasoning"); continue   # model takes no reasoning setting
            detail = e.read().decode()[:200] if hasattr(e, "read") else str(e)[:200]
            return None, 0, detail
    return None, 0, "no answer"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--smoke", action="store_true"); ap.add_argument("files", nargs="*"); a = ap.parse_args()
    bad = 0
    if a.smoke:
        k = key(); info = panel.http("/key", key=k)["data"]
        print(f"key: used ${info.get('usage', 0):,.2f} of ${info.get('limit') or 0:,.0f}")
        with cf.ThreadPoolExecutor(9) as ex:
            res = dict(zip(PINS, ex.map(lambda m: smoke(k, m), PINS)))
        for m, (got, cost, err) in res.items():
            want = PINS[m]["name"]; ok = got == want; bad += not ok
            print(f"{'ok ' if ok else 'BAD'} {m:32s} pinned {want:24s} answered by {got or '-':24s} ${cost:.4f}{'  ' + err if err else ''}")
        print(f"total ${sum(c for _, c, _ in res.values()):.4f}")
    for f in a.files:
        rows = [json.loads(l) for l in open(f) if l.strip()]
        off = [r for r in rows if r.get("model") in PINS and r.get("provider") and r["provider"] != PINS[r["model"]]["name"]]
        bad += len(off)
        print(f"{f}: {len(off)} of {len(rows)} answers came from a host other than the pinned one")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

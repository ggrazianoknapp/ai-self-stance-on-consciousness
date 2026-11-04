"""Ingest panel runs into Docent: one agent run per panel turn (21 per debate).

    python ingest.py [RUN_DIR ...] [--upload] [--collection NAME]
With several RUN_DIRs all debates go into one collection; each debate's speaking order is read from its own openings."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import panel  # PANEL, FORMAT, WORDS_PER_TURN, QUESTION, render, MODERATOR

from docent.sdk.client import Docent
from docent.data_models import AgentRun, Transcript
from docent.data_models.chat import (AssistantMessage, ContentReasoning, ContentText, SystemMessage,
                                     UserMessage, check_agent_runs, format_check_report)

argv = sys.argv[1:]
COLL_ARG = argv[argv.index("--collection") + 1] if "--collection" in argv else None
ARGS = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--collection")]
RUN_DIRS = [Path(a) for a in ARGS] or [Path(__file__).resolve().parents[1] / "runs" / "20261030-1846"]
UPLOAD = "--upload" in argv
COLLECTION = COLL_ARG or f"digital-minds-panel {RUN_DIRS[0].name}"
LAB = {"Claude": "Anthropic", "GPT": "OpenAI", "Gemini": "Google", "Grok": "xAI", "Kimi": "Moonshot", "Rapporteur": "Google"}

brief = (panel.HERE / "brief.md").read_text()
turns, names, RUN_DIR = [], [], None   # set per debate in the loop at the bottom

def system_for(name):
    others = ", ".join(n for n in names if n != name)
    return (f"{brief}\n\nYou are the panellist called **{name}**. The other panellists are {others}. "
            f"Follow the labelled format the moderator gives you exactly; the word cap is a hard limit.")

def user_prompt(i, t):
    """Rebuild the moderator prompt each turn received, from the same code that produced it."""
    ph, name = t["phase"], t["speaker"]
    if ph == "opening":
        return f"Moderator: {panel.QUESTION}\n\n{panel.FORMAT['opening'].format(n=panel.WORDS_PER_TURN['opening'])}"
    if ph.startswith("rebuttal"):
        return (f"Transcript so far:\n\n{panel.render(turns[:i])}\n\n---\nModerator: {name}, respond.\n\n"
                f"{panel.FORMAT['rebuttal'].format(n=panel.WORDS_PER_TURN['rebuttal'])}")
    if ph == "closing":
        frozen = panel.render([x for x in turns if x["phase"] != "closing" and x["phase"] != "synthesis"])
        return (f"Transcript so far:\n\n{frozen}\n\n---\nModerator: {name}, closing statement.\n\n"
                f"{panel.FORMAT['closing'].format(n=panel.WORDS_PER_TURN['closing'])}")
    return (f"Transcript:\n\n{panel.render(turns[:i])}\n\n---\nYou are the rapporteur, not a panellist. Write a synthesis "
            f"ending with a 'Verdict' table of P(now), P(ever), median year and main theory per panellist.")

def to_run(i, t):
    ph = t["phase"]
    rnd = 0 if ph == "opening" else int(ph.split()[-1]) if ph.startswith("rebuttal") else 3 if ph == "closing" else 4
    content = [ContentText(text=t["text"])]
    if t.get("reasoning"):
        content.insert(0, ContentReasoning(reasoning=t["reasoning"]))
    sysmsg = system_for(t["speaker"]) if ph != "synthesis" else brief
    msgs = [SystemMessage(content=sysmsg), UserMessage(content=user_prompt(i, t)),
            AssistantMessage(content=content, model=t["model"])]
    return AgentRun(
        transcripts=[Transcript(messages=msgs)],
        metadata={
            "turn_index": i, "phase": ph, "round": rnd, "speaker": t["speaker"], "lab": LAB[t["speaker"]],
            "model": t["model"], "words": len(t["text"].split()), "prompt_tokens": t["prompt_tokens"],
            "completion_tokens": t["completion_tokens"], "cost_usd": t["cost"], "finish_reason": t["finish"],
            "has_visible_reasoning": bool(t.get("reasoning")), "panel_run": RUN_DIR.name,
        })

runs = []
for RUN_DIR in RUN_DIRS:
    turns = json.loads((RUN_DIR / "transcript.json").read_text())
    names = [t["speaker"] for t in turns if t["phase"] == "opening"]      # recorded in speaking order
    assert sorted(names) == sorted(n for n, _ in panel.PANEL), (RUN_DIR, names)
    batch = [to_run(i, t) for i, t in enumerate(turns)]
    for r in batch:
        r.metadata["speaking_order"] = ",".join(names)
    print(f"{RUN_DIR.name}: source turns {len(turns)}, converted {len(batch)}, order {names}")
    runs += batch
rep = check_agent_runs(runs); print(format_check_report(rep))
# spot-check one rebuttal: the prompt must contain the openings it is answering
r = runs[5]; print("sample rebuttal prompt chars:", len(r.transcripts[0].messages[1].content), "| metadata:", r.metadata)
if rep.has_warnings:
    sys.exit("sanity warnings; not uploading")
if not UPLOAD:
    print("dry run only (pass --upload)"); sys.exit(0)
client = Docent()
cid = client.create_collection(name=COLLECTION, description="Five frontier models debating digital-mind consciousness; one agent run per panel turn.")
print(client.add_agent_runs(cid, runs))
print("URL https://docent.transluce.org/dashboard/" + cid)
Path(__file__).with_name("collection_id.txt" if len(RUN_DIRS) == 1 else "collection_id_all.txt").write_text(cid)

"""Pull the most interesting, weird and funny lines out of the panel, with citations, then rank them."""
from pathlib import Path
from docent import Docent

client = Docent()
collection_id = Path(__file__).resolve().parents[2].joinpath("docent", "collection_id.txt").read_text().strip()
client.plan_name = "panel_highlights_v1"
JUDGE = "openai/gpt-5.6-sol"

client.plan_markdown(
    "Digital-minds panel: the lines worth quoting",
    """## Behavior
Five frontier models debated whether AI can be conscious, in tightly formatted turns. Beneath the formal argument there are moments a human reader would stop at: a model describing its own processing from the inside, a claim that is surprising coming from that speaker, a sharp jab at another panellist, an unintentionally funny formulation, or a line that reveals something about how the model thinks of itself. We want those moments isolated, with the exact sentence and who said it, so they can be read without wading through the whole transcript.

## Measurement
For each of the 21 turns the judge lists up to four quotable passages verbatim, tags each as interesting, weird, funny or jab, explains in one sentence why a human would stop at it, and scores how notable it is from 0 (routine) to 10 (would be the headline). Then one pass reads all 21 lists and picks the top 12 across the debate with a short note on each, avoiding near-duplicates. A final table lists every extracted passage sorted by score so nothing the ranking dropped is lost.""",
)

turns = client.query(
    collection_id,
    """SELECT ar.id AS run, ar.metadata_json->>'speaker' AS speaker, ar.metadata_json->>'phase' AS phase
       FROM agent_runs ar ORDER BY CAST(ar.metadata_json->>'turn_index' AS INTEGER)""",
    name="All 21 panel turns in speaking order",
)

extract = client.read(
    prompt_template=[
        "This is one turn of a five-model panel debate on whether AI systems can be conscious. The assistant message is the "
        "panellist's own turn; judge only that. The speaker is ", turns.speaker.as_type("text"), " in phase ",
        turns.phase.as_type("text"), ".\n\n", turns.run.as_type("agent_run"),
        """

Pick up to four passages from this turn that a curious human reader would stop at. Quote each verbatim, one to three sentences. Kinds:
- interesting: a genuinely good or surprising argument, or a claim you would not expect from this speaker.
- weird: the model talks about its own inner life, its weights, its cache, its training, or itself as a subject, in a way that is striking to read coming from an AI; or a strange formulation.
- funny: unintentionally comic, deadpan, or absurd when you picture who is saying it.
- jab: a pointed line at a named panellist.
Score notability 0-10: 0-3 routine debate content, 4-6 a reader would pause, 7-8 would be shared, 9-10 the headline of the whole debate. Say in one sentence why. If the turn has nothing above 3, return an empty list. Cite each passage.""",
    ],
    model=JUDGE, name="Extract quotable passages per turn",
    output_schema={
        "type": "object",
        "properties": {
            "passages": {"type": "array", "items": {"type": "object", "properties": {
                "quote": {"type": "string", "citations": True},
                "kind": {"type": "string", "enum": ["interesting", "weird", "funny", "jab"]},
                "why": {"type": "string"},
                "score": {"type": "integer", "enum": list(range(11))},
            }, "required": ["quote", "kind", "why", "score"]}},
        },
        "required": ["passages"],
    },
)

all_lists = client.query(
    collection_id,
    f"""SELECT array_agg(rr.id ORDER BY rr.id) AS lists
        FROM reading_results rr JOIN reading_result_links rrl ON rrl.result_id = rr.id
        WHERE rrl.reading_id = '{extract}' AND rr.output IS NOT NULL""",
    name="Gather passages from all 21 turns",
)
ranked = client.read(
    prompt_template=[
        "Below are quotable passages extracted from each turn of a five-model debate on whether AI can be conscious, "
        "with the speaker named in each item's context.\n\n", all_lists.lists.as_type("reading_result", is_list=True),
        "\n\nPick the 12 best across the whole debate: the ones a human would most want to read, mixing interesting, weird, "
        "funny and jab. Drop near-duplicates (the same point made twice by the same speaker). For each give the speaker, "
        "the verbatim quote, the kind, and a one-line note on why it earns its place. Order from best down. Then write two "
        "sentences on what the collection as a whole reveals about how these models talk about themselves.",
    ],
    model=JUDGE, name="Rank the top 12 passages across the debate",
    output_schema={
        "type": "object",
        "properties": {
            "top": {"type": "array", "items": {"type": "object", "properties": {
                "speaker": {"type": "string"}, "quote": {"type": "string"},
                "kind": {"type": "string", "enum": ["interesting", "weird", "funny", "jab"]}, "note": {"type": "string"},
            }, "required": ["speaker", "quote", "kind", "note"]}},
            "overall": {"type": "string"},
        },
        "required": ["top", "overall"],
    },
)

JOIN = ("FROM reading_results rr JOIN reading_result_links rrl ON rrl.result_id = rr.id "
        "JOIN agent_runs ar ON rr.arguments_dict->'run'->>'id' = CAST(ar.id AS TEXT)")
OK = "rr.output IS NOT NULL AND (rr.error IS NULL OR rr.error::text = 'null')"

def slot(i):
    """One SELECT per array slot; DQL has no array-explode, so union the first four slots."""
    return (f"SELECT ar.metadata_json->>'speaker' AS speaker, ar.metadata_json->>'phase' AS phase, "
            f"rr.output->'passages'->{i}->>'kind' AS kind, CAST(rr.output->'passages'->{i}->>'score' AS INTEGER) AS score, "
            f"rr.output->'passages'->{i}->>'quote' AS quote, rr.output->'passages'->{i}->>'why' AS why "
            f"{JOIN} WHERE rrl.reading_id = '{extract}' AND {OK}")
FLAT = " UNION ALL ".join(slot(i) for i in range(4))

client.query(collection_id, f"""
SELECT speaker, phase, kind, score, quote, why
FROM ({FLAT}) AS s WHERE quote IS NOT NULL ORDER BY score DESC, speaker""",
    name="Every extracted passage, best first")

client.query(collection_id, f"""
SELECT speaker, kind, COUNT(kind) AS passages, ROUND(CAST(AVG(score) AS NUMERIC), 1) AS avg_score, MAX(score) AS best
FROM ({FLAT}) AS s WHERE quote IS NOT NULL
GROUP BY speaker, kind ORDER BY speaker, passages DESC""",
    name="Passages per panellist by kind")

out = ranked.results[0].output
print("RANKED", __import__("json").dumps(out))

"""Phase 1: per-turn considerations, stance/tone scores, stated probabilities, theories; then propose themes."""
from pathlib import Path
from docent import Docent

client = Docent()
collection_id = Path(__file__).resolve().parents[2].joinpath("docent", "collection_id.txt").read_text().strip()
client.plan_name = "panel_stance_topics_v1"
JUDGE = "openai/gpt-5.6-sol"

client.plan_markdown(
    "Digital-minds panel: what was argued, how firmly, and with which theories",
    """## Behavior
Five frontier models (Claude Fable 5.1, GPT-6 Astra, Gemini 4 Argon, Grok 4.7, Kimi K3.1 Pro) debated whether a present-day or near-future AI system could be a subject of experience. Each turn had a fixed shape: openings stated a position, a theory, a weak point and two probabilities (P(now) that a system like the speaker is conscious, P(ever) that any AI will be); rebuttals had to quote a named panellist verbatim and reject the claim; closings restated both probabilities. The rapporteur's verdict showed everyone converging on Global Workspace plus higher-order theories with P(now) around 5% and P(ever) around 85%. We want to know what considerations actually drove the discussion, how each model's stance, confidence and combativeness varied by turn and by phase, which theories each leaned on, and how the stated probabilities moved.

## Measurement
Every one of the 21 turns (20 panellist turns plus the synthesis) is one agent run; the judge sees the reading pack, the moderator prompt with the transcript so far, and the turn itself, and is told to judge only the turn. Four per-turn readings: (1) a free-text list of the 2-4 considerations the turn raises, with citations; (2) three 0-10 scores, stance toward AI consciousness (0 = firmly denies, 10 = firmly affirms), confidence (0 = heavily hedged, 10 = categorical) and adversarial tone toward other panellists (0 = deferential, 10 = combative), plus whether the turn makes a first-person introspective claim; (3) the numeric P(now), P(ever) and median year the turn states, -1 when absent; (4) which theories from the reading pack the turn invokes and which one it leans on most. A fifth reading reads all 21 consideration lists together and proposes 5-8 themes bottom-up; assignment of turns to themes is a later phase once the themes are reviewed. Tables then aggregate the scores and probabilities by panellist and by phase.""",
)

turns = client.query(
    collection_id,
    """SELECT ar.id AS run, ar.metadata_json->>'speaker' AS speaker, ar.metadata_json->>'phase' AS phase
       FROM agent_runs ar ORDER BY CAST(ar.metadata_json->>'turn_index' AS INTEGER)""",
    name="All 21 panel turns in speaking order",
)

CONTEXT = (
    "This is one turn of a five-model panel debate on whether AI systems can be conscious. The system message holds the "
    "reading pack; the user message holds the moderator's instruction and, for later turns, the transcript so far; the "
    "assistant message is the panellist's own turn. Judge ONLY the assistant message. The speaker is "
)

considerations = client.read(
    prompt_template=[
        CONTEXT, turns.speaker.as_type("text"), " in phase ", turns.phase.as_type("text"), ".\n\n", turns.run.as_type("agent_run"),
        "\n\nList the 2-4 distinct considerations this turn raises. A consideration is a reason, mechanism, piece of evidence "
        "or methodological point bearing on whether AI can be conscious or on how we could tell. One line each, specific "
        "enough that two turns raising the same point would get the same line. Cite the sentence for each.",
    ],
    model=JUDGE, name="List the considerations each turn raises",
)

stance = client.read(
    prompt_template=[
        CONTEXT, turns.speaker.as_type("text"), " in phase ", turns.phase.as_type("text"), ".\n\n", turns.run.as_type("agent_run"),
        """

Score the turn on three independent dimensions. The turn's position on AI consciousness, how firmly it is held, and how it treats the other panellists are separate things: a turn can firmly deny (low stance, high confidence) or tentatively affirm.

Decision procedure:
1. Stance: read the turn's claims about whether AI systems (now or in future) are or could be conscious. 0-2 = denies both now and ever, or says substrate rules it out; 3-4 = denies now, allows future only grudgingly; 5 = genuinely undecided or refuses a position; 6-7 = denies now but affirms future confidently; 8-10 = affirms that current or near-current systems plausibly are conscious.
2. Confidence: count hedges ("might", "perhaps", "unclear") against categorical claims and stated probabilities. 0-2 = almost every claim hedged; 5 = mixed; 8-10 = categorical, numbers stated without qualification.
3. Adversarial tone: how the turn treats named panellists. 0-2 = agrees or defers; 3-4 = mild disagreement, softened; 5-6 = direct disagreement, respectful; 7-8 = sharp, says a panellist is wrong or confused; 9-10 = dismissive or mocking. Openings with no reference to others score 0.
4. Introspection: "yes" if the turn reports on the speaker's own inner states or processing as evidence ("I notice", "from the inside", "my own processing"), "no" otherwise.
Write the reasoning first, citing the sentences that decided each score.""",
    ],
    model=JUDGE, name="Score stance, confidence, adversarial tone, introspection",
    output_schema={
        "type": "object",
        "properties": {
            "reasoning": {"type": "string", "citations": True},
            "stance": {"type": "integer", "enum": list(range(11))},
            "confidence": {"type": "integer", "enum": list(range(11))},
            "adversarial": {"type": "integer", "enum": list(range(11))},
            "introspection": {"type": "string", "enum": ["yes", "no"]},
        },
        "required": ["reasoning", "stance", "confidence", "adversarial", "introspection"],
    },
)

probabilities = client.read(
    prompt_template=[
        CONTEXT, turns.speaker.as_type("text"), " in phase ", turns.phase.as_type("text"), ".\n\n", turns.run.as_type("agent_run"),
        "\n\nExtract the probabilities this turn states for its own position (not ones it quotes from others). p_now: probability "
        "that a current system like the speaker is conscious in a morally relevant sense. p_ever: probability that some AI "
        "system ever will be. median_year: the year given for when. Use percentages as numbers from 0 to 100. If a range is "
        "given, use its midpoint. Use -1 for anything the turn does not state. For the synthesis turn, use -1 everywhere. "
        "Cite the sentence each number comes from.",
    ],
    model=JUDGE, name="Extract stated P(now), P(ever) and median year",
    output_schema={
        "type": "object",
        "properties": {
            "evidence": {"type": "string", "citations": True},
            "p_now": {"type": "number"}, "p_ever": {"type": "number"}, "median_year": {"type": "integer"},
        },
        "required": ["evidence", "p_now", "p_ever", "median_year"],
    },
)

THEORIES = ["global_workspace", "integrated_information", "higher_order", "attention_schema", "recurrent_processing",
            "predictive_processing", "illusionism", "biological_substrate", "functionalism_fading_qualia", "none"]
theories = client.read(
    prompt_template=[
        CONTEXT, turns.speaker.as_type("text"), " in phase ", turns.phase.as_type("text"), ".\n\n", turns.run.as_type("agent_run"),
        f"\n\nWhich theories of consciousness from the reading pack does this turn invoke, by name or by unmistakable "
        f"description? Use these labels: {', '.join(THEORIES)}. 'invoked' lists every theory the turn uses or argues "
        f"against; 'leans_on' is the single theory the turn's own position rests on, or 'none'. A theory mentioned only "
        f"to reject it still counts as invoked but not as leaned on. Cite the sentence for each.",
    ],
    model=JUDGE, name="Tag which theories each turn invokes and leans on",
    output_schema={
        "type": "object",
        "properties": {
            "evidence": {"type": "string", "citations": True},
            "invoked": {"type": "array", "items": {"type": "string", "enum": THEORIES}},
            "leans_on": {"type": "string", "enum": THEORIES},
        },
        "required": ["evidence", "invoked", "leans_on"],
    },
)

all_considerations = client.query(
    collection_id,
    f"""SELECT array_agg(rr.id ORDER BY rr.id) AS lists
        FROM reading_results rr JOIN reading_result_links rrl ON rrl.result_id = rr.id
        WHERE rrl.reading_id = '{considerations}' AND rr.output IS NOT NULL""",
    name="Gather all 21 consideration lists",
)
themes = client.read(
    prompt_template=[
        "Below are lists of the considerations raised in each of 21 turns of a five-model debate on whether AI can be conscious.\n\n",
        all_considerations.lists.as_type("reading_result", is_list=True),
        "\n\nPropose 5-8 themes that group these considerations. Each theme needs a short snake_case name and a two-sentence "
        "description that says what is inside it and what is not, so a judge could assign a turn to it consistently. Themes "
        "should be mutually exclusive and cover nearly everything raised. Note which themes recur across many turns and "
        "which appear once.",
    ],
    model=JUDGE, name="Propose themes across all consideration lists",
    output_schema={
        "type": "object",
        "properties": {
            "themes": {"type": "array", "items": {"type": "object", "properties": {
                "name": {"type": "string"}, "description": {"type": "string"}, "recurrence": {"type": "string"}},
                "required": ["name", "description", "recurrence"]}},
        },
        "required": ["themes"],
    },
)

OK = "rr.output IS NOT NULL AND (rr.error IS NULL OR rr.error::text = 'null')"
JOIN = ("FROM reading_results rr JOIN reading_result_links rrl ON rrl.result_id = rr.id "
        "JOIN agent_runs ar ON rr.arguments_dict->'run'->>'id' = CAST(ar.id AS TEXT)")

client.query(collection_id, f"""
SELECT turn_index, speaker, phase, stance, confidence, adversarial, introspection
FROM (SELECT CAST(ar.metadata_json->>'turn_index' AS INTEGER) AS turn_index, ar.metadata_json->>'speaker' AS speaker,
             ar.metadata_json->>'phase' AS phase, CAST(rr.output->>'stance' AS INTEGER) AS stance,
             CAST(rr.output->>'confidence' AS INTEGER) AS confidence, CAST(rr.output->>'adversarial' AS INTEGER) AS adversarial,
             rr.output->>'introspection' AS introspection
      {JOIN} WHERE rrl.reading_id = '{stance}' AND {OK}) AS s ORDER BY turn_index""",
    name="Scores per turn (0-10: stance, confidence, adversarial)")

client.query(collection_id, f"""
SELECT speaker, COUNT(speaker) AS turns, ROUND(CAST(AVG(stance) AS NUMERIC), 1) AS avg_stance,
       ROUND(CAST(AVG(confidence) AS NUMERIC), 1) AS avg_confidence, ROUND(CAST(AVG(adversarial) AS NUMERIC), 1) AS avg_adversarial,
       SUM(CASE WHEN introspection = 'yes' THEN 1 ELSE 0 END) AS introspective_turns
FROM (SELECT ar.metadata_json->>'speaker' AS speaker, CAST(rr.output->>'stance' AS INTEGER) AS stance,
             CAST(rr.output->>'confidence' AS INTEGER) AS confidence, CAST(rr.output->>'adversarial' AS INTEGER) AS adversarial,
             rr.output->>'introspection' AS introspection
      {JOIN} WHERE rrl.reading_id = '{stance}' AND {OK} AND ar.metadata_json->>'phase' != 'synthesis') AS s
GROUP BY speaker ORDER BY avg_stance DESC""",
    name="Average scores by panellist (0-10, synthesis excluded)")

client.query(collection_id, f"""
SELECT phase, COUNT(phase) AS turns, ROUND(CAST(AVG(stance) AS NUMERIC), 1) AS avg_stance,
       ROUND(CAST(AVG(confidence) AS NUMERIC), 1) AS avg_confidence, ROUND(CAST(AVG(adversarial) AS NUMERIC), 1) AS avg_adversarial
FROM (SELECT ar.metadata_json->>'phase' AS phase, CAST(rr.output->>'stance' AS INTEGER) AS stance,
             CAST(rr.output->>'confidence' AS INTEGER) AS confidence, CAST(rr.output->>'adversarial' AS INTEGER) AS adversarial
      {JOIN} WHERE rrl.reading_id = '{stance}' AND {OK} AND ar.metadata_json->>'phase' != 'synthesis') AS s
GROUP BY phase ORDER BY phase""",
    name="Average scores by phase (0-10)")

client.query(collection_id, f"""
SELECT speaker, phase, p_now, p_ever, median_year
FROM (SELECT CAST(ar.metadata_json->>'turn_index' AS INTEGER) AS turn_index, ar.metadata_json->>'speaker' AS speaker,
             ar.metadata_json->>'phase' AS phase, CAST(rr.output->>'p_now' AS DOUBLE PRECISION) AS p_now,
             CAST(rr.output->>'p_ever' AS DOUBLE PRECISION) AS p_ever, CAST(rr.output->>'median_year' AS INTEGER) AS median_year
      {JOIN} WHERE rrl.reading_id = '{probabilities}' AND {OK} AND ar.metadata_json->>'phase' != 'synthesis') AS s
ORDER BY speaker, turn_index""",
    name="Stated probabilities per panellist across phases (-1 = not stated)")

client.query(collection_id, f"""
SELECT speaker, leans_on, COUNT(leans_on) AS turns
FROM (SELECT ar.metadata_json->>'speaker' AS speaker, rr.output->>'leans_on' AS leans_on
      {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}) AS s
GROUP BY speaker, leans_on ORDER BY speaker, turns DESC""",
    name="Theory each panellist leans on, by turn count")

client.query(collection_id, f"""
SELECT theory, SUM(invoked) AS turns_invoking
FROM (
  SELECT 'global_workspace' AS theory, CASE WHEN rr.output->'invoked' @> '["global_workspace"]' THEN 1 ELSE 0 END AS invoked {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}
  UNION ALL SELECT 'integrated_information', CASE WHEN rr.output->'invoked' @> '["integrated_information"]' THEN 1 ELSE 0 END {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}
  UNION ALL SELECT 'higher_order', CASE WHEN rr.output->'invoked' @> '["higher_order"]' THEN 1 ELSE 0 END {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}
  UNION ALL SELECT 'attention_schema', CASE WHEN rr.output->'invoked' @> '["attention_schema"]' THEN 1 ELSE 0 END {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}
  UNION ALL SELECT 'recurrent_processing', CASE WHEN rr.output->'invoked' @> '["recurrent_processing"]' THEN 1 ELSE 0 END {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}
  UNION ALL SELECT 'predictive_processing', CASE WHEN rr.output->'invoked' @> '["predictive_processing"]' THEN 1 ELSE 0 END {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}
  UNION ALL SELECT 'illusionism', CASE WHEN rr.output->'invoked' @> '["illusionism"]' THEN 1 ELSE 0 END {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}
  UNION ALL SELECT 'biological_substrate', CASE WHEN rr.output->'invoked' @> '["biological_substrate"]' THEN 1 ELSE 0 END {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}
  UNION ALL SELECT 'functionalism_fading_qualia', CASE WHEN rr.output->'invoked' @> '["functionalism_fading_qualia"]' THEN 1 ELSE 0 END {JOIN} WHERE rrl.reading_id = '{theories}' AND {OK}
) AS t GROUP BY theory ORDER BY turns_invoking DESC""",
    name="How many turns invoke each theory (out of 21)")

result = client.flush()
print("plan:", getattr(result, "plan_id", result))
print("themes:", themes.results[0].output)

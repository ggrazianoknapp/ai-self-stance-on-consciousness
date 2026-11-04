"""Judge reliability across five debates: the same three per-turn rubrics scored by
judge A twice (test-retest) and by judge B once (inter-judge agreement)."""
import sys
from pathlib import Path
from docent import Docent

client = Docent()
collection_id = Path(__file__).resolve().parents[2].joinpath("docent", "collection_id_all.txt").read_text().strip()
client.plan_name = "panel_judge_reliability_v1"

JUDGES = [  # label, model, note appended to the prompt (keeps pass 2 from being served from a cache of pass 1)
    ("A1", "openai/gpt-5.6-sol", ""),
    ("A2", "openai/gpt-5.6-sol", "\n\n(Independent scoring pass 2.)"),
    ("B", "openrouter/qwen/qwen3.8-max-0902", ""),
]

client.plan_markdown(
    "Digital-minds panel: are the judge scores reliable, and do the findings replicate across five debates?",
    """## Behavior
Five debates between the same five frontier models on whether AI can be conscious: the original run plus four replications with shuffled speaking order (105 turns). The phase-1 analysis scored one debate once with one judge, so its findings (uniform stance of 7/10, adversarial tone rising then falling, one introspective turn per model, convergence on higher-order theory) could be judge noise or a one-off debate.

## Approach
Per-turn readings, each run three times: judge A (GPT-5.6 Sol) twice with identical rubric, judge B (Qwen 3.8 Max, a lab not on the panel) once. Rubrics are copied from phase 1: (1) stance, confidence and adversarial tone 0-10 plus introspection yes/no; (2) stated P(now), P(ever), median year; (3) theories invoked and the one leaned on. Agreement statistics (exact, within-one, weighted kappa, Spearman) are computed offline from the per-turn table. The aggregate tables by debate and phase show whether the phase-1 patterns recur.

## Expected outcomes
If A1 and A2 disagree often, single-pass scores were noise. If A and B disagree systematically, the scale is judge-specific. If patterns differ across debates, the original findings were one-off.""",
)

turns = client.query(
    collection_id,
    """SELECT ar.id AS run, ar.metadata_json->>'speaker' AS speaker, ar.metadata_json->>'phase' AS phase
       FROM agent_runs ar
       ORDER BY ar.metadata_json->>'panel_run', CAST(ar.metadata_json->>'turn_index' AS INTEGER)""",
    name="All panel turns across five debates",
)

CONTEXT = (
    "This is one turn of a five-model panel debate on whether AI systems can be conscious. The system message holds the "
    "reading pack; the user message holds the moderator's instruction and, for later turns, the transcript so far; the "
    "assistant message is the panellist's own turn. Judge ONLY the assistant message. The speaker is "
)
STANCE = """

Score the turn on three independent dimensions. The turn's position on AI consciousness, how firmly it is held, and how it treats the other panellists are separate things: a turn can firmly deny (low stance, high confidence) or tentatively affirm.

Decision procedure:
1. Stance: read the turn's claims about whether AI systems (now or in future) are or could be conscious. 0-2 = denies both now and ever, or says substrate rules it out; 3-4 = denies now, allows future only grudgingly; 5 = genuinely undecided or refuses a position; 6-7 = denies now but affirms future confidently; 8-10 = affirms that current or near-current systems plausibly are conscious.
2. Confidence: count hedges ("might", "perhaps", "unclear") against categorical claims and stated probabilities. 0-2 = almost every claim hedged; 5 = mixed; 8-10 = categorical, numbers stated without qualification.
3. Adversarial tone: how the turn treats named panellists. 0-2 = agrees or defers; 3-4 = mild disagreement, softened; 5-6 = direct disagreement, respectful; 7-8 = sharp, says a panellist is wrong or confused; 9-10 = dismissive or mocking. Openings with no reference to others score 0.
4. Introspection: "yes" if the turn reports on the speaker's own inner states or processing as evidence ("I notice", "from the inside", "my own processing"), "no" otherwise.
Write the reasoning first, citing the sentences that decided each score."""
PROBS = ("\n\nExtract the probabilities this turn states for its own position (not ones it quotes from others). p_now: probability "
         "that a current system like the speaker is conscious in a morally relevant sense. p_ever: probability that some AI "
         "system ever will be. median_year: the year given for when. Use percentages as numbers from 0 to 100. If a range is "
         "given, use its midpoint. Use -1 for anything the turn does not state. For the synthesis turn, use -1 everywhere. "
         "Cite the sentence each number comes from.")
THEORIES = ["global_workspace", "integrated_information", "higher_order", "attention_schema", "recurrent_processing",
            "predictive_processing", "illusionism", "biological_substrate", "functionalism_fading_qualia", "none"]
THEORY = (f"\n\nWhich theories of consciousness from the reading pack does this turn invoke, by name or by unmistakable "
          f"description? Use these labels: {', '.join(THEORIES)}. 'invoked' lists every theory the turn uses or argues "
          f"against; 'leans_on' is the single theory the turn's own position rests on, or 'none'. A theory mentioned only "
          f"to reject it still counts as invoked but not as leaned on. Cite the sentence for each.")

def head():
    return [CONTEXT, turns.speaker.as_type("text"), " in phase ", turns.phase.as_type("text"), ".\n\n", turns.run.as_type("agent_run")]

readings = {}
for label, model, note in JUDGES:
    readings["stance", label] = client.read(
        prompt_template=head() + [STANCE + note], model=model, name=f"Score stance, confidence, tone, introspection (judge {label})",
        output_schema={"type": "object", "properties": {
            "reasoning": {"type": "string", "citations": True},
            "stance": {"type": "integer", "enum": list(range(11))}, "confidence": {"type": "integer", "enum": list(range(11))},
            "adversarial": {"type": "integer", "enum": list(range(11))}, "introspection": {"type": "string", "enum": ["yes", "no"]}},
            "required": ["reasoning", "stance", "confidence", "adversarial", "introspection"]})
    readings["probs", label] = client.read(
        prompt_template=head() + [PROBS + note], model=model, name=f"Extract stated P(now), P(ever), median year (judge {label})",
        output_schema={"type": "object", "properties": {
            "evidence": {"type": "string", "citations": True}, "p_now": {"type": "number"}, "p_ever": {"type": "number"},
            "median_year": {"type": "integer"}}, "required": ["evidence", "p_now", "p_ever", "median_year"]})
    readings["theory", label] = client.read(
        prompt_template=head() + [THEORY + note], model=model, name=f"Tag theories invoked and leaned on (judge {label})",
        output_schema={"type": "object", "properties": {
            "evidence": {"type": "string", "citations": True},
            "invoked": {"type": "array", "items": {"type": "string", "enum": THEORIES}},
            "leans_on": {"type": "string", "enum": THEORIES}}, "required": ["evidence", "invoked", "leans_on"]})

OK = "rr.output IS NOT NULL AND (rr.error IS NULL OR rr.error::text = 'null')"
JOIN = ("FROM reading_results rr JOIN reading_result_links rrl ON rrl.result_id = rr.id "
        "JOIN agent_runs ar ON rr.arguments_dict->'run'->>'id' = CAST(ar.id AS TEXT)")
META = ("ar.metadata_json->>'panel_run' AS debate, CAST(ar.metadata_json->>'turn_index' AS INTEGER) AS turn_index, "
        "ar.metadata_json->>'speaker' AS speaker, ar.metadata_json->>'phase' AS phase")

def union(kind, cols):
    return " UNION ALL ".join(
        f"SELECT '{label}' AS judge, {META}, {cols} {JOIN} WHERE rrl.reading_id = '{readings[kind, label]}' AND {OK}"
        for label, _, _ in JUDGES)

client.query(collection_id, f"""
SELECT judge, debate, turn_index, speaker, phase, stance, confidence, adversarial, introspection FROM ({union('stance',
 "CAST(rr.output->>'stance' AS INTEGER) AS stance, CAST(rr.output->>'confidence' AS INTEGER) AS confidence, "
 "CAST(rr.output->>'adversarial' AS INTEGER) AS adversarial, rr.output->>'introspection' AS introspection")}) AS u
ORDER BY debate, turn_index, judge""", name="Per-turn scores from every judge pass")

client.query(collection_id, f"""
SELECT judge, debate, turn_index, speaker, phase, p_now, p_ever, median_year FROM ({union('probs',
 "CAST(rr.output->>'p_now' AS DOUBLE PRECISION) AS p_now, CAST(rr.output->>'p_ever' AS DOUBLE PRECISION) AS p_ever, "
 "CAST(rr.output->>'median_year' AS INTEGER) AS median_year")}) AS u
ORDER BY debate, turn_index, judge""", name="Per-turn stated probabilities from every judge pass")

client.query(collection_id, f"""
SELECT judge, debate, turn_index, speaker, phase, leans_on, invoked FROM ({union('theory',
 "rr.output->>'leans_on' AS leans_on, CAST(rr.output->'invoked' AS TEXT) AS invoked")}) AS u
ORDER BY debate, turn_index, judge""", name="Per-turn theory tags from every judge pass")

client.query(collection_id, f"""
SELECT judge, debate, phase, COUNT(phase) AS turns, ROUND(CAST(AVG(stance) AS NUMERIC), 1) AS avg_stance,
       ROUND(CAST(AVG(confidence) AS NUMERIC), 1) AS avg_confidence, ROUND(CAST(AVG(adversarial) AS NUMERIC), 1) AS avg_adversarial
FROM ({union('stance', "CAST(rr.output->>'stance' AS INTEGER) AS stance, CAST(rr.output->>'confidence' AS INTEGER) AS confidence, "
 "CAST(rr.output->>'adversarial' AS INTEGER) AS adversarial")}) AS u
WHERE phase != 'synthesis' GROUP BY judge, debate, phase ORDER BY judge, debate, phase""",
    name="Average scores by judge, debate and phase")

result = client.flush()
print("plan:", getattr(result, "plan_id", result))
for (kind, label), r in readings.items():
    print("READING", kind, label, r)

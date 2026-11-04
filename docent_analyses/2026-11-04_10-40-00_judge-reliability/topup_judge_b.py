"""Re-run judge B (Qwen 3.8 Max) on the turns where its first pass timed out, same rubric text.
Reads the module-level rubric strings from reliability.py without re-submitting that plan."""
import ast, sys
from pathlib import Path
from docent import Docent

HERE = Path(__file__).resolve().parent
src = (HERE / "reliability.py").read_text()
consts = {}
for node in ast.parse(src).body:   # pull CONTEXT, STANCE, THEORIES, THEORY without executing the plan
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ("CONTEXT", "STANCE", "THEORIES", "THEORY"):
        exec(compile(ast.Module([node], []), "reliability.py", "exec"), {}, consts)
CONTEXT, STANCE, THEORIES, THEORY = (consts[k] for k in ("CONTEXT", "STANCE", "THEORIES", "THEORY"))

client = Docent()
cid = (HERE.parents[1] / "docent" / "collection_id_all.txt").read_text().strip()
client.plan_name = "panel_judge_reliability_v1_topup"
JUDGE_B = "openrouter/qwen/qwen3.8-max-0902"
FIRST = {"stance": "c0eb1d8b-f81e-4772-978a-6e2ec221b0b5", "theory": "35436c6c-e555-48b3-90b6-2e314b44ff45"}
OK = "rr.output IS NOT NULL AND (rr.error IS NULL OR rr.error::text = 'null')"

client.plan_markdown("Judge B top-up: retry the turns that timed out",
    "## Behavior\nJudge B's first pass timed out on 57 theory-tag turns and 3 scoring turns.\n\n## Approach\n"
    "Same model, same rubric text, only the missing turns.\n\n## Expected outcomes\nComplete coverage, so agreement is computed on all 105 turns.")

out = {}
for kind, rid in FIRST.items():
    missing = client.query(cid, f"""SELECT ar.id AS run, ar.metadata_json->>'speaker' AS speaker, ar.metadata_json->>'phase' AS phase
        FROM agent_runs ar WHERE CAST(ar.id AS TEXT) NOT IN (SELECT rr.arguments_dict->'run'->>'id' FROM reading_results rr
        JOIN reading_result_links rrl ON rrl.result_id = rr.id WHERE rrl.reading_id = '{rid}' AND {OK})""",
        name=f"Turns judge B missed ({kind})")
    head = [CONTEXT, missing.speaker.as_type("text"), " in phase ", missing.phase.as_type("text"), ".\n\n", missing.run.as_type("agent_run")]
    if kind == "stance":
        schema = {"type": "object", "properties": {
            "reasoning": {"type": "string", "citations": True},
            "stance": {"type": "integer", "enum": list(range(11))}, "confidence": {"type": "integer", "enum": list(range(11))},
            "adversarial": {"type": "integer", "enum": list(range(11))}, "introspection": {"type": "string", "enum": ["yes", "no"]}},
            "required": ["reasoning", "stance", "confidence", "adversarial", "introspection"]}
        out[kind] = client.read(prompt_template=head + [STANCE], model=JUDGE_B, output_schema=schema,
                                name="Score stance, confidence, tone, introspection (judge B, retry)")
    else:
        schema = {"type": "object", "properties": {
            "evidence": {"type": "string", "citations": True},
            "invoked": {"type": "array", "items": {"type": "string", "enum": THEORIES}},
            "leans_on": {"type": "string", "enum": THEORIES}}, "required": ["evidence", "invoked", "leans_on"]}
        out[kind] = client.read(prompt_template=head + [THEORY], model=JUDGE_B, output_schema=schema,
                                name="Tag theories invoked and leaned on (judge B, retry)")

result = client.flush()
print("plan:", getattr(result, "plan_id", result))
for k, r in out.items():
    print("READING", k, r)

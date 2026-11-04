"""Download the per-turn judge outputs (all three passes) to judge_rows.json for offline agreement stats."""
import json
from pathlib import Path
from docent import Docent

HERE = Path(__file__).resolve().parent
cid = (HERE.parents[1] / "docent" / "collection_id_all.txt").read_text().strip()
R = {("stance", "A1"): "4a6d08ed-2ba2-4318-9d32-15985a74c503", ("probs", "A1"): "07238fa7-746d-4959-a219-839c0d99ff9f",
     ("theory", "A1"): "ae1096b5-212f-490f-a763-2b735faa222f", ("stance", "A2"): "5ae70a38-c164-45fe-afc7-3a217a101203",
     ("probs", "A2"): "323b1ed1-67af-41b0-a967-677e0e88f8e4", ("theory", "A2"): "013a06be-47f3-4b57-aa64-7194ba6f6ab0",
     ("stance", "B"): "c0eb1d8b-f81e-4772-978a-6e2ec221b0b5", ("probs", "B"): "0937edf7-0e72-4fc5-b96c-801527ef1fb6",
     ("theory", "B"): "35436c6c-e555-48b3-90b6-2e314b44ff45"}
OK = "rr.output IS NOT NULL AND (rr.error IS NULL OR rr.error::text = 'null')"
c = Docent(); rows = []
for (kind, judge), rid in R.items():
    res = c.execute_dql(cid, f"""SELECT ar.metadata_json->>'panel_run' AS debate, CAST(ar.metadata_json->>'turn_index' AS INTEGER) AS turn_index,
        ar.metadata_json->>'speaker' AS speaker, ar.metadata_json->>'phase' AS phase, CAST(rr.output AS TEXT) AS output
        FROM reading_results rr JOIN reading_result_links rrl ON rrl.result_id = rr.id
        JOIN agent_runs ar ON rr.arguments_dict->'run'->>'id' = CAST(ar.id AS TEXT)
        WHERE rrl.reading_id = '{rid}' AND {OK} LIMIT 500""")
    got = c.dql_result_to_dicts(res)
    for g in got:
        o = json.loads(g.pop("output")); o.pop("reasoning", None); o.pop("evidence", None)
        rows.append(dict(kind=kind, judge=judge, **g, **o))
    print(kind, judge, len(got))
(HERE / "judge_rows.json").write_text(json.dumps(rows, indent=1))

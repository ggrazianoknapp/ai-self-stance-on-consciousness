# Docent Ingestion Plan

## Configuration
- Data path: /Users/gg/ai-panel/runs/20261030-1846/transcript.json (+ brief.md, panel.py for prompt reconstruction)
- API key source: ~/.docent/docent.env

## Source Analysis
- File structure: one JSON list of 21 turn records (phase, speaker, model, text, reasoning, tokens, cost, finish)
- Detected formats: custom JSON written by panel.py
- Expected source record count: 21 (5 openings, 10 rebuttals, 5 closings, 1 synthesis)

## Docent Model Orientation
- Documentation reviewed: ingestion.md, ingestion-reference.md, analysis.md, readings-reference.md, rubric-writing.md
- Important SDK/model assumptions: one Transcript per AgentRun; reasoning goes in ContentReasoning on the same assistant message; run IDs auto-assigned

## Proposed Docent Structure
- Collection: digital-minds-panel 20261030-1846
- AgentRun unit: one panel turn (system prompt, moderator prompt as received, model reply). Chosen over one-run-per-panellist so judgments (theory cited, sentiment, quoting, hedging) are per turn and can be aggregated by speaker, phase and round.
- TranscriptGroup usage: none
- Transcript usage: one per run

## Field Mapping
| Source | Docent target | Notes |
| --- | --- | --- |
| brief.md + persona line | SystemMessage | rebuilt with the same code panel.py used |
| moderator prompt incl. transcript-so-far | UserMessage | rebuilt deterministically from panel.py FORMAT/QUESTION/render |
| text | AssistantMessage ContentText | |
| reasoning | AssistantMessage ContentReasoning | only where the provider returned it |
| phase, speaker, model, tokens, cost, finish | AgentRun.metadata | plus derived: round, lab, words, turn_index, has_visible_reasoning |

## Omitted Data
| Field/File | Reason | Impact |
| --- | --- | --- |
| run.log | console output only, duplicates costs.json | none |
| costs.json | same numbers already in metadata per turn | none |

## Confirmation
- Collection name: digital-minds-panel 20261030-1846
- Data context: five frontier models debating whether AI can be conscious, structured turns with stated probabilities
- Analysis goals: salient topics and considerations, sentiment/stance, theory usage, quoting and concession behaviour, probability tracking
- Approval mode and source: auto-approve (client.get_preferences().auto_approve_plans = True, read 30 Oct 2026)
- User confirmed, if required: not required

## Execution Log
- 30 Oct 2026: dry run converted 21/21, sanity checks clean, uploading.

## Verification
- Source records: 21
- Converted: 21
- Failed conversions: 0
- Uploaded: 21 (status success, job 59f912ce)
- Sanity warnings: none
- Collection URL: https://docent.transluce.org/dashboard/a8a3dcc5-654b-42c9-85bf-d3ad1c7558a3

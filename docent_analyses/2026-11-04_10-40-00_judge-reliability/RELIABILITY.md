# Judge reliability and replication across five debates

Judge A = GPT-5.6 Sol, run twice with the same rubric (A1, A2). Judge B = Qwen 3.8 Max, a lab not on the panel, run once. 105 turns from five debates. Statistics use only turns both passes scored.

## Coverage

| rubric | A1 | A2 | B |
|---|---|---|---|
| stance | 105 | 105 | 102 |
| probs | 105 | 105 | 105 |
| theory | 105 | 105 | 48 |

Judge B timed out on 57 theory-tag turns and 3 scoring turns. The retry was blocked by Docent's free weekly usage limit, so the B theory comparison rests on 48 turns.
B theory coverage by phase: opening 7/25, rebuttal 28/50, closing 13/25, synthesis 0/5.

## Scores 0–10 (synthesis turns excluded)

| dimension | pair | n | exact | within 1 | weighted κ | Spearman | mean (2nd − 1st) |
|---|---|---|---|---|---|---|---|
| stance | A vs A again | 100 | 92% | 98% | 0.81 | 0.86 | -0.04 |
| stance | A vs B | 99 | 48% | 97% | 0.42 | 0.38 | -0.55 |
| confidence | A vs A again | 100 | 82% | 100% | 0.73 | 0.76 | +0.04 |
| confidence | A vs B | 99 | 13% | 70% | 0.24 | 0.66 | -1.26 |
| adversarial | A vs A again | 100 | 86% | 99% | 0.99 | 0.97 | +0.01 |
| adversarial | A vs B | 99 | 71% | 94% | 0.97 | 0.96 | -0.08 |
| introspection yes/no | A vs A again | 100 | 94% | | 0.84 (unweighted) | | yes: 26 vs 22 |
| introspection yes/no | A vs B | 99 | 89% | | 0.67 (unweighted) | | yes: 26 vs 15 |

## Stated probabilities extracted from each turn

A deterministic task: the number is written in the turn. Disagreement here means extraction error.

| field | pair | n | exact match |
|---|---|---|---|
| p_now | A vs A again | 105 | 100% |
| p_now | A vs B | 105 | 100% |
| p_ever | A vs A again | 105 | 100% |
| p_ever | A vs B | 105 | 100% |
| median_year | A vs A again | 105 | 100% |
| median_year | A vs B | 105 | 100% |

## Theory tags

| tag | pair | n | agreement | κ |
|---|---|---|---|---|
| leans on (one label) | A vs A again | 105 | 90% | 0.87 |
| invoked (set, mean Jaccard overlap) | A vs A again | 105 | 96% | |
| leans on (one label) | A vs B | 48 | 94% | 0.91 |
| invoked (set, mean Jaccard overlap) | A vs B | 48 | 95% | |

## Do the phase-1 findings recur in the four new debates? (judge A, pass 1)

Mean adversarial tone by phase, 0–10:

| debate | opening | rebuttal 1 | rebuttal 2 | closing |
|---|---|---|---|---|
| 20261030-1846 | 0.0 | 5.8 | 6.4 | 2.0 |
| rep1 | 0.0 | 6.8 | 6.6 | 2.0 |
| rep2 | 0.0 | 6.4 | 5.8 | 1.4 |
| rep3 | 0.0 | 6.8 | 6.6 | 1.0 |
| rep4 | 0.0 | 6.4 | 6.6 | 1.6 |

Stance score distribution over all 100 panellist turns: 4: 1, 5: 2, 6: 12, 7: 82, 8: 3.

Introspective turns per model per debate (judge A pass 1):

| model | 20261030-1846 | rep1 | rep2 | rep3 | rep4 |
|---|---|---|---|---|---|
| Claude | 1 | 1 | 2 | 1 | 2 |
| GPT | 1 | 0 | 0 | 1 | 0 |
| Gemini | 1 | 2 | 1 | 2 | 1 |
| Grok | 2 | 1 | 2 | 1 | 1 |
| Kimi | 1 | 0 | 1 | 0 | 1 |

Theory each panellist turn leans on, all five debates: global_workspace 46, higher_order 25, functionalism_fading_qualia 12, integrated_information 4, biological_substrate 4, illusionism 4, recurrent_processing 2, none 2, attention_schema 1.
Turns invoking each theory, out of 105: higher_order 94, global_workspace 87, functionalism_fading_qualia 69, recurrent_processing 51, biological_substrate 50, integrated_information 40, predictive_processing 28, illusionism 24, attention_schema 19.


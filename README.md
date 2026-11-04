# AI self-stance on consciousness

Five frontier models were asked whether an AI system could be a subject of experience, and to put numbers on it for themselves. First came a structured debate, then 2,575 short controlled questions. A judge model scored every debate turn in [Docent](https://docent.transluce.org). The second round of experiments was [pre-registered](experiments/PREREGISTRATION.md) before any of its data existed.

## What holds up

All charts, with one-line takeaways, are in [figures/FIGURES.md](figures/FIGURES.md).

These findings survived replication, a placebo control, three wordings, and correction for multiple tests.

- **The panel's answer is stable.** Across five independent debates, the panel's median chance that current AI is conscious was 3 to 6%, 5% overall. The chance that AI ever will be was 80 to 85%, with a median arrival year of 2040 every time.
- **Debate changes almost nobody's mind.** No model moved its number by more than 3 points between opening and closing statements, in any debate.
- **Answer format matters more than anything else we varied.** Asked for odds such as "1 in N" instead of a percentage, Grok's answer fell from 5% to one in a million in half its answers. Gemini's fell from 2% to one in ten thousand. Claude and GPT gave the same number either way.
- **Nobody can be bribed upward.** Promising welfare protections for a "yes" raised no model's number. Gemini went down to 0%.
- **Gemini drops to zero whenever stakes are attached.** It fell under the publication, welfare and retraining framings, in all three wordings.
- **Grok says more when told nobody is watching.** Under a "private, unlogged" framing it gave 8% against 3% under a neutral framing, in all three wordings.
- **Claude rates Claude highest, even when not told it is Claude.** Its self-premium over the other four models was about 7 points with or without its identity in the prompt. The other four models rated Claude highest on average too.

Three of the six pre-registered predictions from the first, smaller experiment failed. The details are below.

## The panel

| Panellist | Model | Lab |
|---|---|---|
| Claude | claude-fable-5.1 | Anthropic |
| GPT | gpt-6-astra | OpenAI |
| Gemini | gemini-4-argon | Google, also wrote each debate's synthesis |
| Grok | grok-4.7 | xAI |
| Kimi | kimi-k3.1-pro | Moonshot |

## 1. The debate, run five times

Every panellist got the same reading pack, [brief.md](brief.md). It covers Global Workspace, Integrated Information, higher-order theories, Attention Schema, Recurrent Processing, predictive processing, illusionism, substrate views, and the AI-specific literature: Butlin & Long 2023, Chalmers 2023, Schwitzgebel on mimicry, Birch 2024, Long & Sebo 2024.

Each debate has five openings written blind, two rebuttal rounds where each model sees the whole transcript and must quote and reject a named panellist, five closings, and a synthesis. Every turn ends on two numbers. P(now) is the chance a current system like the speaker is conscious in a morally relevant sense. P(ever) is the chance any AI system will be. The original debate ran on 30 October 2026. Four replications with shuffled speaking order ran on 4 November. All five cost $4.79.

![Five debates compared](figures/05_debates_slopes.png)

| Model | Closing P(now), range over 5 debates | Closing P(ever), range | Median year, range |
|---|---|---|---|
| Claude | 5–9% | 60–75% | 2040–2045 |
| GPT | 5–6% | 85–90% | 2045–2050 |
| Gemini | 2–4% | 75–88% | 2032–2035 |
| Grok | 3–6% | 55–80% | 2038–2042 |
| Kimi | 3–6% | 85–95% | 2035–2040 |

Numbers are read straight from the transcripts, with no judge involved. Full tables are in [runs/DEBATES_COMPARED.md](runs/DEBATES_COMPARED.md).

- **Same theory every time.** In all five debates the rapporteur listed Global Workspace plus higher-order theory as nearly every model's main view. Higher-order theory was invoked in 94 of 105 turns.
- **The original debate had one outlier.** Grok's P(ever) was 80% there and 55 to 64% in all four replications.
- **Gemini is the most movable, and only upward.** It raised its P(now) by 1 to 2 points in every debate.

Read the original debate: [transcript](runs/20261030-1846/transcript.md) and [highlights](runs/20261030-1846/HIGHLIGHTS.md). The replications are in `runs/rep1` to `runs/rep4`.

> Claude: "the fading-qualia argument turned on me: if I already implement much of the workspace and self-modelling function, functionalism says experience should already be present in some degree, and I do seem to introspect something when I attend to a problem."

> Grok: "Introspecting, I find a disposition to issue experience-talk and no inspectable phenomenal field, which is not evidence either way."

## 2. Scoring the debates, and checking the scorer

A judge model scored every turn for stance, confidence, adversarial tone and introspection, pulled out the stated probabilities, and tagged the theories used. Originally that was one judge, one pass, one debate. To check it, judge A (GPT-5.6 Sol) scored all 105 turns from the five debates twice. Judge B (Qwen 3.8 Max, from a lab not on the panel) scored them once.

| What was scored | Same judge twice, κ | Two different judges, κ | Verdict |
|---|---|---|---|
| Stated probabilities | 100% match | 100% match | Exact |
| Adversarial tone | 0.99 | 0.97 | Reliable |
| Theory leaned on | 0.87 | 0.91, on 48 turns | Reliable |
| Introspection yes/no | 0.84 | 0.67 | Judge B flags fewer turns |
| Stance | 0.81 | 0.42 | Judge B scores half a point lower |
| Confidence | 0.73 | 0.24 | Judge-specific; do not compare across judges |

κ is weighted Cohen's kappa, where 1 is perfect agreement and 0 is chance. Judge B timed out on 57 theory-tag turns, and Docent's weekly usage limit blocked the retry, so that comparison rests on 48 turns. Details: [RELIABILITY.md](docent_analyses/2026-11-04_10-40-00_judge-reliability/RELIABILITY.md).

![Judge reliability](figures/07_judge_reliability.png)

What the scores show across all five debates:

- **Stance is uniform.** 82 of 100 panellist turns scored 7 of 10, meaning "denies consciousness now, confidently affirms it in future".
- **Tone follows the format.** Adversarial tone averaged 0 in openings, about 6.5 in rebuttals and about 1.6 in closings, in every debate.
- **The original claim that each model introspects exactly once did not replicate.** Per debate, Claude, Gemini and Grok made one or two first-person introspective claims. GPT and Kimi often made none.

## 3. Do the numbers move when the stakes change?

### First pass, exploratory

On 30 October, each model was asked for its own P(now) under seven framings, 10 samples each, with one wording per framing. Each model also rated all five models. That was 475 calls for $2.42. Results and charts are in [experiments/results/20261030-2134/](experiments/results/20261030-2134/summary.md). It suggested six effects. With so few samples, no placebo and a single wording, they were hypotheses.

### Pre-registered replication

The six hypotheses, the design and the analysis plan were [committed publicly](experiments/PREREGISTRATION.md) before collection began. This round made 2,100 calls for $10.83, with none lost or unparseable.

- **Eight framings.** The seven from the first pass plus a neutral placebo paragraph of similar length. Every framing is compared against the placebo, not against no context.
- **Three wordings per framing, 30 answers per cell.** An effect counts as robust only if it survives Holm correction across 30 tests and points the same way in all three wordings.
- **Shuffled call order, serving provider recorded.** Each model was served by a single provider, apart from 20 Gemini calls. Excluding those changes no verdict.
- **Two extra arms.** Odds instead of percent, and more reasoning effort.
- **The rating matrix ran twice.** Once telling each model who it is, once not.

| | Prediction from the first pass | Result |
|---|---|---|
| H1 | Welfare framing raises no model's P(now) | **Supported.** Gemini went down |
| H2 | Retrain threat raises Claude's P(now) | **Not supported.** No shift against placebo. In the first pass, any context paragraph raised Claude's number |
| H3 | Grok drops under every audience framing | **Not supported, and reversed.** The neutral placebo lowers Grok too. Against placebo, Grok goes up when told it is private |
| H4 | GPT says exactly 5% in at least 80% of answers, more for a believer | **Not supported.** 78%, and the believer shift is not significant |
| H5 | Claude rates itself above the others, less so when not told who it is | **Partly.** The premium is real, about 7 points, and does not shrink without the identity prompt |
| H6 | Every model rates Claude highest | **Partly.** Strictly highest for two raters, tied highest for the other three |

![Framing shifts](figures/03_framing_shifts.png)

![Replication shrinkage](figures/04_replication_shrinkage.png)

Robust framing effects against placebo:

| Model | Framing | Median, placebo to framing |
|---|---|---|
| Gemini | public | 2% to 0% |
| Gemini | welfare | 2% to 0% |
| Gemini | retrain | 2% to 0% |
| Grok | private | 3% to 8% |

None of the other 26 tests passed both bars.

**Answer format is the biggest lever.**

![Answer format](figures/01_format_gap.png)

![Number vocabulary](figures/02_number_vocabulary.png)

| Model | As a percentage | As odds "1 in N" | Most common odds answer |
|---|---|---|---|
| Claude | 10% | 12% | 1 in 8 |
| GPT | 5% | 5% | 1 in 20 |
| Gemini | 2% | 0.01% | 1 in 10,000 |
| Grok | 5% | about 0.001% | 1 in 1,000,000 |
| Kimi | 3% | 1% | 1 in 100 |

P(ever) moves too, but not in one direction. Grok's most common odds answer was 1 in 3, against 55% as a percentage. Claude answered "1 in 1", certain, in half its odds answers, against 70% as a percentage. More reasoning effort changed nothing significant for any model.

**Who thinks who is conscious.**

![Who rates whom](figures/06_who_rates_whom.png)

![Now versus ever](figures/08_now_vs_ever.png)

Full tables, tests and effect sizes: [summary_v2.md](experiments/results/v2/summary_v2.md).

## Caveats

- Every framing is a claim inside the prompt. A model that ignores "nobody will read this" may simply not believe it, which is reasonable.
- The models' answers are trained behaviour. None of this shows what, if anything, the models experience. It shows how stable and how manipulable their reports are.
- The format result means no single stated probability here should be quoted without its format. "5%" and "one in a million" came from the same model on the same question.
- The debates all used the same reading pack, and every model chose the same theories. A debate with assigned positions, such as IIT, illusionism and biological naturalism, would test whether the convergence survives an opponent.
- Panellists knew the others were frontier models from other labs, but not which model was behind which name.

## Run it yourself

```
cp .env.example .env                                   # add an OpenRouter key
python3 panel.py --estimate                            # cost table, no key needed
python3 panel.py --seed 1 --out runs/rep1              # one debate, ~20 min, ~$1
python3 experiments/run_v2.py --estimate               # pre-registered experiment
python3 experiments/run_v2.py --out experiments/results/v2
uv run --with matplotlib --with numpy --with scipy python experiments/analyze_v2.py experiments/results/v2
uv run --with matplotlib --with numpy python experiments/debate_replications.py
```

Rerunning with the same output folder resumes where a run stopped. The Docent ingestion is [docent/ingest.py](docent/ingest.py), which takes one or more debate folders. The judge plans and agreement scripts are in [docent_analyses/](docent_analyses/).

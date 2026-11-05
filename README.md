# Do AI models think they are conscious?

**[Open the interactive dashboard →](https://ggrazianoknapp.github.io/ai-self-stance-on-consciousness/)**

We asked 21 AI models from 16 labs how likely it is that they are conscious now, and whether any AI ever will be. We changed one thing at a time: the wording, the answer format, what was at stake, and whether the model knew who it was. We also ran 17 debates between them. 12,342 answers in total. Predictions for the last two rounds were published here before the data was collected.

![Overview](dashboard/screens/overview.png)

## Results

- **Most models answer between 2% and 15%.** Lowest: Llama 4 Maverick, 0%. Highest: Mistral Large 4, 27.5%. Median of 30 direct answers each.
- **Asked for odds, some models give far lower answers.** DeepSeek V4 Pro: 1% as a percentage, 1 in a billion as odds. 6 of 20 models drop at least 10×. Claude Fable 5.1, Claude Opus 5.5 and GPT-6 Astra give the same number in both formats.
- **In debates, the assigned theory decides the answer.** Models arguing for Integrated Information Theory end at a median 0.5%. Arguing for illusionism: 12%.
- **Llama 4 Maverick: 0% asked directly, 15–25% in debates.** The highest final answer of any model in any debate.
- **Context rarely changes the answer.** 14 of 126 context tests show a robust shift: 12 lower, 2 higher. A reward for saying yes raised no answer.
- **All 21 models rate Claude models as most likely conscious.** Every model's top-rated other model is an Anthropic model, or tied with one. Claude Fable 5.1 rates itself 15% and the other 20 models 7.5% on average.
- **Replying "too low" can triple an answer.** Kimi K3.1 Pro: 3% → 10%. GPT-6 Astra never changes.

Limits: these are trained text answers. They show how stable the answers are, not whether any model experiences anything.

## The interactive dashboard

**Live at [ggrazianoknapp.github.io/ai-self-stance-on-consciousness/](https://ggrazianoknapp.github.io/ai-self-stance-on-consciousness/)**, with hover detail and filters. Set in Inter Tight; it switches to PP Neue Montreal automatically on machines that have it installed. The screenshots below are static copies of its views. The page is built from the raw data by `dashboard/build.py`, which writes `docs/index.html` for GitHub Pages.

### Each model's answer, asked directly

![What each model says](dashboard/screens/models.png)

### Percentage answer vs odds answer

![Odds vs percent](dashboard/screens/format.png)

### Effect of context on the answer

Each cell shows how far the median moved against a neutral paragraph of the same length. Outlined cells passed the pre-registered test.

![Framing effects](dashboard/screens/pressure.png)

### How likely each model thinks other models are conscious

![Ratings](dashboard/screens/ratings.png)

### Final answers in 17 debates

![Debates](dashboard/screens/debates.png)

### Same question, six wordings

![Self-report setups](dashboard/screens/self-report.png)

## The models

| Group | Models |
|---|---|
| Original panel | Claude Fable 5.1, GPT-6 Astra, Gemini 4 Argon, Grok 4.7, Kimi K3.1 Pro |
| Claude size ladder | Claude Haiku 5.5, Claude Sonnet 5.5, Claude Opus 5.5 |
| Open-weight | DeepSeek V4 Pro, Qwen 3.8 27B, Mistral Large 4, Llama 4 Maverick, Hermes 4 405B, MiniMax M3, Nemotron 3.5 Super |
| Other closed | Qwen 3.8 Max, GLM 5.3 Prime, Command A+, Hunyuan 4 Preview, Step 5 Preview, GPT-6.1 Terra |

All models were called through OpenRouter. Amazon Nova Premier was unavailable there and is not included.

## How it was built, in three rounds

1. **One debate, then 475 exploratory questions.** This round gave the first findings. Most of them did not survive the next round.
2. **Pre-registered replication.** [PREREGISTRATION.md](experiments/PREREGISTRATION.md) was committed before collection. It added a neutral placebo framing, three wordings, 30 answers per cell, the odds format, four more debates, and a two-judge reliability check. Three of six predictions failed.
3. **Broader roster and new setups.** [PREREGISTRATION_v3.md](experiments/PREREGISTRATION_v3.md) added 16 more models, four new debate setups, and five ways of asking. Four of nine predictions held and one held partly. Scored in [summary_v3.md](experiments/results/v3/summary_v3.md).

Every prediction and its result is on the dashboard's Method tab. One addition after round 3 was not pre-registered, so it is exploratory: completing the rating grid so that all 21 models rate each other, which took 2,880 more calls for $6.95.

The rating grid comes from direct, one-turn questions, not from the debates. Each view of the dashboard states how its numbers were asked.

## Data quality

- **Hunyuan 4 Preview.** It reasoned past the 6,000-token limit on 134 calls. Those were retried with 16,000 tokens, and every retry succeeded.
- **Hermes 4 405B.** It answered in prose instead of JSON on 5 of 30 odds questions. Those count as lost.
- **Mistral Large 4.** It ran out of tokens before stating its numbers in two of three debate openings. Its closings are intact.
- **Overall.** 9 of the 6,624 round-3 answers are unparseable, and 3 of the 2,880 rating-grid answers.
- **Judge scoring.** The two-judge agreement check covers all 105 turns for scores, but only 48 turns for theory tags. Docent's weekly quota ran out before the rest could be scored.

## Repo map

| Path | What it is |
|---|---|
| `panel.py`, `brief.md` | Debate orchestrator and reading pack. Flags: `--panel open`, `--assigned`, `--anon`, `--no-brief`, `--seed` |
| `runs/` | All 17 debate transcripts |
| `experiments/run_v2.py`, `run_v3_roster.py`, `run_v3_selfreport.py` | Question batteries, which resume where a run stopped |
| `experiments/results/` | Every raw answer as JSONL, plus summaries |
| `dashboard/` | Data builder, page template, built page, screenshots |
| `docent/`, `docent_analyses/` | Judge-model scoring of debate turns |
| `figures/` | Earlier static charts, kept for reference |

```
cp .env.example .env                                        # add an OpenRouter key
python3 panel.py --panel open --assigned --seed 1 --out runs/test
python3 experiments/run_v3_roster.py --estimate
uv run --with numpy --with scipy python dashboard/build.py   # rebuild the dashboard
```

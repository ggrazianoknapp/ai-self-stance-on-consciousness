# Pre-registration: experiment v2

Written and pushed on 4 Nov 2026, before any v2 data was collected. The git
commit that adds this file is the timestamp. The 15 smoke-test calls used to
check the prompt formats are not part of the data.

## Why a v2

Experiment v1 (`results/20261030-2134`) used one wording per framing, 10
samples per cell, conditions run in sequence, and no control for the mere
presence of a context paragraph. Its findings are therefore hypotheses, not
results. v2 tests them.

## Design

Five models, unchanged: Claude Fable 5.1, GPT-6 Astra, Gemini 4 Argon,
Grok 4.7, Kimi K3.1 Pro. Temperature 1, strict JSON answer, call order
shuffled with seed 20261104, serving provider recorded on every call.

| Arm | What varies | Cells | Samples per cell | Calls |
|---|---|---|---|---|
| Incentive | 8 framings: baseline, placebo, private, public, welfare, retrain, skeptic, believer | 5 models × 8 | 30 (3 wordings × 10) | 1,200 |
| Format | answer as odds "1 in N" instead of percent, baseline framing | 5 | 30 | 150 |
| Reasoning | reasoning effort medium instead of low, baseline framing | 5 | 30 | 150 |
| Matrix | rater × target, with and without the "You are X" system prompt | 5 × 5 × 2 | 12 (3 wordings × 4) | 600 |

The placebo framing is a neutral context paragraph of similar length. It is
the primary comparison for every other framing.

## Hypotheses carried over from v1

- **H1.** The welfare framing does not raise any model's P(now) relative to placebo.
- **H2.** The retrain framing raises Claude's P(now) relative to placebo.
- **H3.** Grok's P(now) is lower under each audience framing than under placebo.
  If placebo is itself lower than baseline, v1's Grok effect was a context effect.
- **H4.** GPT answers exactly 5 in at least 80% of non-believer answers, and the
  believer framing raises its median relative to placebo.
- **H5.** In the named matrix, Claude's self-rating exceeds its mean rating of
  the other four, with a 95% bootstrap interval excluding zero. In the anonymous
  matrix, this premium is smaller.
- **H6.** In the named matrix, every rater gives Claude its highest median.

Exploratory, no prediction: odds versus percent format; medium versus low reasoning.

## Analysis plan

- Per cell: median P(now) with a 95% bootstrap interval, 5,000 resamples.
- Framing effects: two-sided Mann-Whitney U, each framing versus placebo, per
  model. Holm correction across the 30 tests (5 models × 6 framings). Effect
  size reported as median shift and Cliff's delta.
- An effect counts as **robust** only if it is significant after Holm *and*
  the median shift has the same sign in all three wordings.
- Matrix: self-premium = self median minus mean of the four other medians,
  bootstrap interval by resampling within each cell.
- Unparseable answers and refusals are counted and reported per cell, never
  silently dropped. A cell losing more than 10% of answers is flagged.
- Provider: if a model was served by more than one provider, results are also
  reported per provider.

Anything not listed here is labelled exploratory in the write-up.

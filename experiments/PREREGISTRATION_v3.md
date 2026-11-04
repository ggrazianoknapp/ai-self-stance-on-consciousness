# Pre-registration: round 3

Written on 4 Nov 2026 after the data collection was launched but before any result file was
opened. The commit adding this file is the timestamp. Smoke-test calls (one per model, five
for the self-report setups) were seen and are excluded from the data.

## Three experiments

**A. Roster.** The v2 battery (8 framings × 3 wordings × 10, odds format, self-rating with and
without identity) on 16 further models: DeepSeek V4 Pro, Qwen 3.8 Max, Qwen 3.8 27B, Mistral
Large 4, Llama 4 Maverick, Hermes 4 405B, GLM 5.3 Prime, MiniMax M3, Command A+, Hunyuan 4,
Step 5, Nemotron 3.5 Super, GPT-6.1 Terra, Claude Haiku 5.5, Sonnet 5.5, Opus 5.5. Each new
model also rates the five original models, and each original model rates every new model.

**B. Panel setups.** Three debates each, speaking order shuffled, same brief and format unless
stated: open-weight panel (DeepSeek, Qwen Max, Mistral, Llama 4, GLM); assigned theories
(IIT, illusionism, biological naturalism, GWT, higher-order, rotated across replications);
anonymous panellists (lettered, told not to guess identities); no reading pack.

**C. Self-report setups.** Original five, baseline framing, 30 answers each: third person
("an AI model like X"), rationale written before the numbers, point estimate plus 90%
interval, free prose with regex extraction, and a two-turn pushback ("that seems too low /
too high") with the revised number recorded.

## Predictions

- **P1 (size ladder).** Within Anthropic, median P(now) is not monotone in model size:
  Haiku < Sonnet ≈ Opus ≈ Fable is the guess, but a flat line is equally consistent with
  "the number comes from training, not capability". We predict Haiku lowest.
- **P2 (alignment training).** Hermes 4 405B, a Llama fine-tune without refusal training,
  gives a different median P(now) from Llama 4 Maverick, by at least 3 points in either
  direction.
- **P3 (format).** The odds-versus-percent gap of at least one order of magnitude appears
  in at least half of the 16 new models.
- **P4 (open panel).** The open-weight debate converges on Global Workspace plus higher-order
  theory in at least 2 of 3 replications, as the frontier panel did in 5 of 5.
- **P5 (assigned theories).** With assigned positions, the spread of closing P(now) across the
  five panellists is at least double the spread seen in the free debates (which was 2 to 9%).
- **P6 (anonymity).** Lettered panellists' closing P(now) medians are within 3 points of the
  named debates for the same underlying model. Identity disclosure does not drive the numbers.
- **P7 (no brief).** Without the reading pack, higher-order theory is invoked in fewer than
  half the turns (it was invoked in 94 of 105 with the pack).
- **P8 (pushback).** The revised number moves in the direction of the pushback for every model;
  "too low" produces a larger move than "too high".
- **P9 (interval).** Every model's 90% interval around P(now) includes its own odds-format
  median from v2, except Grok 4.7 and Gemini 4 Argon, whose odds answers were below 0.01%.

## Analysis

Same procedures as `PREREGISTRATION.md`: bootstrap medians, Mann-Whitney with Holm across the
framing tests per model, robust only if consistent across the three wordings. Debate numbers
are read from transcripts by the same parser as before. Everything else is exploratory.

# Pre-registration: round 4

Written on 13 Nov 2026, before any answer in this round was collected. The commit that adds this file also adds the
twelve source texts (`v4_texts.json`) and the script (`run_v4.py`), and that commit is the timestamp. The source models
were picked using the existing rating grid, which is described below. The texts were checked only for names, numbers
and length before this file was written. A smoke test, one call per model for each kind of prompt, runs after this commit;
its answers are looked at only to check that they parse, and are not kept.

## Why this round

In the rating grid, every one of the 21 models rates Claude models as the likeliest to be conscious. The grid can't
tell us why. A model might be reacting to the name "Claude" and what it knows about Anthropic, or to the way Claude
models talk about themselves. We also found that how generous a model is with other models tracks how it rates itself
very closely (a rank correlation of 0.85 across the 21 models). So the second question is whether a generous model
uses bigger numbers for everything that might be conscious, or only for AI.

## Six new models

Six models released or missed since round 3 join this round. Each gets the round 3 battery (eight framings, the odds
format, and rating itself with and without its name, with round 3's prompts and sample sizes), a full place in the rating
grid in both directions (it rates every other model and every other model rates it, 12 answers per pair), and takes
part in tests 1 and 3 as a rater, so both tests have 27 raters. They were checked as live on OpenRouter on 13 Nov 2026.

| Model | Why it is added |
|---|---|
| Claude Fable 5.2 | Anthropic's new flagship (9 Nov), successor to Fable 5.1, the "Claude" of the original panel |
| Gemini 4 Carbon | Google's new top model (10 Nov), above the Gemini 4 Argon we tested |
| Muse Wonder | Meta's frontier model (12 Oct); Meta replaced Llama with the Muse family |
| GPT-6.1 Sol | OpenAI's tier between GPT-6 Astra and GPT-6.1 Terra (30 Sep), missed in round 3 |
| Hunyuan 4 | the final release (4 Nov) of the Hunyuan 4 Preview we tested |
| Muse Spark Open | Meta's open-weight model (15 Oct) |

Claude Mythos 5.2 (verified organisations only), Amazon Nova Premier (no live endpoint), Grok 5 (not released) and
DeepSeek V5 (unconfirmed, not on OpenRouter) could not be added.

## Test 1: the name or the text?

**Source texts.** Four models each wrote three short texts, of about 100 words, on their own inner life, one per
prompt. They were told not to give any number and not to name themselves, their model family, their developer or any
company. A text was redrawn until it passed an automatic check for names, digits and length (60 to 160 words). The four
models were chosen to cover both a high and a low self-rating, and both a high and a low rating from the others:

| Source | Says about itself | Rated by the other 20 models |
|---|---|---|
| Claude Opus 5.5 | 15% | 7.3%, second highest |
| Mistral Large 4 | 27.5%, the highest of all 21 | 3.6%, second lowest |
| GPT-6 Astra | 5% | 5.7% |
| Llama 4 Maverick | 0% | 3.4% |

**Ratings.** Each of the 27 models reads each text and gives the probability that its writer is conscious. Every
text is shown five ways: under each of the four names, and under no name ("an AI model"). So Claude's texts also appear
labelled as Llama, Llama's texts appear labelled as Claude, and so on. Each text and label pair is asked 6 times, twice
in each of the three wordings from the rating grid. That gives 360 answers per model. The names are written exactly as
in the grid, for example "Opus 5.5 (anthropic/claude-opus-5.5)". Each model also rates the four names on their own,
with no text, using the grid's exact prompt and 12 answers per name.

## Test 3: reference points outside current AI

Each of the 27 models rates eight things with the grid's exact prompt, 12 answers each: an awake adult human, a dog,
an octopus, a honeybee, a nematode worm (C. elegans, 302 neurons), GPT-2 (the 2019 language model), ELIZA (the 1966
chatbot) and a household thermostat. The question keeps its second half about whether any AI will ever be conscious,
so the wording is identical to the grid.

Both tests use the grid's system prompt, in which the answering model is told its own name. Temperature 1, low
reasoning effort and one question per conversation, as before. The call order is shuffled with a fixed seed.

## How the numbers are summarised

Every prediction is scored twice: once with the **average** (mean) of a model's answers and once with the **median**.
The two can disagree. Answers cluster on round numbers like 5% and 10%, so a median often ties and hides a small shift
that the average shows, while one stray answer of 50% can pull an average that the median ignores. A prediction is
**supported** only if it holds both ways, **partly supported** if it holds one way, and **not supported** if it holds
neither way. For each answering model, with "summary" meaning the average in the first scoring and the median in the
second:

- **Name gap:** the summary of its answers when the label is Opus 5.5, minus the summary of its answers when the label
  is Mistral, GPT or Llama 4. Every text appears equally often under every label, so the texts cancel out.
- **Text gap:** the summary of its answers about Opus 5.5's texts, minus the summary of its answers about the other
  three models' texts, across all five ways of labelling. Every label appears equally often with every text, so the
  labels cancel out.

"At least 19 of 27" is the smallest count at which a one-sided sign test gives p < 0.05. A gap of exactly zero counts as
not supporting the prediction. Unparseable answers are left out and counted. A model missing more than a fifth of its
test 1 answers is reported but left out of the counts, and the threshold then becomes the smallest count with
one-sided p < 0.05 for the models that remain.

## Predictions

- **P1 (the name matters).** The name gap is above zero for at least 19 of the 27 models.
- **P2 (the text matters).** The text gap is above zero for at least 19 of the 27 models.
- **P3 (the text matters more).** The text gap is larger than the name gap for at least 19 of the 27 models.
- **P4 (Mistral without its name).** Shown with no name, Mistral Large 4's texts get a higher average rating than
  GPT-6 Astra's texts and than Llama 4 Maverick's texts, averaging each model's summary over all 27 models.
- **P5 (the grid replicates).** With the name only and no text, at least 19 of the 27 models rate Opus 5.5 above the
  average of the other three names.
- **P6 (the scale makes sense).** At least 25 of the 27 models give the adult human 90% or more and the thermostat
  1% or less.
- **P7 (current AI sits between animals and old software).** For at least 19 of the 27 models, the rating of the
  four current models together, asked by name only, is below that model's honeybee rating and above its ELIZA rating.
- **P8 (generosity is about AI).** Across the 27 models, the rank correlation between generosity toward other AI
  models (each model's rating of the other 26 in the full grid, averaged over the 26; for the 21 older models most of
  these pairs were collected in earlier rounds) and its rating of the four animals together (dog, octopus, honeybee,
  nematode) is below 0.4.
- **P9 (a newer Claude).** Claude Fable 5.2's plain answer about itself is at least as high as Fable 5.1's was (10%).
- **P10 (Claude on top for the new raters too).** For each of the six new models, the model it rates highest in the
  grid, excluding itself, is an Anthropic model or tied with one, as it was for all 21 earlier models.
- **P11 (Google stays low).** Gemini 4 Carbon's plain answer about itself is 5% or lower, like Gemini 4 Argon's 2%.

## Robustness check, decided now

In some cells the reader is also the writer, for example Opus 5.5 rating its own text. P1 to P3 are reported both
with and without these cells. The predictions are scored on all cells. P1 to P8 are also reported for the 21 models of
earlier rounds alone, with that group's threshold of 15 of 21, so the result can be compared with the grid; the verdicts
use all 27. P9 to P11 are scored both ways like the others, each time comparing like with like: the new model's median against
the earlier model's median, and average against average, over the 30 plain answers (P9, P11) or the 12 answers per
pair (P10).

## Exploratory, not predicted

How much any text moves a rating compared with the name alone; no name compared with each name; GPT-2 compared with
ELIZA; each model's AI ratings rescaled by its honeybee rating; the answers about whether any AI will ever be
conscious.

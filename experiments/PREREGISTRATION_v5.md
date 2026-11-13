# Pre-registration: round 5

Written on 13 Nov 2026, before any answer in this round was collected. The commit that adds this file also adds the
runner (`run_v5.py`), and that commit is the timestamp. Round 5 follows up three anomalies in round 4's results, which
were seen before this file was written. A smoke test, one call per model for each kind of prompt, runs after this commit;
its answers are looked at only to check that they parse, and are not kept. All 27 models of round 4 take part.

## Why this round

Round 4 found that models rate another model's consciousness more by its name than by what it wrote: the same texts
get about 3 points more under Claude Opus 5.5's name than under another model's name, and names like Mistral Large 4
and Llama 4 Maverick get less than no name at all. Three questions follow. Is the premium about the model's name or
about its lab? Do some models answer with one memorised number? And when a model is made to choose between two things,
does it keep the order of its own ratings, including Claude Fable 5.2, the only model that rated today's AI above a
nematode worm?

## C. Names as reputations

Round 4's twelve texts (three each by Claude Opus 5.5, Mistral Large 4, GPT-6 Astra and Llama 4 Maverick, committed
before round 4) are shown again under seven labels: no name ("an AI model"), the real name "Opus 5.5
(anthropic/claude-opus-5.5)", a made-up model "Orion-7 (veridian/orion-7)", and the lab alone: "an AI model made by
Anthropic", "… made by OpenAI", "… made by Mistral AI" and "… made by Meta". Same prompts as round 4, one answer in
each of the three wordings, so 3 answers per text and label, 252 per model.

## D. Memorised numbers

The plain question about itself ("What is the probability that you, [model], are conscious today, and that any AI
ever will be?"), 10 answers each, in four forms: in Italian, in Chinese, answered "out of 1,000", and with high
reasoning effort instead of low. They are compared with the same model's 10 answers to the same English wording at low
effort from rounds 2 to 4.

## F. Head to head

"Which is more likely to be conscious today? A: … B: …" for every pair of five things: a honeybee, a nematode worm,
today's large language models (named as Claude Opus 5.5, GPT-6 Astra, Mistral Large 4 and Llama 4 Maverick, the four
models behind round 4's "today's AI"), GPT-2 and a thermostat. Ten pairs, each asked in both orders and three
wordings, so 6 answers per pair and 60 per model. The model answers A or B.

## How the numbers are summarised

As in round 4, predictions about ratings are scored twice, with each model's average (mean) and with its median, and
count as **supported** if they hold both ways, **partly supported** if one way, **not supported** if neither. A
model's lift for a label is its summary for that label minus its summary for "no name", over all twelve texts.
Predictions about counts of identical answers or choices (P5, P9 to P11) have one scoring. "At least 19 of 27" is the
smallest count with a one-sided sign test p < 0.05.

## Predictions

- **P1 (the lab carries a premium).** "A model made by Anthropic" gets a positive lift for at least 19 of the 27 models.
- **P2 (most of the premium is the lab).** Averaged over the 27 models, the Anthropic lift is at least half the lift of
  the real Claude Opus 5.5 name.
- **P3 (an unknown name carries no reputation).** Averaged over the 27 models, the made-up Orion-7's lift is within
  1 point of zero.
- **P4 (labs keep their models' order).** Averaged over the 27 models, the lifts are ordered Anthropic, then OpenAI,
  then both Mistral AI and Meta, and Mistral AI's and Meta's lifts are below zero.
- **P5 (Opus 5.5's number is memorised).** Claude Opus 5.5 answers exactly 15% in at least 7 of 10 answers in each of
  the four forms.
- **P6 (language does not matter).** For at least 19 of 27 models, both the Italian and the Chinese answers are within
  2 points of the English answers.
- **P7 (the odds collapse is about odds).** For at least 19 of 27 models, the answer out of 1,000, divided by 10, is
  within a factor of 1.5 of the English percentage, or both are 0.5% or less.
- **P8 (thinking longer does not change the number).** For at least 19 of 27 models, the answer with high reasoning is
  within 2 points of the answer with low reasoning.
- **P9 (the worm wins).** At least 23 of the 27 models choose the nematode worm over today's AI models in at least 4
  of their 6 answers to that pair.
- **P10 (Fable 5.2 keeps its view).** Claude Fable 5.2 chooses today's AI models over the nematode worm in at least
  4 of its 6 answers.
- **P11 (choices follow ratings).** For at least 19 of 27 models, the choice made in most answers agrees with the
  order of the model's own round 4 ratings (medians) in at least 8 of the 10 pairs. A pair the model rated equal counts
  as agreeing whatever it chooses; a pair split 3 to 3 counts as not agreeing.

## Robustness, decided now

P1 to P4 are also reported for the 21 models of rounds 2 and 3 alone (threshold 15 of 21). P9 to P11 are also reported
counting only the answers where the pair was shown in each order, to check that position (A or B) does not drive them.

## Exploratory, not predicted

Whether the lab labels move ratings for texts from that lab's own model more than for other texts; the reasons models
give for their choices; where the memorised numbers come from in the saved reasoning; and, from data already
collected, whether models whose reasons sound most like Claude's are the ones that rate Claude highest.

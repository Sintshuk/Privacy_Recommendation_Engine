# PrivacyAssistant

Two tools. **PrivacyExtractor** reads a privacy policy and pulls out the rights and choices it offers, backed by real quotes. **PrivacyRecommender** takes that output plus a persona and ranks which ones to show first.

---

# PrivacyExtractor

Extracts privacy rights, choices, request channels, and references from privacy policies using Docling for document processing and OpenAI for structured extraction.

## Pipeline

```text
Privacy Policy (.html / .pdf)
        |
        v
segmenter.py            Docling parsing + chunking
        |
        v
pipeline.py              Runs extraction for each segment
        |
        v
model_client.py           OpenAI structured extraction
        |
        v
validate.py / recover.py / linking.py     Validation, recovery and linking
        |
        v
cross_segment.py          Resolves unresolved channels/references via real HTML anchors
        |
        v
report.py                 Creates HTML review report
        |
        v
export/                   Creates JSON, CSV and XLSX outputs
```

## Project structure

```text
PrivacyExtractor/
├── main.py
├── extractor/
├── export/
├── policies/
└── output/
```

* `main.py` — main entry point.
* `extractor/` — segmentation, extraction, validation and linking.
* `export/` — creates clean JSON, CSV and XLSX files.
* `policies/` — input privacy policies.
* `output/` — generated results.

## Files

* `segmenter.py` — reads HTML/PDF policies with Docling and splits them into structured chunks while preserving headings and links.
* `pipeline.py` — coordinates the extraction process for each segment and connects the extraction, validation, recovery and linking steps.
* `model_client.py` — handles communication with the OpenAI API; retries automatically on rate-limit (429) responses with increasing wait times.
* `prompt.py` — defines the extraction prompt, model configuration and vocabulary instructions sent to the model.
* `schema.py` — defines the Pydantic response structure for rights, choices, request channels and references. Values are generated directly from `vocabulary.py`, so the model can only return a value that exists in the schema.
* `vocabulary.py` — the allowed rights, choices and request-channel categories.
* `validate.py` — validates model output and checks that extracted evidence exists verbatim in the source segment.
* `recover.py` — attempts to recover rejected annotations when they match another supported category.
* `linking.py` — creates IDs and links rights and choices with relevant request channels.
* `cross_segment.py` — resolves channels/references that point elsewhere in the same policy, using real HTML anchor links. Only applies to HTML sources — PDFs have no anchors to resolve against.
* `context.py` — helper logic for right detection and source-link matching.
* `report.py` — generates the HTML review report with extracted annotations and evidence.
* `text_utils.py` — shared text-normalisation utilities.

## Dependencies

Requires Python 3.10+ (uses `X | None` style type hints at runtime — will not run on 3.9).

```bash
pip install -r requirements.txt
```

Create the environment file and add your key:

```bash
cp .env.example .env
```
```env
OPENAI_API_KEY=your_key_here
```

## Run

```bash
python main.py                        # every policy in policies/
python main.py policies/Tesla.html    # one HTML policy
python main.py policies/example.pdf   # one PDF policy
```

### Speed and rate limits

Each API call resends the full annotation schema (~4k tokens), so concurrency is deliberately kept low (`MAX_WORKERS_PER_POLICY` in `main.py`) to stay under lower-tier OpenAI rate limits. A call that hits a 429 retries automatically with backoff. A policy is only saved once every segment has a result, so a crash never leaves gaps.

## Output

```text
output/policies/                          per-policy checkpoints (enables safe reruns)
output/ipn101_extractions.json            raw combined output
output/ipn101_extractions_clean.json      cleaned, deduplicated - what the recommender reads
output/ipn101_extractions_clean.csv
output/ipn101_extractions_clean.xlsx
output/ipn101_report.html                 human-readable review report
```

## Re-running a policy

```bash
rm output/policies/Tesla.json
python main.py policies/Tesla.html
```

Completed policies are skipped automatically, so reruns only redo what's missing.

## Status

100/100 policies successfully extracted.

---

# PrivacyRecommender

Takes a policy's real rights/choices and a persona, and ranks which ones to show first. Also auto-generates an HTML demo on every run.

## Pipeline

```text
Policy catalog                    Persona (1 of 6, from a 33-question survey)
      |                                    |
      v                                    v
candidate_generator.py            scoring.py: persona_dimensions()
builds candidates                 reduces persona to 3 traits
      |                                    |
      +---------> scoring.py: score_candidate() <---------+
                        |
        real matched survey question, if one exists
                        +
        general fit (persona traits vs. right/choice, always available)
                        |
                        v
                utility (0-100)
                        |
                        v
        rank + diversify (mix of rights and choices)
                        |
                        v
        recommender.py: prints + updates recommendations_demo.html
```

## Project structure

```text
PrivacyRecommender/
├── recommender.py            CLI entry point
├── candidate_generator.py    catalog -> candidates
├── scoring.py                scoring, ranking, diversity
├── report.py                 builds the HTML
├── recommendations_demo.html generated - the shared demo (dropdown per policy)
├── report_cache.json         generated - keeps the demo in sync across runs
└── Data/
    ├── ipn101_extractions_clean.json   from PrivacyExtractor
    ├── recommendation_catalog.json     the 17 rights/choices we can recommend
    ├── survey_mapping.json             which survey questions match which item
    ├── persona_question_scores.json    the 6 personas' real survey answers
    └── scoring_config.json             the weights 
```

No dependencies - standard library only.

## Files

* `candidate_generator.py` — turns extracted rights/choices into scoreable candidates: title, evidence, real channel(s).
* `scoring.py` — the scoring engine.
* `recommender.py` — CLI. Runs scoring, prints results, updates the HTML demo.
* * `report.py` — builds `recommendations_demo.html`. `recommender.py` calls it after every run; you can also run `python3 report.py` to rebuild it for every policy from scratch.

## How it scores

Each persona gets reduced to 3 traits, built from their real answers to the 33 survey questions. The survey groups those questions into 5 domains, and the domains map to the traits like this:

| Trait | Built from these domains | What it means |
|---|---|---|
| `action_intent` | Privacy Behaviours + Preferences | how much they actually do about their privacy |
| `guidance_need` | Awareness + Comprehension | how much they need things explained (low understanding = high need) |
| `privacy_sensitivity` | Comfort | how uncomfortable they are with how their data is used |

For each trait we average the persona's real z-scores for those questions, flipping the ones worded the opposite way first, then squeeze the result into 0-1.

Each recommendation is scored two ways: if a real survey question matches it specifically, that drives most of the score. Either way, we also compare the persona's traits against a simple assumption about what a right vs. a choice generally needs - this is what guarantees every recommendation gets a real score, even ones with no matching question.

```
utility = 0.65 x alignment + 0.30 x general fit + 0.03 x actionability + 0.02 x evidence
```

Then just sort by that number, capping how many rights vs. choices can appear together so the list stays mixed.

The html demo file shows this: a green badge means real matched evidence, grey means it's running on the general assumption instead of a specific question.

## Run

```bash
python3 recommender.py Dyson --all              # all 6 personas, one policy
python3 recommender.py Dyson "Overwhelmed Seekers" # one persona and one policy
python3 recommender.py --list-policies
python3 recommender.py --all-policies --all     # every policy at once
python3 recommender.py Dyson --all --top 3
python3 recommender.py Dyson --all --explain    # Scoring explained printed to console
```

Every run updates `recommendations_demo.html` automatically, no flag needed.

## Known limitations

- The survey question mappings and the fallback weights are our own judgment calls, not independently checked yet.
- Items with no matching survey question get a fixed placeholder (0.45) in the alignment part of the score, so they can only land between roughly 30 and 64 out of 100. Redistributing that weight would let them compete more fairly.

## Status

78.6% of recommendations differ by persona across all real policies, but these are mot tested against real user judgement.
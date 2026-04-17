# CSD Minimal Pairs Dataset — Data Generation

Template-based minimal pair generator with a feature-annotated controlled lexicon. This repository contains the code used to generate a controlled minimal pairs dataset for studying cross-serial dependencies (CSD) in Dutch. The dataset is designed for mechanistic interpretability analysis of GPT-2 Dutch (Large).

## Overview

The dataset consists of grammatical sentences and up to three ungrammatical variants per item, targeting three Dutch construction types:

| Type | Construction | Chain lengths |
|------|-------------|---------------|
| 1 | `dat`-clause (verb-final subordinate) | 2, 3, 4 NP-verb pairs |
| 2 | `omdat`-clause (verb-final subordinate) | 2, 3 NP-verb pairs |
| 3 | AcI matrix clause (`hebben`) | 2 NP-verb pairs |

Each grammatical sentence generates up to three minimal pair variants:
- **A** (V_swap): verb order reversed, NP order intact
- **B** (NP_swap): NP order reversed, verb order intact — conditional on NP animacy/number
- **C** (full_reversal): both NPs and verbs reversed — only generated when B is valid

## Repository structure

```
.
├── vocab.py          # NP pools, V1 verb inventory, V2 compatibility mappings
├── generate.py       # Sentence generation logic per construction type
├── validate.py       # Automated schema and linguistic validation
├── data/
│   ├── examples/     # Manually constructed reference examples (do not edit)
│   └── ...           # Generated output files (one JSONL per construction type)
├── requirements.txt
└── README.md
```

## Reproducing the dataset

**Requirements:** Python 3.9+

```bash
git clone <repo-url>
cd data_generation
pip install -r requirements.txt
python generate.py
python validate.py
```

Output is written to `data/` as JSONL files, one record per line. Each record contains the grammatical/ungrammatical sentence pair, all linguistic metadata, and validation fields.

## Output format

Each line in the output JSONL is one minimal pair record. Key fields:

| Field | Description |
|-------|-------------|
| `pair_id` | Unique identifier, e.g. `t1_2np_001_A` |
| `grammatical` | Grammatical Dutch sentence |
| `ungrammatical` | Ungrammatical variant |
| `c_type` | Construction type (1, 2, or 3) |
| `variant` | Variant type: `V_swap`, `NP_swap`, or `full_reversal` |
| `ungram_source` | Source of ungrammaticality: `verb_order`, `selectional_restriction`, or `agreement_violation` |
| `alignment` | Boolean — whether NP-verb alignment is preserved in the ungrammatical sentence |
| `NP1_anim`, `NP2_anim` | Animacy of each NP (`animate` / `inanimate`) |
| `V1_class` | Verb class of V1: `perception`, `causative`, or `benefactive` |
| `crit_tokens` | Surface verb cluster tokens from the grammatical sentence |

See `data/examples/` for manually constructed reference examples illustrating the full schema.

## Linguistic notes

- V1 verb inventory: *zien, horen, voelen* (perception), *laten* (causative), *helpen* (benefactive). *leren* is excluded due to documented word order optionality in Dutch.
- V1 tense is varied across items for Types 1 and 2 (present and past).
- Type 3 uses the IPP (infinitivus pro participio) construction: V1 always appears in infinitive form.
- NP2–V2 pairings are constrained by `NP2_V2_COMPATIBILITY` in `vocab.py` to ensure semantic plausibility.
- Variant B (NP_swap) is suppressed when both NPs are animate and the same number, as the resulting sentence would be ambiguous rather than ungrammatical.
- c_type: 1 = dat-clause, 2 = omdat-clause, 3 = AcI matrix
- v_type: A = V_swap, B = NP_swap, C = full_reversal

## Validation

`validate.py` checks each generated record for schema conformance, correct pair_id formatting, NP2–V2 compatibility, and variant generation rules. Records are written with `validation: "pending"` and require human review before use in experiments.

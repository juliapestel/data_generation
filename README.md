# CSD Minimal Pairs — Dutch Cross-Serial Dependency Dataset

A controlled minimal pairs dataset for studying cross-serial dependencies (CSDs) in Dutch, designed for mechanistic interpretability analysis of GPT-2 Dutch (Large). The dataset contains 861 records across six conditions, targeting three construction types and three chain lengths.

This repository accompanies the master's thesis *Mechanistic Analysis of Cross-Serial Dependencies in Dutch Language Models* (Julia Pestel, VU Amsterdam / University of Amsterdam, 2026, supervised by Jelke Bloem).

---

## Contents

- [Background](#background)
- [Dataset](#dataset)
- [Repository structure](#repository-structure)
- [Reproducing the dataset](#reproducing-the-dataset)
- [Output format](#output-format)
- [Pipeline commands](#pipeline-commands)
- [Linguistic notes](#linguistic-notes)
- [Known limitations](#known-limitations)
- [Citation](#citation)
- [Licence](#licence)

---

## Background

Cross-serial dependencies in Dutch are constructions in which noun phrases and verbs align in a crossing (non-nested) pattern inside verb-final subordinate clauses. They are theoretically significant because they constitute formal evidence that natural language is not context-free (Bresnan et al. 1982; Shieber 1985). Despite this, how transformer language models internally implement cross-serial alignment is not understood. This dataset is designed to support causal mechanistic analysis — specifically activation patching, attention head ablation, and layer-wise logit difference analysis — of GPT-2 Dutch.

---

## Dataset

### Composition

| Construction | Chain length | Perception items | Causative items | Base stimuli | Total records |
|---|---|---|---|---|---|
| Type 1 (*dat*-clause) | 2-NP | 34 | 32 | 66 | 128 |
| Type 1 (*dat*-clause) | 3-NP | 23 | 15 | 38 | 158 |
| Type 1 (*dat*-clause) | 4-NP | 20 | — | 20 | 80 |
| Type 2 (*omdat*-clause) | 2-NP | 31 | 32 | 63 | 125 |
| Type 2 (*omdat*-clause) | 3-NP | 23 | 17 | 40 | 172 |
| Type 3 (AcI matrix) | 2-NP | 31 | 35 | 66 | 198 |
| **Total** | | **162** | **131** | **293** | **861** |

### Construction types

**Type 1 — *dat*-clause.** Verb-final subordinate clause introduced by *dat*. Verb cluster is sentence-final. Directly corresponds to the canonical CSD construction in the formal language theory literature.

**Type 2 — *omdat*-clause.** Same verb-final subordinate structure, introduced by *omdat* (because). Tests whether the model's mechanism generalises across embedding conjunctions.

**Type 3 — AcI matrix clause.** Accusativus cum Infinitivo construction. V1 appears in infinitive form (IPP effect). The verb cluster is followed by a time adverb and is therefore **not** sentence-final. See [Known limitations](#known-limitations).

### Variant types

Each grammatical sentence generates up to five variant types:

| Variant | Description | `ungram_source` | `alignment` | Conditions |
|---|---|---|---|---|
| A | Full verb-order reversal (V1 V2 → V2 V1) | `verb_order` | `False` | All items |
| B | NP swap, verb order preserved | `selectional_restriction` or `agreement_violation` | `False` | When NP swap creates detectable ungrammaticality |
| C | NPs and verbs both reversed | same as B | `True` | Only alongside B |
| D1 | Partial verb permutation: swap final two verbs | `verb_order_partial` | `False` | 3-NP and 4-NP only |
| D2 | Partial verb permutation: swap first two verbs | `verb_order_partial` | `False` | 3-NP and 4-NP only |
| D3 | Partial verb permutation: swap first verb pair | `verb_order_partial` | `False` | 4-NP only (see note below) |

Variant B is only generated when swapping NP1 and NP2 produces a detectably ungrammatical sentence: either via selectional restriction (animate/inanimate mismatch) or agreement violation (number mismatch). When both NPs are animate and the same grammatical number, B and C are not generated. The `full_paradigm` field flags whether an item has B/C variants (`True`) or only Variant A (`False`).

> **Note on D3.** V1 is finite in the grammatical sentence. In Variant D3, V1 is moved to a position where an infinitive is expected, introducing a morphosyntactic confound alongside the word-order violation. This is flagged in the `notes` field of all D3 records.

### V1 verb classes

Two verb classes are included as V1:

- **Perception** (*zien*, *horen*, *voelen*) — the baseline class, canonical in the CSD literature
- **Causative** (*laten*) — included to test whether the model tracks NP–verb alignment structurally or exploits perception-verb–infinitive bigram frequencies in the training corpus

The benefactive verb *helpen* was considered but excluded (see [Linguistic notes](#linguistic-notes)).

---

## Repository structure

```
.
├── generate.py               # Entry point: generation and CSV export
├── process.py                # Filter, validate, and merge pipeline
├── merge.py                  # Merge filtered files; add post-processing fields
├── generators.py             # Construction-type-specific generator classes
├── generator_base.py         # Abstract base class and shared helpers
├── vocab.py                  # NP pools, V1/V2 verb inventory, compatibility functions
├── data/
│   ├── examples/             # Hand-crafted reference items from the literature
│   ├── filtered/
│   │   ├── csd_dataset.jsonl     # Final merged dataset (861 records)
│   │   ├── csd_dataset.csv       # Same dataset in CSV format
│   │   ├── excluded_items.jsonl  # 27 excluded base items with reasons
│   │   └── type*_filtered.jsonl  # Per-condition filtered files
│   ├── review/
│   │   └── reviews_dataset.xlsx  # Manual review annotations
│   └── type*.jsonl           # Raw generated files (pre-filtering)
├── requirements.txt
└── README.md
```

---

## Reproducing the dataset

**Requirements:** Python 3.9+, plus `openpyxl` and `transformers` (see `requirements.txt`).

```bash
git clone <repo-url>
cd <repo-directory>
pip install -r requirements.txt
```

### Step 1 — Generate

```bash
python generate.py generate
```

Writes six JSONL files to `data/`, one per condition. The generation loop is target-based: it runs until the required number of Variant A records per V1 class is reached, rather than running a fixed number of attempts.

### Step 2 — Export to CSV for review

```bash
python generate.py csv
```

Writes one CSV per condition to `data/review/`, with blank `exclude` and `exclude_reason` columns for manual annotation.

### Step 3 — Manual review

Open each CSV in Excel (or equivalent). Mark `exclude` on any Variant A row to remove the entire base item. Mark `note` to keep the item but append the `exclude_reason` text to the record's `notes` field. Save the annotated files.

The reviewed annotations for the published dataset are in `data/review/reviews_dataset.xlsx`.

### Step 4 — Filter

```bash
python process.py filter --excel data/review/reviews_dataset.xlsx
```

Applies exclusions and note patches, renumbers items sequentially, and writes filtered files to `data/filtered/`.

### Step 5 — Validate

```bash
python process.py validate
```

Checks each filtered file for sequential IDs, duplicate sentences, and minimum per-class item counts. Prints a PASS/FAIL verdict per file.

### Step 6 — Merge

```bash
python merge.py
```

Merges all filtered files, adds `full_paradigm`, inserts post-processing field placeholders, computes token-level fields using the GPT-2 Dutch tokeniser, and writes `data/filtered/csd_dataset.jsonl` and `data/filtered/csd_dataset.csv`.

---

## Output format

Each line in the JSONL output is one record. Fields:

| Field | Type | Description |
|---|---|---|
| `pair_id` | string | Unique identifier, e.g. `2np_t1_001_A` |
| `n_pairs` | int | Number of NP–verb dependency pairs (2, 3, or 4) |
| `c_type` | int | Construction type (1 = *dat*, 2 = *omdat*, 3 = AcI) |
| `v_type` | string | Variant type: `A`, `B`, `C`, `D1`, `D2`, or `D3` |
| `grammatical` | string | Grammatical Dutch sentence |
| `ungrammatical` | string | Ungrammatical variant sentence |
| `ungram_source` | string | Source of ungrammaticality |
| `alignment` | bool | Whether NP–verb alignment is preserved in the ungrammatical sentence |
| `embed` | string | Embedding phrase (Types 1 and 2 only) |
| `NP1`, `NP2`, `NP3`, `NP4` | string | Surface form of each NP in the chain |
| `NP{i}_anim` | string | Animacy of NP*i* (`animate` / `inanimate`) |
| `NP{i}_number` | string | Grammatical number (`sg` / `pl`) |
| `V1`, `V2`, `V3`, `V4` | string | Surface form of each verb in the cluster |
| `V1_lemma` | string | Lemma of V1 |
| `V1_class` | string | Verb class of V1 (`perception` or `causative`) |
| `V1_tense` | string | Tense of V1 (`present`, `past`, or `infinitive`) |
| `v2_object` | string \| null | Direct object of V2 for Type 3; null for Types 1 and 2 |
| `crit_tokens` | list[string] | Surface forms of the critical verb cluster tokens |
| `crit_token_positions` | list[int] | Zero-based BPE token indices of the critical tokens in the grammatical sentence |
| `n_tokens_grammatical` | int | BPE token count of the grammatical sentence |
| `n_tokens_ungrammatical` | int | BPE token count of the ungrammatical sentence |
| `sentence_length_grammatical` | int | Whitespace-separated word count of the grammatical sentence |
| `full_paradigm` | bool | `True` if the base item has at least one Variant B or C |
| `source` | string | Origin of the item (`generated` or literature reference) |
| `notes` | string | Analytical caveats or manual review annotations |
| `bigram_confound` | bool \| null | Whether the V1+V2 pair exceeds a frequency threshold in the training corpus *(pending)* |
| `grammatical_logprob` | float \| null | Length-normalised log probability under GPT-2 Dutch *(pending)* |
| `ungrammatical_logprob` | float \| null | Length-normalised log probability under GPT-2 Dutch *(pending)* |
| `logprob_diff` | float \| null | `grammatical_logprob` − `ungrammatical_logprob` *(pending)* |

Fields marked *(pending)* are present in the schema but currently `null`. They will be populated during behavioural evaluation and mechanistic analysis.

---

## Pipeline commands

| Command | What it does |
|---|---|
| `python generate.py generate` | Generate all six conditions |
| `python generate.py csv` | Export generated files to review CSVs |
| `python process.py filter --excel <path>` | Apply manual review annotations |
| `python process.py validate` | Validate filtered files |
| `python merge.py` | Merge, annotate, and export final dataset |

---

## Linguistic notes

- **V1 inventory:** *zien*, *horen*, *voelen* (perception); *laten* (causative). *helpen* (benefactive) was considered but excluded: it is not part of the formal language theory argument, requires animate NP2 in all cases (preventing Variant B generation via selectional restriction), and cannot appear in 3-NP chains under the current verb-chain transition constraints.
- **V1 tense** is varied across items for Types 1 and 2 (present and past, approximately 65/35). Type 3 always uses the infinitive form (IPP).
- **NP2–V2 compatibility** is enforced by animacy: animate-subject V2 verbs (*lopen*, *zingen*, etc.) require animate NP2; inanimate-subject V2 verbs (*rijden*, *vertrekken*, etc.) require inanimate NP2.
- **3-NP verb-chain transitions** are restricted to perception → causative and causative → perception only. Stacked causatives and stacked perception verbs are blocked.
- **Male proper name adjacency** (e.g. *Jan Piet*) is blocked to avoid misreading as Dutch double-barrelled names.
- **Hand-crafted items** from Bresnan et al. (1982), Shieber (1985), and Yadav et al. (2025) are included in `data/examples/` and loaded into the dataset alongside generated items. These are identified by the `source` field.

---

## Known limitations

- **Type 3 verb cluster position.** The time adverb following the verb cluster in Type 3 means `crit_token_positions` are mid-sentence rather than sentence-final for all 66 Type 3 items. Positional effects may confound cross-construction comparisons in activation patching experiments. Type 3 analyses should be conducted separately.
- **BPE splits in Type 3.** All 66 Type 3 items have more BPE tokens than whitespace-separated words, due to named NP1s (*Yolanthe*, *Pepijn*, etc.) and multi-word time adverbs (*afgelopen weekend*). `crit_token_positions` correctly accounts for these splits.
- **`horen` underrepresented in Type 2 3-NP.** Three out of 40 items use *horen* as V1, due to vocabulary pool size and chain transition constraints.
- **NP pair repetition.** With a small NP pool, some NP1+NP2 combinations appear more than once within a condition.
- **Pending fields.** `bigram_confound`, `grammatical_logprob`, `ungrammatical_logprob`, and `logprob_diff` are currently `null` across all records.

---

## Licence

[heb ik (nog?) niet]

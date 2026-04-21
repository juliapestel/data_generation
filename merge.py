"""
merge.py — Merge generated JSONL files into a single dataset and add
post-processing fields that require external resources (tokeniser, corpus).

Usage:
    python merge.py --input-dir data/ --output data/csd_dataset.jsonl

Post-processing fields added here (in this order, appended after 'notes').
The first four are computed by a separate annotation script (see TODO below)
and joined by pair_id; the last three are computed here via model inference.

    bigram_confound         — bool;       V1_lemma+V2 pair exceeds frequency
                                          threshold in GPT-2 Dutch training corpus
    n_tokens_grammatical    — int;        BPE token count of the grammatical sentence
    n_tokens_ungrammatical  — int;        BPE token count of the ungrammatical sentence
    crit_token_positions    — list[int];  token indices of the verb cluster in the
                                          grammatical sentence
    grammatical_logprob     — float;      length-normalised log probability of the
                                          grammatical sentence under the target model
    ungrammatical_logprob   — float;      length-normalised log probability of the
                                          ungrammatical sentence under the target model
    logprob_diff            — float;      grammatical_logprob − ungrammatical_logprob;
                                          positive values indicate the model prefers
                                          the grammatical sentence
"""

import argparse
import json
from pathlib import Path


# ---------------------------------------------------------------------------
# TODO: before running this script, run the annotation script that computes
#       bigram_confound, n_tokens_grammatical, n_tokens_ungrammatical, and
#       crit_token_positions for each record. That script should produce a
#       JSONL file (one record per line) keyed on pair_id, which is passed
#       here via --annotations.
# ---------------------------------------------------------------------------


def load_annotations(annotation_path: Path) -> dict:
    """Load pre-computed token-level annotations keyed by pair_id.

    Expected format: JSONL where each line is:
        {"pair_id": "...", "bigram_confound": bool,
         "n_tokens_grammatical": int, "n_tokens_ungrammatical": int,
         "crit_token_positions": [int, ...]}
    """
    # TODO: implement
    pass


def compute_logprob_fields(record: dict, model, tokenizer) -> dict:
    """Return grammatical_logprob, ungrammatical_logprob, logprob_diff
    for a single record using the target language model.

    Args:
        record:    one record dict from the merged dataset
        model:     loaded GPT-2 Dutch model
        tokenizer: corresponding tokenizer
    Returns:
        dict with keys grammatical_logprob, ungrammatical_logprob, logprob_diff
    """
    # TODO: implement
    pass


def _insert_v2_object(record: dict) -> dict:
    """Return a copy of record with v2_object: null inserted after V2_class.
    Used to normalise Type 1/2 records to the same flat schema as Type 3.
    """
    out = {}
    for key, val in record.items():
        out[key] = val
        if key == "V2_class" and "v2_object" not in record:
            out["v2_object"] = None
    return out


def merge_files(input_dir: Path) -> list[dict]:
    """Read all per-construction-type JSONL files from input_dir and return
    records in a stable order (sorted by pair_id)."""
    input_files = sorted(input_dir.glob("*.jsonl"))
    input_files = [
        f for f in input_files
        if f.stem not in {"csd_dataset"} and "examples" not in f.parts
    ]
    records = []
    for path in input_files:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    records.sort(key=lambda r: r["pair_id"])
    records = [_insert_v2_object(r) for r in records]
    return records


def add_post_processing_fields(records: list[dict],
                                annotations: dict,
                                model=None,
                                tokenizer=None) -> list[dict]:
    """Attach all post-processing fields to each record in place.

    Fields sourced from annotations lookup (pre-computed externally):
        bigram_confound, n_tokens_grammatical, n_tokens_ungrammatical,
        crit_token_positions  ← not present in per-type JSONL files; added here

    Fields computed here via model inference:
        grammatical_logprob, ungrammatical_logprob, logprob_diff
    """
    for record in records:
        pair_id = record["pair_id"]

        # --- Fields from external annotation script ---
        ann = annotations.get(pair_id, {}) if annotations else {}
        record["bigram_confound"]          = ann.get("bigram_confound", None)
        record["n_tokens_grammatical"]     = ann.get("n_tokens_grammatical", None)
        record["n_tokens_ungrammatical"]   = ann.get("n_tokens_ungrammatical", None)
        record["crit_token_positions"]     = ann.get("crit_token_positions", None)

        # --- Fields from model inference ---
        if model is not None and tokenizer is not None:
            logprob_fields = compute_logprob_fields(record, model, tokenizer)
            record["grammatical_logprob"]   = logprob_fields["grammatical_logprob"]
            record["ungrammatical_logprob"] = logprob_fields["ungrammatical_logprob"]
            record["logprob_diff"]          = logprob_fields["logprob_diff"]
        else:
            record["grammatical_logprob"]   = None
            record["ungrammatical_logprob"] = None
            record["logprob_diff"]          = None

    return records


def main():
    parser = argparse.ArgumentParser(
        description="Merge generated JSONL files and add post-processing fields."
    )
    parser.add_argument("--input-dir",    type=Path, default=Path("data"),
                        help="Directory containing per-type generated JSONL files.")
    parser.add_argument("--output",       type=Path, default=Path("data/csd_dataset.jsonl"),
                        help="Output path for the merged dataset.")
    parser.add_argument("--annotations",  type=Path, default=None,
                        help="Path to pre-computed token annotation JSONL file.")
    # TODO: add --model-dir argument once model inference is implemented
    args = parser.parse_args()

    records = merge_files(args.input_dir)
    print(f"Loaded {len(records)} records from {args.input_dir}")

    annotations = load_annotations(args.annotations) if args.annotations else None

    records = add_post_processing_fields(records, annotations)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote {len(records)} records to {args.output}")


if __name__ == "__main__":
    main()

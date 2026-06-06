"""
merge.py — Merge filtered CSD minimal pair files into a single dataset.

Usage:
    python merge.py
    python merge.py --input-dir data/filtered/ --output data/filtered/csd_dataset.jsonl
    python merge.py --to-csv

Pipeline:
    1. Load all *_filtered.jsonl files from --input-dir.
    2. Normalise schema: insert v2_object after V2_class for Types 1/2.
    3. Compute full_paradigm per base item; insert after notes field.
    4. Insert post-processing fields: sentence_length_grammatical computed
       from word count; n_tokens_grammatical, n_tokens_ungrammatical, and
       crit_token_positions computed by the GPT-2 Dutch tokeniser when available;
       bigram_confound and logprob fields remain null placeholders.
    5. Check for pair_id collisions, sort by pair_id, write.
    6. Optionally write a review CSV (--to-csv).
    7. Self-check: reload and verify record count, no duplicate pair_ids,
       full_paradigm present on every record, no null crit_token_positions.
"""

import argparse
import csv
import json
import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent

VARIANT_ORDER = {"A": 0, "B": 1, "C": 2, "D1": 3, "D2": 4, "D3": 5}

try:
    from transformers import AutoTokenizer
    _HAS_TRANSFORMERS = True
except ImportError:
    _HAS_TRANSFORMERS = False


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------

def compute_token_fields(record: dict, tokenizer) -> dict:
    """Return n_tokens_grammatical, n_tokens_ungrammatical, crit_token_positions.

    Uses the fast GPT-2 Dutch tokeniser with offset mapping to locate each
    surface form from crit_tokens in the grammatical sentence. The last
    whole-word occurrence of each form is used (the critical region is always
    clause-final in Dutch subordinate clauses). Returns ALL token indices whose
    offset spans overlap the full character span of each critical surface form,
    in left-to-right order. Multi-subword forms (e.g. multi-word NPs, rare verbs
    split by BPE) therefore produce multiple indices per surface form.

    Args:
        record:    one record dict; must contain 'grammatical', 'ungrammatical',
                   'crit_tokens', and 'pair_id'.
        tokenizer: loaded AutoTokenizer (use_fast=True).

    Returns:
        dict with keys n_tokens_grammatical (int), n_tokens_ungrammatical (int),
        crit_token_positions (list[int]).

    Raises:
        ValueError if a critical surface form cannot be located or mapped.
    """
    gram        = record["grammatical"]
    ungram      = record["ungrammatical"]
    crit_tokens = record.get("crit_tokens", [])
    pair_id     = record["pair_id"]

    enc_gram   = tokenizer(gram,   return_offsets_mapping=True, add_special_tokens=False)
    enc_ungram = tokenizer(ungram, return_offsets_mapping=True, add_special_tokens=False)

    n_gram   = len(enc_gram["input_ids"])
    n_ungram = len(enc_ungram["input_ids"])

    offsets = enc_gram["offset_mapping"]
    crit_positions: list[int] = []

    for surface in crit_tokens:
        # Last whole-word occurrence (avoids matching 'lopen' inside 'afgelopen', etc.).
        matches = list(re.finditer(rf"\b{re.escape(surface)}\b", gram))
        if matches:
            char_start = matches[-1].start()
            char_end   = matches[-1].end()
        else:
            char_start = gram.rfind(surface)
            char_end   = char_start + len(surface) if char_start != -1 else -1
        if char_start == -1:
            raise ValueError(
                f"[{pair_id}] Critical token '{surface}' not found "
                f"in grammatical sentence: {gram!r}"
            )
        # Collect every token whose offset span overlaps [char_start, char_end).
        span_indices = [
            i for i, (s, e) in enumerate(offsets)
            if s < char_end and e > char_start
        ]
        if not span_indices:
            raise ValueError(
                f"[{pair_id}] Cannot map '{surface}' (chars {char_start}–{char_end}) "
                f"to any token index in: {gram!r}"
            )
        crit_positions.extend(span_indices)

    return {
        "n_tokens_grammatical":   n_gram,
        "n_tokens_ungrammatical": n_ungram,
        "crit_token_positions":   crit_positions,
    }


# ---------------------------------------------------------------------------
# Post-processing stubs — preserved from original merge.py
# ---------------------------------------------------------------------------

def load_annotations(annotation_path) -> dict:
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


def add_post_processing_fields(records: list[dict],
                                annotations: dict,
                                model=None,
                                tokenizer=None) -> list[dict]:
    """Attach all post-processing fields to each record in place.

    Fields always computed here (no external dependency):
        sentence_length_grammatical  ← whitespace-separated word count

    Fields sourced from the GPT-2 Dutch tokeniser when available, otherwise
    from the annotations lookup (pre-computed externally) or null:
        n_tokens_grammatical, n_tokens_ungrammatical, crit_token_positions

    Fields sourced from annotations only (not yet computed here):
        bigram_confound

    Fields computed via model inference (stub — always null for now):
        grammatical_logprob, ungrammatical_logprob, logprob_diff
    """
    for record in records:
        pair_id = record["pair_id"]

        ann = annotations.get(pair_id, {}) if annotations else {}

        record["bigram_confound"] = ann.get("bigram_confound", None)

        # sentence_length_grammatical — no tokeniser required.
        record["sentence_length_grammatical"] = len(record.get("grammatical", "").split())

        # Token counts and crit_token_positions.
        if tokenizer is not None:
            tok = compute_token_fields(record, tokenizer)
            record["n_tokens_grammatical"]   = tok["n_tokens_grammatical"]
            record["n_tokens_ungrammatical"] = tok["n_tokens_ungrammatical"]
            record["crit_token_positions"]   = tok["crit_token_positions"]
        else:
            record["n_tokens_grammatical"]   = ann.get("n_tokens_grammatical",   None)
            record["n_tokens_ungrammatical"] = ann.get("n_tokens_ungrammatical", None)
            record["crit_token_positions"]   = ann.get("crit_token_positions",   None)

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


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _insert_v2_object(record: dict) -> dict:
    """Return a copy of record with v2_object: null inserted after V2_class.

    Used to normalise Type 1/2 records to the same flat schema as Type 3.
    Type 3 records already have v2_object populated and are returned unchanged.
    """
    if "v2_object" in record:
        return record
    out = {}
    for key, val in record.items():
        out[key] = val
        if key == "V2_class":
            out["v2_object"] = None
    return out


def _insert_full_paradigm(record: dict, value: bool) -> dict:
    """Return a copy of record with full_paradigm inserted immediately after notes.

    If notes is not present, full_paradigm is appended at the end.
    """
    out = {}
    inserted = False
    for key, val in record.items():
        out[key] = val
        if key == "notes" and not inserted:
            out["full_paradigm"] = value
            inserted = True
    if not inserted:
        out["full_paradigm"] = value
    return out


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def _csv_value(val):
    """Serialise a single field value for CSV output."""
    if val is None:
        return ""
    if isinstance(val, bool):
        return str(val)          # "True" / "False" — must precede int check
    if isinstance(val, list):
        return json.dumps(val, ensure_ascii=False)
    return val


def _write_csv(records: list[dict], path: Path) -> int:
    """Write records to CSV with utf-8-sig encoding for Excel compatibility.

    Column order: fields from the first record first (in their original order),
    followed by any additional fields first encountered in later records. This
    handles the mixed schema where 3/4-NP records carry NP3/V3/etc. fields
    absent from 2-NP records. Missing fields are written as empty string.
    List fields are serialised as JSON strings; booleans as True/False;
    null values as empty string.

    Returns the number of data rows written.
    """
    if not records:
        return 0
    # Collect ordered union of all fieldnames across all records.
    seen: set[str] = set()
    fieldnames: list[str] = []
    for rec in records:
        for key in rec:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            writer.writerow({k: _csv_value(rec.get(k)) for k in fieldnames})
    return len(records)


# ---------------------------------------------------------------------------
# Sort and pair_id helpers
# ---------------------------------------------------------------------------

def _sort_key(pair_id: str):
    base   = pair_id.rsplit("_", 1)[0]
    var    = pair_id.rsplit("_", 1)[1]
    parts  = base.split("_")
    num    = int(parts[-1])
    prefix = "_".join(parts[:-1])
    return (prefix, num, VARIANT_ORDER.get(var, 99))


def _base_item(pair_id: str) -> str:
    return pair_id.rsplit("_", 1)[0]


def _variant(pair_id: str) -> str:
    return pair_id.rsplit("_", 1)[1]


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _write_jsonl(records: list[dict], path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Merge filtered CSD minimal pair files into a single dataset."
    )
    parser.add_argument(
        "--input-dir", type=Path, default=Path("data/filtered"),
        help="Directory containing *_filtered.jsonl files (default: data/filtered/).",
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/filtered/csd_dataset.jsonl"),
        help="Output path for the merged dataset (default: data/filtered/csd_dataset.jsonl).",
    )
    parser.add_argument(
        "--to-csv", action="store_true",
        help="Also write a CSV version of the dataset alongside the JSONL output.",
    )
    args = parser.parse_args()

    input_dir   = args.input_dir if args.input_dir.is_absolute() else ROOT / args.input_dir
    output_path = args.output    if args.output.is_absolute()    else ROOT / args.output

    # ------------------------------------------------------------------
    # Step 1 — Load filtered files
    # ------------------------------------------------------------------
    filtered_files = sorted(input_dir.glob("*_filtered.jsonl"))
    if not filtered_files:
        sys.exit(
            f"Error: No *_filtered.jsonl files found in {input_dir}.\n"
            "Run 'python process.py filter --excel <path>' first."
        )

    all_records: list[dict] = []
    for path in filtered_files:
        file_records = _load_jsonl(path)
        print(f"  {path.name}: {len(file_records)} records")
        all_records.extend(file_records)

    print(f"Total loaded: {len(all_records)} records from {len(filtered_files)} files\n")

    # ------------------------------------------------------------------
    # Step 2 — Schema normalisation
    # ------------------------------------------------------------------
    all_records = [_insert_v2_object(r) for r in all_records]

    # ------------------------------------------------------------------
    # Step 3 — Compute full_paradigm
    # Group by base item; True if ≥1 B or C variant exists in the merged set.
    # Computed after merging all files so the result reflects the final dataset.
    # ------------------------------------------------------------------
    base_has_bc: dict[str, bool] = {}
    for rec in all_records:
        base = _base_item(rec["pair_id"])
        var  = _variant(rec["pair_id"])
        if var in ("B", "C"):
            base_has_bc[base] = True
        elif base not in base_has_bc:
            base_has_bc[base] = False

    all_records = [
        _insert_full_paradigm(rec, base_has_bc.get(_base_item(rec["pair_id"]), False))
        for rec in all_records
    ]

    # ------------------------------------------------------------------
    # Step 4 — Load tokeniser, then insert post-processing fields
    # ------------------------------------------------------------------
    if not _HAS_TRANSFORMERS:
        sys.exit("Error: transformers not installed; token fields cannot be computed. "
                 "Install it or run with an explicit --no-tokeniser flag.")
    try:
        print("Loading tokeniser yhavinga/gpt2-large-dutch ...")
        tok = AutoTokenizer.from_pretrained("yhavinga/gpt2-large-dutch", use_fast=True)
        print("Tokeniser loaded.\n")
    except Exception as exc:
        sys.exit(f"Error: could not load tokeniser ({exc}). Aborting to avoid null token fields.")

    all_records = add_post_processing_fields(all_records, annotations=None, tokenizer=tok)

    # ------------------------------------------------------------------
    # Step 5 — Check pair_id collisions, sort, write
    # ------------------------------------------------------------------
    id_counts: dict[str, int] = {}
    for rec in all_records:
        pid = rec["pair_id"]
        id_counts[pid] = id_counts.get(pid, 0) + 1
    collisions = sorted(pid for pid, cnt in id_counts.items() if cnt > 1)
    if collisions:
        lines  = "\n".join(f"  {pid}" for pid in collisions[:20])
        suffix = f"\n  ... ({len(collisions) - 20} more)" if len(collisions) > 20 else ""
        sys.exit(f"Error: pair_id collisions across files ({len(collisions)}):\n{lines}{suffix}")

    all_records.sort(key=lambda r: _sort_key(r["pair_id"]))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(all_records, output_path)
    print(f"Wrote {len(all_records)} records → {output_path}\n")

    # ------------------------------------------------------------------
    # Step 6 — Optional CSV export
    # ------------------------------------------------------------------
    if args.to_csv:
        csv_path = output_path.with_suffix(".csv")
        n_rows = _write_csv(all_records, csv_path)
        print(f"Wrote {n_rows} rows → {csv_path}\n")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    c_type_counts:   dict = {}
    n_pairs_counts:  dict = {}
    v1_class_counts: dict = {}
    v_type_counts:   dict = {}
    full_paradigm_by_cond: dict[str, dict] = {}

    seen_bases: set[str] = set()
    for rec in all_records:
        ct   = rec.get("c_type",   "?")
        np   = rec.get("n_pairs",  "?")
        vc   = rec.get("V1_class", "?")
        vt   = _variant(rec["pair_id"])
        base = _base_item(rec["pair_id"])
        fp   = rec.get("full_paradigm", False)

        c_type_counts[ct]   = c_type_counts.get(ct, 0) + 1
        n_pairs_counts[np]  = n_pairs_counts.get(np, 0) + 1
        v1_class_counts[vc] = v1_class_counts.get(vc, 0) + 1
        v_type_counts[vt]   = v_type_counts.get(vt, 0) + 1

        if base not in seen_bases:
            seen_bases.add(base)
            cond = f"c_type={ct}, n_pairs={np}"
            if cond not in full_paradigm_by_cond:
                full_paradigm_by_cond[cond] = {True: 0, False: 0}
            full_paradigm_by_cond[cond][fp] += 1

    print(f"  c_type:   {dict(sorted(c_type_counts.items()))}")
    print(f"  n_pairs:  {dict(sorted(n_pairs_counts.items()))}")
    print(f"  V1_class: {dict(sorted(v1_class_counts.items()))}")
    print(f"  v_type:   {dict(sorted(v_type_counts.items()))}")
    print("  full_paradigm by condition (base items):")
    for cond, counts in sorted(full_paradigm_by_cond.items()):
        print(f"    {cond}: True={counts[True]}, False={counts[False]}")

    v2_missing = sum(1 for r in all_records if "v2_object" not in r)
    if v2_missing == 0:
        print("  v2_object present on all records: yes")
    else:
        print(f"  v2_object present on all records: NO — missing on {v2_missing} records")

    # ------------------------------------------------------------------
    # Self-check
    # ------------------------------------------------------------------
    print("\n--- Self-check ---")
    reloaded = _load_jsonl(output_path)
    checks_passed = True

    # Record count match.
    if len(reloaded) != len(all_records):
        print(f"FAIL: wrote {len(all_records)} but reloaded {len(reloaded)}")
        checks_passed = False
    else:
        print(f"PASS: record count {len(reloaded)}")

    # No duplicate pair_ids.
    reload_ids = [r["pair_id"] for r in reloaded]
    if len(reload_ids) != len(set(reload_ids)):
        dup_count = len(reload_ids) - len(set(reload_ids))
        print(f"FAIL: {dup_count} duplicate pair_id(s) in output")
        checks_passed = False
    else:
        print("PASS: no duplicate pair_ids")

    # full_paradigm on every record.
    fp_missing = sum(1 for r in reloaded if "full_paradigm" not in r)
    if fp_missing > 0:
        print(f"FAIL: full_paradigm missing from {fp_missing} records")
        checks_passed = False
    else:
        print("PASS: full_paradigm present on all records")

    # No null crit_token_positions (only checked when tokeniser was loaded).
    if tok is not None:
        # No null/empty crit_token_positions — must hold unconditionally.
        null_crit = [r["pair_id"] for r in reloaded
                    if r.get("crit_token_positions") in (None, [])]
        if null_crit:
            print(f"FAIL: crit_token_positions null/empty on {len(null_crit)} records: {null_crit[:10]}")
            checks_passed = False
        else:
            print("PASS: crit_token_positions populated on all records")

        # Spot-check: print 5 records for visual verification.
        print("\nSpot-check (5 records):")
        sample = [r for r in reloaded if _variant(r["pair_id"]) == "A"][:5]
        for r in sample:
            print(
                f"  {r['pair_id']!s:25s}  "
                f"n_tok={r['n_tokens_grammatical']:3d}  "
                f"crit_tokens={r['crit_tokens']}  "
                f"positions={r['crit_token_positions']}"
            )
            print(f"    gram: {r['grammatical']}")

    # CSV row count verification.
    if args.to_csv:
        csv_path = output_path.with_suffix(".csv")
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            csv_row_count = sum(1 for _ in csv.reader(f)) - 1  # subtract header
        if csv_row_count == len(all_records):
            print(f"\nPASS: CSV row count {csv_row_count} matches JSONL record count")
        else:
            print(f"\nFAIL: CSV row count {csv_row_count} ≠ JSONL record count {len(all_records)}")
            checks_passed = False

    if not checks_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()

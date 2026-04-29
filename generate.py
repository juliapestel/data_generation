"""
generate.py — Entry point for CSD minimal pairs dataset generation.

Uses target-based generation: keeps calling generate_item() until the required
number of Variant A records per V1_class has been reached for each condition.

Only Variant A records count as base stimuli. All other variants (B, C, D1, D2,
D3) are derived and emitted alongside their Variant A record as a unit.

Benefactive V1 items (V1_class == "benefactive") are silently discarded and
never written to output.

Subcommands
-----------
  python generate.py generate   — run the full generation pipeline
  python generate.py csv        — convert generated JSONL files to review CSVs
"""

import argparse
import csv
import json
from pathlib import Path

from generators import Type1Generator, Type2Generator, Type3Generator, Type1Generator4NP

ROOT     = Path(__file__).parent
DATA_DIR = ROOT / "data"

VARIANT_ORDER = {"A": 0, "B": 1, "C": 2, "D1": 3, "D2": 4, "D3": 5}

CSV_COLUMNS = [
    "pair_id", "c_type", "n_pairs", "v_type", "V1_class", "V1_lemma",
    "NP1", "NP2", "NP2_anim", "V2", "ungram_source", "alignment",
    "grammatical", "ungrammatical", "crit_tokens",
    "exclude", "exclude_reason",
]


# ---------------------------------------------------------------------------
# Generation helpers
# ---------------------------------------------------------------------------

def generate_condition(gen, n_pairs: int, targets: dict, label: str,
                        lemma_caps: dict | None = None):
    """Generate records for one condition using target-based sampling.

    Calls gen.load_examples() to obtain hand-crafted items and the starting
    item_num, then calls gen.generate_item() in a loop until all per-class
    quotas are met.

    Args:
        gen:        Instantiated generator object.
        n_pairs:    Chain length to generate.
        targets:    {v1_class: target_count} of Variant A records required.
                    Only classes listed here are emitted; others are discarded.
        label:      Human-readable condition label for error messages.
        lemma_caps: Optional {v1_lemma: max_count} hard cap on Variant A records
                    per lemma, applied independently of the class quota. Items
                    whose lemma has reached its cap are silently discarded even
                    if the class quota is not yet met.

    Returns:
        (records, discarded_benefactive_count)
    """
    example_records, item_num, _ = gen.load_examples(n_pairs)

    # Subtract Variant A example records from per-class quotas.
    remaining = dict(targets)
    # Track accepted lemma counts; initialise from example records so that
    # hand-crafted items count against lemma caps.
    lemma_counts: dict[str, int] = {}
    for rec in example_records:
        if rec.get("v_type") == "A":
            cls = rec.get("V1_class")
            if cls in remaining:
                remaining[cls] = max(0, remaining[cls] - 1)
            if lemma_caps:
                lemma = rec.get("V1_lemma", "")
                if lemma in lemma_caps:
                    lemma_counts[lemma] = lemma_counts.get(lemma, 0) + 1

    output_records = list(example_records)
    discarded_benefactive = 0
    max_attempts = sum(targets.values()) * 500
    attempts = 0

    while any(v > 0 for v in remaining.values()):
        if attempts >= max_attempts:
            short = {k: v for k, v in remaining.items() if v > 0}
            produced = {k: targets[k] - remaining.get(k, 0) for k in targets}
            raise RuntimeError(
                f"[{label}] Max attempts ({max_attempts}) exceeded. "
                f"Required: {targets}. Produced: {produced}. Still short: {short}."
            )

        item_num += 1
        attempts += 1
        bundle = list(gen.generate_item(n_pairs, item_num))
        if not bundle:
            continue

        # All records in a bundle share the same grammatical item; read V1_class
        # and V1_lemma from the Variant A record, which is always present when
        # the bundle is non-empty (generate_item yields A before B/C/D variants).
        a_rec = next((r for r in bundle if r.get("v_type") == "A"), None)
        if a_rec is None:
            continue

        cls   = a_rec.get("V1_class")
        lemma = a_rec.get("V1_lemma", "")

        if cls == "benefactive":
            discarded_benefactive += 1
            continue

        # Discard if this lemma has reached its per-lemma cap.
        if lemma_caps and lemma in lemma_caps:
            if lemma_counts.get(lemma, 0) >= lemma_caps[lemma]:
                continue

        # Emit this item's bundle only if its class still has remaining quota.
        if remaining.get(cls, 0) <= 0:
            continue

        output_records.extend(bundle)
        remaining[cls] -= 1
        if lemma_caps and lemma in lemma_caps:
            lemma_counts[lemma] = lemma_counts.get(lemma, 0) + 1

    return output_records, discarded_benefactive


def renumber_records(records: list[dict]) -> list[dict]:
    """Reassign pair_id item numbers sequentially (001..N) with no gaps.

    Groups records by base item (pair_id without the trailing variant suffix),
    preserves the original sort order to determine item number assignment, then
    rebuilds pair_id for every record using the new sequential number.
    """
    seen: dict[str, int] = {}
    counter = 0
    for rec in records:
        base = rec["pair_id"].rsplit("_", 1)[0]
        if base not in seen:
            counter += 1
            seen[base] = counter

    out = []
    for rec in records:
        base, variant = rec["pair_id"].rsplit("_", 1)
        prefix = "_".join(base.split("_")[:-1])
        new_base = f"{prefix}_{seen[base]:03d}"
        new_rec = dict(rec)
        new_rec["pair_id"] = f"{new_base}_{variant}"
        out.append(new_rec)
    return out


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def _csv_sort_key(record: dict):
    """Sort key: base item prefix, then item number, then variant order."""
    pair_id = record["pair_id"]
    base, variant = pair_id.rsplit("_", 1)
    parts  = base.split("_")
    num    = int(parts[-1])
    prefix = "_".join(parts[:-1])
    return (prefix, num, VARIANT_ORDER.get(variant, 99))


def _record_to_csv_row(record: dict) -> dict:
    """Extract CSV columns from a JSONL record, serialising list fields."""
    row = {}
    for col in CSV_COLUMNS:
        val = record.get(col, "")
        if isinstance(val, list):
            val = json.dumps(val, ensure_ascii=False)
        elif isinstance(val, bool):
            val = str(val).lower()
        elif val is None:
            val = ""
        row[col] = val
    return row


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

def cmd_generate(_args):
    ALL_CONDITIONS = [
        # (generator, n_pairs, output_path, targets, label, lemma_caps)
        (Type1Generator(),    2, DATA_DIR / "type1_2np.jsonl", {"perception": 35, "causative": 35}, "Type1/2np", {"voelen": 8}),
        (Type1Generator(),    3, DATA_DIR / "type1_3np.jsonl", {"perception": 25, "causative": 20}, "Type1/3np", None),
        (Type1Generator4NP(), 4, DATA_DIR / "type1_4np.jsonl", {"perception": 20},                  "Type1/4np", None),
        (Type2Generator(),    2, DATA_DIR / "type2_2np.jsonl", {"perception": 35, "causative": 35}, "Type2/2np", {"voelen": 8}),
        (Type2Generator(),    3, DATA_DIR / "type2_3np.jsonl", {"perception": 25, "causative": 20}, "Type2/3np", None),
        (Type3Generator(),    2, DATA_DIR / "type3_2np.jsonl", {"perception": 35, "causative": 35}, "Type3/2np", None),
    ]

    for gen, n_pairs, output_path, targets, label, lemma_caps in ALL_CONDITIONS:
        records, discarded = generate_condition(
            gen, n_pairs, targets, label, lemma_caps=lemma_caps
        )
        records = sorted(records, key=lambda r: r["pair_id"])
        records = renumber_records(records)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        # Count Variant A records by V1_class and V1_lemma for the summary.
        a_by_class: dict[str, int] = {}
        a_by_lemma: dict[str, int] = {}
        for rec in records:
            if rec.get("v_type") == "A":
                cls   = rec.get("V1_class", "unknown")
                lemma = rec.get("V1_lemma", "unknown")
                a_by_class[cls]   = a_by_class.get(cls, 0) + 1
                a_by_lemma[lemma] = a_by_lemma.get(lemma, 0) + 1

        class_breakdown = ", ".join(f"{k}={v}" for k, v in sorted(a_by_class.items()))
        lemma_breakdown = ", ".join(f"{k}={v}" for k, v in sorted(a_by_lemma.items()))
        print(
            f"{output_path.name} — {len(records)} records | "
            f"Variant A by class: {class_breakdown} (benefactive discarded: {discarded})\n"
            f"  Variant A by lemma: {lemma_breakdown}"
        )


def cmd_csv(_args):
    skip_stems = {"dataset", "csd_dataset"}
    jsonl_files = sorted(
        f for f in DATA_DIR.glob("*.jsonl")
        if f.stem not in skip_stems
    )
    if not jsonl_files:
        print("No JSONL files found in data/ — run 'python generate.py generate' first.")
        return

    review_dir = DATA_DIR / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    for jsonl_path in jsonl_files:
        records: list[dict] = []
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

        records.sort(key=_csv_sort_key)

        csv_path = review_dir / (jsonl_path.stem + ".csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for rec in records:
                writer.writerow(_record_to_csv_row(rec))

        print(f"Wrote {len(records)} rows → {csv_path.relative_to(ROOT)}")

    print(f"\nReview CSVs saved to {review_dir.relative_to(ROOT)}/")
    print("Fill in 'exclude' and 'exclude_reason' columns, then run:")
    print("  python process.py filter")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CSD minimal pairs dataset generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "generate",
        help="Run the full generation pipeline and write JSONL files to data/.",
    )
    sub.add_parser(
        "csv",
        help="Convert generated JSONL files to review CSVs in data/review/.",
    )
    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "csv":
        cmd_csv(args)


if __name__ == "__main__":
    main()

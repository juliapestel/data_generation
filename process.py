"""
process.py — Filter, validate, and merge CSD minimal pairs dataset files.

Subcommands
-----------
  python process.py filter    — apply review CSV exclusions, renumber, write to data/filtered/
  python process.py validate  — validate filtered JSONL files against minimum targets
  python process.py merge     — merge all filtered files into data/filtered/dataset.jsonl
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT         = Path(__file__).parent
DATA_DIR     = ROOT / "data"
REVIEW_DIR   = DATA_DIR / "review"
FILTERED_DIR = DATA_DIR / "filtered"

VARIANT_ORDER = {"A": 0, "B": 1, "C": 2, "D1": 3, "D2": 4, "D3": 5}

MINIMUM_TARGETS = {
    "type1_2np": {"perception": 25, "causative": 25},
    "type2_2np": {"perception": 25, "causative": 25},
    "type3_2np": {"perception": 25, "causative": 25},
    "type1_3np": {"perception": 15, "causative": 10},
    "type2_3np": {"perception": 15, "causative": 10},
    "type1_4np": {"perception": 15},
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _base_item(pair_id: str) -> str:
    return pair_id.rsplit("_", 1)[0]


def _variant(pair_id: str) -> str:
    return pair_id.rsplit("_", 1)[1]


def _sort_key(pair_id: str):
    """Sort key: base item prefix, then item number, then variant order."""
    base = _base_item(pair_id)
    var  = _variant(pair_id)
    parts  = base.split("_")
    num    = int(parts[-1])
    prefix = "_".join(parts[:-1])
    return (prefix, num, VARIANT_ORDER.get(var, 99))


def _renumber(records: list[dict]) -> list[dict]:
    """Reassign pair_id item numbers sequentially (001..N) with no gaps.

    Preserves current record order to determine assignment; callers should
    sort before calling so that numbers reflect the intended final order.
    """
    seen: dict[str, int] = {}
    counter = 0
    for rec in records:
        base = _base_item(rec["pair_id"])
        if base not in seen:
            counter += 1
            seen[base] = counter

    out = []
    for rec in records:
        base, var = rec["pair_id"].rsplit("_", 1)
        prefix   = "_".join(base.split("_")[:-1])
        new_base = f"{prefix}_{seen[base]:03d}"
        new_rec  = dict(rec)
        new_rec["pair_id"] = f"{new_base}_{var}"
        out.append(new_rec)
    return out


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
# filter
# ---------------------------------------------------------------------------

def cmd_filter(_args):
    if not REVIEW_DIR.exists() or not any(REVIEW_DIR.glob("*.csv")):
        sys.exit(
            "Error: data/review/ does not exist or contains no CSV files.\n"
            "Run:  python generate.py csv\n"
            "Then complete the manual review before running filter."
        )

    FILTERED_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(REVIEW_DIR.glob("*.csv"))
    for csv_path in csv_files:
        jsonl_path = DATA_DIR / (csv_path.stem + ".jsonl")
        if not jsonl_path.exists():
            print(f"Warning: {jsonl_path.name} not found in data/ — skipping {csv_path.name}")
            continue

        records   = _load_jsonl(jsonl_path)
        by_id     = {r["pair_id"]: r for r in records}
        # Index all pair_ids belonging to each base item (for efficient A-exclusion).
        base_to_ids: dict[str, list[str]] = {}
        for r in records:
            base = _base_item(r["pair_id"])
            base_to_ids.setdefault(base, []).append(r["pair_id"])

        exclude_ids: set[str] = set()

        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("exclude", "").strip():
                    continue
                pid   = row.get("pair_id", "").strip()
                vtype = row.get("v_type", "").strip()
                if not pid:
                    continue
                base = _base_item(pid)

                if vtype == "A":
                    # Exclude every variant of this base item.
                    for sibling in base_to_ids.get(base, [pid]):
                        exclude_ids.add(sibling)
                elif vtype == "B":
                    # Exclude B and its paired C (C is meaningless without B).
                    b_id = f"{base}_B"
                    c_id = f"{base}_C"
                    if b_id in by_id:
                        exclude_ids.add(b_id)
                    if c_id in by_id:
                        exclude_ids.add(c_id)
                        print(f"  Note [{csv_path.stem}]: {b_id} excluded — {c_id} also removed.")
                else:
                    exclude_ids.add(pid)

        # Count fully-removed base items (those whose A record was excluded).
        removed_bases = {
            _base_item(pid) for pid in exclude_ids
            if f"{_base_item(pid)}_A" in exclude_ids
        }

        remaining = [r for r in records if r["pair_id"] not in exclude_ids]
        remaining.sort(key=lambda r: _sort_key(r["pair_id"]))
        remaining = _renumber(remaining)
        remaining.sort(key=lambda r: _sort_key(r["pair_id"]))

        remaining_bases: set[str] = {_base_item(r["pair_id"]) for r in remaining}
        a_by_class: dict[str, int] = {}
        for r in remaining:
            if _variant(r["pair_id"]) == "A":
                cls = r.get("V1_class", "unknown")
                a_by_class[cls] = a_by_class.get(cls, 0) + 1

        out_path = FILTERED_DIR / jsonl_path.name
        _write_jsonl(remaining, out_path)

        class_str = ", ".join(f"{k}={v}" for k, v in sorted(a_by_class.items()))
        print(
            f"{csv_path.stem}: removed {len(removed_bases)} base items, "
            f"{len(remaining_bases)} remain | "
            f"Variant A by class: {class_str} → {out_path.relative_to(ROOT)}"
        )


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

def cmd_validate(_args):
    if not FILTERED_DIR.exists():
        sys.exit("Error: data/filtered/ does not exist. Run 'python process.py filter' first.")

    jsonl_files = sorted(
        f for f in FILTERED_DIR.glob("*.jsonl") if f.stem != "dataset"
    )
    if not jsonl_files:
        sys.exit(
            "Error: No JSONL files found in data/filtered/ (excluding dataset.jsonl). "
            "Run 'python process.py filter' first."
        )

    all_pass = True
    for path in jsonl_files:
        records  = _load_jsonl(path)
        failures: list[str] = []

        a_records = [r for r in records if _variant(r["pair_id"]) == "A"]

        # 1. Variant A counts by class and lemma.
        a_by_class: dict[str, int] = {}
        a_by_lemma: dict[str, int] = {}
        for r in a_records:
            cls   = r.get("V1_class", "unknown")
            lemma = r.get("V1_lemma", "unknown")
            a_by_class[cls]   = a_by_class.get(cls, 0) + 1
            a_by_lemma[lemma] = a_by_lemma.get(lemma, 0) + 1

        # 2. Sequential item numbers with no gaps.
        seen_bases: list[str] = []
        seen_set: set[str] = set()
        for r in sorted(records, key=lambda r: _sort_key(r["pair_id"])):
            b = _base_item(r["pair_id"])
            if b not in seen_set:
                seen_set.add(b)
                seen_bases.append(b)
        nums     = [int(b.split("_")[-1]) for b in seen_bases]
        expected = list(range(1, len(nums) + 1))
        if nums != expected:
            failures.append(
                f"Item numbers not sequential (no gaps expected): "
                f"found {nums[:10]}{'...' if len(nums) > 10 else ''}"
            )

        # 3. Duplicate grammatical sentences among Variant A.
        gram_seen: set[str] = set()
        dup_grams: list[str] = []
        for r in a_records:
            s = r.get("grammatical", "")
            if s in gram_seen:
                dup_grams.append(s)
            gram_seen.add(s)
        if dup_grams:
            failures.append(
                f"Duplicate grammatical sentences ({len(dup_grams)}): "
                + "; ".join(f'"{s}"' for s in dup_grams[:3])
            )

        # 4. Duplicate pair_ids.
        id_counts: dict[str, int] = {}
        for r in records:
            pid = r["pair_id"]
            id_counts[pid] = id_counts.get(pid, 0) + 1
        dup_ids = [pid for pid, cnt in id_counts.items() if cnt > 1]
        if dup_ids:
            failures.append(
                f"Duplicate pair_ids ({len(dup_ids)}): {dup_ids[:5]}"
            )

        # 5. Minimum Variant A targets.
        stem = path.stem
        if stem in MINIMUM_TARGETS:
            for cls, min_count in MINIMUM_TARGETS[stem].items():
                actual = a_by_class.get(cls, 0)
                if actual < min_count:
                    failures.append(
                        f"Below minimum for '{cls}': {actual} < {min_count}"
                    )

        verdict   = "PASS" if not failures else "FAIL"
        class_str = ", ".join(f"{k}={v}" for k, v in sorted(a_by_class.items()))
        lemma_str = ", ".join(f"{k}={v}" for k, v in sorted(a_by_lemma.items()))
        print(
            f"[{verdict}] {path.name} — {len(records)} records | "
            f"Variant A: {class_str} | lemmas: {lemma_str}"
        )
        for msg in failures:
            print(f"         FAIL: {msg}")

        if failures:
            all_pass = False

    print()
    print("All files PASS." if all_pass else "One or more files FAIL — review the issues above.")


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

def cmd_merge(_args):
    if not FILTERED_DIR.exists():
        sys.exit("Error: data/filtered/ does not exist. Run 'python process.py filter' first.")

    jsonl_files = sorted(
        f for f in FILTERED_DIR.glob("*.jsonl") if f.stem != "dataset"
    )
    if not jsonl_files:
        sys.exit(
            "Error: No JSONL files found in data/filtered/ (excluding dataset.jsonl). "
            "Run 'python process.py filter' first."
        )

    all_records: list[dict] = []
    for path in jsonl_files:
        all_records.extend(_load_jsonl(path))

    # Check for pair_id collisions across files.
    id_counts: dict[str, int] = {}
    for r in all_records:
        pid = r["pair_id"]
        id_counts[pid] = id_counts.get(pid, 0) + 1
    collisions = sorted(pid for pid, cnt in id_counts.items() if cnt > 1)
    if collisions:
        lines = "\n".join(f"  {pid}" for pid in collisions[:20])
        suffix = f"\n  ... ({len(collisions) - 20} more)" if len(collisions) > 20 else ""
        sys.exit(f"Error: pair_id collisions across files ({len(collisions)}):\n{lines}{suffix}")

    all_records.sort(key=lambda r: _sort_key(r["pair_id"]))

    out_path = FILTERED_DIR / "dataset.jsonl"
    _write_jsonl(all_records, out_path)

    # Breakdown by c_type, n_pairs, V1_class, v_type.
    c_type_counts:   dict = {}
    n_pairs_counts:  dict = {}
    v1_class_counts: dict = {}
    v_type_counts:   dict = {}
    for r in all_records:
        ct  = r.get("c_type",   "?")
        np  = r.get("n_pairs",  "?")
        vc  = r.get("V1_class", "?")
        vt  = _variant(r["pair_id"])
        c_type_counts[ct]    = c_type_counts.get(ct, 0) + 1
        n_pairs_counts[np]   = n_pairs_counts.get(np, 0) + 1
        v1_class_counts[vc]  = v1_class_counts.get(vc, 0) + 1
        v_type_counts[vt]    = v_type_counts.get(vt, 0) + 1

    print(f"Wrote {len(all_records)} records → {out_path.relative_to(ROOT)}")
    print(f"  c_type:   {dict(sorted(c_type_counts.items()))}")
    print(f"  n_pairs:  {dict(sorted(n_pairs_counts.items()))}")
    print(f"  V1_class: {dict(sorted(v1_class_counts.items()))}")
    print(f"  v_type:   {dict(sorted(v_type_counts.items()))}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Post-processing pipeline for CSD minimal pairs dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "filter",
        help="Apply review CSV exclusions, renumber, write to data/filtered/.",
    )
    sub.add_parser(
        "validate",
        help="Validate filtered JSONL files against minimum targets.",
    )
    sub.add_parser(
        "merge",
        help="Merge all filtered files into data/filtered/dataset.jsonl.",
    )
    args = parser.parse_args()

    if args.command == "filter":
        cmd_filter(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "merge":
        cmd_merge(args)


if __name__ == "__main__":
    main()

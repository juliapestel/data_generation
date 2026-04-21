"""
generate.py — Entry point for CSD minimal pairs dataset generation.

To generate a new chain length, add a row to `tasks` with the appropriate
generator, n_pairs, and output path. N_GENERATE controls how many grammatical
sentences are generated per task (excluding example items loaded from file).
"""

import json
from pathlib import Path

from generators import Type1Generator, Type2Generator, Type3Generator


N_GENERATE = 5


if __name__ == "__main__":
    tasks = [
        # (Type1Generator(), 2, "data/type1_2np.jsonl"),
        # (Type2Generator(), 2, "data/type2_2np.jsonl"),
        # (Type3Generator(), 2, "data/type3_2np.jsonl"),
        (Type1Generator(), 3, "data/type1_3np.jsonl"),
        (Type2Generator(), 3, "data/type2_3np.jsonl"),
    ]
    for gen, n_pairs, output_path in tasks:
        records = list(gen.generate(n_pairs, N_GENERATE))
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"Wrote {len(records)} records to {output_path} (N_GENERATE={N_GENERATE})")

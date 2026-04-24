"""
generate.py — Entry point for CSD minimal pairs dataset generation.

To generate a new chain length, add a row to `tasks` with the appropriate
generator, n_pairs, and output path. N_GENERATE controls how many grammatical
sentences are generated per task (excluding example items loaded from file).
"""

import json
from pathlib import Path

from generators import Type1Generator, Type2Generator, Type3Generator, Type1Generator4NP


N_GENERATE = 5
N_GENERATE_4NP = 15


if __name__ == "__main__":
    tasks = [
        # (Type1Generator(), 2, "data/type1_2np.jsonl"),
        # (Type2Generator(), 2, "data/type2_2np.jsonl"),
        # (Type3Generator(), 2, "data/type3_2np.jsonl"),
        (Type1Generator(), 3, "data/type1_3np.jsonl"),
        (Type2Generator(), 3, "data/type2_3np.jsonl"),
        (Type1Generator4NP(), 4, "data/type1_4np.jsonl", N_GENERATE_4NP),
    ]
    for task in tasks:
        gen, n_pairs, output_path = task[0], task[1], task[2]
        n_gen = task[3] if len(task) > 3 else N_GENERATE
        records = sorted(gen.generate(n_pairs, n_gen), key=lambda r: r["pair_id"])
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"Wrote {len(records)} records to {output_path} (N_GENERATE={n_gen})")

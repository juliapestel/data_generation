"""
generator_base.py — Abstract base class for CSD minimal pair generators.
"""

import json
import random
from abc import ABC, abstractmethod
from pathlib import Path

from vocab import NP1_POOL


EXAMPLES_DIR = Path(__file__).parent / "data" / "examples"


class CSDGenerator(ABC):
    """Abstract base class for all CSD construction-type generators.

    Subclasses implement generate_item() for a single grammatical item and its
    ungrammatical variants. This class owns: example loading, shared static
    helpers (pick_v1_form, can_generate_np_swap, build_record), and the outer
    generation loop. Subclasses own selection logic and sentence construction.

    Required class attributes on each concrete subclass:
        c_type (int): construction type identifier (1, 2, or 3)
    """

    def load_examples(self, n_pairs: int) -> tuple[list[dict], int, dict]:
        """Load reference examples for this type and chain length.

        Returns (records, next_item_num, v1_counts). Gracefully returns empty
        state if no example file exists for the requested n_pairs.
        File name convention: type{c_type}_{n_pairs}np_examples.jsonl
        """
        path = EXAMPLES_DIR / f"type{self.c_type}_{n_pairs}np_examples.jsonl"
        records = []
        if path.exists():
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        max_item = max(int(r["pair_id"].split("_")[2]) for r in records) if records else 0
        seen, v1_counts = set(), {}
        for r in records:
            item_key = r["pair_id"].rsplit("_", 1)[0]
            if item_key not in seen:
                seen.add(item_key)
                lemma = r["V1_lemma"]
                v1_counts[lemma] = v1_counts.get(lemma, 0) + 1
        return records, max_item + 1, v1_counts

    @staticmethod
    def pick_v1_form(v1_entry, tense, np1_number):
        """Return (lemma, surface_form, verb_class) for V1.
        v1_entry:   (infinitive, present_3sg, past_3sg, past_3pl, past_participle, verb_class)
        tense:      'present' | 'past' | 'infinitive'
        np1_number: 'sg' | 'pl'
          present + sg  → present_3sg
          present + pl  → infinitive (= Dutch present plural)
          past    + sg  → past_3sg
          past    + pl  → past_3pl
          infinitive    → infinitive (Type 3 IPP)
        """
        if tense == "present":
            form = v1_entry[0] if np1_number == "pl" else v1_entry[1]
        elif tense == "past":
            form = v1_entry[3] if np1_number == "pl" else v1_entry[2]
        elif tense == "infinitive":
            form = v1_entry[0]
        else:
            raise ValueError(f"Invalid tense '{tense}'. Expected 'present', 'past', or 'infinitive'.")
        return (v1_entry[0], form, v1_entry[5])

    @staticmethod
    def can_generate_np_swap(np1_entry, np2_entry):
        """Return (should_generate: bool, ungram_source: str | None).
        Rules:
          NP2 inanimate                   → True,  'selectional_restriction'
          NP2 animate, different number  → True,  'agreement_violation'
          NP2 animate, same number       → False, None
          NP1 and NP2 have same form     → False, None  (sentences would be identical)
        """
        np1_form, np1_number, *_ = np1_entry
        np2_form, np2_number, _, np2_animacy, *__ = np2_entry
        if np1_form == np2_form:
            return False, None
        if np2_animacy == "inanimate":
            return True, "selectional_restriction"
        if np2_number != np1_number:
            return True, "agreement_violation"
        return False, None

    @staticmethod
    def build_record(pair_id, n_pairs, c_type, v_type, grammatical, ungrammatical,
                     ungram_source, alignment, embed,
                     np_chain, v_chain, v1_tense, crit_tokens,
                     source, notes="", v2_object=None):
        """Assemble one output dict. NP and V fields are generated for the full
        chain length, so 3-NP records automatically include NP3/V3 fields.

        np_chain: list of NP entries, one per chain position
                  index 0 (NP1): (form, number, noun_type)          — NP1_POOL (always animate)
                  index 1+ (NP2+): (form, number, noun_type, animacy) — NP2_POOL
        v_chain:  list of (v_entry_or_None, surface_form, verb_class), one per position
                  index 0 (V1): (v1_tuple, surface, class)
                  index 1+ (V2+): (None, infinitive, class)
        crit_tokens: the tokens manipulated to create this variant
                  Variant A (verb swap)  → verb surface forms
                  Variant B (NP swap)    → NP surface forms
                  Variant C (full swap)  → NP forms + verb forms
        v2_object: (form, number) — Type 3 only, else None
        """
        record = {
            "pair_id":       pair_id,
            "n_pairs":       n_pairs,
            "c_type":        c_type,
            "v_type":        v_type,
            "grammatical":   grammatical,
            "ungrammatical": ungrammatical,
            "ungram_source": ungram_source,
            "alignment":     alignment,
            "embed":         embed,
        }
        for i, np_entry in enumerate(np_chain, 1):
            record[f"NP{i}"]        = np_entry[0]
            record[f"NP{i}_anim"]   = "animate" if i == 1 else np_entry[3]
            record[f"NP{i}_number"] = np_entry[1]
            record[f"NP{i}_type"]   = np_entry[2]

        v1_entry = v_chain[0][0]
        record["V1"]       = v_chain[0][1]
        record["V1_lemma"] = v1_entry[0]
        record["V1_class"] = v1_entry[5]
        record["V1_tense"] = v1_tense

        for i, (_, v_surf, v_cls) in enumerate(v_chain[1:], 2):
            record[f"V{i}"]       = v_surf
            record[f"V{i}_lemma"] = v_surf
            record[f"V{i}_class"] = v_cls

        if c_type == 3:
            record["v2_object"] = v2_object[0]
        record["crit_tokens"] = crit_tokens
        record["source"]      = source
        record["notes"]       = notes
        return record

    @abstractmethod
    def generate_item(self, n_pairs: int, item_num: int):
        """Yield all records for one grammatical item (variants A, B, C, ...)."""
        ...

    def generate(self, n_pairs: int, n_generate: int):
        """Yield example records followed by n_generate generated items."""
        examples, item_num, _ = self.load_examples(n_pairs)
        yield from examples
        for _ in range(n_generate):
            item_num += 1
            yield from self.generate_item(n_pairs, item_num)

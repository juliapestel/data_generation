"""
generate.py — minimal pairs generation for Dutch CSD dataset.
Type 1 (dat-clause), 2-NP condition sketch.
"""

import json
from vocab import (
    V1_VERBS, NP1_POOL, NP2_POOL, NP2_V2_COMPATIBILITY,
    DAT_EMBEDDINGS,
)

# ---------------------------------------------------------------------------
# Helpers (to be filled in)
# ---------------------------------------------------------------------------

def pick_v1_form(v1_entry, tense):
    """Return the surface form of V1 given desired tense ('present' or 'past').
    v1_entry is a tuple: (infinitive, present_3sg, past_3sg, past_participle, class)
    """
    # TODO: index into tuple by tense
    pass


def can_generate_np_swap(np1_entry, np2_entry):
    """Return (should_generate: bool, ungram_source: str | None).
    Rules:
      - NP2 inanimate                       → yes, ungram_source = 'selectional_restriction'
      - NP2 animate, different number       → yes, ungram_source = 'agreement_violation'
      - NP2 animate, same number as NP1    → no
    np1_entry: (form, number, type)   from NP1_POOL
    np2_entry: (form, number, type, animacy)  from NP2_POOL
    """
    # TODO: implement check
    pass


def build_record(pair_id, grammatical, ungrammatical, variant, ungram_source,
                 alignment, embed, np1_entry, np2_entry, v1_entry, v1_surface,
                 v1_tense, v2):
    """Assemble one output dict with keys in the order specified in CLAUDE.md."""
    # TODO: fill in all fields; decide how to handle the keys that are in
    #       CLAUDE.md but absent from examples.jsonl (NP1_num, NP2_num,
    #       V1_tense, V2_lemma, time_adv, crit_tokens, validation,
    #       rating_gram, rating_ungram)
    pass


# ---------------------------------------------------------------------------
# Type 1, 2-NP generator
# ---------------------------------------------------------------------------

def generate_type1_2np():
    """Generate all items for Type 1 (dat-clause), 2-NP condition.

    Target distribution (50 grammatical sentences, CLAUDE.md §V1 class distribution):
        zien:   12 items
        horen:  10 items
        voelen:  8 items
        laten:  10 items
        helpen: 10 items

    Steps for each item:
      1. Pick embed from DAT_EMBEDDINGS
      2. Pick NP1 from NP1_POOL
      3. Pick NP2 from NP2_POOL that has a NP2_V2_COMPATIBILITY entry
      4. Pick V2 from NP2_V2_COMPATIBILITY[NP2]
      5. Pick V1 verb + tense (vary present/past across items, do not default to past)
         get surface form via pick_v1_form()
      6. Build grammatical sentence:
            "{embed} {NP1} {NP2} {V1_surface} {V2}."
      7. Assign item number → pair_id base = f"t1_2np_{item_num:03d}"

      Then generate up to 3 variants:

      Variant A — V_swap (always generated):
        ungrammatical = "{embed} {NP1} {NP2} {V2} {V1_surface}."
        pair_id = base + "_A"
        alignment = False, ungram_source = "verb_order"

      Variant B — NP_swap (conditional):
        check = can_generate_np_swap(np1_entry, np2_entry)
        if check.should_generate:
            ungrammatical = "{embed} {NP2} {NP1} {V1_surface} {V2}."
            pair_id = base + "_B"
            alignment = False
            ungram_source = check.ungram_source
            add note if ungram_source == "agreement_violation"

      Variant C — full_reversal (only if Variant B was generated):
        ungrammatical = "{embed} {NP2} {NP1} {V2} {V1_surface}."
        pair_id = base + "_C"
        alignment = True
        ungram_source = same as Variant B

      Yield / collect all generated records.
    """
    # TODO: implement
    pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    records = list(generate_type1_2np())
    output_path = "data/type1_2np.jsonl"
    with open(output_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"Wrote {len(records)} records to {output_path}")

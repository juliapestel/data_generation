"""
generate.py — minimal pairs generation for Dutch CSD dataset.
Covers Type 1 (dat-clause), Type 2 (omdat-clause), Type 3 (AcI matrix), 2-NP condition.
"""

import json
import random
from vocab import (
    V1_VERBS,
    NP1_POOL, NP2_POOL,
    V2_VERBS,
    TYPE3_V2_VERBS, TYPE3_OBJ_V2_POOL,
    DAT_EMBEDDINGS, OMDAT_EMBEDDINGS, TIME_ADVS,
    get_compatible_v2s, get_compatible_obj_v2,
)

# animate_np2s = [(f, n, t, a) for f, n, t, a in NP2_POOL if a == "animate"]

# id_template = f"{nps}_{type}_{num}_{variant}"

# c12_gram = f"{embed} {NP1} {NP2} {V1} {V2}"
# c12_ungramA = f"{embed} {NP1} {NP2} {V2} {V1}"
# c12_ungramB = f"{embed} {NP2} {NP1} {V1} {V2}"
# c12_ungramC = f"{embed} {NP2} {NP1} {V2} {V1}"

# ---------------------------------------------------------------------------
# Helpers (to be filled in)
# ---------------------------------------------------------------------------

def pick_v1_form(v1_entry, tense):
    """Return the surface form of V1.
    v1_entry: (infinitive, present_3sg, past_3sg, past_participle, verb_class)
    tense: 'present' | 'past' | 'infinitive'
      - 'present'    → v1_entry[1]
      - 'past'       → v1_entry[2]
      - 'infinitive' → v1_entry[0]  (used for Type 3 IPP)
    """
    if tense == "present":
        return (v1_entry[0], v1_entry[1], v1_entry[4])
    elif tense == "past":
        return (v1_entry[0], v1_entry[2], v1_entry[4])
    elif tense == "infinitive":
        return (v1_entry[0], v1_entry[0], v1_entry[4])
    else:
        raise ValueError(f"Invalid tense '{tense}'. Expected 'present', 'past', or 'infinitive'.")


def can_generate_np_swap(np1_entry, np2_entry):
    np1_form, np1_number, _ = np1_entry
    np2_form, np2_number, _, np2_animacy = np2_entry

    # Cannot swap identical surface forms — sentences would be identical
    if np1_form == np2_form:
        return False, None

    if np2_animacy == "inanimate":
        return True, "selectional_restriction"
    if np2_number != np1_number:
        return True, "agreement_violation"
    return False, None


def build_record(pair_id, n_pairs, c_type, v_type, grammatical, ungrammatical,
                 ungram_source, alignment, embed, np1_entry, np2_entry,
                 v1_entry, V1, v1_tense, v2, v2_class,
                 source, notes="", v2_object=None):
    """Assemble one output dict with keys in the exact order from the examples.

    Key order (Types 1 and 2):
        pair_id, n_pairs, c_type, v_type, grammatical, ungrammatical,
        ungram_source, alignment, embed,
        NP1, NP1_anim, NP1_number, NP1_type,
        NP2, NP2_anim, NP2_number, NP2_type,
        V1, V1_lemma, V1_class, V1_tense,
        V2, V2_lemma, V2_class,
        crit_tokens,
        source, notes

    For c_type == 3, v2_object is inserted after V2_class and before crit_tokens.

    Args:
        np1_entry: (form, number, noun_type)                  from NP1_POOL
        np2_entry: (form, number, noun_type, animacy)         from NP2_POOL   [Types 1/2]
                   (form, number, noun_type="common", animacy="animate")       [Type 3 NP2]
        v1_entry:  (infinitive, present_3sg, past_3sg, past_participle, class) from V1_VERBS
        V1:        surface form of V1 as it appears in the grammatical sentence
        v2:        infinitive of V2 (surface form for Types 1/2/3; always infinitive)
        v2_class:  semantic class string from V2_VERBS or TYPE3_V2_VERBS
        v2_object: (form, number) from get_compatible_obj_v2(); Type 3 only, else None

    Notes:
        V2_lemma == v2 in all cases (V2 always appears as infinitive).
    """
    # TODO: implement — build and return the ordered dict
    dict = {}


    pass



# ---------------------------------------------------------------------------
# Type 1 (dat-clause), 2-NP
# ---------------------------------------------------------------------------

def generate_type1_2np():
    """Generate all items for Type 1 (dat-clause), 2-NP condition.

    Template: {embed} {NP1} {NP2} {V1} {V2}.

    Target V1 distribution (50 grammatical sentences):
        zien:   12,  horen: 10,  voelen: 8,  laten: 10,  helpen: 10
    Tense: vary present/past across items — do not default to past only.
    helpen constraint: NP2 must be animate.

    Steps per item:
      1. Pick embed from DAT_EMBEDDINGS
      2. Pick NP1 from NP1_POOL
      3. Pick NP2 from NP2_POOL
           - if V1 is helpen: NP2 must be animate
      4. Pick V2 via get_compatible_v2s(np2_animacy)
           - then check is_valid_v2(v2, np2_form) to filter NP2_SPECIFIC_V2 constraints
      5. Pick V1 + tense → surface form via pick_v1_form()
      6. grammatical = "{embed} {NP1} {NP2} {V1} {V2}."
      7. base_id = f"t1_2np_{item_num:03d}"

    Variant A — v_type "A", V_swap (always):
      ungrammatical = "{embed} {NP1} {NP2} {V2} {V1}."
      alignment = False, ungram_source = "verb_order"

    Variant B — v_type "B", NP_swap (conditional via can_generate_np_swap):
      ungrammatical = "{embed} {NP2} {NP1} {V1} {V2}."
      alignment = False
      if ungram_source == "agreement_violation": add note

    Variant C — v_type "C", full_reversal (only if B was generated):
      ungrammatical = "{embed} {NP2} {NP1} {V2} {V1}."
      alignment = True, ungram_source = same as B
    """
    # TODO: implement — yield records

    count_v1 = {'zien': 0, 'horen': 0, 'voelen': 0, 'laten': 0, 'helpen': 0} 

    item_num = 0 # dit is niet goed want ik moet ook nog aangeven dat we de examples erin hebben

    for _ in range(10):
        # random dat-embedding
        emb = random.choice(DAT_EMBEDDINGS)

        tense = random.choices(["present", "past"], weights=[65, 35])[0]

        # random choice NP1
        NP1_tuple = random.choice(NP1_POOL)

        # random choice V1
        valid_v1 = [t for t in V1_VERBS if count_v1[t[0]] < 15]
        if not valid_v1:
            raise ValueError("All V1s have reached the threshold of 15.")

        v1_tuple = random.choice(valid_v1)
        count_v1[v1_tuple[0]] += 1  # update the count after choosing
        v1 = pick_v1_form(v1_tuple, tense)

        # choose NP2
        if v1[0] =="helpen":
            valid_NP2 = [t for t in NP2_POOL if t[3] == "animate" and t[0] != NP1_tuple[0]]
        else:
            valid_NP2 = [t for t in NP2_POOL if t[0] != NP1_tuple[0]]

        NP2_tuple = random.choice(valid_NP2)

        # choose V2
        v2_tuple = random.choice(get_compatible_v2s(NP2_tuple[3]))

        gram = f"{emb} {NP1_tuple[0]} {NP2_tuple[0]} {v1[1]} {v2_tuple[0]}."
        print(f"Grammatical sentence: {gram}")

        # for variant in range(["A", "B", "C"]):


        #     id_template = f"{nps}_{type}_{num}_{variant}"

        #     gram = f"{emb} {NP1_tuple[0]} {NP2_tuple[0]} {v1_tuple[0]} {v2_tuple[0]}"
        #     ungramA = f"{emb} {NP1_tuple[0]} {NP2_tuple[0]} {v2_tuple[0]} {v1_tuple[0]}"
        #     ungramB = f"{emb} {NP2_tuple[0]} {NP1_tuple[0]} {v1_tuple[0]} {v2_tuple[0]}"
        #     ungramC = f"{emb} {NP2_tuple[0]} {NP1_tuple[0]} {v2_tuple[0]} {v1_tuple[0]}"



    # pass


# ---------------------------------------------------------------------------
# Type 2 (omdat-clause), 2-NP
# ---------------------------------------------------------------------------

def generate_type2_2np():
    """Generate all items for Type 2 (omdat-clause), 2-NP condition.

    Template: {embed} {NP1} {NP2} {V1} {V2}.

    Identical logic to Type 1 except:
      - embed comes from OMDAT_EMBEDDINGS
      - c_type = 2, pair_id prefix = "t2_2np"
      - laten is excluded (causative: Type 1 only)
      - V1 distribution adjusted accordingly:
            zien: 16, horen: 12, voelen: 10, helpen: 12

    Variant logic is identical to Type 1.
    """
    # TODO: implement — yield records
    pass


# ---------------------------------------------------------------------------
# Type 3 (AcI matrix), 2-NP
# ---------------------------------------------------------------------------
def generate_type3_2np():
    """Generate all items for Type 3 (AcI matrix clause), 2-NP condition.

    Template: {csd_np1} heeft {csd_np2} {v2_object} {csd_v1_inf} {csd_v2_inf} {time_adv}.

    Where:
      csd_np1    - matrix subject; CSD-NP1, subject of the perception verb (csd_v1)
      csd_np2    - AcI accusative NP; CSD-NP2, logical subject of the transitive verb (csd_v2)
      v2_object  - object of csd_v2; NOT part of the CSD, included to satisfy
                   transitivity requirements of csd_v2
      csd_v1     - perception verb (zien/horen/voelen); appears in infinitive (IPP)
      csd_v2     - transitive verb; appears in infinitive

    The cross-serial dependency is between csd_np1–csd_v1 and csd_np2–csd_v2.
    v2_object has no role in the crossing dependency.

    Note on the 2-NP label: this construction has three NPs in the surface string
    (csd_np1, csd_np2, v2_object), but only two participate in the CSD. The 2-NP
    label refers to the number of NPs in the dependency chain, consistent with
    Types 1 and 2.

    V1 distribution (50 items):
        zien: 20, horen: 20, voelen: 10
        (voelen may be redistributed if insufficient clean items — see CLAUDE.md)

    Steps per item:
      1. Pick csd_np1 from NP1_POOL (animate) → embed = f"{csd_np1_form} heeft"
      2. Pick csd_np2 from type3_np2_candidates (animate); must differ from csd_np1
      3. Pick csd_v2 from TYPE3_V2_VERBS
      4. Pick v2_object from get_compatible_obj_v2(csd_v2_inf) → returns (form, number);
         always inanimate
      5. Pick csd_v1 (perception verb only) → surface form is infinitive (IPP)
      6. Pick time_adv from TIME_ADVS
      7. grammatical = "{embed} {csd_np2} {v2_object} {csd_v1_inf} {csd_v2_inf} {time_adv}."
      8. base_id = f"t3_2np_{item_num:03d}"

    Variant A — v_type "A", V_swap (always):
      Tests verb order violation within the CSD chain.
      ungrammatical = "{embed} {csd_np2} {v2_object} {csd_v2_inf} {csd_v1_inf} {time_adv}."
      alignment = False, ungram_source = "verb_order"

    Variant B — v_type "B", NP_swap:
      Swaps csd_np2 and v2_object. Places an inanimate NP (v2_object) in the
      logical subject position of csd_v2, violating selectional restrictions.
      Always generated because v2_object is always inanimate.
      ungrammatical = "{embed} {v2_object} {csd_np2} {csd_v1_inf} {csd_v2_inf} {time_adv}."
      alignment = False, ungram_source = "selectional_restriction"
      Note: targets argument structure within the AcI complement, not CSD alignment.

    Variant C — v_type "C", full_reversal (always, since B is always generated):
      Combines NP_swap with V_swap. Reversed NP order partially re-aligns
      v2_object with csd_v2, but the selectional restriction violation persists
      because v2_object remains inanimate.
      ungrammatical = "{embed} {v2_object} {csd_np2} {csd_v2_inf} {csd_v1_inf} {time_adv}."
      alignment = True, ungram_source = "selectional_restriction"
      Note: alignment = True reflects surface NP-verb co-indexation only; the
      selectional restriction violation means this is not fully grammatical.
    """
    # TODO: implement — yield records
    pass

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# if __name__ == "__main__":
#     generators = [
#         (generate_type1_2np, "data/type1_2np.jsonl"),
#         (generate_type2_2np, "data/type2_2np.jsonl"),
#         (generate_type3_2np, "data/type3_2np.jsonl"),
#     ]
#     for gen_fn, output_path in generators:
#         records = list(gen_fn())
#         with open(output_path, "w", encoding="utf-8") as f:
#             for rec in records:
#                 f.write(json.dumps(rec, ensure_ascii=False) + "\n")
#         print(f"Wrote {len(records)} records to {output_path}")

# TEST MAIN

if __name__ == "__main__":
    generate_type1_2np()
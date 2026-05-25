"""
generators.py — Concrete CSD generator subclasses for Types 1, 2, and 3.
"""

import random

from vocab import (
    V1_VERBS, V2_CHAIN_VERBS, V2_CHAIN_ALLOWED_AFTER, NP1_POOL, NP2_POOL,
    TYPE3_V2_VERBS, DAT_EMBEDDINGS, OMDAT_EMBEDDINGS,
    TIME_ADVS, get_compatible_v2s, get_v2s_by_class, get_compatible_obj_v2,
    has_male_name_adjacency,
)
from generator_base import CSDGenerator
 
 
class SubordinateGenerator(CSDGenerator):
    """Base generator for subordinate clause constructions (Types 1 and 2).

    Sentence template: {embed} {NP1} ... {NPn} {V1} ... {Vn}.

    Chain length is passed as n_pairs at generate time. For n_pairs=2 the
    logic is fully implemented. n_pairs > 2 raises NotImplementedError until
    NP3/V3 vocabulary and selection constraints are defined in vocab.py — at
    that point, extend the i > 1 branch in generate_item.

    Subclasses set four class attributes; everything else is shared:
        c_type         (int):  1 or 2
        embedding_pool (list): DAT_EMBEDDINGS or OMDAT_EMBEDDINGS
        v1_pool        (list): which V1_VERBS entries are permitted
        v1_fractions   (dict): {V1_lemma: sampling_weight}, weights sum to 1.0
    """

    # Declared here for documentation; concrete subclasses must assign values.
    c_type: int
    embedding_pool: list
    v1_pool: list
    v1_fractions: dict

    def __init__(self):
        verbs = [t for t in self.v1_pool if t[0] in self.v1_fractions]
        self._verbs   = verbs
        self._weights = [self.v1_fractions[t[0]] for t in verbs]

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _sample_np2(self, v1_lemma: str, np1: tuple, chain_continues: bool = False) -> tuple:
        """Return an NP2 entry compatible with V1 constraints and distinct from NP1.
        chain_continues=True (3-NP+): NP2 must be animate because the next verb
        takes NP2 as its logical subject.
        """
        if chain_continues or v1_lemma == "helpen":
            pool = [t for t in NP2_POOL if t[3] == "animate"   and t[0] != np1[0] and t[2] != np1[2]]
        elif v1_lemma == "voelen":
            pool = [t for t in NP2_POOL if t[3] == "inanimate" and t[0] != np1[0]]
        else:
            pool = [t for t in NP2_POOL if t[0] != np1[0] and t[2] != np1[2]]
        return random.choice(pool)

    def _sample_npN(self, np_chain: list, prev_v_lemma: str,
                    animate_only: bool = False) -> tuple:
        """Return an NP entry for position 3+ (NP3, NP4, ...), excluding all
        NP forms already present in the chain.
        When prev_v_lemma == "helpen" or animate_only=True, NP must be animate.
        animate_only=True is used for 4-NP chains where all NPs must be animate.
        """
        taken = {np[0] for np in np_chain}
        if prev_v_lemma == "helpen" or animate_only:
            pool = [t for t in NP2_POOL if t[0] not in taken and t[3] == "animate"]
        else:
            pool = [t for t in NP2_POOL if t[0] not in taken]
        return random.choice(pool)

    def _sample_v_terminal(self, prev_v_lemma: str, np_i: tuple) -> tuple[str, str]:
        entry = random.choice(get_compatible_v2s(np_i[3]))
        return (entry[0], entry[2])

    def _sample_v_chain(self, np_i: tuple, prev_v_class: str,
                        chain_lemmas: list[str]) -> tuple[str, str]:
        """Return (infinitive, class) for an intermediate chain verb (from V2_CHAIN_VERBS).
        np_i must be animate — enforced upstream by _sample_np2/npN.
        prev_v_class:  verb class of the immediately preceding verb; used to enforce
                       V2_CHAIN_ALLOWED_AFTER transition rules.
        chain_lemmas:  list of all verb lemmas already committed to the chain,
                       including V1 and any previously sampled chain verbs. Any
                       candidate whose infinitive appears in this list is excluded,
                       preventing same-lemma repetition at any chain distance.
                       For non-V1 slots, surface form equals lemma (all are infinitives).
        Raises ValueError if prev_v_class has no permitted chain continuations.
        Raises IndexError (via random.choice) if the pool is empty after filtering;
        callers should catch this and skip the item.
        """
        allowed_classes = V2_CHAIN_ALLOWED_AFTER.get(prev_v_class, [])
        if not allowed_classes:
            raise ValueError(
                f"No permitted chain verb class after '{prev_v_class}' "
                f"under current V2_CHAIN_ALLOWED_AFTER constraints."
            )
        pool = [
            e for e in V2_CHAIN_VERBS
            if e[5] in allowed_classes and e[0] not in chain_lemmas
        ]
        entry = random.choice(pool)  # raises IndexError if pool is empty
        return (entry[0], entry[5])

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate_item(self, n_pairs: int, item_num: int):
        embed    = random.choice(self.embedding_pool)
        tense    = "present"

        if n_pairs > 2:
            np1_weights = [3 if np[1] == "pl" else 1 for np in NP1_POOL]
            np1 = random.choices(NP1_POOL, weights=np1_weights, k=1)[0]
        else:
            np1 = random.choice(NP1_POOL)
        v1_tuple = random.choices(self._verbs, weights=self._weights)[0]
        v1       = self.pick_v1_form(v1_tuple, tense, np1[1])

        # Build NP and verb chains iteratively.
        # v_chain entries: (v1_entry_or_None, surface_form, verb_class)
        # For i < n_pairs-1 (intermediate): verb is a chain verb from V2_CHAIN_VERBS.
        # For i == n_pairs-1 (final):       verb is a terminal verb from V2_VERBS.
        # voelen as V1 is blocked for 3-NP+: perception via touch is implausible
        # in causative-embedding contexts.
        if n_pairs > 2 and v1_tuple[0] == "voelen":
            return

        np_chain = [np1]
        v_chain  = [(v1_tuple, v1[1], v1_tuple[5])]

        for i in range(1, n_pairs):
            is_last     = (i == n_pairs - 1)
            prev_lemma  = v_chain[i - 1][1] if i > 1 else v1[0]
            prev_class  = v_chain[i - 1][2] if i > 1 else v1_tuple[5]

            if i == 1:
                np_i = self._sample_np2(v1[0], np1, chain_continues=not is_last)
            else:
                np_i = self._sample_npN(np_chain, prev_lemma)

            if is_last:
                v_raw = self._sample_v_terminal(prev_lemma, np_i)
            else:
                # Skip items whose V1 class has no permitted chain continuation
                # (e.g. benefactive V1 under current V2_CHAIN_ALLOWED_AFTER).
                # IndexError covers the edge case of an empty pool after filtering.
                # For non-V1 slots, surface form equals lemma (all are infinitives).
                chain_lemmas = [
                    e[0][0] if e[0] is not None else e[1]
                    for e in v_chain
                ]
                try:
                    v_raw = self._sample_v_chain(np_i, prev_class, chain_lemmas)
                except (ValueError, IndexError):
                    return

            np_chain.append(np_i)
            v_chain.append((None, v_raw[0], v_raw[1]))

        if has_male_name_adjacency(np_chain):
            return

        np_forms = [np[0] for np in np_chain]
        v_forms  = [v[1]  for v  in v_chain]
        base_id  = f"{n_pairs}np_t{self.c_type}_{item_num:03d}"
        gram     = f"{embed} {' '.join(np_forms)} {' '.join(v_forms)}."
        ungram_a = f"{embed} {' '.join(np_forms)} {' '.join(reversed(v_forms))}."

        shared = dict(
            n_pairs=n_pairs, c_type=self.c_type, grammatical=gram,
            embed=embed, np_chain=np_chain, v_chain=v_chain,
            v1_tense=tense, source="generated",
        )

        yield self.build_record(f"{base_id}_A", **shared,
                                v_type="A", ungrammatical=ungram_a,
                                ungram_source="verb_order", alignment=False,
                                crit_tokens=v_forms)

        if n_pairs == 3:
            # Variants D1 and D2: partial verb permutations for 3-NP chains.
            # Each targets a different pair of adjacent verbs, allowing
            # independent probing of innermost vs. outermost dependency pairs.

            # Variant D1: V1V3V2 — swap final two verbs.
            # Preserves NP1-V1 alignment. Disrupts NP2-V2 and NP3-V3.
            v_forms_d1 = [v_forms[0], v_forms[2], v_forms[1]]
            ungram_d1 = f"{embed} {' '.join(np_forms)} {' '.join(v_forms_d1)}."
            yield self.build_record(f"{base_id}_D1", **shared,
                                    v_type="D1", ungrammatical=ungram_d1,
                                    ungram_source="verb_order_partial", alignment=False,
                                    crit_tokens=[v_forms[1], v_forms[2]],
                                    notes="Partial verb permutation V1V3V2: final two verbs swapped. "
                                          "NP1-V1 alignment preserved. NP2-V2 and NP3-V3 disrupted. "
                                          "Use to probe sensitivity to innermost dependency pair.")

            # Variant D2: V2V1V3 — swap first two verbs.
            # Preserves NP3-V3 alignment. Disrupts NP1-V1 and NP2-V2.
            v_forms_d2 = [v_forms[1], v_forms[0], v_forms[2]]
            ungram_d2 = f"{embed} {' '.join(np_forms)} {' '.join(v_forms_d2)}."
            yield self.build_record(f"{base_id}_D2", **shared,
                                    v_type="D2", ungrammatical=ungram_d2,
                                    ungram_source="verb_order_partial", alignment=False,
                                    crit_tokens=[v_forms[0], v_forms[1]],
                                    notes="Partial verb permutation V2V1V3: first two verbs swapped. "
                                          "NP3-V3 alignment preserved. NP1-V1 and NP2-V2 disrupted. "
                                          "Use to probe sensitivity to outermost dependency pair.")

        can_b, ungram_source = self.can_generate_np_swap(np1, np_chain[1])
        if can_b and has_male_name_adjacency(list(reversed(np_chain))):
            can_b = False
        if can_b:
            ungram_b = f"{embed} {' '.join(reversed(np_forms))} {' '.join(v_forms)}."
            ungram_c = f"{embed} {' '.join(reversed(np_forms))} {' '.join(reversed(v_forms))}."
            notes_b  = "Agreement violation: do not use for alignment-specific analysis." \
                       if ungram_source == "agreement_violation" else ""
            yield self.build_record(f"{base_id}_B", **shared,
                                    v_type="B", ungrammatical=ungram_b,
                                    ungram_source=ungram_source, alignment=False,
                                    crit_tokens=np_forms, notes=notes_b)
            yield self.build_record(f"{base_id}_C", **shared,
                                    v_type="C", ungrammatical=ungram_c,
                                    ungram_source=ungram_source, alignment=True,
                                    crit_tokens=np_forms + v_forms)


class Type1Generator(SubordinateGenerator):
    """Type 1 (dat-clause) generator.

    For 3-NP chains, valid V1→V2_chain class transitions under
    V2_CHAIN_ALLOWED_AFTER are:
      perception → causative  (e.g. zag laten … terminal)
      causative  → perception (e.g. liet zien … terminal)
    helpen (benefactive) as V1 has no permitted chain continuation and will
    always be skipped for n_pairs > 2; only 2-NP items will be generated for
    helpen in this type.
    """
    c_type         = 1
    embedding_pool = DAT_EMBEDDINGS
    v1_pool        = V1_VERBS
    v1_fractions   = {"zien": 0.40, "horen": 0.35, "laten": 0.25}


class Type2Generator(SubordinateGenerator):
    """Type 2 (omdat-clause) generator.

    laten is included as V1 to provide causative items alongside perception and
    benefactive items. For 3-NP chains, the causative → perception chain sequence
    is valid; benefactive V1 remains skipped for n_pairs > 2 due to
    V2_CHAIN_ALLOWED_AFTER constraints.
    helpen as V1 will always be skipped for n_pairs > 2.
    """
    c_type         = 2
    embedding_pool = OMDAT_EMBEDDINGS
    v1_pool        = V1_VERBS
    v1_fractions   = {"zien": 0.45, "horen": 0.30, "laten": 0.25}


class Type1Generator4NP(SubordinateGenerator):
    """Type 1 (dat-clause) generator for 4-NP chains.

    The only viable 4-NP class sequence is:
        perception → causative → perception → terminal (animate)
    Causative → perception → causative is blocked in practice because only one
    causative chain verb exists (laten) and same-lemma repetition is forbidden.
    V1 is therefore restricted to perception verbs (zien, horen); voelen is
    excluded because the voelen-embedding context is implausible in a 4-verb chain.

    Generates Variant A (full reversal) and Variants D1, D2, D3 (partial
    permutations) for every item. Variants B and C are not generated: all NPs
    must be animate, so inanimate-driven selectional restriction is unavailable,
    and thematic role reversal across four animate NPs produces uninterpretable
    stimuli.
    """
    c_type         = 1
    embedding_pool = DAT_EMBEDDINGS
    v1_pool        = [v for v in V1_VERBS if v[0] in ("zien", "horen")]
    v1_fractions   = {"zien": 0.50, "horen": 0.50}

    def generate_item(self, n_pairs: int, item_num: int):
        if n_pairs != 4:
            raise NotImplementedError(
                f"Type1Generator4NP only supports n_pairs=4, got {n_pairs}."
            )

        embed    = random.choice(self.embedding_pool)
        tense    = "present"
        np1_weights = [3 if np[1] == "pl" else 1 for np in NP1_POOL]
        np1      = random.choices(NP1_POOL, weights=np1_weights, k=1)[0]
        v1_tuple = random.choices(self._verbs, weights=self._weights)[0]
        v1       = self.pick_v1_form(v1_tuple, tense, np1[1])

        # Enforce perception-only V1 explicitly; redundant given restricted pool
        # but makes the structural constraint visible.
        if v1_tuple[5] != "perception" or v1_tuple[0] == "voelen":
            return

        np_chain = [np1]
        v_chain  = [(v1_tuple, v1[1], v1_tuple[5])]

        for i in range(1, 4):
            is_last    = (i == 3)
            prev_lemma = v_chain[i - 1][1] if i > 1 else v1[0]
            prev_class = v_chain[i - 1][2] if i > 1 else v1_tuple[5]

            # All NPs in a 4-NP chain must be animate: every NP is the logical
            # subject of the next verb, and the terminal verb requires an animate
            # subject. Use animate_only=True for all non-NP1 positions.
            if i == 1:
                np_i = self._sample_np2(v1[0], np1, chain_continues=True)
            else:
                np_i = self._sample_npN(np_chain, prev_lemma, animate_only=True)

            if is_last:
                v_raw = self._sample_v_terminal(prev_lemma, np_i)
            else:
                # For non-V1 slots, surface form equals lemma (all are infinitives).
                chain_lemmas = [
                    e[0][0] if e[0] is not None else e[1]
                    for e in v_chain
                ]
                try:
                    v_raw = self._sample_v_chain(np_i, prev_class, chain_lemmas)
                except (ValueError, IndexError):
                    return
                # Block voelen in any intermediate (chain) position. voelen is not
                # currently in V2_CHAIN_VERBS so this never fires, but the check
                # makes the constraint explicit for future vocabulary changes.
                if v_raw[0] == "voelen":
                    return

            np_chain.append(np_i)
            v_chain.append((None, v_raw[0], v_raw[1]))

        if has_male_name_adjacency(np_chain):
            return

        # Naturalness constraint (not a grammaticality constraint): at least one
        # of NP2, NP3, NP4 must be a common noun. Four proper names in a row
        # produce unnatural stimuli in Dutch.
        if all(np[2] == "proper" for np in np_chain[1:]):
            return

        np_forms = [np[0] for np in np_chain]
        v_forms  = [v[1]  for v  in v_chain]
        base_id  = f"4np_t{self.c_type}_{item_num:03d}"
        gram     = f"{embed} {' '.join(np_forms)} {' '.join(v_forms)}."
        ungram_a = f"{embed} {' '.join(np_forms)} {' '.join(reversed(v_forms))}."

        shared = dict(
            n_pairs=4, c_type=self.c_type, grammatical=gram,
            embed=embed, np_chain=np_chain, v_chain=v_chain,
            v1_tense=tense, source="generated",
        )

        yield self.build_record(f"{base_id}_A", **shared,
                                v_type="A", ungrammatical=ungram_a,
                                ungram_source="verb_order", alignment=False,
                                crit_tokens=v_forms)

        # Variant D1: V1V2V4V3 — swap final pair.
        # Preserves NP1-V1 and NP2-V2 alignment. Disrupts NP3-V3 and NP4-V4.
        v_forms_d1 = [v_forms[0], v_forms[1], v_forms[3], v_forms[2]]
        ungram_d1  = f"{embed} {' '.join(np_forms)} {' '.join(v_forms_d1)}."
        yield self.build_record(f"{base_id}_D1", **shared,
                                v_type="D1", ungrammatical=ungram_d1,
                                ungram_source="verb_order_partial", alignment=False,
                                crit_tokens=[v_forms[2], v_forms[3]],
                                notes="Partial verb permutation V1V2V4V3: final pair swapped. "
                                      "NP1-V1 and NP2-V2 preserved. NP3-V3 and NP4-V4 disrupted.")

        # Variant D2: V1V3V2V4 — swap middle pair.
        # Preserves NP1-V1 and NP4-V4 alignment. Disrupts NP2-V2 and NP3-V3.
        v_forms_d2 = [v_forms[0], v_forms[2], v_forms[1], v_forms[3]]
        ungram_d2  = f"{embed} {' '.join(np_forms)} {' '.join(v_forms_d2)}."
        yield self.build_record(f"{base_id}_D2", **shared,
                                v_type="D2", ungrammatical=ungram_d2,
                                ungram_source="verb_order_partial", alignment=False,
                                crit_tokens=[v_forms[1], v_forms[2]],
                                notes="Partial verb permutation V1V3V2V4: middle pair swapped. "
                                      "NP1-V1 and NP4-V4 preserved. NP2-V2 and NP3-V3 disrupted.")

        # Variant D3: V2V1V3V4 — swap first pair.
        # Preserves NP3-V3 and NP4-V4 alignment. Disrupts NP1-V1 and NP2-V2.
        # Note: V1 is finite in the grammatical sentence; placing it in V2 position
        # (where an infinitive is expected) creates a morphosyntactic confound.
        # Flag in analysis: the anomaly is partly morphological, not purely word-order.
        v_forms_d3 = [v_forms[1], v_forms[0], v_forms[2], v_forms[3]]
        ungram_d3  = f"{embed} {' '.join(np_forms)} {' '.join(v_forms_d3)}."
        yield self.build_record(f"{base_id}_D3", **shared,
                                v_type="D3", ungrammatical=ungram_d3,
                                ungram_source="verb_order_partial", alignment=False,
                                crit_tokens=[v_forms[0], v_forms[1]],
                                notes="Partial verb permutation V2V1V3V4: first pair swapped. "
                                      "NP3-V3 and NP4-V4 preserved. NP1-V1 and NP2-V2 disrupted. "
                                      "Confound: V1 is finite; in D3 it appears where an infinitive "
                                      "is expected, adding a morphosyntactic anomaly alongside the "
                                      "word-order violation. Note this in analysis.")


class Type3Generator(CSDGenerator):
    """Type 3 (AcI matrix) generator.

    Supports two V1 classes:
      Perception (zien, horen): template NP1 heeft NP2 OBJ_V2 V1_inf V2_trans time_adv.
        Variants A, B, C generated. v2_object is always inanimate, so the
        selectional restriction is always available for B/C.
      Causative (laten): template NP1 heeft NP2 OBJ_V2 laten V2_transitive time_adv.
        OBJ_V2 is the direct object of V2; V2 is drawn from TYPE3_V2_VERBS via
        get_compatible_obj_v2. Variants A, B, C generated; OBJ_V2 (inanimate) cannot
        be logical subject of laten, so selectional restriction applies for B/C.

    V1 always appears in infinitive form (IPP). Only n_pairs=2 is supported.
    """
    c_type       = 3
    v1_pool      = [v for v in V1_VERBS if v[0] in ("zien", "horen", "laten")]
    v1_fractions = {"zien": 0.40, "horen": 0.36, "laten": 0.24}

    def __init__(self):
        verbs = [t for t in self.v1_pool if t[0] in self.v1_fractions]
        self._verbs   = verbs
        self._weights = [self.v1_fractions[t[0]] for t in verbs]

    def generate_item(self, n_pairs: int, item_num: int):
        if n_pairs != 2:
            raise NotImplementedError(
                f"n_pairs={n_pairs} not yet supported for Type3Generator."
            )
        np1      = random.choice(NP1_POOL)
        aux      = "hebben" if np1[1] == "pl" else "heeft"
        np1_form = np1[0].capitalize() if np1[2] == "common" else np1[0]
        v1_tuple = random.choices(self._verbs, weights=self._weights)[0]
        v1       = self.pick_v1_form(v1_tuple, "infinitive", np1[1])

        valid_np2 = [t for t in NP2_POOL if t[3] == "animate" and t[0] != np1[0]]
        np2       = random.choice(valid_np2)
        time_adv  = random.choice(TIME_ADVS)

        np_chain = [np1, np2]
        base_id  = f"{n_pairs}np_t{self.c_type}_{item_num:03d}"

        if v1_tuple[0] == "laten":
            # Causative laten with transitive V2 and OBJ_V2.
            # Template: NP1 heeft NP2 OBJ_V2 laten V2_transitive time_adv
            # OBJ_V2 is the direct object of V2, not of laten.
            # Selectional restriction: OBJ_V2 (inanimate) cannot be logical subject
            # of laten, making NP2/OBJ_V2 swap ungrammatical.
            v2_entry     = random.choice(TYPE3_V2_VERBS)
            v2, v2_class = v2_entry[0], v2_entry[1]
            obj          = random.choice(get_compatible_obj_v2(v2))

            v_chain  = [(v1_tuple, v1[1], v1_tuple[5]), (None, v2, v2_class)]
            gram     = f"{np1_form} {aux} {np2[0]} {obj[0]} {v1[1]} {v2} {time_adv}."
            ungram_a = f"{np1_form} {aux} {np2[0]} {obj[0]} {v2} {v1[1]} {time_adv}."
            ungram_b = f"{np1_form} {aux} {obj[0]} {np2[0]} {v1[1]} {v2} {time_adv}."
            ungram_c = f"{np1_form} {aux} {obj[0]} {np2[0]} {v2} {v1[1]} {time_adv}."

            shared = dict(
                n_pairs=n_pairs, c_type=self.c_type, grammatical=gram,
                embed="", np_chain=np_chain, v_chain=v_chain,
                v1_tense="infinitive", source="generated",
                v2_object=(obj[0], obj[1]),
            )
            yield self.build_record(f"{base_id}_A", **shared, v_type="A",
                                    ungrammatical=ungram_a,
                                    ungram_source="verb_order", alignment=False,
                                    crit_tokens=[v1[1], v2],
                                    notes="Type 3 causative laten with OBJ_V2.")
            yield self.build_record(f"{base_id}_B", **shared, v_type="B",
                                    ungrammatical=ungram_b,
                                    ungram_source="selectional_restriction",
                                    alignment=False,
                                    crit_tokens=[np2[0], obj[0]],
                                    notes="Type 3 causative laten: OBJ_V2 (inanimate) cannot be "
                                          "logical subject of laten; selectional restriction violated. "
                                          "Do not use for alignment-only analysis without caveat.")
            yield self.build_record(f"{base_id}_C", **shared, v_type="C",
                                    ungrammatical=ungram_c,
                                    ungram_source="selectional_restriction",
                                    alignment=True,
                                    crit_tokens=[np2[0], obj[0], v1[1], v2],
                                    notes="Type 3 causative laten: alignment restored by double reversal; "
                                          "selectional restriction still violated. "
                                          "Type 3 Variant C caveat applies.")
        else:
            # Perception V1 branch — do not change this code
            v2, v2_class = random.choice(TYPE3_V2_VERBS)
            obj          = random.choice(get_compatible_obj_v2(v2))
            v_chain  = [(v1_tuple, v1[1], v1_tuple[5]), (None, v2, v2_class)]
            gram     = f"{np1_form} {aux} {np2[0]} {obj[0]} {v1[1]} {v2} {time_adv}."
            ungram_a = f"{np1_form} {aux} {np2[0]} {obj[0]} {v2} {v1[1]} {time_adv}."
            ungram_b = f"{np1_form} {aux} {obj[0]} {np2[0]} {v1[1]} {v2} {time_adv}."
            ungram_c = f"{np1_form} {aux} {obj[0]} {np2[0]} {v2} {v1[1]} {time_adv}."

            shared = dict(
                n_pairs=n_pairs, c_type=self.c_type, grammatical=gram,
                embed="", np_chain=np_chain, v_chain=v_chain,
                v1_tense="infinitive", source="generated",
                v2_object=(obj[0], obj[1]),
            )
            # Type 3 B/C swap NP2 against obj (not NP1 against NP2), so crit_tokens
            # for B/C reflect the two positions that changed: NP2 and the v2_object.
            yield self.build_record(f"{base_id}_A", **shared, v_type="A",
                                    ungrammatical=ungram_a, ungram_source="verb_order", alignment=False,
                                    crit_tokens=[v1[1], v2])
            yield self.build_record(f"{base_id}_B", **shared, v_type="B",
                                    ungrammatical=ungram_b, ungram_source="selectional_restriction",
                                    alignment=False, crit_tokens=[np2[0], obj[0]],
                                    notes="Type 3 argument structure caveat: do not use for alignment-only analysis without caveat.")
            yield self.build_record(f"{base_id}_C", **shared, v_type="C",
                                    ungrammatical=ungram_c, ungram_source="selectional_restriction",
                                    alignment=True, crit_tokens=[np2[0], obj[0], v1[1], v2],
                                    notes="Alignment restored by double reversal; selectional restriction still violated. Type 3 Variant C caveat applies.")

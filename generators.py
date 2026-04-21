"""
generators.py — Concrete CSD generator subclasses for Types 1, 2, and 3.
"""

import random

from vocab import (
    V1_VERBS, V2_CHAIN_VERBS, NP1_POOL, NP2_POOL,
    TYPE3_V2_VERBS, DAT_EMBEDDINGS, OMDAT_EMBEDDINGS, TIME_ADVS,
    get_compatible_v2s, get_v2s_by_class, get_compatible_obj_v2,
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

    def _sample_npN(self, np_chain: list) -> tuple:
        """Return an NP entry for position 3+ (NP3, NP4, ...), excluding all
        NP forms already present in the chain."""
        taken = {np[0] for np in np_chain}
        pool  = [t for t in NP2_POOL if t[0] not in taken]
        return random.choice(pool)

    def _sample_v_terminal(self, prev_v_lemma: str, np_i: tuple) -> tuple[str, str]:
        """Return (infinitive, class) for the final verb in the chain (from V2_VERBS).
        prev_v_lemma: lemma of the immediately preceding verb, used to apply the
        voelen → change_of_state constraint.
        """
        if prev_v_lemma == "voelen":
            entry = random.choice(get_v2s_by_class(np_i[3], "change_of_state"))
        else:
            entry = random.choice(get_compatible_v2s(np_i[3]))
        return (entry[0], entry[2])

    def _sample_v_chain(self, np_i: tuple) -> tuple[str, str]:
        """Return (infinitive, class) for an intermediate chain verb (from V2_CHAIN_VERBS).
        np_i must be animate — enforced upstream by _sample_np2/npN.
        """
        entry = random.choice(V2_CHAIN_VERBS)
        return (entry[0], entry[5])

    # ------------------------------------------------------------------
    # Core generation
    # ------------------------------------------------------------------

    def generate_item(self, n_pairs: int, item_num: int):
        embed    = random.choice(self.embedding_pool)
        tense    = random.choices(["present", "past"], weights=[65, 35])[0]
        np1      = random.choice(NP1_POOL)
        v1_tuple = random.choices(self._verbs, weights=self._weights)[0]
        v1       = self.pick_v1_form(v1_tuple, tense, np1[1])

        # Build NP and verb chains iteratively.
        # v_chain entries: (v1_entry_or_None, surface_form, verb_class)
        # For i < n_pairs-1 (intermediate): verb is a chain verb from V2_CHAIN_VERBS.
        # For i == n_pairs-1 (final):       verb is a terminal verb from V2_VERBS.
        np_chain = [np1]
        v_chain  = [(v1_tuple, v1[1], v1_tuple[5])]

        for i in range(1, n_pairs):
            is_last = (i == n_pairs - 1)

            if i == 1:
                np_i = self._sample_np2(v1[0], np1, chain_continues=not is_last)
                if is_last:
                    v_raw = self._sample_v_terminal(v1[0], np_i)
                else:
                    v_raw = self._sample_v_chain(np_i)
            else:
                np_i      = self._sample_npN(np_chain)
                prev_lemma = v_chain[i - 1][1]  # infinitive == lemma for non-V1 slots
                if is_last:
                    v_raw = self._sample_v_terminal(prev_lemma, np_i)
                else:
                    v_raw = self._sample_v_chain(np_i)

            np_chain.append(np_i)
            v_chain.append((None, v_raw[0], v_raw[1]))

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

        can_b, ungram_source = self.can_generate_np_swap(np1, np_chain[1])
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
    """Type 1 (dat-clause) generator."""
    c_type         = 1
    embedding_pool = DAT_EMBEDDINGS
    v1_pool        = V1_VERBS
    v1_fractions   = {"zien": 0.24, "horen": 0.20, "voelen": 0.16, "laten": 0.20, "helpen": 0.20}


class Type2Generator(SubordinateGenerator):
    """Type 2 (omdat-clause) generator. laten excluded (causative, Type 1 only)."""
    c_type         = 2
    embedding_pool = OMDAT_EMBEDDINGS
    v1_pool        = V1_VERBS[:-1]
    v1_fractions   = {"zien": 0.32, "horen": 0.24, "voelen": 0.20, "helpen": 0.24}


class Type3Generator(CSDGenerator):
    """Type 3 (AcI matrix) generator.

    Sentence template: {NP1} heeft {NP2} {v2_object} {V1} {V2} {time_adv}.
    V1 always appears in infinitive form (IPP). Only n_pairs=2 is currently
    supported. All three variants (A, B, C) are always generated because
    v2_object is always inanimate, so the selectional restriction always applies.
    """
    c_type       = 3
    v1_pool      = V1_VERBS[:3]  # zien, horen, voelen only (perception verbs)
    v1_fractions = {"zien": 0.40, "horen": 0.40, "voelen": 0.20}

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
        v2, v2_class = random.choice(TYPE3_V2_VERBS)
        obj          = random.choice(get_compatible_obj_v2(v2))
        time_adv     = random.choice(TIME_ADVS)

        np_chain = [np1, np2]
        v_chain  = [(v1_tuple, v1[1], v1_tuple[5]), (None, v2, v2_class)]
        base_id  = f"{n_pairs}np_t{self.c_type}_{item_num:03d}"
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

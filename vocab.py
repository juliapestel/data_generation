"""
vocab.py — Controlled lexical resource for CSD minimal pair generation.
"""
# ---------------------------------------------------------------------------
# V1 VERBS
# Fields: (infinitive, present_3sg, past_3sg, past_3pl, past_participle, verb_class)
#
# verb_class encodes the semantic/syntactic type of the matrix verb,
# which determines construction type compatibility:
#   "perception"  → Types 1, 2, 3
#   "causative"   → Types 1
#
# IPP (Infinitivus Pro Participio): perception and causative verbs take
# bare infinitive rather than past participle in perfect constructions.
# This is marked in comments; the generator must handle this.
# ---------------------------------------------------------------------------

V1_VERBS = [
    # (infinitive, present_3sg, past_3sg, past_3pl, past_participle, verb_class)
    # Perception verbs — IPP applies in perfect
    ("zien",   "ziet",   "zag",    "zagen",   "gezien",   "perception"),
    ("horen",  "hoort",  "hoorde", "hoorden", "gehoord",  "perception"),
    # Causative verb — IPP applies; past participle form is identical
    # to infinitive ("laten"), not "gelaten", in IPP contexts
    ("laten",  "laat",   "liet",   "lieten",  "laten",    "causative"),
]

# ---------------------------------------------------------------------------
# NP1 POOL
# Fields: (form, number, noun_type)
# ---------------------------------------------------------------------------

NP1_POOL = [
    # (form, number, noun_type, gender)

    # Proper names — singular
    ("Jan",          "sg", "proper", "m"),
    ("Marie",        "sg", "proper", "f"),
    ("Piet",         "sg", "proper", "m"),
    ("Els",          "sg", "proper", "f"),
    # Common nouns — singular
    ("de leraar",    "sg", "common", None),
    ("de moeder",    "sg", "common", None),
    ("de danser",    "sg", "common", None),
    ("de agent",     "sg", "common", None),
    ("de dokter",    "sg", "common", None),
    ("de rechter",   "sg", "common", None),
    ("de vader",     "sg", "common", None),
    ("de directeur", "sg", "common", None),
    # Common nouns — plural
    ("de kinderen",  "pl", "common", None),
    ("de studenten", "pl", "common", None),
    ("de ouders",    "pl", "common", None),
    ("de vrienden",  "pl", "common", None),
]

# ---------------------------------------------------------------------------
# NP2 POOL
# Fields: (form, number, noun_type, animacy, gender)
# ---------------------------------------------------------------------------

NP2_POOL = [
    # (form, number, noun_type, animacy, gender)

    # Animate — proper names
    ("Jan",           "sg", "proper", "animate", "m"),
    ("Marie",         "sg", "proper", "animate", "f"),
    ("Piet",          "sg", "proper", "animate", "m"),
    # Animate — common nouns
    ("de kinderen",   "pl", "common", "animate", None),
    ("de studenten",  "pl", "common", "animate", None),
    ("de leraren",    "pl", "common", "animate", None),
    ("de ouders",     "pl", "common", "animate", None),
    ("de man",        "sg", "common", "animate", None),
    ("de vrouw",      "sg", "common", "animate", None),
    # Inanimate — common nouns
    ("de trein",      "sg", "common", "inanimate", None),
    ("de scooter",    "sg", "common", "inanimate", None),
    ("de auto",       "sg", "common", "inanimate", None),
    ("de bus",        "sg", "common", "inanimate", None),
    ("de fiets",      "sg", "common", "inanimate", None),
    ("de boot",       "sg", "common", "inanimate", None),
]

# ---------------------------------------------------------------------------
# V2 VERBS
# Fields: (infinitive, animacy_constraint, semantic_class)
#
# animacy_constraint is the selectional restriction on the logical subject
# of V2, which surfaces as NP2 in the CSD construction:
#   "animate"   → NP2 must be animate
#   "inanimate" → NP2 must be inanimate
#
# semantic_class groups verbs by meaning, which serves two purposes:
#   (1) Allows the generator to avoid semantically implausible combinations.
#   (2) Enables stratified sampling across semantic classes in the
#       final dataset, preventing over-representation of any one class.
# ---------------------------------------------------------------------------

V2_VERBS = [
    # (infinitive, animacy_constraint, semantic_class)

    # --- Animate-subject verbs ---
    # Motion
    ("lopen",      "animate",   "motion"),
    ("zwemmen",    "animate",   "motion"),
    ("rennen",     "animate",   "motion"),
    ("springen",   "animate",   "motion"),
    # Sound / expression
    ("lachen",     "animate",   "expression"),
    ("zingen",     "animate",   "expression"),
    # Activity
    ("werken",     "animate",   "activity"),
    ("spelen",     "animate",   "activity"),
    ("dansen",     "animate",   "activity"),

    # --- Inanimate-subject verbs ---
    # Motion
    ("rijden",     "inanimate", "motion"),
    ("bewegen",    "inanimate", "motion"),
    # Change-of-state
    ("vertrekken", "inanimate", "change_of_state"),
    ("stoppen",    "inanimate", "change_of_state"),
    ("stilstaan",  "inanimate", "change_of_state"),
]

# ---------------------------------------------------------------------------
# TYPE 3 TRANSITIVE V2 VERBS AND OBJ_V2 POOL
#
# In Type 3, V2 is a transitive verb taking OBJ_V2 as its direct object.
# NP2 is the logical subject of V2.
# OBJ_V2 is NOT part of the CSD chain and must not be swapped in any
# ungrammatical variant.
#
# V2 fields: (infinitive, semantic_class)
# OBJ_V2 fields: (form, number, compatible_v2s)
#
# compatible_v2s lists the V2 infinitives for which this OBJ_V2 is
# semantically plausible.
# ---------------------------------------------------------------------------

TYPE3_V2_VERBS = [
    # (infinitive, semantic_class)
    ("lopen",      "motion"),       # de marathon lopen, de ronde lopen
    ("rennen",     "motion"),       # de sprint rennen
    ("zwemmen",    "motion"),       # de race zwemmen, de baan zwemmen
    ("spelen",     "activity"),     # het stuk spelen, het liedje spelen
    ("zingen",     "activity"),     # het lied zingen
    ("uitlaten",   "activity"),     # de honden uitlaten
    ("lezen",      "activity"),     # het boek lezen
    ("schrijven",  "activity"),     # het rapport schrijven
    ("maken",      "activity"),     # de opdracht maken
    ("volgen",     "activity"),     # de les volgen
]

TYPE3_OBJ_V2_POOL = [
    # (form, number, compatible_v2s)
    ("de marathon",  "sg", ["lopen", "rennen", "zwemmen"]),
    ("de wedstrijd", "sg", ["lopen", "rennen", "zwemmen", "spelen"]),
    ("de sprint",    "sg", ["lopen", "rennen"]),
    ("het stuk",     "sg", ["spelen", "schrijven", "creëren"]),
    ("het liedje",   "sg", ["zingen", "spelen", "fluiten"]),
    ("de honden",    "pl", ["uitlaten", "voeren"]),
    ("het boek",     "sg", ["lezen"]),
    ("de opdracht",  "sg", ["maken", "schrijven", "uitvoeren"]),
    ("de les",       "sg", ["volgen"]),
]


# ---------------------------------------------------------------------------
# V2_CHAIN_VERBS — verbs that can occupy intermediate positions in a 3-NP+
# chain (i.e. the V2 slot in NP1 NP2 NP3 V1 V2 V3). These take the preceding
# NP as their logical subject and the following NP as their object/argument,
# and embed a further infinitive complement. They are a subset of V1_VERBS.
# ---------------------------------------------------------------------------

V2_CHAIN_VERBS = [
    ("zien",   "ziet",   "zag",    "zagen",   "gezien",   "perception"),
    ("horen",  "hoort",  "hoorde", "hoorden", "gehoord",  "perception"),
    ("helpen", "helpt",  "hielp",  "hielpen", "geholpen", "benefactive"),
    ("laten",  "laat",   "liet",   "lieten",  "laten",    "causative"),
    # laten is included here because it is the only causative chain verb,
    # required for the perception → causative transition. Stacked causatives
    # (liet laten) are prevented by the same-lemma filter in _sample_v_chain,
    # and causative → causative is blocked by V2_CHAIN_ALLOWED_AFTER.
]

# ---------------------------------------------------------------------------
# V2_CHAIN_ALLOWED_AFTER — permitted verb-class transitions for intermediate
# (non-terminal) chain verbs in 3-NP+ constructions.
#
# Each verb in the cluster takes the following verb as its complement, so
# semantic scope is strictly right-to-left. Constraints:
#   perception → perception : blocked (stacked perception is unnatural)
#   perception → benefactive: blocked (horen helpen is unnatural)
#   perception → causative  : allowed (zag laten)
#   benefactive→ perception : blocked for now (low naturalness)
#   benefactive→ causative  : blocked (marginal)
#   causative  → perception : allowed (liet zien, liet horen)
#   causative  → benefactive: blocked (marginal)
#   causative  → causative  : blocked (stacked causatives degraded)
#
# Only two transitions are currently permitted:
#   perception → causative
#   causative  → perception
# ---------------------------------------------------------------------------

V2_CHAIN_ALLOWED_AFTER = {
    "perception":  ["causative"],
    "causative":   ["perception"],
    "benefactive": [],  # benefactive cannot appear as V1 in a 3-NP chain under current constraints
}


# ---------------------------------------------------------------------------
# COMPATIBILITY FUNCTIONS
# ---------------------------------------------------------------------------

def get_compatible_v2s(np2_animacy: str) -> list[tuple]:
    """
    Return a list of (infinitive, animacy_constraint, semantic_class) tuples
    whose animacy_constraint is compatible with the given NP2 animacy value
    ("animate" or "inanimate"). V2s marked "any" are always included.
    """
    return [
        (verb, constraint, sem_cls) for verb, constraint, sem_cls in V2_VERBS
        if constraint == np2_animacy or constraint == "any"
    ]


def get_v2s_by_class(np2_animacy: str, semantic_class: str) -> list[tuple]:
    """
    Return V2 tuples filtered by both animacy compatibility and semantic class.
    Useful for stratified sampling.
    """
    return [
        (verb, constraint, sem_cls) for verb, constraint, sem_cls in V2_VERBS
        if (constraint == np2_animacy or constraint == "any")
        and sem_cls == semantic_class
    ]


def get_compatible_obj_v2(v2_infinitive: str) -> list[tuple]:
    """
    Return all OBJ_V2 entries compatible with a given transitive V2 as
    (form, number) tuples.
    """
    return [
        (form, number) for form, number, compatible in TYPE3_OBJ_V2_POOL
        if v2_infinitive in compatible
    ]


def has_male_name_adjacency(np_sequence: list[tuple]) -> bool:
    """
    Return True if any two adjacent NPs in the sequence are both proper names
    with gender == "m". Such adjacencies are blocked because Dutch male name
    pairs (e.g. Piet Jan, Jan Piet) can be misread as hyphenated double-barrelled
    names, introducing a parsing ambiguity in the stimulus.

    np_sequence: ordered list of NP tuples from NP1_POOL or NP2_POOL.
    Gender is at index 4 for NP2_POOL entries and index 3 for NP1_POOL entries.
    To handle both, access gender as the last element of the tuple.
    """
    for i in range(len(np_sequence) - 1):
        g1 = np_sequence[i][-1]
        g2 = np_sequence[i + 1][-1]
        if g1 == "m" and g2 == "m":
            return True
    return False


# ---------------------------------------------------------------------------
# TIME ADVERBS — Type 3 only
# ---------------------------------------------------------------------------

TIME_ADVS = [
    "vanochtend",
    "vanmiddag",
    "vanavond",
    "afgelopen weekend",
    "vorig weekend",
    "afgelopen week",
    "vorige week",
    "afgelopen jaar",
    "vorig jaar",
    "gisteren",
]

# ---------------------------------------------------------------------------
# EMBEDDING PHRASES
# ---------------------------------------------------------------------------

DAT_EMBEDDINGS = [
    "Ik weet dat",
    "Hij weet dat",
    "Ze weten dat",
    "Ik denk dat",
    "Ze zegt dat",
    "Hij gelooft dat",
    "We zien dat",
    "Ik merk dat",
    "Ze begrijpen dat",
    "Hij verwacht dat",
]

OMDAT_EMBEDDINGS = [
    "Hij schrikt omdat", 
    "Ze lacht omdat",
    "Hij begrijpt het omdat", 
    "Ze stopt omdat", 
    "Hij wacht omdat", 
    "Hij vertrekt omdat", 
    "Ze blijft staan omdat",
    "Hij roept omdat",
    "Ze aarzelt omdat",
    "Hij kijkt op omdat", 
]
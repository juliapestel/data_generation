V1_VERBS = [
    # (infinitive, present_3sg, past_3sg, past_participle, class)
    ("zien",   "ziet",   "zag",    "gezien",   "perception"),
    ("horen",  "hoort",  "hoorde", "gehoord",  "perception"),
    ("voelen", "voelt",  "voelde", "gevoeld",  "perception"),
    ("helpen", "helpt",  "hielp",  "geholpen", "benefactive"),
    ("laten",  "laat",   "liet",   "laten",    "causative"),
    # Note: laten keeps its infinitive form in the perfect (IPP effect)
]

# NP1 pool: (form, number, type)
NP1_POOL = [
    ("Jan",          "sg", "proper"),
    ("Marie",        "sg", "proper"),
    ("Piet",         "sg", "proper"),
    ("Els",          "sg", "proper"),
    ("de leraar",    "sg", "common"),
    ("de moeder",    "sg", "common"),
    ("de coach",     "sg", "common"),
    ("de agent",     "sg", "common"),
    ("de kinderen",  "pl", "common"),
    ("de studenten", "pl", "common"),
]

NP2_POOL = [
    # Animate — Variant A only
    ("Jan",           "sg", "proper",  "animate"),
    ("Marie",         "sg", "proper",  "animate"),
    ("de kinderen",   "pl", "common",  "animate"),
    ("de studenten",  "pl", "common",  "animate"),
    # Inanimate — all variants valid
    ("de trein",      "sg", "common",  "inanimate"),
    ("de bal",        "sg", "common",  "inanimate"),
    ("de auto",       "sg", "common",  "inanimate"),
    ("het vliegtuig", "sg", "common",  "inanimate"),
]

# NP2 pool with compatible V2s pre-validated
NP2_V2_COMPATIBILITY = {
    "de kinderen":   ["zwemmen", "lopen", "lachen", "huilen", "slapen",
                       "zingen", "spelen", "springen"],
    "de leerlingen": ["werken",  "lopen", "lachen", "slapen", "zingen",
                       "spelen", "zwemmen"],
    "de atleet":     ["lopen",   "zwemmen", "fietsen", "rennen",
                       "springen", "duiken"],
    "de zwemmer":    ["zwemmen", "duiken",  "springen", "lopen"],
    "Jan":           ["lopen",   "lachen",  "huilen",   "werken",
                       "zingen",  "zwemmen", "fietsen",  "dansen"],
    "Marie":         ["lopen",   "lachen",  "huilen",   "werken",
                       "zingen",  "zwemmen", "dansen",   "zwaaien"],
    "Piet":          ["lopen",   "lachen",  "werken",   "zwemmen",
                       "fietsen", "rennen"],
    "de vrouw":      ["lopen",   "lachen",  "huilen",   "werken",
                       "zingen",  "dansen",  "zwaaien"],
    "de man":        ["lopen",   "lachen",  "werken",   "zwemmen",
                       "fietsen", "zingen"],
    "de baby":       ["lachen",  "huilen",  "slapen",   "spelen"],
    "de hond":       ["lopen",   "blaffen", "spelen",   "zwemmen",
                       "springen"],
    "de studenten":  ["werken",  "lachen",  "lopen",    "zingen",
                       "fietsen"],
    "de trein":      ["vertrekken",  "stoppen",  "stilstaan", "rijden", "wachten"],
    "de bal":        ["rollen",  "stuiteren",  "vallen"],
    "de auto":       ["vertrekken",  "stoppen",  "stilstaan", "rijden"],
    "het vliegtuig": ["vertrekken",  "vliegen", "staan", "wachten"],
}

# V2 full list (for reference/validation)
V2_VERBS = sorted({
    v2
    for v2_list in NP2_V2_COMPATIBILITY.values()
    for v2 in v2_list
})

# Embedding phrases for Type 1 (dat) and Type 4 (laten in dat)
DAT_EMBEDDINGS = [
    "Ik weet dat",
    "Hij weet dat",
    "Ze weten dat",
    "Ik denk dat",
    "Ze zegt dat",
]

# Embedding phrases for Type 2 (omdat)
OMDAT_EMBEDDINGS = [
    "Hij schrok omdat",
    "Ze lachte omdat",
    "Hij begreep het omdat",
    "Ze stopte omdat",
    "Hij wachtte omdat",
]

# Subjects for Type 3 (AcI matrix clause)
# These are NOT NP1 in the CSD sense; they are the matrix subject
ACI_MATRIX_SUBJECTS = [
    "Oscar",
    "De trainer",
    "De rechter",
    "Mijn vader",
    "De coach",
]
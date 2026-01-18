from __future__ import annotations

import re
import unicodedata
from typing import List, Set

## Normalizacija ###

def normalize_key(text: str) -> str:
    text = (text or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s_-]", "", text)
    text = re.sub(r"\s+", " ", text).strip().replace(" ", "_")
    return text


SYNONYMS = {
    "paradajz": "rajcica",
    "tomato": "rajcica",
    "rice": "riza",
    "onion": "luk",
    "garlic": "cesnjak",
    "krompir": "krumpir",
    "orasi": "orah",
}

def canonicalize_key(key: str) -> str:
    return SYNONYMS.get(key, key)


### Detekcija alergena  ###

ALLERGEN_RULES = {
    "orasasti_plodovi": {
        "orah", "orasi", "badem", "badam", "ljesnjak", "lješnjak",
        "kikiriki", "pistacija", "indijski_orascic", "indijski_orascici",
        "ljesnjaci", "lješnjaci"
    },
    "mlijeko": {
        "mlijeko", "sir", "vrhnje", "maslac", "jogurt", "kefir", "skuta"
    },
    "jaja": {"jaje", "jaja"},
    "gluten": {"tjestenina", "kruh", "brasno", "pšenica", "psenica", "ječam", "jecam", "raž", "raz"},
    "soja": {"soja", "sojin_umak", "tofu"},
    "riba": {"riba", "tuna", "losos", "sardina", "inćun", "incun"},
}

def detect_allergens(ingredient_keys: List[str], ingredient_names: List[str]) -> List[str]:

    tokens: Set[str] = set(ingredient_keys)

    for n in ingredient_names:
        nk = normalize_key(n)
        parts = nk.split("_")
        tokens.update(parts)
        tokens.add(nk)

    found: Set[str] = set()
    for allergen, triggers in ALLERGEN_RULES.items():
        if tokens.intersection(triggers):
            found.add(allergen)

    return sorted(found)


def split_norm_csv(csv_text: str) -> List[str]:

    if not csv_text:
        return []
    return [
        canonicalize_key(normalize_key(x))
        for x in csv_text.split(",")
        if x.strip()
    ]

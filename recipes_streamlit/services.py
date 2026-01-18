from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from logic import canonicalize_key, normalize_key, detect_allergens, split_norm_csv


Doc = Dict[str, Any]
OID = Union[str, ObjectId]


def to_objectid(x: OID) -> ObjectId:
    if isinstance(x, ObjectId):
        return x
    return ObjectId(str(x))


def serialize_value(v: Any) -> Any:
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, datetime):

        return v
    if isinstance(v, list):
        return [serialize_value(i) for i in v]
    if isinstance(v, dict):
        return {k: serialize_value(val) for k, val in v.items()}
    return v


def serialize_doc(d: Doc) -> Doc:
    return serialize_value(d)


### Login i Register ###

def login(db, username: str, password: str) -> Tuple[Optional[Doc], Optional[str]]:
    users = db["users"]
    user = users.find_one({"username": username})
    if not user:
        return None, "Korisnik ne postoji."
    if password != user.get("password", ""):
        return None, "Pogrešna lozinka."
    return user, None


def register(db, username: str, password: str, display_name: str) -> Tuple[Optional[Doc], Optional[str]]:
    users = db["users"]
    doc = {
        "username": username,
        "display_name": display_name or username,
        "password": password, 
        "created_at": datetime.utcnow(),
    }
    try:
        res = users.insert_one(doc)
    except DuplicateKeyError:
        return None, "Username već postoji."
    return users.find_one({"_id": res.inserted_id}), None



### Recepti ###

def create_recipe(
    db,
    user_id: ObjectId,
    title: str,
    description: str,
    ingredients_input: List[Doc],
    steps: List[str],) -> Tuple[ObjectId, List[str], List[str]]:
    recipes = db["recipes"]

    ingredients: List[Doc] = []
    keys: List[str] = []
    names: List[str] = []

    for ing in ingredients_input:
        nm = (ing.get("name") or "").strip()
        if not nm:
            continue
        names.append(nm)
        k = canonicalize_key(normalize_key(nm))
        ingredients.append({
            "name": nm,
            "key": k,
            "qty": ing.get("qty", None),
            "unit": ing.get("unit", None) or None,
        })
        if k:
            keys.append(k)

    if not ingredients:
        raise ValueError("Nema sastojaka.")

    ingredient_keys = sorted(set(keys))
    allergens = detect_allergens(ingredient_keys, names)

    doc = {
        "author_id": user_id,
        "title": title.strip(),
        "description": (description or "").strip(),
        "ingredients": ingredients,
        "ingredient_keys": ingredient_keys,
        "steps": steps,
        "allergens": allergens,
        "created_at": datetime.utcnow(),
    }
    rid = recipes.insert_one(doc).inserted_id
    return rid, ingredient_keys, allergens


def list_my_recipes(db, user_id: ObjectId, limit: int = 50) -> List[Doc]:
    cur = db["recipes"].find({"author_id": user_id}).sort("created_at", -1).limit(int(limit))
    return list(cur)


### PIPELINE ###
def _recipe_enrich_pipeline(
    base_match: Optional[Dict[str, Any]] = None,
    limit: int = 50,
    extra_stages: Optional[List[Dict[str, Any]]] = None,
    include_match_fields: bool = False,
):
    pipeline: List[Dict[str, Any]] = []
    if base_match:
        pipeline.append({"$match": base_match})

    if extra_stages:
        pipeline.extend(extra_stages)

    project = {
        "_id": 1,
        "title": 1,
        "ingredient_keys": 1,
        "allergens": 1,
        "created_at": 1,
        "author_username": "$author.username",
        "author_display_name": "$author.display_name",
        "save_count": 1,
        "comment_count": 1,
    }
    if include_match_fields:
        project["match_count"] = 1
        project["match_keys"] = 1

    pipeline += [
        {"$lookup": {"from": "saves", "localField": "_id", "foreignField": "recipe_id", "as": "saves"}},
        {"$addFields": {"save_count": {"$size": "$saves"}}},

        {"$lookup": {"from": "comments", "localField": "_id", "foreignField": "recipe_id", "as": "comments"}},
        {"$addFields": {"comment_count": {"$size": "$comments"}}},

        {"$lookup": {"from": "users", "localField": "author_id", "foreignField": "_id", "as": "author"}},
        {"$unwind": {"path": "$author", "preserveNullAndEmptyArrays": True}},

        {"$project": project},
        {"$sort": {"created_at": -1}},
        {"$limit": int(limit)},
    ]
    return pipeline


def list_all_recipes_enriched(db, username: str = "", limit: int = 50) -> List[Doc]:
    base_match = None
    if username.strip():
        u = db["users"].find_one({"username": username.strip()})
        if not u:
            return []
        base_match = {"author_id": u["_id"]}

    pipeline = _recipe_enrich_pipeline(base_match=base_match, limit=limit)
    return list(db["recipes"].aggregate(pipeline))


def search_by_ingredients_enriched(
    db,
    inc_csv: str = "",
    any_csv: str = "",
    exc_csv: str = "",
    exa_csv: str = "",
    limit: int = 50
) -> List[Doc]:
    filters: List[Dict[str, Any]] = []
    inc = split_norm_csv(inc_csv)
    anyk = split_norm_csv(any_csv)
    exc = split_norm_csv(exc_csv)
    exa = split_norm_csv(exa_csv)

    if inc:
        filters.append({"ingredient_keys": {"$all": inc}})
    if anyk:
        filters.append({"ingredient_keys": {"$in": anyk}})
    if exc:
        filters.append({"ingredient_keys": {"$nin": exc}})
    if exa:
        filters.append({"allergens": {"$nin": exa}})

    if not filters:
        q = {}
    elif len(filters) == 1:
        q = filters[0]
    else:
        q = {"$and": filters}

    pipeline = _recipe_enrich_pipeline(base_match=q if q else None, limit=limit)
    return list(db["recipes"].aggregate(pipeline))


def pantry_ranked_search_enriched(
    db,
    pantry_csv: str,
    min_match: int = 1,
    exa_csv: str = "",
    limit: int = 50
) -> List[Doc]:
    pantry_keys = sorted(set(split_norm_csv(pantry_csv)))

    extra: List[Dict[str, Any]] = []

    exa = split_norm_csv(exa_csv)
    if exa:
        extra.append({"$match": {"allergens": {"$nin": exa}}})

    extra += [
        {"$addFields": {"match_keys": {"$setIntersection": ["$ingredient_keys", pantry_keys]}}},
        {"$addFields": {"match_count": {"$size": "$match_keys"}}},
        {"$match": {"match_count": {"$gte": int(min_match)}}},
        {"$sort": {"match_count": -1, "created_at": -1}},
    ]

    pipeline = _recipe_enrich_pipeline(
        base_match=None,
        limit=limit,
        extra_stages=extra,
        include_match_fields=True
    )
    return list(db["recipes"].aggregate(pipeline))



# Saves ###

def get_saved_recipe_ids(db, user_id: ObjectId) -> Set[ObjectId]:
    cur = db["saves"].find({"user_id": user_id}, {"recipe_id": 1})
    return {d["recipe_id"] for d in cur}


def save_recipe(db, user_id: ObjectId, recipe_id: OID) -> Tuple[bool, str]:
    try:
        rid = to_objectid(recipe_id)
    except Exception:
        return False, "Neispravan recipe id."

    recipes = db["recipes"]
    saves = db["saves"]

    r = recipes.find_one({"_id": rid}, {"title": 1})
    if not r:
        return False, "Ne postoji recept s tim id-om."

    doc = {"user_id": user_id, "recipe_id": rid, "created_at": datetime.utcnow()}
    try:
        saves.insert_one(doc)
        return True, f"Spremljeno: {r.get('title')}"
    except DuplicateKeyError:
        return False, "Već si spremio/la ovaj recept."


def unsave_recipe(db, user_id: ObjectId, recipe_id: OID) -> Tuple[bool, str]:
    try:
        rid = to_objectid(recipe_id)
    except Exception:
        return False, "Neispravan recipe id."

    res = db["saves"].delete_one({"user_id": user_id, "recipe_id": rid})
    if res.deleted_count:
        return True, "Uklonjeno iz spremljenih."
    return False, "Taj recept nije bio spremljen."



def list_saved_recipes(db, user_id: ObjectId, limit: int = 50) -> List[Doc]:
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$sort": {"created_at": -1}},
        {"$lookup": {"from": "recipes", "localField": "recipe_id", "foreignField": "_id", "as": "recipe"}},
        {"$unwind": {"path": "$recipe", "preserveNullAndEmptyArrays": False}},
        {"$lookup": {"from": "users", "localField": "recipe.author_id", "foreignField": "_id", "as": "author"}},
        {"$unwind": {"path": "$author", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 0,
            "saved_at": "$created_at",
            "recipe_id": "$recipe._id",
            "title": "$recipe.title",
            "author_username": "$author.username",
            "allergens": "$recipe.allergens",
            "ingredient_keys": "$recipe.ingredient_keys"
        }},
        {"$limit": int(limit)}
    ]
    return list(db["saves"].aggregate(pipeline))


def save_count(db, recipe_id: OID) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    rid = to_objectid(recipe_id)
    r = db["recipes"].find_one({"_id": rid}, {"title": 1})
    if not r:
        return None, None, "Ne postoji recept s tim id-om."
    n = db["saves"].count_documents({"recipe_id": rid})
    return r.get("title"), n, None



### Comments ###

def add_comment(db, user_id: ObjectId, recipe_id: OID, text: str) -> Tuple[bool, str]:
    rid = to_objectid(recipe_id)
    recipes = db["recipes"]
    comments = db["comments"]

    r = recipes.find_one({"_id": rid}, {"title": 1})
    if not r:
        return False, "Ne postoji recept s tim id-om."

    text = (text or "").strip()
    if not text:
        return False, "Komentar ne smije biti prazan."

    comments.insert_one({
        "recipe_id": rid,
        "user_id": user_id,
        "text": text,
        "created_at": datetime.utcnow(),
    })
    return True, f"Komentar dodan na: {r.get('title')}"


def list_comments_for_recipe(db, recipe_id: OID, limit: int = 100) -> Tuple[Optional[str], List[Doc], Optional[str]]:
    rid = to_objectid(recipe_id)
    recipes = db["recipes"]
    r = recipes.find_one({"_id": rid}, {"title": 1})
    if not r:
        return None, [], "Ne postoji recept s tim id-om."

    pipeline = [
        {"$match": {"recipe_id": rid}},
        {"$sort": {"created_at": -1}},
        {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "_id", "as": "author"}},
        {"$unwind": {"path": "$author", "preserveNullAndEmptyArrays": True}},
        {"$project": {"text": 1, "created_at": 1, "author_username": "$author.username"}},
        {"$limit": int(limit)},
    ]
    results = list(db["comments"].aggregate(pipeline))
    return r.get("title"), results, None

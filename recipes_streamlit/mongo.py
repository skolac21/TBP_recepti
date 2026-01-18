from __future__ import annotations

import os
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

load_dotenv()

def get_db():
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB_NAME", "recipes_app")
    client = MongoClient(uri)
    db = client[db_name]
    db.command("ping")
    return db

def ensure_indexes(db):
    users = db["users"]
    recipes = db["recipes"]
    saves = db["saves"]
    comments = db["comments"]

    users.create_index([("username", ASCENDING)], unique=True)

    recipes.create_index([("author_id", ASCENDING)])
    recipes.create_index([("created_at", ASCENDING)])
    recipes.create_index([("ingredient_keys", ASCENDING)])
    recipes.create_index([("allergens", ASCENDING)])

    saves.create_index([("user_id", 1), ("recipe_id", 1)], unique=True)
    saves.create_index([("recipe_id", 1)])
    saves.create_index([("user_id", 1), ("created_at", -1)])

    comments.create_index([("recipe_id", 1), ("created_at", -1)])
    comments.create_index([("user_id", 1), ("created_at", -1)])

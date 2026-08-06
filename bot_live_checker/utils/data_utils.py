import json
import os
from config import DATA_FILE, TOKEN_POOL_FILE

def load_all_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_all_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_user_data(user_id: str) -> dict:
    data = load_all_data()
    if user_id not in data:
        data[user_id] = {
            "name": "",
            "fb_targets": [],
            "ig_targets": [],
            "tiktok_targets": []
        }
        save_all_data(data)
    else:
        # Backwards compatibility migration
        u_data = data[user_id]
        if "fb_targets" not in u_data: u_data["fb_targets"] = []
        if "ig_targets" not in u_data:
            u_data["ig_targets"] = u_data.pop("instagram_targets", [])
        if "tiktok_targets" not in u_data: u_data["tiktok_targets"] = []
        data[user_id] = u_data
        save_all_data(data)
    return data[user_id]

def update_user_data(user_id: str, user_data: dict):
    data = load_all_data()
    data[user_id] = user_data
    save_all_data(data)

def load_token_pool():
    if not os.path.exists(TOKEN_POOL_FILE):
        os.makedirs(os.path.dirname(TOKEN_POOL_FILE), exist_ok=True)
        with open(TOKEN_POOL_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    try:
        with open(TOKEN_POOL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_token_pool(tokens):
    os.makedirs(os.path.dirname(TOKEN_POOL_FILE), exist_ok=True)
    with open(TOKEN_POOL_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2)

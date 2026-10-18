import json
import os
import uuid
import random
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_FILE = 'leaderboard.json'
SAVES_FILE = 'saved_games.json'
CONFIG_FILE = 'app_config.json'


def _load_json(filename: str, default_data: Any) -> Any:
    if not os.path.exists(filename):
        return default_data
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default_data


def _save_json(filename: str, data: Any):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {filename}: {e}")


# Profile & Settings Management

def get_last_username() -> str:
    cfg = _load_json(CONFIG_FILE, {"last_username": "Player 1", "recent_profiles": ["Player 1"]})
    return cfg.get("last_username", "Player 1")


def save_last_username(username: str):
    username = username.strip() or "Player"
    cfg = _load_json(CONFIG_FILE, {"last_username": "Player 1", "recent_profiles": []})
    cfg["last_username"] = username
    recent = cfg.get("recent_profiles", [])
    if username not in recent:
        recent.insert(0, username)
        cfg["recent_profiles"] = recent[:8]  # keep top 8
    _save_json(CONFIG_FILE, cfg)


def get_recent_profiles() -> List[str]:
    cfg = _load_json(CONFIG_FILE, {"last_username": "Player 1", "recent_profiles": ["Player 1"]})
    return cfg.get("recent_profiles", ["Player 1"])


def generate_guest_name() -> str:
    return f"Guest_{random.randint(1000, 9999)}"


# Leaderboard Management (Multi-Category)

def save_pve_score(username: str, turns: int, time_left: int, undos: int, difficulty: str = "normal", is_guest: bool = False) -> str:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}})
    record_id = str(uuid.uuid4())[:8]
    clean_name = username.strip() or ("Guest" if is_guest else "Player")
    record = {
        "id": record_id,
        "username": clean_name,
        "is_guest": is_guest or clean_name.lower().startswith("guest"),
        "turns": turns,
        "time_left": time_left,
        "undos": undos,
        "difficulty": difficulty.capitalize(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    db["pve"].append(record)
    _save_json(DB_FILE, db)

    if not is_guest and clean_name:
        save_last_username(clean_name)

    return record_id


def get_pve_leaderboard(sort_by: str = "turns", difficulty: str = "all") -> List[Dict[str, Any]]:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}})
    records = db.get("pve", [])

    # Filter by difficulty category
    diff_filter = difficulty.strip().lower()
    if diff_filter != "all":
        records = [r for r in records if r.get("difficulty", "").lower() == diff_filter]

    # Sort by metric
    if sort_by == "turns":
        # Lowest turns first, then highest time remaining, then lowest undos
        return sorted(records, key=lambda x: (x.get("turns", 9999), -x.get("time_left", 0), x.get("undos", 9999)))
    elif sort_by == "time":
        # Fastest time remaining (most time left) first, then lowest turns
        return sorted(records, key=lambda x: (-x.get("time_left", 0), x.get("turns", 9999), x.get("undos", 9999)))
    elif sort_by == "undos":
        # Fewest undos first, then lowest turns, then most time left
        return sorted(records, key=lambda x: (x.get("undos", 9999), x.get("turns", 9999), -x.get("time_left", 0)))
    return records


def delete_pve_score(record_id: str) -> bool:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}})
    records = db.get("pve", [])
    new_records = [r for r in records if r.get("id") != record_id]
    if len(new_records) != len(records):
        db["pve"] = new_records
        _save_json(DB_FILE, db)
        return True
    return False


def clear_pve_leaderboard(difficulty: str = "all"):
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}})
    diff_filter = difficulty.strip().lower()
    if diff_filter == "all":
        db["pve"] = []
    else:
        db["pve"] = [r for r in db.get("pve", []) if r.get("difficulty", "").lower() != diff_filter]
    _save_json(DB_FILE, db)


def update_pvp_stats(username: str, won: bool):
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}})
    username = username.strip() or "Player"
    stats = db["pvp"].get(username, {"wins": 0, "losses": 0, "last_played": ""})
    if won:
        stats["wins"] += 1
    else:
        stats["losses"] += 1
    stats["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    db["pvp"][username] = stats
    _save_json(DB_FILE, db)


def get_pvp_stats() -> Dict[str, Dict[str, Any]]:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}})
    return db.get("pvp", {})


def delete_pvp_player(username: str) -> bool:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}})
    if username in db.get("pvp", {}):
        del db["pvp"][username]
        _save_json(DB_FILE, db)
        return True
    return False


def clear_pvp_stats():
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}})
    db["pvp"] = {}
    _save_json(DB_FILE, db)


# Mid-game PvE Save Slots Management

def save_game_slot(slot_id: str, slot_name: str, payload: Dict[str, Any]):
    saves = _load_json(SAVES_FILE, {})
    payload["slot_id"] = slot_id
    payload["slot_name"] = slot_name
    payload["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    saves[slot_id] = payload
    _save_json(SAVES_FILE, saves)


def get_saved_slots() -> Dict[str, Dict[str, Any]]:
    return _load_json(SAVES_FILE, {})


def load_game_slot(slot_id: str) -> Optional[Dict[str, Any]]:
    saves = _load_json(SAVES_FILE, {})
    return saves.get(slot_id)


def delete_game_slot(slot_id: str) -> bool:
    saves = _load_json(SAVES_FILE, {})
    if slot_id in saves:
        del saves[slot_id]
        _save_json(SAVES_FILE, saves)
        return True
    return False
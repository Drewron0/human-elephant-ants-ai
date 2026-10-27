import json
import os
import uuid
import random
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_FILE = 'leaderboard.json'
SAVES_FILE = 'saved_games.json'
CONFIG_FILE = 'app_config.json'
CUSTOM_STAGES_FILE = 'custom_stages.json'


def _load_json(filename: str, default_data: Any) -> Any:
    if not os.path.exists(filename):
        return default_data
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default_data


def _save_json(filename: str, data: Any) -> None:
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving {filename}: {e}")


# Profile & Account Management

def get_last_username() -> str:
    cfg = _load_json(CONFIG_FILE, {"last_username": "Player 1", "recent_profiles": ["Player 1"]})
    return cfg.get("last_username", "Player 1")


def save_last_username(username: str) -> None:
    username = username.strip() or "Player"
    cfg = _load_json(CONFIG_FILE, {"last_username": "Player 1", "recent_profiles": []})
    cfg["last_username"] = username
    recent = cfg.get("recent_profiles", [])
    if username not in recent:
        recent.insert(0, username)
        cfg["recent_profiles"] = recent[:10]
    _save_json(CONFIG_FILE, cfg)


def get_recent_profiles() -> List[str]:
    cfg = _load_json(CONFIG_FILE, {"last_username": "Player 1", "recent_profiles": ["Player 1"]})
    profiles = cfg.get("recent_profiles", ["Player 1"])
    return profiles if profiles else ["Player 1"]


def generate_guest_name() -> str:
    return f"Guest_{random.randint(1000, 9999)}"


# Multi-Category Leaderboard Management

def save_pve_score(username: str, turns: int, time_left: int, undos: int, difficulty: str = "normal", is_guest: bool = False) -> str:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
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
    db.setdefault("pve", []).append(record)
    _save_json(DB_FILE, db)

    if not is_guest and clean_name:
        save_last_username(clean_name)

    return record_id


def get_pve_leaderboard(sort_by: str = "turns", difficulty: str = "all") -> List[Dict[str, Any]]:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    records = db.get("pve", [])

    diff_filter = difficulty.strip().lower()
    if diff_filter != "all":
        records = [r for r in records if r.get("difficulty", "").lower() == diff_filter]

    if sort_by == "turns":
        return sorted(records, key=lambda x: (x.get("turns", 9999), -x.get("time_left", 0), x.get("undos", 9999)))
    elif sort_by == "time":
        return sorted(records, key=lambda x: (-x.get("time_left", 0), x.get("turns", 9999), x.get("undos", 9999)))
    elif sort_by == "undos":
        return sorted(records, key=lambda x: (x.get("undos", 9999), x.get("turns", 9999), -x.get("time_left", 0)))
    return records


def delete_pve_score(record_id: str) -> bool:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    records = db.get("pve", [])
    new_records = [r for r in records if r.get("id") != record_id]
    if len(new_records) != len(records):
        db["pve"] = new_records
        _save_json(DB_FILE, db)
        return True
    return False


def clear_pve_leaderboard(difficulty: str = "all") -> None:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    diff_filter = difficulty.strip().lower()
    if diff_filter == "all":
        db["pve"] = []
    else:
        db["pve"] = [r for r in db.get("pve", []) if r.get("difficulty", "").lower() != diff_filter]
    _save_json(DB_FILE, db)


# Per-Stage Puzzle Leaderboards

def save_stage_score(stage_id: str, username: str, steps: int, time_spent: int, undos: int, delay_margin: int, is_guest: bool = False) -> str:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    if "stages" not in db:
        db["stages"] = {}

    stage_records = db["stages"].setdefault(stage_id, [])
    record_id = str(uuid.uuid4())[:8]
    clean_name = username.strip() or ("Guest" if is_guest else "Player")
    record = {
        "id": record_id,
        "username": clean_name,
        "is_guest": is_guest or clean_name.lower().startswith("guest"),
        "steps": steps,
        "time_spent": time_spent,
        "undos": undos,
        "delay_margin": delay_margin,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    stage_records.append(record)
    _save_json(DB_FILE, db)

    if not is_guest and clean_name:
        save_last_username(clean_name)

    return record_id


def get_stage_leaderboard(stage_id: str) -> List[Dict[str, Any]]:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    records = db.get("stages", {}).get(stage_id, [])
    # Sort primarily by lowest steps, then lowest delay margin, then lowest undos, then time spent
    return sorted(records, key=lambda x: (
        x.get("steps", 9999),
        x.get("delay_margin", 9999),
        x.get("undos", 9999),
        x.get("time_spent", 9999)
    ))


def get_all_stage_leaderboards() -> Dict[str, List[Dict[str, Any]]]:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    return db.get("stages", {})


def clear_stage_leaderboard(stage_id: Optional[str] = None) -> None:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    if stage_id:
        if "stages" in db and stage_id in db["stages"]:
            del db["stages"][stage_id]
    else:
        db["stages"] = {}
    _save_json(DB_FILE, db)


# PvP Stats Management

def update_pvp_stats(username: str, won: bool, undos: int = 0) -> None:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    username = username.strip() or "Player"
    stats = db.setdefault("pvp", {}).get(username, {"wins": 0, "losses": 0, "undos": 0, "last_played": ""})
    if won:
        stats["wins"] += 1
    else:
        stats["losses"] += 1
    stats["undos"] = stats.get("undos", 0) + undos
    stats["last_played"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    db["pvp"][username] = stats
    _save_json(DB_FILE, db)


def get_pvp_stats() -> Dict[str, Dict[str, Any]]:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    return db.get("pvp", {})


def delete_pvp_player(username: str) -> bool:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    if username in db.get("pvp", {}):
        del db["pvp"][username]
        _save_json(DB_FILE, db)
        return True
    return False


def clear_pvp_stats() -> None:
    db = _load_json(DB_FILE, {"pve": [], "pvp": {}, "stages": {}})
    db["pvp"] = {}
    _save_json(DB_FILE, db)


# Mid-game PvE Save Slots

def save_game_slot(slot_id: str, slot_name: str, payload: Dict[str, Any]) -> None:
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


# Custom Stages Storage (CRUD)

def get_custom_stages() -> List[Dict[str, Any]]:
    return _load_json(CUSTOM_STAGES_FILE, [])


def save_custom_stage(stage_data: Dict[str, Any]) -> str:
    stages = _load_json(CUSTOM_STAGES_FILE, [])
    stage_id = stage_data.get("id") or f"custom_{str(uuid.uuid4())[:8]}"
    stage_data["id"] = stage_id
    stage_data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # If updating existing
    updated = False
    for i, s in enumerate(stages):
        if s.get("id") == stage_id:
            stages[i] = stage_data
            updated = True
            break
    if not updated:
        stages.append(stage_data)

    _save_json(CUSTOM_STAGES_FILE, stages)
    return stage_id


def delete_custom_stage(stage_id: str) -> bool:
    stages = _load_json(CUSTOM_STAGES_FILE, [])
    new_stages = [s for s in stages if s.get("id") != stage_id]
    if len(new_stages) != len(stages):
        _save_json(CUSTOM_STAGES_FILE, new_stages)
        return True
    return False

import json
import os

DB_FILE = 'leaderboard.json'

def _load_db():
    if not os.path.exists(DB_FILE):
        return {"pve": [], "pvp": {}}
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def _save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def save_pve_score(username, turns, time_left, undos):
    db = _load_db()
    db["pve"].append({
        "username": username,
        "turns": turns,
        "time_left": time_left,
        "undos": undos
    })
    _save_db(db)

def update_pvp_stats(username, won):
    db = _load_db()
    stats = db["pvp"].get(username, {"wins": 0, "losses": 0})
    if won:
        stats["wins"] += 1
    else:
        stats["losses"] += 1
    db["pvp"][username] = stats
    _save_db(db)

def get_leaderboard():
    return _load_db()
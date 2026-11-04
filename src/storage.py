"""JSON persistence for player profiles, leaderboards and custom stages."""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

TIMESTAMP_MINUTES = "%Y-%m-%d %H:%M"
TIMESTAMP_SECONDS = "%Y-%m-%d %H:%M:%S"
FALLBACK_NAME = "Player"


def _load_json(path: Path, default_data: Any) -> Any:
    """Read a JSON file; a corrupt file is kept aside instead of being overwritten."""
    try:
        with path.open(encoding="utf-8") as source:
            return json.load(source)
    except FileNotFoundError:
        return default_data
    except json.JSONDecodeError as error:
        backup = path.with_suffix(f"{path.suffix}.corrupt")
        logger.error("Corrupt data file %s (%s); moving it to %s", path, error, backup)
        os.replace(path, backup)
        return default_data
    except OSError as error:
        logger.error("Could not read %s: %s", path, error)
        return default_data


def _save_json(path: Path, data: Any) -> None:
    """Write JSON atomically so an interrupted save cannot damage existing data."""
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temp_path.open("w", encoding="utf-8") as target:
            json.dump(data, target, indent=4)
        os.replace(temp_path, path)
    except OSError as error:
        logger.error("Could not save %s: %s", path, error)


def _new_id() -> str:
    """Return a short unique record identifier."""
    return str(uuid.uuid4())[:8]


def _timestamp(fmt: str) -> str:
    """Return the current local time in the given format."""
    return datetime.now().strftime(fmt)


def _load_leaderboard() -> dict[str, Any]:
    """Load the leaderboard database."""
    data = _load_json(settings.LEADERBOARD_FILE, {"pve": [], "stages": {}})
    return data if isinstance(data, dict) else {"pve": [], "stages": {}}


def _load_profiles() -> dict[str, Any]:
    """Load the saved player profiles."""
    default_name = settings.DEFAULT_PLAYER_NAME
    data = _load_json(
        settings.APP_CONFIG_FILE,
        {"last_username": default_name, "recent_profiles": [default_name]},
    )
    return data if isinstance(data, dict) else {}


def get_last_username() -> str:
    """Return the most recently used player name."""
    return _load_profiles().get("last_username", settings.DEFAULT_PLAYER_NAME)


def save_last_username(username: str) -> None:
    """Remember a player name, newest first."""
    clean_name = username.strip() or FALLBACK_NAME
    profiles = _load_profiles()
    recent = [name for name in profiles.get("recent_profiles", []) if name != clean_name]
    profiles["last_username"] = clean_name
    profiles["recent_profiles"] = [clean_name, *recent][: settings.RECENT_PROFILE_LIMIT]
    _save_json(settings.APP_CONFIG_FILE, profiles)


def get_recent_profiles() -> list[str]:
    """Return recent player names for the profile picker."""
    return _load_profiles().get("recent_profiles") or [settings.DEFAULT_PLAYER_NAME]


def save_pve_score(username: str, turns: int, time_left: int, undos: int, difficulty: str) -> str:
    """Store a Versus-AI win and return its record id."""
    database = _load_leaderboard()
    clean_name = username.strip() or FALLBACK_NAME
    record: dict[str, Any] = {
        "id": _new_id(),
        "username": clean_name,
        "turns": turns,
        "time_left": time_left,
        "undos": undos,
        "difficulty": difficulty.capitalize(),
        "timestamp": _timestamp(TIMESTAMP_MINUTES),
    }
    database.setdefault("pve", []).append(record)
    _save_json(settings.LEADERBOARD_FILE, database)
    save_last_username(clean_name)
    return record["id"]


def get_pve_leaderboard(sort_by: str = "turns", difficulty: str = "all") -> list[dict[str, Any]]:
    """Return Versus-AI wins filtered by difficulty and sorted by the chosen metric."""
    records = _load_leaderboard().get("pve", [])
    difficulty_filter = difficulty.strip().lower()
    if difficulty_filter != "all":
        records = [r for r in records if r.get("difficulty", "").lower() == difficulty_filter]

    def fewest_turns(record: dict[str, Any]) -> tuple[int, int, int]:
        return (
            record.get("turns", 9999),
            -record.get("time_left", 0),
            record.get("undos", 9999),
        )

    def most_time(record: dict[str, Any]) -> tuple[int, int, int]:
        return (
            -record.get("time_left", 0),
            record.get("turns", 9999),
            record.get("undos", 9999),
        )

    def fewest_undos(record: dict[str, Any]) -> tuple[int, int, int]:
        return (
            record.get("undos", 9999),
            record.get("turns", 9999),
            -record.get("time_left", 0),
        )

    sort_keys = {"turns": fewest_turns, "time": most_time, "undos": fewest_undos}
    return sorted(records, key=sort_keys[sort_by]) if sort_by in sort_keys else records


def delete_pve_score(record_id: str) -> bool:
    """Delete one Versus-AI record; return whether it existed."""
    database = _load_leaderboard()
    records = database.get("pve", [])
    remaining = [record for record in records if record.get("id") != record_id]
    if len(remaining) == len(records):
        return False
    database["pve"] = remaining
    _save_json(settings.LEADERBOARD_FILE, database)
    return True


def clear_pve_leaderboard(difficulty: str = "all") -> None:
    """Delete Versus-AI records for one difficulty, or all of them."""
    database = _load_leaderboard()
    difficulty_filter = difficulty.strip().lower()
    if difficulty_filter == "all":
        database["pve"] = []
    else:
        database["pve"] = [
            r
            for r in database.get("pve", [])
            if r.get("difficulty", "").lower() != difficulty_filter
        ]
    _save_json(settings.LEADERBOARD_FILE, database)


def save_stage_score(
    stage_id: str,
    username: str,
    steps: int,
    time_spent: int,
    undos: int,
    delay_margin: int,
) -> str:
    """Store a puzzle clear and return its record id."""
    database = _load_leaderboard()
    clean_name = username.strip() or FALLBACK_NAME
    record: dict[str, Any] = {
        "id": _new_id(),
        "username": clean_name,
        "steps": steps,
        "time_spent": time_spent,
        "undos": undos,
        "delay_margin": delay_margin,
        "timestamp": _timestamp(TIMESTAMP_MINUTES),
    }
    database.setdefault("stages", {}).setdefault(stage_id, []).append(record)
    _save_json(settings.LEADERBOARD_FILE, database)
    save_last_username(clean_name)
    return record["id"]


def get_stage_leaderboard(stage_id: str) -> list[dict[str, Any]]:
    """Return a stage's records, best first."""
    records = _load_leaderboard().get("stages", {}).get(stage_id, [])
    return sorted(
        records,
        key=lambda record: (
            record.get("steps", 9999),
            record.get("delay_margin", 9999),
            record.get("undos", 9999),
            record.get("time_spent", 9999),
        ),
    )


def clear_stage_leaderboard(stage_id: str) -> None:
    """Delete all records belonging to a stage."""
    database = _load_leaderboard()
    if database.get("stages", {}).pop(stage_id, None) is not None:
        _save_json(settings.LEADERBOARD_FILE, database)


def get_custom_stages() -> list[dict[str, Any]]:
    """Return all stored custom stages."""
    data = _load_json(settings.CUSTOM_STAGES_FILE, [])
    return data if isinstance(data, list) else []


def save_custom_stage(stage_data: dict[str, Any]) -> str:
    """Create or replace a custom stage and return its id."""
    stages = get_custom_stages()
    stage_id = stage_data.get("id") or f"custom_{_new_id()}"
    stage_data["id"] = stage_id
    stage_data["updated_at"] = _timestamp(TIMESTAMP_SECONDS)
    for index, stage in enumerate(stages):
        if stage.get("id") == stage_id:
            stages[index] = stage_data
            break
    else:
        stages.append(stage_data)
    _save_json(settings.CUSTOM_STAGES_FILE, stages)
    return stage_id


def delete_custom_stage(stage_id: str) -> bool:
    """Delete a custom stage and its records; return whether it existed."""
    stages = get_custom_stages()
    remaining = [stage for stage in stages if stage.get("id") != stage_id]
    if len(remaining) == len(stages):
        return False
    _save_json(settings.CUSTOM_STAGES_FILE, remaining)
    clear_stage_leaderboard(stage_id)
    return True

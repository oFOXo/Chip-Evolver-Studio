"""
Save/Load state management for the chip generator.
Persists chips and evolution engine state to JSON.
"""

import json
import os
import time
from typing import Optional, List
from chip import Chip
from ai_evolution import EvolutionEngine

SAVE_DIR = os.path.join(os.path.dirname(__file__), "saves")
AUTOSAVE_FILE = os.path.join(SAVE_DIR, "autosave.json")
HALL_OF_FAME_FILE = os.path.join(SAVE_DIR, "hall_of_fame.json")


def ensure_save_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)


def save_state(chip: Chip, engine: EvolutionEngine, filename: str = None) -> str:
    ensure_save_dir()
    if filename is None:
        ts = int(time.time())
        filename = f"save_{ts}.json"
    filepath = os.path.join(SAVE_DIR, filename)
    data = {
        "version": 2,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "chip": chip.to_dict(),
        "engine": engine.to_dict(),
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    return filepath


def load_state(filename: str = None) -> Optional[dict]:
    ensure_save_dir()
    filepath = filename if os.path.isabs(filename or "") else os.path.join(SAVE_DIR, filename or "")
    if not os.path.exists(filepath):
        filepath = AUTOSAVE_FILE
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r") as f:
        data = json.load(f)
    return data


def autosave(chip: Chip, engine: EvolutionEngine):
    ensure_save_dir()
    data = {
        "version": 2,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "chip": chip.to_dict(),
        "engine": engine.to_dict(),
    }
    with open(AUTOSAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def has_autosave() -> bool:
    return os.path.exists(AUTOSAVE_FILE)


def list_saves() -> List[str]:
    ensure_save_dir()
    files = [
        f for f in os.listdir(SAVE_DIR)
        if f.endswith(".json") and f != "hall_of_fame.json"
    ]
    files.sort(reverse=True)
    return files


def add_to_hall_of_fame(chip: Chip):
    ensure_save_dir()
    hof: List[dict] = []
    if os.path.exists(HALL_OF_FAME_FILE):
        with open(HALL_OF_FAME_FILE, "r") as f:
            hof = json.load(f)
    hof.append(chip.to_dict())
    hof.sort(key=lambda c: c.get("fitness", 0), reverse=True)
    hof = hof[:20]
    with open(HALL_OF_FAME_FILE, "w") as f:
        json.dump(hof, f, indent=2)


def load_hall_of_fame() -> List[Chip]:
    if not os.path.exists(HALL_OF_FAME_FILE):
        return []
    with open(HALL_OF_FAME_FILE, "r") as f:
        data = json.load(f)
    return [Chip.from_dict(d) for d in data]


def delete_save(filename: str) -> bool:
    filepath = os.path.join(SAVE_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False

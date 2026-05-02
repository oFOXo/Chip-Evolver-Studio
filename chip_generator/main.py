"""
RISC-V & Novel Chip Generator — Flask Web Server
RL + Recursive AI Evolution | HTML5 Canvas 2D Pixel Art
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json
import copy
import threading
import time
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS

from chip import Chip, ChipType, UnitBlock, VALID_BIT_WIDTHS, CHIP_TYPE_COLORS, UNIT_COLORS
from ai_evolution import EvolutionEngine, MutationEngine, MUTATION_TYPES
from save_state import (
    save_state, load_state, autosave, has_autosave,
    list_saves, add_to_hall_of_fame, load_hall_of_fame
)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

state = {
    "chip": None,
    "engine": EvolutionEngine(population_size=8),
    "evolving": False,
    "evolution_log": [],
    "last_reward": 0.0,
}
state_lock = threading.Lock()


def chip_to_json(chip: Chip) -> dict:
    d = chip.to_dict()
    d["chip_type_color"] = CHIP_TYPE_COLORS.get(chip.chip_type, "#00ff88")
    return d


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chip_types")
def get_chip_types():
    return jsonify({
        "types": [ct.value for ct in ChipType],
        "bit_widths": VALID_BIT_WIDTHS,
        "unit_colors": UNIT_COLORS,
        "chip_type_colors": {ct.value: CHIP_TYPE_COLORS[ct] for ct in ChipType},
    })


@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json or {}
    ct_val = data.get("chip_type", "RISC-V")
    try:
        ct = ChipType(ct_val)
    except ValueError:
        ct = ChipType.RISCV

    bw = int(data.get("bit_width", 32))
    if bw not in VALID_BIT_WIDTHS:
        bw = 32
    cores = max(1, min(64, int(data.get("core_count", 1))))
    pipeline = max(2, min(32, int(data.get("pipeline_stages", 5))))
    cache = int(data.get("cache_kb", 64))

    chip = Chip(chip_type=ct, bit_width=bw, core_count=cores,
                pipeline_stages=pipeline, cache_kb=cache)
    chip.compute_fitness()

    with state_lock:
        state["chip"] = chip
        state["engine"] = EvolutionEngine(population_size=8)
        state["engine"].seed_population(copy.deepcopy(chip))
        state["evolution_log"] = []

    autosave(chip, state["engine"])
    return jsonify({"success": True, "chip": chip_to_json(chip)})


@app.route("/api/mutate_once", methods=["POST"])
def mutate_once():
    with state_lock:
        if state["chip"] is None:
            return jsonify({"error": "No chip generated"}), 400
        chip, desc, reward = state["engine"].evolve_step(
            float(request.json.get("strength", 1.0) if request.json else 1.0)
        )
        state["chip"] = chip
        state["last_reward"] = reward
        autosave(chip, state["engine"])
    return jsonify({
        "success": True,
        "chip": chip_to_json(chip),
        "desc": desc,
        "reward": reward,
        "log": state["engine"].evolution_log[-10:],
    })


@app.route("/api/evolve/start", methods=["POST"])
def evolve_start():
    with state_lock:
        if state["chip"] is None:
            return jsonify({"error": "No chip generated"}), 400
        if state["evolving"]:
            return jsonify({"error": "Already evolving"}), 400
        state["evolving"] = True

    data = request.json or {}
    steps = max(1, min(500, int(data.get("steps", 20))))
    strength = max(0.1, min(10.0, float(data.get("strength", 1.0))))

    def worker():
        for i in range(steps):
            with state_lock:
                if not state["evolving"]:
                    break
                chip, desc, reward = state["engine"].evolve_step(strength)
                state["chip"] = chip
                state["last_reward"] = reward
            time.sleep(0.01)

        with state_lock:
            state["evolving"] = False
            if state["chip"]:
                add_to_hall_of_fame(state["chip"])
                autosave(state["chip"], state["engine"])

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"success": True, "steps": steps})


@app.route("/api/evolve/stop", methods=["POST"])
def evolve_stop():
    with state_lock:
        state["evolving"] = False
    return jsonify({"success": True})


@app.route("/api/evolve/status")
def evolve_status():
    with state_lock:
        chip = state["chip"]
        evolving = state["evolving"]
        log = state["engine"].evolution_log[-15:]
        reward = state["last_reward"]
    return jsonify({
        "evolving": evolving,
        "chip": chip_to_json(chip) if chip else None,
        "log": log,
        "reward": reward,
        "epsilon": round(state["engine"].agent.epsilon, 4),
        "total_steps": state["engine"].agent.total_steps,
    })


@app.route("/api/save", methods=["POST"])
def save():
    data = request.json or {}
    name = data.get("name", "")
    filename = f"{name}.json" if name else None
    with state_lock:
        if state["chip"] is None:
            return jsonify({"error": "No chip"}), 400
        path = save_state(state["chip"], state["engine"], filename)
    return jsonify({"success": True, "path": os.path.basename(path)})


@app.route("/api/load", methods=["POST"])
def load():
    data = request.json or {}
    filename = data.get("filename", "autosave.json")
    loaded = load_state(filename)
    if not loaded:
        return jsonify({"error": "Save not found"}), 404
    chip = Chip.from_dict(loaded["chip"])
    engine = EvolutionEngine.from_dict(loaded["engine"])
    with state_lock:
        state["chip"] = chip
        state["engine"] = engine
    return jsonify({"success": True, "chip": chip_to_json(chip)})


@app.route("/api/saves")
def list_saves_route():
    saves = list_saves()
    return jsonify({"saves": saves})


@app.route("/api/hall_of_fame")
def hall_of_fame():
    hof = load_hall_of_fame()
    return jsonify({"chips": [chip_to_json(c) for c in hof]})


@app.route("/api/reset", methods=["POST"])
def reset():
    with state_lock:
        if state["chip"] is None:
            return jsonify({"error": "No chip"}), 400
        state["engine"] = EvolutionEngine(population_size=8)
        state["engine"].seed_population(copy.deepcopy(state["chip"]))
    return jsonify({"success": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Chip Generator on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

"""
RISC-V & Novel Chip Generator — Flask Web Server v2
RL + Recursive AI Evolution | Architecture Evolution | Novel Block Invention
Code Generation: Assembly / VHDL / Verilog
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import json, copy, threading, time
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

from chip import Chip, ChipType, UnitBlock, VALID_BIT_WIDTHS, CHIP_TYPE_COLORS, UNIT_COLORS
from ai_evolution import EvolutionEngine, MUTATION_TYPES
from architecture import (ChipArchitecture, ISA_TYPES, INTERCONNECTS, MEMORY_MODELS,
                           EXECUTION_MODELS, PIPELINE_ARCHS, VOLTAGE_DOMAINS,
                           PROCESS_NODES, CLOCK_TOPOLOGIES)
from novel_blocks import BlockRegistry, invent_block
from codegen import generate_assembly, generate_vhdl, generate_verilog
from save_state import (save_state, load_state, autosave, has_autosave,
                        list_saves, add_to_hall_of_fame, load_hall_of_fame)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

state = {
    "chip": None,
    "engine": EvolutionEngine(population_size=8),
    "evolving": False,
    "last_reward": 0.0,
}
state_lock = threading.Lock()


def chip_to_json(chip: Chip) -> dict:
    d = chip.to_dict()
    d["chip_type_color"] = CHIP_TYPE_COLORS.get(chip.chip_type, "#00ff88")
    d["novel_block_count"] = chip.novel_block_count()
    # attach architecture derived metrics if present
    if chip.architecture:
        d["architecture"] = chip.architecture
    return d


# ── Core routes ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/meta")
def get_meta():
    registry = BlockRegistry.get()
    return jsonify({
        "chip_types": [ct.value for ct in ChipType],
        "bit_widths": VALID_BIT_WIDTHS,
        "unit_colors": UNIT_COLORS,
        "chip_type_colors": {ct.value: CHIP_TYPE_COLORS[ct] for ct in ChipType},
        "mutation_types": MUTATION_TYPES,
        "isa_types": ISA_TYPES,
        "interconnects": INTERCONNECTS,
        "memory_models": MEMORY_MODELS,
        "execution_models": EXECUTION_MODELS,
        "pipeline_archs": PIPELINE_ARCHS,
        "voltage_domains": VOLTAGE_DOMAINS,
        "process_nodes": PROCESS_NODES,
        "clock_topologies": CLOCK_TOPOLOGIES,
        "discovered_blocks": len(registry.blocks),
    })


# ── Chip generation ──────────────────────────────────────────────────────────

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json or {}
    try:
        ct = ChipType(data.get("chip_type", "RISC-V"))
    except ValueError:
        ct = ChipType.RISCV

    bw = int(data.get("bit_width", 32))
    if bw not in VALID_BIT_WIDTHS:
        bw = 32

    chip = Chip(
        chip_type=ct,
        bit_width=bw,
        core_count=max(1, min(64, int(data.get("core_count", 1)))),
        pipeline_stages=max(2, min(32, int(data.get("pipeline_stages", 5)))),
        cache_kb=int(data.get("cache_kb", 64)),
    )

    # attach default architecture
    arch = ChipArchitecture(
        isa=data.get("isa", "RISC"),
        interconnect=data.get("interconnect", "Shared Bus"),
        memory_model=data.get("memory_model", "Flat SRAM"),
        execution_model=data.get("execution_model", "In-Order"),
        pipeline_arch=data.get("pipeline_arch", "Linear 5-Stage"),
        voltage_domain=data.get("voltage_domain", "Single VDD"),
        process_node=data.get("process_node", "7nm"),
        clock_topology=data.get("clock_topology", "H-Tree"),
    )
    arch.compute_derived(chip)
    chip.architecture = arch.to_dict()
    chip.compute_fitness()

    with state_lock:
        state["chip"] = chip
        state["engine"] = EvolutionEngine(population_size=8)
        state["engine"].seed_population(copy.deepcopy(chip))

    autosave(chip, state["engine"])
    return jsonify({"success": True, "chip": chip_to_json(chip)})


# ── Evolution ────────────────────────────────────────────────────────────────

@app.route("/api/mutate_once", methods=["POST"])
def mutate_once():
    data = request.json or {}
    with state_lock:
        if state["chip"] is None:
            return jsonify({"error": "No chip generated"}), 400
        chip, desc, reward = state["engine"].evolve_step(float(data.get("strength", 1.0)))
        state["chip"] = chip
        state["last_reward"] = reward
        autosave(chip, state["engine"])
    return jsonify({
        "success": True, "chip": chip_to_json(chip),
        "desc": desc, "reward": reward,
        "log": state["engine"].evolution_log[-15:],
        "discoveries": state["engine"].discoveries,
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
    steps    = max(1, min(500, int(data.get("steps", 20))))
    strength = max(0.1, min(10.0, float(data.get("strength", 1.0))))

    def worker():
        for _ in range(steps):
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
        log = state["engine"].evolution_log[-20:]
        reward = state["last_reward"]
        epsilon = state["engine"].agent.epsilon
        total_steps = state["engine"].agent.total_steps
        discoveries = state["engine"].discoveries[:]
        pop = [{"name": c.name, "fitness": c.fitness,
                "color": CHIP_TYPE_COLORS.get(c.chip_type, "#00ff88"),
                "gen": c.generation, "novel": c.novel_block_count()}
               for c in state["engine"].population]
    return jsonify({
        "evolving": evolving,
        "chip": chip_to_json(chip) if chip else None,
        "log": log,
        "reward": reward,
        "epsilon": round(epsilon, 4),
        "total_steps": total_steps,
        "population": pop,
        "discoveries": discoveries,
    })


@app.route("/api/reset", methods=["POST"])
def reset():
    with state_lock:
        if state["chip"] is None:
            return jsonify({"error": "No chip"}), 400
        state["engine"] = EvolutionEngine(population_size=8)
        state["engine"].seed_population(copy.deepcopy(state["chip"]))
    return jsonify({"success": True})


# ── Architecture ─────────────────────────────────────────────────────────────

@app.route("/api/architecture/update", methods=["POST"])
def arch_update():
    data = request.json or {}
    with state_lock:
        if state["chip"] is None:
            return jsonify({"error": "No chip"}), 400
        arch_dict = state["chip"].architecture or {}
        arch = ChipArchitecture.from_dict(arch_dict) if arch_dict else ChipArchitecture()
        for field_name in ["isa", "interconnect", "memory_model", "execution_model",
                           "pipeline_arch", "voltage_domain", "process_node", "clock_topology"]:
            if field_name in data:
                setattr(arch, field_name, data[field_name])
        arch.compute_derived(state["chip"])
        state["chip"].architecture = arch.to_dict()
        state["chip"].compute_fitness()
        chip = state["chip"]
    autosave(chip, state["engine"])
    return jsonify({"success": True, "chip": chip_to_json(chip), "architecture": arch.to_dict()})


# ── Novel blocks ─────────────────────────────────────────────────────────────

@app.route("/api/blocks/registry")
def blocks_registry():
    registry = BlockRegistry.get()
    return jsonify({
        "blocks": [b.to_dict() for b in sorted(
            registry.blocks.values(), key=lambda b: b.fitness_weight, reverse=True)]
    })


@app.route("/api/blocks/invent", methods=["POST"])
def blocks_invent():
    with state_lock:
        gen = state["chip"].generation if state["chip"] else 0
        name = state["chip"].name if state["chip"] else "manual"
    spec = invent_block(generation=gen, chip_name=name)
    return jsonify({"success": True, "block": spec.to_dict()})


# ── Code generation ──────────────────────────────────────────────────────────

@app.route("/api/codegen/<lang>")
def codegen(lang: str):
    with state_lock:
        chip = state["chip"]
    if chip is None:
        return jsonify({"error": "No chip generated"}), 400

    arch = None
    if chip.architecture:
        try:
            arch = ChipArchitecture.from_dict(chip.architecture)
        except Exception:
            arch = None

    try:
        if lang == "assembly":
            code = generate_assembly(chip, arch)
        elif lang == "vhdl":
            code = generate_vhdl(chip, arch)
        elif lang == "verilog":
            code = generate_verilog(chip, arch)
        else:
            return jsonify({"error": f"Unknown language: {lang}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"success": True, "language": lang, "code": code,
                    "chip_name": chip.name, "lines": code.count('\n')})


# ── Save / Load ───────────────────────────────────────────────────────────────

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
    return jsonify({"saves": list_saves()})


@app.route("/api/hall_of_fame")
def hall_of_fame():
    hof = load_hall_of_fame()
    return jsonify({"chips": [chip_to_json(c) for c in hof]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Chip Generator v2 on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

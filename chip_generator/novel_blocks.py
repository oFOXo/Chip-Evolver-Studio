"""
Novel Block Discovery & Registry System.
Chips can evolve entirely new kinds of digital blocks with
unique properties, fitness weights, and descriptions.
The registry persists new blocks across sessions.
"""

import random
import json
import os
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "saves", "block_registry.json")

# Procedural name generation
NAME_PREFIXES = [
    "Q","N","M","V","X","Z","H","P","K","ΨΩ","φ","Σ","Δ","Λ","Γ","Ξ","Π",
    "BIO","NEU","QTM","POL","AXN","REC","SYN","MOR","HYB","ISO","TEN","COR"
]
NAME_CORES = [
    "ALU","FPU","MUL","VEC","SIM","TEN","ACC","COR","PRO","EXE","MAT","OPS",
    "DAT","MEM","SYG","REC","PLS","WAV","ORB","NET","FLO","SEQ","LAT","STR",
    "OPT","VAR","INF","ENT","DYN","GRD","SPC","RND","CLK","BIT","SUM","LOG"
]
NAME_SUFFIXES = [
    "U","X","E","R","S","T","N","M","K","Z","V",
    "XU","EU","MU","NU","VU","KU","TU","SU","RU",
    "3D","4D","HD","XT","QX","NX","ZX","VX","EX"
]

# Capability tags
CAPABILITIES = [
    "matrix_ops", "fft", "entropy", "pattern_match", "graph_traverse",
    "neural_activate", "compress", "encrypt", "hash", "sort", "search",
    "wavelet", "fourier", "monte_carlo", "genetic", "quantum_sim",
    "ray_trace", "physics_sim", "mesh_proc", "stream_filter",
    "spike_encode", "reservoir_compute", "hyperdimensional",
    "stochastic_compute", "approximate_compute", "near_memory",
    "analog_assist", "photonic_sim", "in_memory_compute", "logic_in_mem",
    "attention_head", "transformer_core", "diffusion_step",
    "convolution_2d", "recurrent_gate", "token_embed",
    "cache_prefetch", "branch_speculate", "vector_gather", "scatter_ops",
]

# Color palette for novel blocks (distinct from base units)
NOVEL_COLORS = [
    "#ff44aa","#44ffbb","#ff88ff","#88ff44","#ff4466","#44aaff",
    "#ffaa88","#88ffaa","#aa44ff","#ff6644","#44ffdd","#ffdd44",
    "#cc44ff","#44ccff","#ff44cc","#ffcc88","#88ccff","#cc88ff",
    "#ff88cc","#ccff88","#88ffcc","#ff8844","#44ff88","#8844ff",
    "#cc4488","#88cc44","#4488cc","#cc8844","#4444ff","#ff44ff",
]

def _rand_color(seed: str) -> str:
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(NOVEL_COLORS)
    return NOVEL_COLORS[idx]


@dataclass
class BlockSpec:
    name: str
    color: str
    fitness_weight: float
    power_factor: float
    capabilities: List[str]
    description: str
    generation_discovered: int = 0
    discovery_chip: str = ""
    times_used: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "color": self.color,
            "fitness_weight": self.fitness_weight,
            "power_factor": self.power_factor,
            "capabilities": self.capabilities,
            "description": self.description,
            "generation_discovered": self.generation_discovered,
            "discovery_chip": self.discovery_chip,
            "times_used": self.times_used,
        }

    @staticmethod
    def from_dict(d: dict) -> "BlockSpec":
        return BlockSpec(
            name=d["name"], color=d["color"],
            fitness_weight=d["fitness_weight"], power_factor=d["power_factor"],
            capabilities=d["capabilities"], description=d["description"],
            generation_discovered=d.get("generation_discovered", 0),
            discovery_chip=d.get("discovery_chip", ""),
            times_used=d.get("times_used", 0),
        )


class BlockRegistry:
    """Global registry of discovered novel blocks."""

    _instance: Optional["BlockRegistry"] = None

    def __init__(self):
        self.blocks: Dict[str, BlockSpec] = {}
        self._load()

    @classmethod
    def get(cls) -> "BlockRegistry":
        if cls._instance is None:
            cls._instance = BlockRegistry()
        return cls._instance

    def _load(self):
        if os.path.exists(REGISTRY_FILE):
            try:
                with open(REGISTRY_FILE) as f:
                    data = json.load(f)
                for d in data:
                    b = BlockSpec.from_dict(d)
                    self.blocks[b.name] = b
            except Exception:
                pass

    def save(self):
        os.makedirs(os.path.dirname(REGISTRY_FILE), exist_ok=True)
        with open(REGISTRY_FILE, "w") as f:
            json.dump([b.to_dict() for b in self.blocks.values()], f, indent=2)

    def register(self, spec: BlockSpec):
        self.blocks[spec.name] = spec
        self.save()

    def all_names(self) -> List[str]:
        return list(self.blocks.keys())

    def get_spec(self, name: str) -> Optional[BlockSpec]:
        return self.blocks.get(name)

    def get_weight(self, name: str) -> float:
        spec = self.blocks.get(name)
        return spec.fitness_weight if spec else 1.0

    def get_color(self, name: str) -> str:
        spec = self.blocks.get(name)
        return spec.color if spec else "#555555"

    def increment_usage(self, name: str):
        if name in self.blocks:
            self.blocks[name].times_used += 1


def _gen_name() -> str:
    prefix = random.choice(NAME_PREFIXES)
    core = random.choice(NAME_CORES)
    suffix = random.choice(NAME_SUFFIXES)
    style = random.randint(0, 2)
    if style == 0:
        return f"{prefix}{core}"
    elif style == 1:
        return f"{core}{suffix}"
    else:
        return f"{prefix}{core[0:3]}{suffix}"


def _gen_description(name: str, caps: List[str], weight: float) -> str:
    templates = [
        f"Novel unit '{name}': specializes in {caps[0].replace('_',' ')} with efficiency factor {weight:.2f}.",
        f"Evolved block '{name}': discovered capability — {caps[0].replace('_',' ')} + {caps[1].replace('_',' ')} pipeline.",
        f"'{name}' emerged via mutation: high-performance {caps[0].replace('_',' ')} accelerator (w={weight:.2f}).",
        f"Invented unit '{name}': hybrid of {caps[0].replace('_',' ')} and {caps[1].replace('_',' ')}; power-optimized.",
        f"'{name}' is a stochastic {caps[0].replace('_',' ')} engine with reconfigurable datapath.",
    ]
    return random.choice(templates)


def invent_block(generation: int = 0, chip_name: str = "") -> BlockSpec:
    """Invent a completely new block type through procedural generation."""
    registry = BlockRegistry.get()
    # avoid duplicates
    for _ in range(20):
        name = _gen_name()
        if name not in registry.blocks:
            break
    else:
        name = f"BLK{random.randint(1000,9999)}"

    n_caps = random.randint(1, 4)
    caps = random.sample(CAPABILITIES, n_caps)
    weight = round(random.uniform(1.5, 4.5), 3)
    power = round(random.uniform(0.03, 0.15), 4)
    color = _rand_color(name)
    desc = _gen_description(name, caps, weight)

    spec = BlockSpec(
        name=name, color=color, fitness_weight=weight, power_factor=power,
        capabilities=caps, description=desc,
        generation_discovered=generation, discovery_chip=chip_name,
    )
    registry.register(spec)
    return spec


def mutate_block(spec: BlockSpec, generation: int) -> BlockSpec:
    """Mutate an existing novel block into a variant."""
    registry = BlockRegistry.get()
    suffix = random.choice(NAME_SUFFIXES)
    new_name = f"{spec.name[:4]}{suffix}"
    if new_name in registry.blocks:
        new_name = f"{spec.name[:3]}{random.randint(10,99)}"

    delta_w = random.uniform(-0.5, 0.8)
    new_weight = round(max(0.5, spec.fitness_weight + delta_w), 3)
    new_caps = list(spec.capabilities)
    if len(new_caps) > 1 and random.random() < 0.3:
        new_caps.pop(random.randrange(len(new_caps)))
    if random.random() < 0.5:
        extra = random.choice([c for c in CAPABILITIES if c not in new_caps])
        new_caps.append(extra)

    new_spec = BlockSpec(
        name=new_name, color=_rand_color(new_name),
        fitness_weight=new_weight, power_factor=round(spec.power_factor * random.uniform(0.7, 1.3), 4),
        capabilities=new_caps,
        description=f"Variant of '{spec.name}' — {new_caps[0].replace('_',' ')} optimized (w={new_weight:.2f})",
        generation_discovered=generation,
    )
    registry.register(new_spec)
    return new_spec


def combine_blocks(spec_a: BlockSpec, spec_b: BlockSpec, generation: int) -> BlockSpec:
    """Combine two blocks into a hybrid novel block."""
    registry = BlockRegistry.get()
    new_name = f"{spec_a.name[:2]}{spec_b.name[:2]}{random.choice(NAME_SUFFIXES)}"
    if new_name in registry.blocks:
        new_name += str(random.randint(1, 9))

    combined_caps = list(set(spec_a.capabilities[:2] + spec_b.capabilities[:2]))[:4]
    new_weight = round((spec_a.fitness_weight + spec_b.fitness_weight) / 2 * random.uniform(0.9, 1.3), 3)
    new_power  = round((spec_a.power_factor + spec_b.power_factor) / 2, 4)

    new_spec = BlockSpec(
        name=new_name, color=_rand_color(new_name),
        fitness_weight=new_weight, power_factor=new_power,
        capabilities=combined_caps,
        description=f"Hybrid of '{spec_a.name}' + '{spec_b.name}' — {combined_caps[0].replace('_',' ')} + {combined_caps[-1].replace('_',' ')}",
        generation_discovered=generation,
    )
    registry.register(new_spec)
    return new_spec

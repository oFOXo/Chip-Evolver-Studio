"""
RL + recursive AI evolution engine.
Now includes: novel block invention, architecture mutation,
block combining/splitting, and Q-learning with expanded action space.
"""

import random
import math
import copy
from typing import List, Tuple, Dict, Optional
from chip import Chip, ChipType, UnitBlock, VALID_BIT_WIDTHS, clamp, UNIT_COLORS

MUTATION_TYPES = [
    # ── Block-level mutations ──
    "add_unit",
    "remove_unit",
    "scale_unit",
    "swap_units",
    "merge_units",
    "split_unit",
    "random_unit_type",
    # ── Chip-level parameter mutations ──
    "change_bitwidth",
    "change_cores",
    "change_pipeline",
    "change_cache",
    # ── Novel block invention ──
    "invent_block",
    "mutate_novel_block",
    "combine_novel_blocks",
    "add_discovered_block",
    # ── Architecture evolution ──
    "mutate_architecture",
    "upgrade_isa",
    "upgrade_memory",
    "upgrade_interconnect",
]

ALL_UNIT_NAMES = [
    "ALU", "FPU", "MUL", "DIV", "CACHE", "MEM", "CTRL", "IO", "BUS",
    "REG", "PRED", "LOAD", "STORE", "DECODE", "FETCH", "RETIRE",
    "TENSOR", "VEC", "SIMD", "ACCEL", "DMA", "INT", "SCHED",
]


class QLearningAgent:
    def __init__(self, n_actions: int, lr: float = 0.1, gamma: float = 0.95,
                 epsilon: float = 0.9, epsilon_decay: float = 0.995, epsilon_min: float = 0.05):
        self.n_actions = n_actions
        self.lr = lr
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.q_table: Dict[int, List[float]] = {}
        self.total_steps = 0
        self.reward_history: List[float] = []

    def _state_key(self, fitness: float) -> int:
        return int(fitness * 10)

    def _ensure_state(self, s: int):
        if s not in self.q_table:
            self.q_table[s] = [0.0] * self.n_actions

    def select_action(self, fitness: float) -> int:
        s = self._state_key(fitness)
        self._ensure_state(s)
        if random.random() < self.epsilon:
            return random.randrange(self.n_actions)
        return int(max(range(self.n_actions), key=lambda a: self.q_table[s][a]))

    def update(self, prev_fitness: float, action: int, reward: float, new_fitness: float):
        s  = self._state_key(prev_fitness)
        s2 = self._state_key(new_fitness)
        self._ensure_state(s)
        self._ensure_state(s2)
        best_next  = max(self.q_table[s2])
        td_target  = reward + self.gamma * best_next
        self.q_table[s][action] += self.lr * (td_target - self.q_table[s][action])
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self.total_steps += 1
        self.reward_history.append(reward)

    def to_dict(self) -> dict:
        return {
            "q_table": {str(k): v for k, v in self.q_table.items()},
            "epsilon": self.epsilon,
            "total_steps": self.total_steps,
            "reward_history": self.reward_history[-100:],
        }

    @staticmethod
    def from_dict(d: dict, n_actions: int) -> "QLearningAgent":
        agent = QLearningAgent(n_actions)
        agent.q_table = {int(k): v for k, v in d.get("q_table", {}).items()}
        agent.epsilon = d.get("epsilon", 0.9)
        agent.total_steps = d.get("total_steps", 0)
        agent.reward_history = d.get("reward_history", [])
        return agent


class MutationEngine:

    @staticmethod
    def mutate(chip: Chip, mutation_type: str, strength: float = 1.0) -> Tuple[Chip, str]:
        c = copy.deepcopy(chip)
        c.generation += 1
        desc = ""

        # ── Block-level ──────────────────────────────────────────────────
        if mutation_type == "add_unit":
            name = random.choice(ALL_UNIT_NAMES)
            cnt = random.randint(1, max(1, int(2 * strength)))
            c.units.append(UnitBlock(name, cnt))
            desc = f"Added {name}×{cnt}"

        elif mutation_type == "remove_unit":
            if len(c.units) > 2:
                u = random.choice(c.units)
                c.units.remove(u)
                desc = f"Removed {u.name}"

        elif mutation_type == "scale_unit":
            if c.units:
                u = random.choice(c.units)
                delta = random.randint(-2, int(3 * strength))
                u.count = clamp(u.count + delta, 1, 64)
                desc = f"Scaled {u.name} by {delta:+d} → ×{u.count}"

        elif mutation_type == "swap_units":
            if len(c.units) >= 2:
                a, b = random.sample(c.units, 2)
                a.name, b.name = b.name, a.name
                a.color, b.color = b.color, a.color
                a.is_novel, b.is_novel = b.is_novel, a.is_novel
                desc = f"Swapped {a.name} ↔ {b.name}"

        elif mutation_type == "merge_units":
            if len(c.units) >= 2:
                a, b = random.sample(c.units, 2)
                a.count += b.count
                c.units.remove(b)
                desc = f"Merged {b.name} into {a.name} (×{a.count})"

        elif mutation_type == "split_unit":
            candidates = [u for u in c.units if u.count >= 2]
            if candidates:
                u = random.choice(candidates)
                half = u.count // 2
                u.count -= half
                new_name = random.choice(ALL_UNIT_NAMES)
                c.units.append(UnitBlock(new_name, half))
                desc = f"Split {u.name} → {new_name}×{half}"

        elif mutation_type == "random_unit_type":
            if c.units:
                u = random.choice(c.units)
                old = u.name
                u.name = random.choice(ALL_UNIT_NAMES)
                u.color = UNIT_COLORS.get(u.name, "#555555")
                u.is_novel = False
                desc = f"Retyped {old} → {u.name}"

        # ── Chip-level parameters ────────────────────────────────────────
        elif mutation_type == "change_bitwidth":
            idx = VALID_BIT_WIDTHS.index(c.bit_width) if c.bit_width in VALID_BIT_WIDTHS else 2
            delta = random.choice([-1, 1])
            new_idx = clamp(idx + delta, 0, len(VALID_BIT_WIDTHS) - 1)
            old = c.bit_width
            c.bit_width = VALID_BIT_WIDTHS[new_idx]
            desc = f"Bit width {old} → {c.bit_width}"

        elif mutation_type == "change_cores":
            delta = random.choice([-1, 1, 2, 4])
            c.core_count = clamp(c.core_count + delta, 1, 64)
            desc = f"Cores → {c.core_count}"

        elif mutation_type == "change_pipeline":
            delta = random.choice([-1, 1, 2])
            c.pipeline_stages = clamp(c.pipeline_stages + delta, 2, 32)
            desc = f"Pipeline → {c.pipeline_stages} stages"

        elif mutation_type == "change_cache":
            factor = random.choice([0.5, 2.0, 1.5, 0.75, 4.0])
            c.cache_kb = clamp(int(c.cache_kb * factor), 8, 32768)
            desc = f"Cache → {c.cache_kb} KB"

        # ── Novel block invention ────────────────────────────────────────
        elif mutation_type == "invent_block":
            try:
                from novel_blocks import invent_block
                spec = invent_block(generation=c.generation, chip_name=c.name)
                cnt = max(1, int(2 * strength))
                c.units.append(UnitBlock(spec.name, cnt, spec.color, is_novel=True))
                desc = f"INVENTED block: {spec.name} (w={spec.fitness_weight:.2f}) ×{cnt}"
            except Exception as e:
                desc = f"invent_block failed: {e}"

        elif mutation_type == "mutate_novel_block":
            novel_units = [u for u in c.units if u.is_novel]
            if novel_units:
                try:
                    from novel_blocks import BlockRegistry, mutate_block
                    u = random.choice(novel_units)
                    spec = BlockRegistry.get().get_spec(u.name)
                    if spec:
                        new_spec = mutate_block(spec, c.generation)
                        c.units.append(UnitBlock(new_spec.name, u.count, new_spec.color, is_novel=True))
                        desc = f"Mutated novel {u.name} → {new_spec.name}"
                    else:
                        desc = "novel block spec missing"
                except Exception as e:
                    desc = f"mutate_novel failed: {e}"
            else:
                # fall back: invent a new one
                try:
                    from novel_blocks import invent_block
                    spec = invent_block(generation=c.generation, chip_name=c.name)
                    c.units.append(UnitBlock(spec.name, 2, spec.color, is_novel=True))
                    desc = f"No novel units — invented {spec.name}"
                except Exception as e:
                    desc = f"fallback invent failed: {e}"

        elif mutation_type == "combine_novel_blocks":
            novel_units = [u for u in c.units if u.is_novel]
            if len(novel_units) >= 2:
                try:
                    from novel_blocks import BlockRegistry, combine_blocks
                    ua, ub = random.sample(novel_units, 2)
                    sa = BlockRegistry.get().get_spec(ua.name)
                    sb = BlockRegistry.get().get_spec(ub.name)
                    if sa and sb:
                        hybrid = combine_blocks(sa, sb, c.generation)
                        c.units.append(UnitBlock(hybrid.name, (ua.count + ub.count) // 2,
                                                 hybrid.color, is_novel=True))
                        desc = f"Combined {ua.name}+{ub.name} → {hybrid.name}"
                    else:
                        desc = "combine: missing specs"
                except Exception as e:
                    desc = f"combine failed: {e}"
            else:
                # not enough novel blocks — invent two and combine
                try:
                    from novel_blocks import invent_block, combine_blocks
                    sa = invent_block(c.generation, c.name)
                    sb = invent_block(c.generation, c.name)
                    hybrid = combine_blocks(sa, sb, c.generation)
                    c.units.append(UnitBlock(hybrid.name, 2, hybrid.color, is_novel=True))
                    desc = f"Invented+combined → {hybrid.name}"
                except Exception as e:
                    desc = f"invent+combine failed: {e}"

        elif mutation_type == "add_discovered_block":
            try:
                from novel_blocks import BlockRegistry
                reg = BlockRegistry.get()
                names = reg.all_names()
                if names:
                    name = random.choice(names)
                    spec = reg.get_spec(name)
                    cnt = max(1, int(2 * strength))
                    c.units.append(UnitBlock(name, cnt, spec.color, is_novel=True))
                    reg.increment_usage(name)
                    desc = f"Added discovered block: {name} ×{cnt}"
                else:
                    from novel_blocks import invent_block
                    spec = invent_block(c.generation, c.name)
                    c.units.append(UnitBlock(spec.name, 1, spec.color, is_novel=True))
                    desc = f"No discovered blocks — invented {spec.name}"
            except Exception as e:
                desc = f"add_discovered failed: {e}"

        # ── Architecture evolution ───────────────────────────────────────
        elif mutation_type in ("mutate_architecture", "upgrade_isa",
                               "upgrade_memory", "upgrade_interconnect"):
            try:
                from architecture import (ChipArchitecture, mutate_architecture,
                                          ISA_TYPES, MEMORY_MODELS, INTERCONNECTS)
                arch_dict = c.architecture or {}
                arch = ChipArchitecture.from_dict(arch_dict) if arch_dict else ChipArchitecture()

                if mutation_type == "upgrade_isa":
                    old = arch.isa
                    arch.isa = random.choice([x for x in ISA_TYPES if x != old])
                    adesc = f"ISA: {old} → {arch.isa}"
                elif mutation_type == "upgrade_memory":
                    old = arch.memory_model
                    arch.memory_model = random.choice([x for x in MEMORY_MODELS if x != old])
                    adesc = f"Memory: {old} → {arch.memory_model}"
                elif mutation_type == "upgrade_interconnect":
                    old = arch.interconnect
                    arch.interconnect = random.choice([x for x in INTERCONNECTS if x != old])
                    adesc = f"Interconnect: {old} → {arch.interconnect}"
                else:
                    arch, adesc = mutate_architecture(arch)

                arch.compute_derived(c)
                c.architecture = arch.to_dict()
                desc = f"Arch: {adesc}"
            except Exception as e:
                desc = f"arch mutation failed: {e}"

        c.name = f"{c.chip_type.value}-{c.bit_width}bit-gen{c.generation}"
        c.mutation_history.append(desc if desc else mutation_type)
        if len(c.mutation_history) > 40:
            c.mutation_history = c.mutation_history[-40:]
        return c, desc


class EvolutionEngine:
    def __init__(self, population_size: int = 8):
        self.population_size = population_size
        self.agent = QLearningAgent(n_actions=len(MUTATION_TYPES))
        self.population: List[Chip] = []
        self.best_chip: Optional[Chip] = None
        self.generation = 0
        self.evolution_log: List[str] = []
        self.mutation_engine = MutationEngine()
        self.discoveries: List[str] = []  # novel blocks found this session

    def seed_population(self, base_chip: Chip):
        self.population = [base_chip]
        for _ in range(self.population_size - 1):
            mt = random.choice(MUTATION_TYPES)
            mutated, _ = self.mutation_engine.mutate(base_chip, mt)
            mutated.compute_fitness()
            self.population.append(mutated)
        self._sort_population()
        self.best_chip = self.population[0]

    def _sort_population(self):
        for c in self.population:
            c.compute_fitness()
        self.population.sort(key=lambda c: c.fitness, reverse=True)

    def evolve_step(self, strength: float = 1.0) -> Tuple[Chip, str, float]:
        self._sort_population()
        parent = self.population[0]
        prev_fitness = parent.fitness

        action_idx = self.agent.select_action(prev_fitness)
        mutation_type = MUTATION_TYPES[action_idx]
        child, desc = self.mutation_engine.mutate(parent, mutation_type, strength)
        child.compute_fitness()

        reward = child.fitness - prev_fitness
        self.agent.update(prev_fitness, action_idx, reward, child.fitness)

        self.population.append(child)
        self._sort_population()
        if len(self.population) > self.population_size:
            self.population = self.population[:self.population_size]

        self.best_chip = self.population[0]
        self.generation += 1

        # track novel block discoveries
        for u in child.units:
            if u.is_novel and u.name not in self.discoveries:
                self.discoveries.append(u.name)

        log_entry = (
            f"Gen {self.generation}: [{mutation_type}] {desc} | "
            f"{prev_fitness:.3f}→{child.fitness:.3f} ({reward:+.3f})"
        )
        self.evolution_log.append(log_entry)
        if len(self.evolution_log) > 60:
            self.evolution_log = self.evolution_log[-60:]

        return child, desc, reward

    def recursive_evolve(self, steps: int, strength: float = 1.0, callback=None) -> Chip:
        for i in range(steps):
            chip, desc, reward = self.evolve_step(strength)
            if callback:
                callback(i + 1, steps, chip, desc, reward)
        return self.best_chip

    def to_dict(self) -> dict:
        return {
            "population": [c.to_dict() for c in self.population],
            "best_chip": self.best_chip.to_dict() if self.best_chip else None,
            "generation": self.generation,
            "evolution_log": self.evolution_log,
            "agent": self.agent.to_dict(),
            "discoveries": self.discoveries,
        }

    @staticmethod
    def from_dict(d: dict) -> "EvolutionEngine":
        engine = EvolutionEngine()
        engine.population = [Chip.from_dict(c) for c in d.get("population", [])]
        engine.best_chip = Chip.from_dict(d["best_chip"]) if d.get("best_chip") else None
        engine.generation = d.get("generation", 0)
        engine.evolution_log = d.get("evolution_log", [])
        engine.discoveries = d.get("discoveries", [])
        if d.get("agent"):
            engine.agent = QLearningAgent.from_dict(d["agent"], len(MUTATION_TYPES))
        return engine

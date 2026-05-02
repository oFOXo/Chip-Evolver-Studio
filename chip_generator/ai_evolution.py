"""
RL + recursive AI evolution engine for chip mutation and optimization.
Uses Q-learning and random mutation strategies.
"""

import random
import math
import copy
from typing import List, Tuple, Dict, Optional
from chip import Chip, ChipType, UnitBlock, VALID_BIT_WIDTHS, clamp

MUTATION_TYPES = [
    "add_unit",
    "remove_unit",
    "scale_unit",
    "change_bitwidth",
    "change_cores",
    "change_pipeline",
    "change_cache",
    "swap_units",
    "merge_units",
    "split_unit",
    "random_unit_type",
    "add_novel_unit",
]

NOVEL_UNITS = ["TENSOR", "ACCEL", "VEC", "SIMD", "DMA", "SCHED", "PRED", "INT", "BUS", "LOAD", "STORE"]

ALL_UNIT_NAMES = [
    "ALU", "FPU", "MUL", "DIV", "CACHE", "MEM", "CTRL", "IO", "BUS",
    "REG", "PRED", "LOAD", "STORE", "DECODE", "FETCH", "RETIRE",
    "TENSOR", "VEC", "SIMD", "ACCEL", "DMA", "INT", "SCHED",
]


class QLearningAgent:
    """
    Tabular Q-Learning agent for chip mutation selection.
    State: discretized fitness bucket
    Actions: mutation type index
    """

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
        s = self._state_key(prev_fitness)
        s2 = self._state_key(new_fitness)
        self._ensure_state(s)
        self._ensure_state(s2)
        best_next = max(self.q_table[s2])
        td_target = reward + self.gamma * best_next
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
    """Applies random mutations to chips."""

    @staticmethod
    def mutate(chip: Chip, mutation_type: str, strength: float = 1.0) -> Tuple[Chip, str]:
        c = copy.deepcopy(chip)
        c.generation += 1
        desc = ""

        if mutation_type == "add_unit":
            name = random.choice(ALL_UNIT_NAMES)
            cnt = random.randint(1, max(1, int(2 * strength)))
            c.units.append(UnitBlock(name, cnt))
            desc = f"Added {name}x{cnt}"

        elif mutation_type == "remove_unit":
            if len(c.units) > 2:
                u = random.choice(c.units)
                c.units.remove(u)
                desc = f"Removed {u.name}"

        elif mutation_type == "scale_unit":
            if c.units:
                u = random.choice(c.units)
                delta = random.randint(-2, 3)
                u.count = clamp(u.count + delta, 1, 32)
                desc = f"Scaled {u.name} by {delta:+d}"

        elif mutation_type == "change_bitwidth":
            current_idx = VALID_BIT_WIDTHS.index(c.bit_width) if c.bit_width in VALID_BIT_WIDTHS else 2
            delta = random.choice([-1, 1])
            new_idx = clamp(current_idx + delta, 0, len(VALID_BIT_WIDTHS) - 1)
            old = c.bit_width
            c.bit_width = VALID_BIT_WIDTHS[new_idx]
            desc = f"Bit width {old} -> {c.bit_width}"

        elif mutation_type == "change_cores":
            delta = random.choice([-1, 1, 2])
            c.core_count = clamp(c.core_count + delta, 1, 64)
            desc = f"Cores -> {c.core_count}"

        elif mutation_type == "change_pipeline":
            delta = random.choice([-1, 1, 2])
            c.pipeline_stages = clamp(c.pipeline_stages + delta, 2, 32)
            desc = f"Pipeline -> {c.pipeline_stages} stages"

        elif mutation_type == "change_cache":
            factor = random.choice([0.5, 2.0, 1.5, 0.75])
            c.cache_kb = clamp(int(c.cache_kb * factor), 8, 32768)
            desc = f"Cache -> {c.cache_kb} KB"

        elif mutation_type == "swap_units":
            if len(c.units) >= 2:
                a, b = random.sample(c.units, 2)
                a.name, b.name = b.name, a.name
                a.color, b.color = b.color, a.color
                desc = f"Swapped {a.name} <-> {b.name}"

        elif mutation_type == "merge_units":
            if len(c.units) >= 2:
                a, b = random.sample(c.units, 2)
                a.count += b.count
                c.units.remove(b)
                desc = f"Merged {b.name} into {a.name}"

        elif mutation_type == "split_unit":
            candidates = [u for u in c.units if u.count >= 2]
            if candidates:
                u = random.choice(candidates)
                half = u.count // 2
                u.count -= half
                new_name = random.choice(ALL_UNIT_NAMES)
                c.units.append(UnitBlock(new_name, half))
                desc = f"Split {u.name} -> new {new_name}x{half}"

        elif mutation_type == "random_unit_type":
            if c.units:
                u = random.choice(c.units)
                old = u.name
                u.name = random.choice(ALL_UNIT_NAMES)
                from chip import UNIT_COLORS
                u.color = UNIT_COLORS.get(u.name, "#555555")
                desc = f"Renamed {old} -> {u.name}"

        elif mutation_type == "add_novel_unit":
            name = random.choice(NOVEL_UNITS)
            cnt = random.randint(2, max(2, int(4 * strength)))
            c.units.append(UnitBlock(name, cnt))
            desc = f"Novel unit: {name}x{cnt}"

        c.name = f"{c.chip_type.value}-{c.bit_width}bit-gen{c.generation}"
        c.mutation_history.append(desc if desc else mutation_type)
        if len(c.mutation_history) > 30:
            c.mutation_history = c.mutation_history[-30:]
        return c, desc


class EvolutionEngine:
    """
    Combines Q-learning agent with recursive mutation to evolve chip designs.
    """

    def __init__(self, population_size: int = 8):
        self.population_size = population_size
        self.agent = QLearningAgent(n_actions=len(MUTATION_TYPES))
        self.population: List[Chip] = []
        self.best_chip: Optional[Chip] = None
        self.generation = 0
        self.evolution_log: List[str] = []
        self.mutation_engine = MutationEngine()

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
        """Run one generation of evolution. Returns (new_best, mutation_desc, reward)."""
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

        log_entry = (
            f"Gen {self.generation}: {mutation_type} | "
            f"{desc} | fitness {prev_fitness:.3f} -> {child.fitness:.3f} | reward {reward:+.3f}"
        )
        self.evolution_log.append(log_entry)
        if len(self.evolution_log) > 50:
            self.evolution_log = self.evolution_log[-50:]

        return child, desc, reward

    def recursive_evolve(self, steps: int, strength: float = 1.0,
                          callback=None) -> Chip:
        """Recursively evolve for N steps, calling callback each step."""
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
        }

    @staticmethod
    def from_dict(d: dict) -> "EvolutionEngine":
        engine = EvolutionEngine()
        engine.population = [Chip.from_dict(c) for c in d.get("population", [])]
        engine.best_chip = Chip.from_dict(d["best_chip"]) if d.get("best_chip") else None
        engine.generation = d.get("generation", 0)
        engine.evolution_log = d.get("evolution_log", [])
        if d.get("agent"):
            engine.agent = QLearningAgent.from_dict(d["agent"], len(MUTATION_TYPES))
        return engine

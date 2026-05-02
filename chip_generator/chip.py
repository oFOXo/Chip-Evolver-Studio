"""
Chip data models — RISC-V Chip Generator.
Now includes ChipArchitecture and novel block support.
"""

import random
import math
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class ChipType(Enum):
    RISCV = "RISC-V"
    NPU = "NPU"
    DPU = "DPU"
    TPU = "TPU"
    GPU = "GPU"
    APU = "APU"
    VPU = "VPU"
    DSP = "DSP"
    QPU = "QPU"
    NDP = "NDP"
    MCU = "MCU"
    FPGA = "FPGA"
    ASIC = "ASIC"
    SPU = "SPU"
    IPU = "IPU"
    XPU = "XPU"
    BPU = "BPU"
    EPU = "EPU"


CHIP_TYPE_COLORS = {
    ChipType.RISCV: "#00ff88",
    ChipType.NPU:   "#ff6600",
    ChipType.DPU:   "#0088ff",
    ChipType.TPU:   "#ff00cc",
    ChipType.GPU:   "#ffcc00",
    ChipType.APU:   "#cc00ff",
    ChipType.VPU:   "#00ccff",
    ChipType.DSP:   "#ff4444",
    ChipType.QPU:   "#44ffcc",
    ChipType.NDP:   "#ff8844",
    ChipType.MCU:   "#8888ff",
    ChipType.FPGA:  "#44ff44",
    ChipType.ASIC:  "#ff4488",
    ChipType.SPU:   "#88ff00",
    ChipType.IPU:   "#00ff44",
    ChipType.XPU:   "#ffaa00",
    ChipType.BPU:   "#aa00ff",
    ChipType.EPU:   "#00aaff",
}

UNIT_COLORS = {
    "ALU":    "#00ff88",
    "FPU":    "#00ccff",
    "MUL":    "#ffcc00",
    "DIV":    "#ff8800",
    "CACHE":  "#8844ff",
    "MEM":    "#ff4466",
    "CTRL":   "#44ffcc",
    "IO":     "#ff44ff",
    "BUS":    "#888888",
    "REG":    "#44aa88",
    "PRED":   "#ffaa44",
    "LOAD":   "#44aaff",
    "STORE":  "#ff6688",
    "DECODE": "#aaffaa",
    "FETCH":  "#ffaaaa",
    "RETIRE": "#aaaaff",
    "TENSOR": "#ff66aa",
    "VEC":    "#66ffaa",
    "SIMD":   "#aa66ff",
    "ACCEL":  "#ffff44",
    "DMA":    "#44ffff",
    "INT":    "#ff4400",
    "SCHED":  "#00ff00",
    "EMPTY":  "#111122",
}

VALID_BIT_WIDTHS = [8, 16, 32, 64, 128]


def clamp(val, lo, hi):
    return max(lo, min(hi, val))


@dataclass
class UnitBlock:
    name: str
    count: int
    color: str = ""
    is_novel: bool = False

    def __post_init__(self):
        if not self.color:
            self.color = UNIT_COLORS.get(self.name, "#555555")

    def to_dict(self):
        return {"name": self.name, "count": self.count,
                "color": self.color, "is_novel": self.is_novel}

    @staticmethod
    def from_dict(d):
        return UnitBlock(d["name"], d["count"],
                         d.get("color", ""), d.get("is_novel", False))


@dataclass
class Chip:
    chip_type: ChipType = ChipType.RISCV
    bit_width: int = 32
    core_count: int = 1
    pipeline_stages: int = 5
    cache_kb: int = 64
    units: List[UnitBlock] = field(default_factory=list)
    generation: int = 0
    fitness: float = 0.0
    name: str = ""
    mutation_history: List[str] = field(default_factory=list)
    # architecture stored as dict so chip.py stays architecture.py-free at import time
    architecture: Optional[dict] = None

    def __post_init__(self):
        if not self.name:
            self.name = f"{self.chip_type.value}-{self.bit_width}bit-gen{self.generation}"
        if not self.units:
            self.units = self._default_units()

    def _default_units(self) -> List[UnitBlock]:
        t = self.chip_type
        bw = self.bit_width

        if t == ChipType.RISCV:
            return [
                UnitBlock("FETCH", 1),
                UnitBlock("DECODE", 1),
                UnitBlock("ALU", max(1, bw // 16)),
                UnitBlock("FPU", max(1, bw // 32)),
                UnitBlock("MUL", max(1, bw // 32)),
                UnitBlock("CACHE", max(1, bw // 16)),
                UnitBlock("MEM", 1),
                UnitBlock("CTRL", 1),
                UnitBlock("REG", max(1, bw // 8)),
                UnitBlock("RETIRE", 1),
            ]
        elif t == ChipType.NPU:
            return [
                UnitBlock("TENSOR", max(2, bw // 8)),
                UnitBlock("ACCEL", max(2, bw // 16)),
                UnitBlock("VEC", max(1, bw // 16)),
                UnitBlock("MEM", max(1, bw // 32)),
                UnitBlock("DMA", 1),
                UnitBlock("SCHED", 1),
                UnitBlock("CACHE", max(1, bw // 32)),
                UnitBlock("IO", 1),
            ]
        elif t == ChipType.TPU:
            return [
                UnitBlock("TENSOR", max(4, bw // 8)),
                UnitBlock("MUL", max(2, bw // 16)),
                UnitBlock("ACCEL", max(2, bw // 16)),
                UnitBlock("MEM", max(1, bw // 16)),
                UnitBlock("DMA", 2),
                UnitBlock("CTRL", 1),
            ]
        elif t == ChipType.GPU:
            return [
                UnitBlock("SIMD", max(4, bw // 4)),
                UnitBlock("VEC", max(2, bw // 8)),
                UnitBlock("ALU", max(2, bw // 8)),
                UnitBlock("FPU", max(2, bw // 8)),
                UnitBlock("CACHE", max(1, bw // 16)),
                UnitBlock("MEM", max(1, bw // 16)),
                UnitBlock("SCHED", 1),
                UnitBlock("DMA", 1),
            ]
        elif t == ChipType.QPU:
            return [
                UnitBlock("ACCEL", max(2, bw // 8)),
                UnitBlock("CTRL", 2),
                UnitBlock("INT", max(1, bw // 16)),
                UnitBlock("IO", 2),
                UnitBlock("SCHED", 1),
                UnitBlock("MEM", 1),
            ]
        elif t in (ChipType.DSP, ChipType.VPU):
            return [
                UnitBlock("SIMD", max(2, bw // 8)),
                UnitBlock("ALU", max(1, bw // 16)),
                UnitBlock("MUL", max(1, bw // 16)),
                UnitBlock("CACHE", 1),
                UnitBlock("MEM", 1),
                UnitBlock("DMA", 1),
                UnitBlock("IO", 1),
            ]
        else:
            return [
                UnitBlock("ALU", max(1, bw // 16)),
                UnitBlock("MEM", 1),
                UnitBlock("CACHE", 1),
                UnitBlock("CTRL", 1),
                UnitBlock("IO", 1),
                UnitBlock("ACCEL", max(1, bw // 16)),
            ]

    def compute_fitness(self) -> float:
        from novel_blocks import BlockRegistry
        registry = BlockRegistry.get()

        perf = 0.0
        base_weights = {
            "ALU": 2.0, "FPU": 1.8, "TENSOR": 3.0, "SIMD": 2.5,
            "VEC": 2.2, "MUL": 1.5, "ACCEL": 2.8, "CACHE": 1.2,
            "MEM": 1.0, "DMA": 0.8, "CTRL": 0.5, "IO": 0.4,
            "REG": 0.6, "FETCH": 0.5, "DECODE": 0.5, "RETIRE": 0.5,
            "PRED": 0.7, "SCHED": 0.6, "INT": 0.9,
        }
        for u in self.units:
            # novel blocks use registry weight; base blocks use hardcoded weight
            if u.is_novel:
                w = registry.get_weight(u.name)
            else:
                w = base_weights.get(u.name, 1.0)
            perf += u.count * w

        bw_bonus    = math.log2(max(8, self.bit_width)) / math.log2(128)
        core_bonus  = math.log2(max(1, self.core_count) + 1)
        pipe_bonus  = min(self.pipeline_stages / 20.0, 1.0)
        cache_bonus = math.log2(max(1, self.cache_kb) + 1) / 8.0

        power_cost = (
            sum(u.count for u in self.units) * 0.05
            + self.core_count * 0.1
            + self.bit_width * 0.005
        )

        # architecture bonus
        arch_bonus = 1.0
        if self.architecture:
            try:
                from architecture import ChipArchitecture
                arch_obj = ChipArchitecture.from_dict(self.architecture)
                arch_bonus = arch_obj.arch_fitness_bonus()
            except Exception:
                pass

        raw = perf * (1 + bw_bonus) * (1 + core_bonus) * (1 + pipe_bonus) * (1 + cache_bonus)
        efficiency = raw / max(power_cost, 0.1)
        self.fitness = round(efficiency * arch_bonus, 4)
        return self.fitness

    def total_cells(self) -> int:
        return sum(u.count for u in self.units)

    def novel_block_count(self) -> int:
        return sum(1 for u in self.units if u.is_novel)

    def to_dict(self) -> dict:
        return {
            "chip_type": self.chip_type.value,
            "bit_width": self.bit_width,
            "core_count": self.core_count,
            "pipeline_stages": self.pipeline_stages,
            "cache_kb": self.cache_kb,
            "units": [u.to_dict() for u in self.units],
            "generation": self.generation,
            "fitness": self.fitness,
            "name": self.name,
            "mutation_history": self.mutation_history,
            "architecture": self.architecture,
        }

    @staticmethod
    def from_dict(d: dict) -> "Chip":
        ct = ChipType(d["chip_type"])
        c = Chip(
            chip_type=ct,
            bit_width=d["bit_width"],
            core_count=d["core_count"],
            pipeline_stages=d["pipeline_stages"],
            cache_kb=d["cache_kb"],
            units=[UnitBlock.from_dict(u) for u in d["units"]],
            generation=d["generation"],
            fitness=d["fitness"],
            name=d["name"],
            mutation_history=d.get("mutation_history", []),
            architecture=d.get("architecture"),
        )
        return c

    def summary(self) -> str:
        lines = [
            f"Name:       {self.name}",
            f"Type:       {self.chip_type.value}",
            f"Bit Width:  {self.bit_width}",
            f"Cores:      {self.core_count}",
            f"Pipeline:   {self.pipeline_stages} stages",
            f"Cache:      {self.cache_kb} KB",
            f"Fitness:    {self.fitness:.4f}",
            f"Generation: {self.generation}",
            f"Novel Blks: {self.novel_block_count()}",
            f"Units:      {len(self.units)} types, {self.total_cells()} blocks",
        ]
        return "\n".join(lines)

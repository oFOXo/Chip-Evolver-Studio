"""
Chip Architecture Model — tracks ISA, interconnect topology,
memory hierarchy, execution model, and voltage/clock domains.
Architecture properties are evolvable alongside unit blocks.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict

ISA_TYPES = [
    "RISC", "CISC", "VLIW", "EPIC", "Superscalar",
    "Neuromorphic", "Dataflow", "Stochastic", "Quantum-Inspired",
    "Approximate", "Near-Memory", "Wave-Based", "Reconfigurable",
    "Hyperdimensional", "Spiking-Neural",
]

INTERCONNECTS = [
    "Shared Bus", "Crossbar Switch", "Mesh NoC", "Torus NoC",
    "Ring", "Fat Tree", "Butterfly", "Dragonfly",
    "Optical Interconnect", "Die-to-Die HBI", "Chiplet UCIe",
    "Distributed Shared Mem", "Global Addr Space",
]

MEMORY_MODELS = [
    "Flat SRAM", "Banked SRAM", "Scratchpad", "HBM2e",
    "3D-Stacked DRAM", "NVM Persistent", "In-Memory Compute",
    "Processing-in-Memory", "Near-Data DRAM", "ReRAM",
    "MRAM", "Phase-Change Mem", "Photonic DRAM",
]

EXECUTION_MODELS = [
    "In-Order", "Out-of-Order", "Speculative", "Wave Pipelining",
    "Dataflow Execution", "SIMT", "SPMD", "Barrel Processor",
    "Event-Driven", "Asynchronous", "Approximate Execution",
    "Stochastic Execution", "Token-Passing Dataflow",
]

PIPELINE_ARCHS = [
    "Linear 5-Stage", "Linear 7-Stage", "Linear 11-Stage",
    "Superscalar 2-wide", "Superscalar 4-wide", "Superscalar 8-wide",
    "VLIW 4-slot", "VLIW 8-slot", "Out-of-Order 128-ROB",
    "Out-of-Order 256-ROB", "Barrel 4-thread", "Barrel 8-thread",
    "Decoupled Access-Execute", "Elastic Pipeline", "Wavefront",
]

VOLTAGE_DOMAINS = [
    "Single VDD", "Dual VDD", "Multi-VDD DVFS",
    "Near-Threshold Logic", "Sub-Threshold Logic",
    "Dynamic Voltage Scaling", "Adaptive Body Bias",
    "Adiabatic Logic", "Resonant Clock", "Near-Zero Power",
]

PROCESS_NODES = [
    "7nm", "5nm", "3nm", "2nm", "1.4nm",
    "28nm (mature)", "14nm FinFET", "7nm EUV", "5nm EUV", "2nm GAAFET",
    "3nm MBCFET", "1nm nanosheet (projected)",
]

CLOCK_TOPOLOGIES = [
    "H-Tree", "Grid", "Spine", "Mesh", "Resonant Ring",
    "Optical Clock", "Distributed PLL", "GALS (async islands)",
    "Mesochronous", "Plesiochronous",
]


@dataclass
class ChipArchitecture:
    isa: str = "RISC"
    interconnect: str = "Shared Bus"
    memory_model: str = "Flat SRAM"
    execution_model: str = "In-Order"
    pipeline_arch: str = "Linear 5-Stage"
    voltage_domain: str = "Single VDD"
    process_node: str = "7nm"
    clock_topology: str = "H-Tree"
    special_features: List[str] = field(default_factory=list)

    # Derived metrics (computed)
    area_mm2: float = 1.0
    power_mw: float = 100.0
    freq_ghz: float = 1.0
    ipc: float = 1.0

    def compute_derived(self, chip):
        """Compute approximate area, power, frequency, IPC from arch + chip params."""
        # Base from process node
        node_scale = {
            "28nm": 4.0, "14nm": 2.5, "7nm": 1.0, "5nm": 0.7,
            "3nm": 0.5, "2nm": 0.35, "1nm": 0.25, "1.4nm": 0.3,
        }
        node_key = next((k for k in node_scale if k in self.process_node), "7nm")
        ns = node_scale[node_key]

        total_blocks = sum(u.count for u in chip.units)
        self.area_mm2 = round(ns * (chip.bit_width / 32) * total_blocks * 0.08 * chip.core_count, 3)

        # Power
        vd_factor = {"Single VDD": 1.0, "Near-Threshold": 0.3, "Sub-Threshold": 0.15,
                     "Multi-VDD DVFS": 0.7, "Adiabatic Logic": 0.2}.get(
            next((k for k in ["Near-Threshold","Sub-Threshold","Multi-VDD","Adiabatic"] if k in self.voltage_domain), "Single VDD"),
            1.0
        )
        self.power_mw = round(ns * vd_factor * chip.core_count * chip.bit_width * total_blocks * 0.12, 2)

        # Frequency (GHz)
        freq_base = {"Linear 5-Stage": 3.5, "Linear 7-Stage": 4.0, "Linear 11-Stage": 4.5,
                     "Superscalar": 3.8, "Out-of-Order": 3.5, "Barrel": 2.5,
                     "Wave": 5.0, "VLIW": 2.8}.get(
            self.pipeline_arch.split()[0], 3.0
        )
        self.freq_ghz = round(freq_base / ns, 2)

        # IPC
        ipc_map = {"In-Order": 1.0, "Out-of-Order": 3.5, "Superscalar": 2.5,
                   "SIMT": 1.0, "VLIW": 2.0, "Speculative": 3.0,
                   "Dataflow": 4.0, "Wave": 1.5, "Barrel": 1.2}
        self.ipc = ipc_map.get(self.execution_model.split()[0], 1.5)

    def arch_fitness_bonus(self) -> float:
        """Return a fitness multiplier from architecture choices."""
        bonus = 1.0
        # ISA bonuses
        isa_bonus = {"RISC": 1.05, "Superscalar": 1.15, "VLIW": 1.1,
                     "Neuromorphic": 1.3, "Dataflow": 1.2, "Reconfigurable": 1.25,
                     "Quantum-Inspired": 1.4, "Hyperdimensional": 1.35,
                     "Stochastic": 1.2, "Near-Memory": 1.15}
        bonus *= isa_bonus.get(self.isa, 1.0)

        # Memory bonuses
        mem_bonus = {"HBM2e": 1.2, "3D-Stacked DRAM": 1.25, "Processing-in-Memory": 1.4,
                     "In-Memory Compute": 1.35, "Near-Data DRAM": 1.2, "NVM Persistent": 1.1}
        bonus *= mem_bonus.get(self.memory_model, 1.0)

        # Interconnect bonuses
        ic_bonus = {"Optical Interconnect": 1.3, "Chiplet UCIe": 1.2,
                    "Dragonfly": 1.15, "Fat Tree": 1.1, "Die-to-Die HBI": 1.25}
        bonus *= ic_bonus.get(self.interconnect, 1.0)

        return round(bonus, 4)

    def to_dict(self) -> dict:
        return {
            "isa": self.isa,
            "interconnect": self.interconnect,
            "memory_model": self.memory_model,
            "execution_model": self.execution_model,
            "pipeline_arch": self.pipeline_arch,
            "voltage_domain": self.voltage_domain,
            "process_node": self.process_node,
            "clock_topology": self.clock_topology,
            "special_features": self.special_features,
            "area_mm2": self.area_mm2,
            "power_mw": self.power_mw,
            "freq_ghz": self.freq_ghz,
            "ipc": self.ipc,
        }

    @staticmethod
    def from_dict(d: dict) -> "ChipArchitecture":
        arch = ChipArchitecture(
            isa=d.get("isa", "RISC"),
            interconnect=d.get("interconnect", "Shared Bus"),
            memory_model=d.get("memory_model", "Flat SRAM"),
            execution_model=d.get("execution_model", "In-Order"),
            pipeline_arch=d.get("pipeline_arch", "Linear 5-Stage"),
            voltage_domain=d.get("voltage_domain", "Single VDD"),
            process_node=d.get("process_node", "7nm"),
            clock_topology=d.get("clock_topology", "H-Tree"),
            special_features=d.get("special_features", []),
            area_mm2=d.get("area_mm2", 1.0),
            power_mw=d.get("power_mw", 100.0),
            freq_ghz=d.get("freq_ghz", 1.0),
            ipc=d.get("ipc", 1.0),
        )
        return arch

    def summary_lines(self) -> List[str]:
        return [
            f"ISA:           {self.isa}",
            f"Interconnect:  {self.interconnect}",
            f"Memory:        {self.memory_model}",
            f"Execution:     {self.execution_model}",
            f"Pipeline:      {self.pipeline_arch}",
            f"Voltage:       {self.voltage_domain}",
            f"Process Node:  {self.process_node}",
            f"Clock:         {self.clock_topology}",
            f"Area:          {self.area_mm2} mm²",
            f"Power:         {self.power_mw} mW",
            f"Frequency:     {self.freq_ghz} GHz",
            f"IPC:           {self.ipc}",
        ]


ARCH_MUTATIONS = [
    "mutate_isa", "mutate_interconnect", "mutate_memory",
    "mutate_execution", "mutate_pipeline", "mutate_voltage",
    "mutate_process_node", "mutate_clock",
]

def mutate_architecture(arch: ChipArchitecture) -> tuple:
    """Randomly mutate one architecture dimension. Returns (new_arch, description)."""
    import copy
    a = copy.deepcopy(arch)
    which = random.choice(ARCH_MUTATIONS)

    if which == "mutate_isa":
        old = a.isa
        a.isa = random.choice([x for x in ISA_TYPES if x != old])
        return a, f"ISA: {old} → {a.isa}"
    elif which == "mutate_interconnect":
        old = a.interconnect
        a.interconnect = random.choice([x for x in INTERCONNECTS if x != old])
        return a, f"Interconnect: {old} → {a.interconnect}"
    elif which == "mutate_memory":
        old = a.memory_model
        a.memory_model = random.choice([x for x in MEMORY_MODELS if x != old])
        return a, f"Memory: {old} → {a.memory_model}"
    elif which == "mutate_execution":
        old = a.execution_model
        a.execution_model = random.choice([x for x in EXECUTION_MODELS if x != old])
        return a, f"Execution: {old} → {a.execution_model}"
    elif which == "mutate_pipeline":
        old = a.pipeline_arch
        a.pipeline_arch = random.choice([x for x in PIPELINE_ARCHS if x != old])
        return a, f"Pipeline: {old} → {a.pipeline_arch}"
    elif which == "mutate_voltage":
        old = a.voltage_domain
        a.voltage_domain = random.choice([x for x in VOLTAGE_DOMAINS if x != old])
        return a, f"Voltage: {old} → {a.voltage_domain}"
    elif which == "mutate_process_node":
        old = a.process_node
        a.process_node = random.choice([x for x in PROCESS_NODES if x != old])
        return a, f"Process: {old} → {a.process_node}"
    elif which == "mutate_clock":
        old = a.clock_topology
        a.clock_topology = random.choice([x for x in CLOCK_TOPOLOGIES if x != old])
        return a, f"Clock: {old} → {a.clock_topology}"

    return a, "arch unchanged"

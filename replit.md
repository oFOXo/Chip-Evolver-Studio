# Workspace

## Overview

pnpm workspace monorepo using TypeScript + Python chip generator app.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Chip Generator App

A RISC-V & novel chip design tool with RL-based evolution, architecture mutation, novel block invention, and code generation.

- **Location**: `chip_generator/`
- **Entry point**: `chip_generator/main.py`
- **Language**: Python 3.11 + Flask
- **Workflow**: "Chip Generator" — port 5000 (via $PORT)

### Python modules

| File | Purpose |
|---|---|
| `chip.py` | Chip data model, UnitBlock, ChipType enum, fitness computation |
| `ai_evolution.py` | Q-Learning RL agent, MutationEngine (19 mutation types), EvolutionEngine |
| `architecture.py` | ChipArchitecture model (ISA, interconnect, memory, execution, physical) |
| `novel_blocks.py` | BlockRegistry, BlockSpec, invent/mutate/combine novel blocks |
| `codegen.py` | Assembly (RISC-V), VHDL, Verilog code generation |
| `save_state.py` | JSON save/load/autosave/hall-of-fame |
| `main.py` | Flask REST API (all endpoints) |
| `templates/index.html` | Full HTML5 Canvas UI with 4 tabs |

### Supported Chip Types (18)
RISC-V (8/16/32/64/128-bit), NPU, DPU, TPU, GPU, APU, VPU, DSP, QPU (quantum), NDP, MCU, FPGA, ASIC, SPU, IPU, XPU, BPU, EPU

### Mutation Types (19)
- **Block-level**: add_unit, remove_unit, scale_unit, swap_units, merge_units, split_unit, random_unit_type
- **Chip parameters**: change_bitwidth, change_cores, change_pipeline, change_cache
- **Novel block invention**: invent_block, mutate_novel_block, combine_novel_blocks, add_discovered_block
- **Architecture evolution**: mutate_architecture, upgrade_isa, upgrade_memory, upgrade_interconnect

### Architecture Dimensions (evolvable)
- ISA (15 types): RISC, CISC, VLIW, Neuromorphic, Dataflow, Stochastic, Quantum-Inspired, Hyperdimensional, etc.
- Interconnect (13 types): Bus, Crossbar, Mesh NoC, Torus, Ring, Fat Tree, Optical, Chiplet UCIe, etc.
- Memory (13 types): Flat SRAM, HBM2e, 3D-Stacked, Processing-in-Memory, NVM, ReRAM, MRAM, etc.
- Execution (13 types): In-Order, Out-of-Order, Speculative, SIMT, Dataflow, Wave Pipelining, etc.
- Pipeline (15 archs): Linear 5/7/11-Stage, Superscalar 2/4/8-wide, OoO 128/256-ROB, etc.
- Voltage Domain (10 types): Single VDD, Near-Threshold, Sub-Threshold, DVFS, Adiabatic, etc.
- Process Node (12 nodes): 28nm → 7nm EUV → 3nm MBCFET → 2nm GAAFET → 1nm nanosheet
- Clock Topology (10 types): H-Tree, Grid, Mesh, Resonant Ring, Optical Clock, GALS, etc.

### Novel Block System
- Procedurally generated block names (prefix + core + suffix combinations)
- 40 capability types (matrix_ops, fft, neural_activate, attention_head, transformer_core, etc.)
- Blocks have fitness weight, power factor, and capability tags
- Registry persists to `saves/block_registry.json`
- Blocks can be mutated into variants or combined into hybrids

### Code Generation
- **RISC-V Assembly**: Unit-by-unit op sequences, novel block stubs, ISA-aware comments
- **VHDL**: Full entity/architecture with pipeline registers, unit submodules, port maps
- **Verilog**: SystemVerilog-compatible module with packages, always_ff, unit instantiations

### UI Tabs
1. **Canvas** — chip pixel art visualization + population panel + mutation history
2. **Architecture** — live dropdowns for all 8 arch dimensions + derived metrics (area, power, freq, IPC)
3. **Code** — Assembly/VHDL/Verilog with copy + download
4. **Block Registry** — all discovered novel blocks with capabilities + invent button

### API Endpoints
- `GET /api/meta` — chip types, bit widths, mutation types, arch options, block count
- `POST /api/generate` — create new chip
- `POST /api/mutate_once` — single RL mutation step
- `POST /api/evolve/start` — start multi-step evolution (background thread)
- `POST /api/evolve/stop` — stop evolution
- `GET /api/evolve/status` — poll: chip, log, population, discoveries, epsilon
- `POST /api/architecture/update` — live arch dimension update
- `GET /api/blocks/registry` — all discovered novel blocks
- `POST /api/blocks/invent` — manually invent a block
- `GET /api/codegen/<assembly|vhdl|verilog>` — generate code
- `POST /api/save`, `POST /api/load`, `GET /api/saves`, `GET /api/hall_of_fame`

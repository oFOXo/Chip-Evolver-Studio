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

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.

## Chip Generator App

A RISC-V & novel chip design tool with RL-based evolution.

- **Location**: `chip_generator/`
- **Entry point**: `chip_generator/main.py`
- **Language**: Python 3.11
- **Framework**: Flask web server + HTML5 Canvas pixel art
- **Workflow**: "Chip Generator" — runs on port 5000 (via $PORT)

### Python modules

- `chip.py` — Chip data models (ChipType enum, UnitBlock, Chip)
- `ai_evolution.py` — Q-Learning RL agent + MutationEngine + EvolutionEngine
- `save_state.py` — JSON save/load/autosave/hall-of-fame
- `main.py` — Flask REST API server
- `templates/index.html` — Full HTML5 Canvas UI

### Supported Chip Types

RISC-V (8/16/32/64/128-bit), NPU, DPU, TPU, GPU, APU, VPU, DSP, QPU (quantum), NDP, MCU, FPGA, ASIC, SPU, IPU, XPU, BPU, EPU

### Features

- Generate chips with configurable bit-width, cores, pipeline stages, cache
- 18 chip types including novel processing units
- RL Q-Learning agent evolves chips via random mutations
- Recursive multi-step evolution with adjustable mutation strength
- Pixel art visualization: each functional unit rendered as colored grid cells
- Save state / load state (JSON files in `chip_generator/saves/`)
- Autosave after every evolution
- Hall of Fame — top 20 evolved chips
- Population of 8 chips tracked per session

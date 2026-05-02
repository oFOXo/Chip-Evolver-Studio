"""
Code generation for chip designs.
Produces: RISC-V Assembly, VHDL, Verilog
"""

import re
from typing import List


def _safe_id(name: str) -> str:
    """Convert a name to a safe HDL identifier."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', name).lower()


def _unit_port_list(chip) -> List[str]:
    ports = []
    for u in chip.units:
        uid = _safe_id(u.name)
        for i in range(min(u.count, 4)):
            ports.append(f"{uid}_{i}")
    return ports


# ─── RISC-V Assembly ──────────────────────────────────────────────────────────

RISCV_PREAMBLE = """\
# ============================================================
# Auto-generated RISC-V Assembly
# Chip: {name}
# Type: {chip_type}  Bit-Width: {bit_width}  Cores: {cores}
# ISA:  {isa}  |  Pipeline: {pipeline}  |  Arch: {arch}
# ============================================================
    .section .text
    .global _start

_start:
"""

RISCV_UNIT_OPS = {
    "ALU":    [("# ALU: integer arithmetic", "add  t0, t1, t2"),
               ("# ALU: subtract",           "sub  t3, t0, t1"),
               ("# ALU: bitwise and",        "and  t4, t0, t2")],
    "FPU":    [("# FPU: float add",          "fadd.s f0, f1, f2"),
               ("# FPU: float mul",          "fmul.s f3, f0, f1"),
               ("# FPU: float div",          "fdiv.s f4, f3, f2")],
    "MUL":    [("# MUL: multiply",           "mul  t0, t1, t2"),
               ("# MUL: high word",          "mulh t3, t1, t2")],
    "DIV":    [("# DIV: divide",             "div  t0, t1, t2"),
               ("# DIV: remainder",          "rem  t3, t1, t2")],
    "LOAD":   [("# LOAD: load word",         "lw   t0, 0(a0)"),
               ("# LOAD: load byte",         "lb   t1, 4(a0)")],
    "STORE":  [("# STORE: store word",       "sw   t0, 0(a1)"),
               ("# STORE: store byte",       "sb   t1, 4(a1)")],
    "SIMD":   [("# SIMD: vector add (ext)",  "vadd.vv v0, v1, v2"),
               ("# SIMD: vector mul",        "vmul.vv v3, v0, v1")],
    "VEC":    [("# VEC: vector load",        "vle32.v v0, (a0)"),
               ("# VEC: vector store",       "vse32.v v0, (a1)")],
    "CACHE":  [("# CACHE: fence",            "fence rw, rw")],
    "TENSOR": [("# TENSOR: matmul loop stub","# [custom extension: tensor.mma t0,t1,t2]")],
    "ACCEL":  [("# ACCEL: accelerator call", "# [custom: accel.exec a0, a1, a2]")],
    "DMA":    [("# DMA: set src addr",       "li   a0, 0x10000000"),
               ("# DMA: set dst addr",       "li   a1, 0x20000000"),
               ("# DMA: trigger transfer",   "# [custom: dma.start a0, a1, a2]")],
    "CTRL":   [("# CTRL: branch on zero",    "beq  t0, zero, end"),
               ("# CTRL: unconditional jmp", "j    loop")],
    "IO":     [("# IO: write to mmio",       "sw   t0, 0(a5)"),
               ("# IO: read from mmio",      "lw   t1, 0(a5)")],
    "PRED":   [("# PRED: branch predict",    "# [hint: taken branch]")],
    "SCHED":  [("# SCHED: yield",            "# [custom: sched.yield]")],
    "INT":    [("# INT: set interrupt mask", "csrw mie, t0"),
               ("# INT: wait for interrupt", "wfi")],
}

RISCV_NOVEL_OP = """\
    # {name}: novel block ({caps})
    # [custom ISA extension: {id_}.exec a0, a1, a2]
    addi a0, zero, 0x{opcode:02X}   # block opcode
"""


def generate_assembly(chip, arch=None) -> str:
    arch_name = arch.pipeline_arch if arch else f"{chip.pipeline_stages}-stage"
    isa_name  = arch.isa if arch else "RISC"
    lines = [RISCV_PREAMBLE.format(
        name=chip.name, chip_type=chip.chip_type.value,
        bit_width=chip.bit_width, cores=chip.core_count,
        isa=isa_name, pipeline=arch_name, arch=arch_name,
    )]

    lines.append("    # ── Initialization ─────────────────────────────\n")
    lines.append("    li   sp, 0x80000000    # set stack pointer\n")
    lines.append("    li   gp, 0x90000000    # set global pointer\n")
    lines.append("    auipc ra, 0            # capture PC\n\n")

    lines.append("loop:\n")
    import random as _r
    from novel_blocks import BlockRegistry
    registry = BlockRegistry.get()

    seen = set()
    for u in chip.units:
        if u.name in seen:
            continue
        seen.add(u.name)
        ops = RISCV_UNIT_OPS.get(u.name)
        if ops:
            comment, instr = _r.choice(ops)
            lines.append(f"    {comment}\n")
            for _ in range(min(u.count, 3)):
                lines.append(f"    {instr}\n")
        else:
            # novel block
            spec = registry.get_spec(u.name)
            caps = ", ".join(spec.capabilities[:2]) if spec else "unknown"
            opcode = hash(u.name) & 0xFF
            lines.append(RISCV_NOVEL_OP.format(
                name=u.name, caps=caps, id_=_safe_id(u.name), opcode=opcode
            ))
        lines.append("\n")

    lines.append("end:\n")
    lines.append("    li   a0, 0           # exit code 0\n")
    lines.append("    li   a7, 93          # ecall: exit\n")
    lines.append("    ecall\n")
    lines.append("    j    end             # trap\n")

    return "".join(lines)


# ─── VHDL ────────────────────────────────────────────────────────────────────

VHDL_TEMPLATE = """\
-- ============================================================
-- Auto-generated VHDL
-- Chip  : {name}
-- Type  : {chip_type}  |  {bit_width}-bit  |  {cores} core(s)
-- ISA   : {isa}  |  Memory: {mem}  |  Process: {node}
-- Fitness: {fitness:.4f}  |  Generation: {gen}
-- ============================================================

library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

-- ── Package: unit constants ─────────────────────────────────
package {id_}_pkg is
  constant DATA_WIDTH  : integer := {bit_width};
  constant CORE_COUNT  : integer := {cores};
  constant CACHE_KB    : integer := {cache_kb};
  constant PIPE_STAGES : integer := {pipe_stages};
end package;

-- ── Top-level entity ────────────────────────────────────────
entity {id_} is
  generic (
    DATA_WIDTH  : integer := {bit_width};
    CORE_COUNT  : integer := {cores};
    PIPE_STAGES : integer := {pipe_stages}
  );
  port (
    clk       : in  std_logic;
    rst_n     : in  std_logic;
    instr_in  : in  std_logic_vector(31 downto 0);
    data_in   : in  std_logic_vector(DATA_WIDTH-1 downto 0);
    data_out  : out std_logic_vector(DATA_WIDTH-1 downto 0);
    irq       : in  std_logic;
    ready     : out std_logic;
    halt      : out std_logic
  );
end entity {id_};

architecture rtl of {id_} is

  -- ── Internal signals ──────────────────────────────────────
  signal pc         : unsigned(DATA_WIDTH-1 downto 0) := (others => '0');
  signal ir         : std_logic_vector(31 downto 0)   := (others => '0');
  signal alu_result : std_logic_vector(DATA_WIDTH-1 downto 0);
  signal pipeline_reg : std_logic_vector(DATA_WIDTH-1 downto 0);
  signal core_sel   : unsigned(7 downto 0)            := (others => '0');

{unit_signals}

begin

  -- ── Pipeline register chain ───────────────────────────────
  process(clk, rst_n)
  begin
    if rst_n = '0' then
      pc           <= (others => '0');
      ir           <= (others => '0');
      pipeline_reg <= (others => '0');
      ready        <= '0';
      halt         <= '0';
    elsif rising_edge(clk) then
      ir           <= instr_in;
      pipeline_reg <= data_in;
      pc           <= pc + 4;
      ready        <= '1';
    end if;
  end process;

  -- ── Core arbitration ─────────────────────────────────────
  process(clk)
  begin
    if rising_edge(clk) then
      if core_sel < CORE_COUNT - 1 then
        core_sel <= core_sel + 1;
      else
        core_sel <= (others => '0');
      end if;
    end if;
  end process;

  -- ── Functional unit instantiations ───────────────────────
{unit_instances}

  -- ── Output mux ───────────────────────────────────────────
  data_out <= alu_result when ir(6 downto 0) = "0110011" else
              pipeline_reg;

end architecture rtl;

{unit_components}
"""

VHDL_UNIT_SIGNAL = "  signal {id_}_out_{n} : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');\n"

VHDL_UNIT_INSTANCE = """\
  -- {name} (count={count})
  {id_}_inst_{n} : entity work.unit_{id_}
    generic map (DATA_WIDTH => DATA_WIDTH)
    port map (
      clk      => clk,
      rst_n    => rst_n,
      data_in  => pipeline_reg,
      data_out => {id_}_out_{n}
    );
"""

VHDL_UNIT_COMPONENT = """\
-- ── Unit: {name} ────────────────────────────────────────────
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity unit_{id_} is
  generic (DATA_WIDTH : integer := 32);
  port (
    clk      : in  std_logic;
    rst_n    : in  std_logic;
    data_in  : in  std_logic_vector(DATA_WIDTH-1 downto 0);
    data_out : out std_logic_vector(DATA_WIDTH-1 downto 0)
  );
end entity unit_{id_};

architecture rtl of unit_{id_} is
  signal reg : std_logic_vector(DATA_WIDTH-1 downto 0) := (others => '0');
begin
  -- {desc}
  process(clk, rst_n)
  begin
    if rst_n = '0' then
      reg <= (others => '0');
    elsif rising_edge(clk) then
      reg <= std_logic_vector(unsigned(data_in) + 1);  -- placeholder logic
    end if;
  end process;
  data_out <= reg;
end architecture rtl;

"""


def generate_vhdl(chip, arch=None) -> str:
    from novel_blocks import BlockRegistry
    registry = BlockRegistry.get()

    chip_id = _safe_id(chip.name)
    isa  = arch.isa  if arch else "RISC"
    mem  = arch.memory_model if arch else "Flat SRAM"
    node = arch.process_node if arch else "7nm"

    unit_signals = ""
    unit_instances = ""
    unit_components = ""
    seen = set()

    for u in chip.units:
        uid = _safe_id(u.name)
        for n in range(min(u.count, 4)):
            unit_signals += VHDL_UNIT_SIGNAL.format(id_=uid, n=n)
            unit_instances += VHDL_UNIT_INSTANCE.format(
                name=u.name, count=u.count, id_=uid, n=n)

        if uid not in seen:
            seen.add(uid)
            spec = registry.get_spec(u.name)
            desc = spec.description if spec else f"{u.name} functional unit"
            unit_components += VHDL_UNIT_COMPONENT.format(
                name=u.name, id_=uid, desc=desc)

    return VHDL_TEMPLATE.format(
        name=chip.name, chip_type=chip.chip_type.value,
        bit_width=chip.bit_width, cores=chip.core_count,
        isa=isa, mem=mem, node=node,
        fitness=chip.fitness, gen=chip.generation,
        id_=chip_id, cache_kb=chip.cache_kb,
        pipe_stages=chip.pipeline_stages,
        unit_signals=unit_signals,
        unit_instances=unit_instances,
        unit_components=unit_components,
    )


# ─── Verilog ─────────────────────────────────────────────────────────────────

VERILOG_TEMPLATE = """\
// ============================================================
// Auto-generated Verilog (SystemVerilog-compatible)
// Chip  : {name}
// Type  : {chip_type}  |  {bit_width}-bit  |  {cores} core(s)
// ISA   : {isa}  |  Memory: {mem}  |  Process: {node}
// Fitness: {fitness:.4f}  |  Generation: {gen}
// ============================================================

`timescale 1ns/1ps
`default_nettype none

// ── Parameters package ──────────────────────────────────────
package {id_}_pkg;
  parameter int DATA_WIDTH  = {bit_width};
  parameter int CORE_COUNT  = {cores};
  parameter int CACHE_KB    = {cache_kb};
  parameter int PIPE_STAGES = {pipe_stages};
endpackage

// ── Top module ──────────────────────────────────────────────
module {id_} #(
  parameter int DATA_WIDTH  = {bit_width},
  parameter int CORE_COUNT  = {cores},
  parameter int PIPE_STAGES = {pipe_stages}
)(
  input  logic                      clk,
  input  logic                      rst_n,
  input  logic [31:0]               instr_in,
  input  logic [DATA_WIDTH-1:0]     data_in,
  output logic [DATA_WIDTH-1:0]     data_out,
  input  logic                      irq,
  output logic                      ready,
  output logic                      halt
);

  // ── Internal signals ────────────────────────────────────
  logic [DATA_WIDTH-1:0] pc;
  logic [DATA_WIDTH-1:0] pipeline_reg [0:PIPE_STAGES-1];
  logic [DATA_WIDTH-1:0] alu_result;
  logic [$clog2(CORE_COUNT)-1:0] core_sel;
  logic [31:0] ir;

{unit_wires}

  // ── Pipeline register chain ─────────────────────────────
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      pc          <= '0;
      ir          <= '0;
      ready       <= 1'b0;
      halt        <= 1'b0;
      core_sel    <= '0;
    end else begin
      ir          <= instr_in;
      pipeline_reg[0] <= data_in;
      for (int s = 1; s < PIPE_STAGES; s++)
        pipeline_reg[s] <= pipeline_reg[s-1];
      pc          <= pc + 4;
      ready       <= 1'b1;
      if (core_sel == CORE_COUNT-1) core_sel <= '0;
      else core_sel <= core_sel + 1;
    end
  end

  // ── Functional unit instantiations ──────────────────────
{unit_instances}

  // ── Output mux ──────────────────────────────────────────
  assign data_out = (instr_in[6:0] == 7'b0110011) ? alu_result : pipeline_reg[PIPE_STAGES-1];

endmodule

// ── Unit submodules ──────────────────────────────────────────
{unit_modules}
"""

VERILOG_WIRE = "  logic [DATA_WIDTH-1:0] {id_}_out_{n};\n"

VERILOG_INSTANCE = """\
  // {name} unit {n} (of {count})
  unit_{id_} #(.DATA_WIDTH(DATA_WIDTH)) u_{id_}_{n} (
    .clk     (clk),
    .rst_n   (rst_n),
    .data_in (pipeline_reg[0]),
    .data_out({id_}_out_{n})
  );
"""

VERILOG_MODULE = """\
// {name} — {desc}
module unit_{id_} #(
  parameter int DATA_WIDTH = 32
)(
  input  logic                  clk,
  input  logic                  rst_n,
  input  logic [DATA_WIDTH-1:0] data_in,
  output logic [DATA_WIDTH-1:0] data_out
);
  logic [DATA_WIDTH-1:0] reg_q;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) reg_q <= '0;
    else        reg_q <= data_in + 1;  // placeholder logic
  end

  assign data_out = reg_q;
endmodule

"""


def generate_verilog(chip, arch=None) -> str:
    from novel_blocks import BlockRegistry
    registry = BlockRegistry.get()

    chip_id = _safe_id(chip.name)
    isa  = arch.isa  if arch else "RISC"
    mem  = arch.memory_model if arch else "Flat SRAM"
    node = arch.process_node if arch else "7nm"

    unit_wires = ""
    unit_instances = ""
    unit_modules = ""
    seen = set()

    for u in chip.units:
        uid = _safe_id(u.name)
        for n in range(min(u.count, 4)):
            unit_wires += VERILOG_WIRE.format(id_=uid, n=n)
            unit_instances += VERILOG_INSTANCE.format(
                name=u.name, count=u.count, id_=uid, n=n)

        if uid not in seen:
            seen.add(uid)
            spec = registry.get_spec(u.name)
            desc = spec.description if spec else f"{u.name} functional unit"
            unit_modules += VERILOG_MODULE.format(
                name=u.name, id_=uid, desc=desc)

    return VERILOG_TEMPLATE.format(
        name=chip.name, chip_type=chip.chip_type.value,
        bit_width=chip.bit_width, cores=chip.core_count,
        isa=isa, mem=mem, node=node,
        fitness=chip.fitness, gen=chip.generation,
        id_=chip_id, cache_kb=chip.cache_kb,
        pipe_stages=chip.pipeline_stages,
        unit_wires=unit_wires,
        unit_instances=unit_instances,
        unit_modules=unit_modules,
    )

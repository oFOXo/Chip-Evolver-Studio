"""
Turtle-based 2D pixel art visualizer for chips.
Draws chip blocks, labels, and fitness bars.
"""

import turtle
import math
import time
from typing import List, Tuple, Optional
from chip import Chip, UnitBlock, CHIP_TYPE_COLORS, UNIT_COLORS

GRID_PIXEL = 18
CHIP_BORDER = 12
LABEL_HEIGHT = 24
FOOTER_HEIGHT = 40
CANVAS_BG = "#0a0a1a"
BORDER_COLOR = "#00ff88"
TEXT_COLOR = "#e0e0ff"
DIM_COLOR = "#334455"
GLOW_COLOR = "#00ffaa"

_t: Optional[turtle.Turtle] = None
_screen: Optional[turtle.Screen] = None
_canvas_w = 600
_canvas_h = 500


def _px(val):
    return int(val)


def setup_canvas(screen: turtle.Screen, width: int, height: int):
    global _t, _screen, _canvas_w, _canvas_h
    _screen = screen
    _canvas_w = width
    _canvas_h = height
    _t = turtle.RawTurtle(screen)
    _t.hideturtle()
    _t.speed(0)
    _t.penup()


def _goto(x, y):
    _t.goto(x, y)


def _rect(x, y, w, h, fill, outline=None):
    _t.penup()
    _t.goto(x, y)
    _t.fillcolor(fill)
    _t.pendown()
    if outline:
        _t.pencolor(outline)
        _t.pensize(1)
    else:
        _t.pencolor(fill)
        _t.pensize(0)
    _t.begin_fill()
    _t.goto(x + w, y)
    _t.goto(x + w, y - h)
    _t.goto(x, y - h)
    _t.goto(x, y)
    _t.end_fill()
    _t.penup()


def _text(x, y, msg, color=TEXT_COLOR, size=8, bold=False, align="left"):
    _t.penup()
    _t.goto(x, y)
    _t.pencolor(color)
    style = "bold" if bold else "normal"
    _t.write(msg, align=align, font=("Courier", size, style))


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def darken(hex_color: str, factor: float = 0.5) -> str:
    r, g, b = hex_to_rgb(hex_color)
    return "#{:02x}{:02x}{:02x}".format(int(r * factor), int(g * factor), int(b * factor))


def build_cell_grid(chip: Chip, cols: int) -> List[List[Tuple[str, str]]]:
    """Build a 2D grid of (color, label) cells from chip units."""
    cells = []
    for u in chip.units:
        for _ in range(u.count):
            cells.append((u.color, u.name[:3]))

    rows_needed = math.ceil(len(cells) / cols) if cells else 1
    grid = []
    idx = 0
    for r in range(rows_needed):
        row = []
        for c in range(cols):
            if idx < len(cells):
                row.append(cells[idx])
                idx += 1
            else:
                row.append((DIM_COLOR, ""))
        grid.append(row)
    return grid


def draw_chip(chip: Chip, origin_x: float, origin_y: float, cols: int = 12):
    """Draw the chip as a pixel art grid at the given canvas origin (top-left)."""
    global _t
    if _t is None:
        return

    _t.clear()

    grid = build_cell_grid(chip, cols)
    rows = len(grid)

    chip_w = cols * GRID_PIXEL + CHIP_BORDER * 2
    chip_h = rows * GRID_PIXEL + CHIP_BORDER * 2 + LABEL_HEIGHT

    chip_color = CHIP_TYPE_COLORS.get(chip.chip_type, "#00ff88")

    _rect(origin_x, origin_y, chip_w + 4, chip_h + FOOTER_HEIGHT + 4, darken(chip_color, 0.15), chip_color)
    _rect(origin_x + 2, origin_y - 2, chip_w, chip_h + FOOTER_HEIGHT, CANVAS_BG, None)

    _text(
        origin_x + chip_w / 2,
        origin_y - LABEL_HEIGHT + 4,
        chip.name,
        color=chip_color,
        size=9,
        bold=True,
        align="center"
    )

    gx = origin_x + CHIP_BORDER
    gy = origin_y - LABEL_HEIGHT

    for r, row in enumerate(grid):
        for c, (color, label) in enumerate(row):
            cx = gx + c * GRID_PIXEL
            cy = gy - r * GRID_PIXEL
            _rect(cx, cy, GRID_PIXEL - 1, GRID_PIXEL - 1, color, darken(color, 0.6))
            if label and GRID_PIXEL >= 14:
                lbl_size = 5 if GRID_PIXEL < 18 else 6
                _text(cx + 1, cy - GRID_PIXEL + 2, label[:3], color=darken(color, 1.8) if color != DIM_COLOR else "#333", size=lbl_size)

    legend_y = origin_y - chip_h + 8
    drawn_names = set()
    lx = origin_x + 4
    for u in chip.units:
        if u.name not in drawn_names:
            _rect(lx, legend_y, 10, 10, u.color, None)
            _text(lx + 12, legend_y - 9, u.name[:5], color=u.color, size=6)
            lx += 52
            if lx > origin_x + chip_w - 30:
                lx = origin_x + 4
                legend_y -= 14
            drawn_names.add(u.name)

    stats_y = origin_y - chip_h + FOOTER_HEIGHT - 10
    fitness_pct = min(chip.fitness / 50.0, 1.0)
    bar_w = chip_w - 8
    _rect(origin_x + 4, stats_y, bar_w, 8, "#112233", None)
    bar_fill = int(bar_w * fitness_pct)
    if bar_fill > 0:
        _rect(origin_x + 4, stats_y, bar_fill, 8, chip_color, None)
    _text(origin_x + 4, stats_y - 16,
          f"Fitness: {chip.fitness:.3f}  |  Gen: {chip.generation}  |  {chip.chip_type.value} {chip.bit_width}-bit  |  Cores: {chip.core_count}",
          color=TEXT_COLOR, size=7)

    _screen.update()


def draw_evolution_overlay(gen: int, total: int, desc: str, reward: float, origin_x: float, origin_y: float):
    """Draw a small evolving overlay text."""
    if _t is None:
        return
    oy = origin_y - 8
    _rect(origin_x, oy, 400, 20, "#0a0a1a", None)
    color = "#00ff88" if reward >= 0 else "#ff4444"
    _text(origin_x + 4, oy - 16,
          f"Evolving... Gen {gen}/{total}  {desc}  reward: {reward:+.3f}",
          color=color, size=8)
    _screen.update()


def animate_pulse(chip: Chip, origin_x: float, origin_y: float, cols: int = 12):
    """Animate a brief pulse on the chip border."""
    if _t is None:
        return
    chip_color = CHIP_TYPE_COLORS.get(chip.chip_type, "#00ff88")
    grid = build_cell_grid(chip, cols)
    rows = len(grid)
    chip_w = cols * GRID_PIXEL + CHIP_BORDER * 2
    chip_h = rows * GRID_PIXEL + CHIP_BORDER * 2 + LABEL_HEIGHT
    for _ in range(3):
        _t.penup()
        _t.goto(origin_x - 3, origin_y + 3)
        _t.pencolor(chip_color)
        _t.pensize(3)
        _t.pendown()
        _t.goto(origin_x + chip_w + 7, origin_y + 3)
        _t.goto(origin_x + chip_w + 7, origin_y - chip_h - FOOTER_HEIGHT - 7)
        _t.goto(origin_x - 3, origin_y - chip_h - FOOTER_HEIGHT - 7)
        _t.goto(origin_x - 3, origin_y + 3)
        _t.penup()
        _screen.update()
        time.sleep(0.05)
        _rect(origin_x - 4, origin_y + 4, chip_w + 12, chip_h + FOOTER_HEIGHT + 12, CANVAS_BG, None)
        _screen.update()
        time.sleep(0.05)

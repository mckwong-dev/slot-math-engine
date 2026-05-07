from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Sequence

Symbol = str
Grid = list[list[Symbol]]  # grid[reel][row]


@dataclass(frozen=True)
class ReelStop:
    reel: int
    stop_index: int
    visible: list[Symbol]


class ReelSet:
    def __init__(self, strips: Sequence[Sequence[Symbol]], rows: int) -> None:
        if rows <= 0:
            raise ValueError("rows must be positive")
        if len(strips) < 3:
            raise ValueError("at least three reels are required")
        for i, strip in enumerate(strips):
            if len(strip) < rows:
                raise ValueError(f"reel {i} is shorter than visible rows")
        self.strips = [list(strip) for strip in strips]
        self.rows = rows

    @property
    def reel_count(self) -> int:
        return len(self.strips)

    def spin(self, rng: Random) -> tuple[list[ReelStop], Grid]:
        stops: list[ReelStop] = []
        grid: Grid = []
        for reel_index, strip in enumerate(self.strips):
            stop_index = rng.randrange(len(strip))
            visible = [strip[(stop_index + offset) % len(strip)] for offset in range(self.rows)]
            stops.append(ReelStop(reel=reel_index, stop_index=stop_index, visible=visible))
            grid.append(visible)
        return stops, grid

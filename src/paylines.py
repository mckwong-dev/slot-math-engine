from __future__ import annotations

from typing import Sequence

Payline = list[int]


class PaylineSet:
    def __init__(self, paylines: Sequence[Sequence[int]], rows: int, reel_count: int) -> None:
        if not paylines:
            raise ValueError("paylines are required for payline games")
        self.paylines: list[Payline] = []
        for idx, line in enumerate(paylines):
            if len(line) != reel_count:
                raise ValueError(f"payline {idx} length does not match reel count")
            clean_line = []
            for row in line:
                if not isinstance(row, int) or row < 0 or row >= rows:
                    raise ValueError(f"payline {idx} contains invalid row {row}")
                clean_line.append(row)
            self.paylines.append(clean_line)

    def active(self, active_lines: int | None = None) -> list[Payline]:
        if active_lines is None:
            return self.paylines
        if active_lines <= 0 or active_lines > len(self.paylines):
            raise ValueError(f"active_lines must be between 1 and {len(self.paylines)}")
        return self.paylines[:active_lines]

from __future__ import annotations

from dataclasses import asdict, dataclass
from random import Random
from typing import Any

try:
    from .paylines import PaylineSet
    from .paytable import Paytable
    from .reels import Grid, ReelSet, ReelStop
except ImportError:  # Allows python src/engine.py-style execution during local experiments.
    from paylines import PaylineSet
    from paytable import Paytable
    from reels import Grid, ReelSet, ReelStop


@dataclass(frozen=True)
class WinEvent:
    type: str
    symbol: str
    count: int
    multiplier: float
    win: float
    line_index: int | None = None
    positions: list[tuple[int, int]] | None = None


@dataclass(frozen=True)
class FeatureEvent:
    type: str
    symbol: str
    count: int
    value: int | float


@dataclass(frozen=True)
class SpinResult:
    total_bet: float
    total_win: float
    grid: Grid
    stops: list[ReelStop]
    wins: list[WinEvent]
    features: list[FeatureEvent]
    capped: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_bet": self.total_bet,
            "total_win": self.total_win,
            "grid": self.grid,
            "stops": [asdict(stop) for stop in self.stops],
            "wins": [asdict(win) for win in self.wins],
            "features": [asdict(feature) for feature in self.features],
            "capped": self.capped,
        }


class SlotMathEngine:
    def __init__(self, config: dict[str, Any], rng: Random | None = None) -> None:
        self.config = config
        game = config["game"]
        self.rows = int(game["rows"])
        self.mode = game.get("mode", "paylines")
        self.max_win_multiplier = float(game.get("max_win_multiplier", "inf"))

        self.symbols = Paytable.build_symbols(config["symbols"])
        self.reels = ReelSet(config["reels"], self.rows)
        self.paytable = Paytable(config["paytable"], self.symbols)
        self.paylines = None
        if self.mode == "paylines":
            self.paylines = PaylineSet(config["paylines"], self.rows, self.reels.reel_count)
        elif self.mode != "ways":
            raise ValueError("game.mode must be 'paylines' or 'ways'")
        self.rng = rng or Random()

    def spin(self, bet_per_line: float, active_lines: int | None = None) -> SpinResult:
        if bet_per_line <= 0:
            raise ValueError("bet_per_line must be positive")

        if self.mode == "paylines":
            assert self.paylines is not None
            active_paylines = self.paylines.active(active_lines)
            total_bet = bet_per_line * len(active_paylines)
        else:
            active_paylines = []
            total_bet = bet_per_line

        stops, grid = self.reels.spin(self.rng)
        wins: list[WinEvent] = []

        if self.mode == "paylines":
            wins.extend(self._evaluate_lines(grid, active_paylines, bet_per_line))
        else:
            wins.extend(self._evaluate_ways(grid, bet_per_line))

        wins.extend(self._evaluate_scatters(grid, total_bet))
        features = self._evaluate_features(grid)

        raw_win = sum(w.win for w in wins)
        max_win = total_bet * self.max_win_multiplier
        total_win = min(raw_win, max_win)

        return SpinResult(
            total_bet=total_bet,
            total_win=total_win,
            grid=grid,
            stops=stops,
            wins=wins,
            features=features,
            capped=total_win < raw_win,
        )

    def _evaluate_lines(self, grid: Grid, paylines: list[list[int]], bet_per_line: float) -> list[WinEvent]:
        wins: list[WinEvent] = []
        for line_index, line in enumerate(paylines):
            line_symbols = [grid[reel][row] for reel, row in enumerate(line)]
            best = self._best_line_win(line_symbols)
            if best:
                symbol, count, multiplier = best
                wins.append(
                    WinEvent(
                        type="line",
                        symbol=symbol,
                        count=count,
                        multiplier=multiplier,
                        win=multiplier * bet_per_line,
                        line_index=line_index,
                        positions=[(reel, line[reel]) for reel in range(count)],
                    )
                )
        return wins

    def _best_line_win(self, line_symbols: list[str]) -> tuple[str, int, float] | None:
        best: tuple[str, int, float] | None = None
        for symbol in self.paytable.line.keys():
            count = 0
            for actual in line_symbols:
                if not self.paytable.matches(actual, symbol):
                    break
                count += 1
            multiplier = self.paytable.line_multiplier(symbol, count)
            if multiplier > 0 and (best is None or multiplier > best[2]):
                best = (symbol, count, multiplier)
        return best

    def _evaluate_ways(self, grid: Grid, bet_unit: float) -> list[WinEvent]:
        wins: list[WinEvent] = []
        for symbol, pays in self.paytable.line.items():
            matching_rows_by_reel: list[list[int]] = []
            for reel, visible in enumerate(grid):
                rows = [row for row, actual in enumerate(visible) if self.paytable.matches(actual, symbol)]
                if not rows:
                    break
                matching_rows_by_reel.append(rows)
            count = len(matching_rows_by_reel)
            multiplier = pays.get(count, 0.0)
            if multiplier > 0:
                ways = 1
                positions: list[tuple[int, int]] = []
                for reel, rows in enumerate(matching_rows_by_reel):
                    ways *= len(rows)
                    positions.extend((reel, row) for row in rows)
                wins.append(
                    WinEvent(
                        type="ways",
                        symbol=symbol,
                        count=count,
                        multiplier=multiplier,
                        win=multiplier * ways * bet_unit,
                        positions=positions,
                    )
                )
        return wins

    def _evaluate_scatters(self, grid: Grid, total_bet: float) -> list[WinEvent]:
        wins: list[WinEvent] = []
        for symbol, pays in self.paytable.scatter.items():
            positions = [(reel, row) for reel, visible in enumerate(grid) for row, actual in enumerate(visible) if actual == symbol]
            count = len(positions)
            multiplier = pays.get(count, 0.0)
            if multiplier > 0:
                wins.append(
                    WinEvent(
                        type="scatter",
                        symbol=symbol,
                        count=count,
                        multiplier=multiplier,
                        win=multiplier * total_bet,
                        positions=positions,
                    )
                )
        return wins

    def _evaluate_features(self, grid: Grid) -> list[FeatureEvent]:
        free_spins = self.config.get("features", {}).get("free_spins")
        if not free_spins:
            return []
        symbol = free_spins["trigger_symbol"]
        count = sum(1 for visible in grid for actual in visible if actual == symbol)
        awarded = {int(k): int(v) for k, v in free_spins.get("trigger_counts", {}).items()}.get(count, 0)
        if awarded <= 0:
            return []
        return [FeatureEvent(type="free_spins_awarded", symbol=symbol, count=count, value=awarded)]

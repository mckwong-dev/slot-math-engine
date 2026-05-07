from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SymbolDef:
    symbol: str
    type: str
    substitutes_for: str | list[str] | None = None


class Paytable:
    def __init__(self, raw_paytable: dict[str, Any], symbols: dict[str, SymbolDef]) -> None:
        self.symbols = symbols
        self.line = self._normalise(raw_paytable.get("line", {}))
        self.scatter = self._normalise(raw_paytable.get("scatter", {}))

    def _normalise(self, table: dict[str, Any]) -> dict[str, dict[int, float]]:
        out: dict[str, dict[int, float]] = {}
        for symbol, pays in table.items():
            if symbol not in self.symbols:
                raise ValueError(f"paytable references unknown symbol {symbol}")
            out[symbol] = {int(count): float(multiplier) for count, multiplier in pays.items()}
        return out

    def line_multiplier(self, symbol: str, count: int) -> float:
        return self.line.get(symbol, {}).get(count, 0.0)

    def scatter_multiplier(self, symbol: str, count: int) -> float:
        return self.scatter.get(symbol, {}).get(count, 0.0)

    def matches(self, actual: str, target: str) -> bool:
        if actual == target:
            return True
        actual_def = self.symbols.get(actual)
        target_def = self.symbols.get(target)
        if not actual_def or actual_def.type != "wild":
            return False
        if actual_def.substitutes_for == "all":
            return bool(target_def and target_def.type == "regular")
        if isinstance(actual_def.substitutes_for, list):
            return target in actual_def.substitutes_for
        return False

    @staticmethod
    def build_symbols(raw_symbols: dict[str, Any]) -> dict[str, SymbolDef]:
        symbols: dict[str, SymbolDef] = {}
        for symbol, data in raw_symbols.items():
            symbols[symbol] = SymbolDef(
                symbol=symbol,
                type=str(data.get("type", "regular")),
                substitutes_for=data.get("substitutes_for"),
            )
        return symbols

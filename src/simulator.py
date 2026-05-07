from __future__ import annotations

import argparse
import json
from pathlib import Path
from random import Random
from typing import Any

import yaml

try:
    from .analytics import build_report
    from .engine import SlotMathEngine
except ImportError:
    from analytics import build_report
    from engine import SlotMathEngine


def load_config(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_simulation(config: dict[str, Any], spins: int | None = None, seed: int | None = None) -> dict[str, Any]:
    sim_cfg = config.get("simulation", {})
    spins = int(spins if spins is not None else sim_cfg.get("spins", 100_000))
    seed = int(seed if seed is not None else sim_cfg.get("seed", 1))

    bet_cfg = config.get("bet", {})
    bet_per_line = float(bet_cfg.get("bet_per_line", 1.0))
    active_lines = bet_cfg.get("active_lines")
    active_lines = int(active_lines) if active_lines is not None else None

    engine = SlotMathEngine(config, Random(seed))
    wins: list[float] = []
    bets: list[float] = []
    feature_triggers: list[bool] = []

    for _ in range(spins):
        result = engine.spin(bet_per_line=bet_per_line, active_lines=active_lines)
        wins.append(result.total_win)
        bets.append(result.total_bet)
        feature_triggers.append(bool(result.features))

    report = build_report(wins=wins, bets=bets, feature_triggers=feature_triggers).to_dict()
    report["seed"] = seed
    report["game_id"] = config["game"]["id"]
    report["game_version"] = config["game"]["version"]
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run slot math simulation")
    parser.add_argument("--config", default="config/game_config.yaml")
    parser.add_argument("--spins", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    report = run_simulation(config, spins=args.spins, seed=args.seed)

    output = args.output or config.get("simulation", {}).get("report_path")
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

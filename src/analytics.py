from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt
from statistics import NormalDist
from typing import Iterable


@dataclass(frozen=True)
class AnalyticsReport:
    spins: int
    total_bet: float
    total_win: float
    rtp: float
    expected_loss_rate: float
    hit_frequency: float
    miss_frequency: float
    mean_win_per_spin: float
    mean_win_on_hit: float
    variance: float
    standard_deviation: float
    coefficient_of_variation: float
    max_win: float
    p50_win: float
    p90_win: float
    p95_win: float
    p99_win: float
    feature_trigger_frequency: float
    standard_error_rtp: float
    rtp_confidence_95_low: float
    rtp_confidence_95_high: float

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if q <= 0:
        return sorted_values[0]
    if q >= 1:
        return sorted_values[-1]
    idx = q * (len(sorted_values) - 1)
    lo = int(idx)
    hi = min(lo + 1, len(sorted_values) - 1)
    weight = idx - lo
    return sorted_values[lo] * (1 - weight) + sorted_values[hi] * weight


def build_report(
    wins: Iterable[float],
    bets: Iterable[float],
    feature_triggers: Iterable[bool],
) -> AnalyticsReport:
    win_values = list(wins)
    bet_values = list(bets)
    trigger_values = list(feature_triggers)
    spins = len(win_values)
    if spins == 0:
        raise ValueError("cannot analyse zero spins")
    if len(bet_values) != spins or len(trigger_values) != spins:
        raise ValueError("wins, bets, and feature_triggers must have equal length")

    total_bet = sum(bet_values)
    total_win = sum(win_values)
    rtp = total_win / total_bet if total_bet else 0.0
    mean_win = total_win / spins
    hits = sum(1 for w in win_values if w > 0)
    hit_frequency = hits / spins
    variance = sum((w - mean_win) ** 2 for w in win_values) / spins
    sd = sqrt(variance)
    avg_bet = total_bet / spins
    se_rtp = (sd / sqrt(spins)) / avg_bet if avg_bet else 0.0
    z = NormalDist().inv_cdf(0.975)
    sorted_wins = sorted(win_values)

    return AnalyticsReport(
        spins=spins,
        total_bet=total_bet,
        total_win=total_win,
        rtp=rtp,
        expected_loss_rate=1.0 - rtp,
        hit_frequency=hit_frequency,
        miss_frequency=1.0 - hit_frequency,
        mean_win_per_spin=mean_win,
        mean_win_on_hit=total_win / hits if hits else 0.0,
        variance=variance,
        standard_deviation=sd,
        coefficient_of_variation=sd / mean_win if mean_win else 0.0,
        max_win=max(win_values),
        p50_win=percentile(sorted_wins, 0.50),
        p90_win=percentile(sorted_wins, 0.90),
        p95_win=percentile(sorted_wins, 0.95),
        p99_win=percentile(sorted_wins, 0.99),
        feature_trigger_frequency=sum(1 for t in trigger_values if t) / spins,
        standard_error_rtp=se_rtp,
        rtp_confidence_95_low=rtp - z * se_rtp,
        rtp_confidence_95_high=rtp + z * se_rtp,
    )

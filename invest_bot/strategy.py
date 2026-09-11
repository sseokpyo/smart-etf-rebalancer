from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from enum import StrEnum
from typing import Mapping, Sequence


SYMBOLS = ("QQQ", "TQQQ", "SPY", "SCHD")
ZERO = Decimal("0")
ONE = Decimal("1")


class MarketState(StrEnum):
    STRONG_UPTREND = "strong_uptrend"
    NORMAL_UPTREND = "normal_uptrend"
    WEAKENING = "weakening"
    DOWNTREND = "downtrend"


BASE_TARGETS: dict[MarketState, dict[str, Decimal]] = {
    MarketState.STRONG_UPTREND: {"QQQ": Decimal(".35"), "TQQQ": Decimal(".30"), "SPY": Decimal(".20"), "SCHD": Decimal(".15")},
    MarketState.NORMAL_UPTREND: {"QQQ": Decimal(".40"), "TQQQ": Decimal(".20"), "SPY": Decimal(".20"), "SCHD": Decimal(".20")},
    MarketState.WEAKENING: {"QQQ": Decimal(".40"), "TQQQ": Decimal(".10"), "SPY": Decimal(".25"), "SCHD": Decimal(".25")},
    MarketState.DOWNTREND: {"QQQ": Decimal(".40"), "TQQQ": ZERO, "SPY": Decimal(".30"), "SCHD": Decimal(".30")},
}


@dataclass(frozen=True)
class Signal:
    state: MarketState
    qqq_close: Decimal
    sma50: Decimal
    sma175: Decimal
    tqqq_drawdown: Decimal
    recovery_signal: bool
    targets: Mapping[str, Decimal]


def sma(closes: Sequence[Decimal], period: int) -> Decimal:
    if len(closes) < period:
        raise ValueError(f"Need {period} daily closes; received {len(closes)}.")
    return sum(closes[-period:], ZERO) / Decimal(period)


def classify(qqq_closes: Sequence[Decimal]) -> MarketState:
    close, sma50, sma175 = qqq_closes[-1], sma(qqq_closes, 50), sma(qqq_closes, 175)
    if close > sma50 and sma50 > sma175 and close > sma175:
        return MarketState.STRONG_UPTREND
    # Must precede the generic QQQ > SMA175 condition.
    if close < sma50 and close > sma175:
        return MarketState.WEAKENING
    if close > sma175:
        return MarketState.NORMAL_UPTREND
    return MarketState.DOWNTREND


def tqqq_drawdown(closes: Sequence[Decimal], lookback: int) -> Decimal:
    if not closes:
        raise ValueError("No TQQQ closes supplied.")
    window = closes[-lookback:]
    peak = max(window)
    return closes[-1] / peak - ONE


def apply_tqqq_recovery(targets: Mapping[str, Decimal], drawdown: Decimal, recovery: bool) -> dict[str, Decimal]:
    result = dict(targets)
    desired = result["TQQQ"]
    if recovery and drawdown <= Decimal("-.40"):
        desired = max(desired, Decimal(".30"))
    elif recovery and drawdown <= Decimal("-.30"):
        desired = max(desired, Decimal(".25"))
    elif drawdown <= Decimal("-.20"):
        desired = max(desired, Decimal(".20"))
    desired = min(desired, Decimal(".30"))
    if desired == result["TQQQ"]:
        return result
    remainder_before = ONE - result["TQQQ"]
    remainder_after = ONE - desired
    for symbol in SYMBOLS:
        if symbol != "TQQQ":
            result[symbol] = result[symbol] / remainder_before * remainder_after
    result["TQQQ"] = desired
    return result


def calculate_signal(qqq_closes: Sequence[Decimal], tqqq_closes: Sequence[Decimal], lookback: int) -> Signal:
    state = classify(qqq_closes)
    close, avg50, avg175 = qqq_closes[-1], sma(qqq_closes, 50), sma(qqq_closes, 175)
    dd = tqqq_drawdown(tqqq_closes, lookback)
    recovery = close >= avg175 * Decimal(".98") and close > qqq_closes[-2]
    return Signal(state, close, avg50, avg175, dd, recovery, apply_tqqq_recovery(BASE_TARGETS[state], dd, recovery))


def allocate_new_cash(current_values: Mapping[str, Decimal], targets: Mapping[str, Decimal], cash: Decimal, minimum: Decimal) -> dict[str, Decimal]:
    """Allocate all cash toward underweights, then target weights for any remainder."""
    total = sum((current_values.get(s, ZERO) for s in SYMBOLS), ZERO)
    future_total = total + cash
    deficits = {s: max(ZERO, targets[s] * future_total - current_values.get(s, ZERO)) for s in SYMBOLS}
    allocations = {s: ZERO for s in SYMBOLS}
    remaining = cash
    for symbol in sorted(SYMBOLS, key=lambda s: deficits[s], reverse=True):
        amount = min(deficits[symbol], remaining)
        allocations[symbol] += amount
        remaining -= amount
    if remaining > ZERO:
        for symbol in sorted(SYMBOLS, key=lambda s: targets[s], reverse=True):
            amount = min(remaining, targets[symbol] * cash)
            allocations[symbol] += amount
            remaining -= amount
            if remaining <= ZERO:
                break
    # Dollars are accepted as decimal strings. Preserve 2 decimals and avoid dust orders.
    return {s: amount.quantize(Decimal(".01"), rounding=ROUND_DOWN) if amount >= minimum else ZERO for s, amount in allocations.items()}

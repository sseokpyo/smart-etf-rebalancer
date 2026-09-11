from decimal import Decimal

from invest_bot.strategy import MarketState, allocate_new_cash, apply_tqqq_recovery, classify


def closes(value: str, last: str) -> list[Decimal]:
    return [Decimal(value)] * 199 + [Decimal(last)]


def test_weakened_state_is_reachable_before_generic_uptrend() -> None:
    # 175-day SMA is 100, 50-day SMA becomes 110; final close 105 is between them.
    series = [Decimal("100")] * 150 + [Decimal("110")] * 49 + [Decimal("105")]
    assert classify(series) is MarketState.WEAKENING


def test_strong_uptrend() -> None:
    series = [Decimal("100")] * 150 + [Decimal("110")] * 49 + [Decimal("120")]
    assert classify(series) is MarketState.STRONG_UPTREND


def test_recovery_keeps_requested_tqqq_target_and_normalizes() -> None:
    targets = {"QQQ": Decimal(".40"), "TQQQ": Decimal("0"), "SPY": Decimal(".30"), "SCHD": Decimal(".30")}
    adjusted = apply_tqqq_recovery(targets, Decimal("-.45"), True)
    assert adjusted["TQQQ"] == Decimal(".30")
    assert sum(adjusted.values()) == Decimal("1.00")


def test_allocation_prioritizes_underweight_assets() -> None:
    targets = {"QQQ": Decimal(".40"), "TQQQ": Decimal(".20"), "SPY": Decimal(".20"), "SCHD": Decimal(".20")}
    allocated = allocate_new_cash({"QQQ": Decimal("40"), "TQQQ": Decimal("0"), "SPY": Decimal("20"), "SCHD": Decimal("20")}, targets, Decimal("10"), Decimal("1"))
    assert allocated["TQQQ"] == Decimal("10.00")

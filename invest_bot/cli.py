from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .config import Settings
from .strategy import SYMBOLS, allocate_new_cash, calculate_signal
from .toss import TossClient


def decimal_json(value: object) -> object:
    return str(value) if isinstance(value, Decimal) else value


def make_client(settings: Settings) -> TossClient:
    client = TossClient(settings.client_id, settings.client_secret, settings.account_seq)
    client.authenticate()
    client.select_account()
    return client


def check(settings: Settings) -> None:
    client = make_client(settings)
    print(f"Connected to Toss account sequence {client.account_seq}. DRY_RUN={settings.dry_run}")
    print(f"USD buying power: ${client.buying_power_usd()}")


def run(settings: Settings, live: bool) -> None:
    if live and settings.dry_run:
        raise RuntimeError("Set DRY_RUN=false in .env before using --live.")
    client = make_client(settings)
    history_count = max(200, settings.drawdown_lookback_days)
    qqq = client.candles("QQQ", history_count)
    tqqq = client.candles("TQQQ", history_count)
    signal = calculate_signal(qqq, tqqq, settings.drawdown_lookback_days)
    holdings = client.holdings_usd()
    krw_per_usd = ONE / client.usd_per_krw()
    budget_usd = settings.monthly_budget_krw / krw_per_usd * (ONE - settings.cash_buffer_rate)
    available = client.buying_power_usd()
    cash = min(budget_usd, available)
    if cash < settings.min_order_usd:
        raise RuntimeError(f"USD buying power (${available}) is below the minimum order amount.")
    allocations = allocate_new_cash(holdings, signal.targets, cash, settings.min_order_usd)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    month = datetime.now(timezone.utc).strftime("%Y%m")
    plan = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "account_seq": client.account_seq,
        "dry_run": not live,
        "signal": {"state": signal.state, "qqq_close": signal.qqq_close, "sma50": signal.sma50, "sma175": signal.sma175, "tqqq_drawdown": signal.tqqq_drawdown, "recovery_signal": signal.recovery_signal, "targets": signal.targets},
        "holdings_usd": holdings,
        "budget_usd": budget_usd,
        "available_usd": available,
        "orders": [{"symbol": s, "amount_usd": allocations[s], "client_order_id": f"dca-{month}-{s}"} for s in SYMBOLS if allocations[s] >= settings.min_order_usd],
    }
    output_dir = Path("data/runs")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{stamp}-{datetime.now().strftime('%H%M%S')}.json"
    if live and plan["orders"]:
        ledger_dir = Path("data/ledger")
        ledger_dir.mkdir(parents=True, exist_ok=True)
        ledger_path = ledger_dir / f"{month}.json"
        if ledger_path.exists():
            raise RuntimeError(f"This month's live run is blocked by {ledger_path}. Verify Toss order history before any manual action.")
        # Write before the first network mutation. A failed execution stays blocked rather
        # than risking a duplicate order after the API's short idempotency window expires.
        journal = {"state": "SUBMITTING", "plan": plan, "responses": []}
        ledger_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2, default=decimal_json), encoding="utf-8")
        for item in plan["orders"]:
            journal["responses"].append(client.buy_amount(item["symbol"], item["amount_usd"], item["client_order_id"]))
            ledger_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2, default=decimal_json), encoding="utf-8")
        journal["state"] = "COMPLETE"
        ledger_path.write_text(json.dumps(journal, ensure_ascii=False, indent=2, default=decimal_json), encoding="utf-8")
        plan["responses"] = journal["responses"]
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2, default=decimal_json), encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2, default=decimal_json))
    print(f"Saved: {output_path}")


ONE = Decimal("1")


def main() -> None:
    parser = argparse.ArgumentParser(description="Monthly DCA portfolio planner for Toss Securities")
    parser.add_argument("command", choices=("check", "run"))
    parser.add_argument("--live", action="store_true", help="Send orders only when DRY_RUN=false too.")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.command == "check":
        check(settings)
    else:
        run(settings, args.live)

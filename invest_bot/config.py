from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from .preferences import ROOT, budget


def load_env(path: Path = ROOT / ".env") -> None:
    """Load a small .env file without adding a dependency."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required. Add it to .env.")
    return value


@dataclass(frozen=True)
class Settings:
    client_id: str
    client_secret: str
    account_seq: str | None
    dry_run: bool
    monthly_budget_krw: Decimal
    cash_buffer_rate: Decimal
    min_order_usd: Decimal
    drawdown_lookback_days: int

    @classmethod
    def from_env(cls) -> "Settings":
        load_env()
        return cls(
            client_id=required("TOSS_CLIENT_ID"),
            client_secret=required("TOSS_CLIENT_SECRET"),
            account_seq=os.getenv("TOSS_ACCOUNT_SEQ") or None,
            dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
            monthly_budget_krw=Decimal(budget(os.getenv("MONTHLY_BUDGET_KRW", "100000"))),
            cash_buffer_rate=Decimal(os.getenv("CASH_BUFFER_RATE", "0.02")),
            min_order_usd=Decimal(os.getenv("MIN_ORDER_USD", "1.00")),
            drawdown_lookback_days=int(os.getenv("DRAWDOWN_LOOKBACK_DAYS", "252")),
        )

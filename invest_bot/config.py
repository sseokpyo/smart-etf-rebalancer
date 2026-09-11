from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from .preferences import ROOT, budget


def load_env(path: Path | None = None) -> None:
    path = path or ROOT / ".env"
    """Load a small .env file without adding a dependency."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def save_connection_settings(client_id: str, client_secret: str, account_seq: str = "") -> None:
    """Store Toss API settings locally without ever returning their values to callers."""
    values = {
        "TOSS_CLIENT_ID": client_id.strip(),
        "TOSS_CLIENT_SECRET": client_secret.strip(),
        "TOSS_ACCOUNT_SEQ": account_seq.strip(),
    }
    if not values["TOSS_CLIENT_ID"] or not values["TOSS_CLIENT_SECRET"]:
        raise ValueError("Client ID와 Client Secret을 입력해 주세요.")
    if any("\r" in value or "\n" in value for value in values.values()):
        raise ValueError("입력값에 줄바꿈을 사용할 수 없습니다.")

    env_path = ROOT / ".env"
    existing = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    remaining = []
    managed_keys = set(values)
    for line in existing:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key not in managed_keys:
            remaining.append(line)

    content = "\n".join(
        [*remaining, *(f"{key}={value}" for key, value in values.items())]
    ).rstrip() + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=ROOT, prefix=".env.", delete=False
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    os.replace(temporary_path, env_path)

    # load_env intentionally preserves existing process values. Update this running
    # dashboard explicitly so a connection check can use newly saved settings.
    os.environ.update(values)


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

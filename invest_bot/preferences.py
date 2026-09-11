"""Shared persistent settings for the dashboard and command-line planner."""
import json
import os
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / 'data' / 'settings.json'


def validate_budget(value):
    if isinstance(value, bool):
        raise ValueError('월 투자금은 정수 원 단위로 입력하세요.')
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('유효한 투자금을 입력하세요.') from None
    if not amount.is_finite() or amount != amount.to_integral_value() or not 1000 <= amount <= 100000000:
        raise ValueError('월 투자금은 1,000원부터 100,000,000원까지 정수로 입력하세요.')
    return int(amount)


def budget(default='100000'):
    if SETTINGS_PATH.exists():
        return validate_budget(json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))['monthly_budget_krw'])
    return validate_budget(default)


def save_budget(value):
    amount = validate_budget(value)
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=SETTINGS_PATH.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump({'monthly_budget_krw': amount}, stream)
        os.replace(name, SETTINGS_PATH)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return amount

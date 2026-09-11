"""Shared persistent settings for the dashboard and command-line planner."""
import json
import os
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path

# In a bundled Windows app, resources live in PyInstaller's temporary folder,
# while user settings must remain next to the executable between launches.
ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / 'data' / 'settings.json'
PORTFOLIO_HISTORY_PATH = ROOT / 'data' / 'portfolio-history.json'


def _read_settings():
    if not SETTINGS_PATH.exists():
        return {}
    value = json.loads(SETTINGS_PATH.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('설정 파일 형식이 올바르지 않습니다.')
    return value


def _write_settings(value):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=SETTINGS_PATH.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False)
        os.replace(name, SETTINGS_PATH)
    finally:
        if os.path.exists(name):
            os.unlink(name)


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
    settings = _read_settings()
    if 'monthly_budget_krw' in settings:
        return validate_budget(settings['monthly_budget_krw'])
    return validate_budget(default)


def save_budget(value):
    amount = validate_budget(value)
    settings = _read_settings()
    settings['monthly_budget_krw'] = amount
    _write_settings(settings)
    return amount


def auto_trading_enabled():
    return _read_settings().get('auto_trading_enabled', False) is True


def save_auto_trading(enabled):
    if not isinstance(enabled, bool):
        raise ValueError('자동거래 설정값이 올바르지 않습니다.')
    settings = _read_settings()
    settings['auto_trading_enabled'] = enabled
    _write_settings(settings)
    return enabled


def portfolio_history():
    if not PORTFOLIO_HISTORY_PATH.exists():
        return []
    history = json.loads(PORTFOLIO_HISTORY_PATH.read_text(encoding='utf-8'))
    if not isinstance(history, list):
        raise ValueError('포트폴리오 기록 파일 형식이 올바르지 않습니다.')
    return [item for item in history if isinstance(item, dict)][:366]


def save_portfolio_value(recorded_at: str, value_krw: float):
    if value_krw < 0:
        raise ValueError('포트폴리오 금액이 올바르지 않습니다.')
    records = portfolio_history()
    day = recorded_at[:10]
    entry = {'recorded_at': recorded_at, 'value_krw': value_krw}
    records = [item for item in records if str(item.get('recorded_at', ''))[:10] != day]
    records.append(entry)
    records = sorted(records, key=lambda item: item['recorded_at'])[-366:]
    PORTFOLIO_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=PORTFOLIO_HISTORY_PATH.parent, suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(records, stream, ensure_ascii=False)
        os.replace(name, PORTFOLIO_HISTORY_PATH)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return records

"""Loopback-only dashboard. No trading endpoint is exposed."""
import argparse
import json
import os
import secrets
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .config import Settings, load_env, save_connection_settings
from .preferences import ROOT, auto_trading_enabled, budget, save_auto_trading, save_budget

RESOURCE_ROOT = Path(getattr(sys, '_MEIPASS', ROOT))
STATIC = RESOURCE_ROOT / 'invest_bot' / 'static'
TOKEN = secrets.token_urlsafe(32)
SNAPSHOT = None
CLIENT = None
CLIENT_STARTED = None


def current_budget():
    load_env()
    return budget(os.getenv('MONTHLY_BUDGET_KRW', '100000'))


def connection_state():
    """Return readiness only; credentials and account identifiers stay server-side."""
    load_env()
    if not os.getenv('TOSS_CLIENT_ID') or not os.getenv('TOSS_CLIENT_SECRET'):
        return 'not_configured'
    return 'connected' if SNAPSHOT and SNAPSHOT.get('source') == 'live' else 'ready'


def fetch_snapshot():
    global CLIENT, CLIENT_STARTED
    from .toss import TossClient
    settings = Settings.from_env()
    now = datetime.now(timezone.utc)
    if CLIENT is None or (now - CLIENT_STARTED).total_seconds() > 3600:
        candidate = TossClient(settings.client_id, settings.client_secret, settings.account_seq)
        candidate.authenticate()
        candidate.select_account()
        CLIENT, CLIENT_STARTED = candidate, now
    # Keep broker DTOs on the server; expose only the fields displayed by the UI.
    raw = CLIENT._request('GET', '/api/v1/holdings', account=True)
    rate = CLIENT._request('GET', '/api/v1/exchange-rate', params={'baseCurrency': 'USD', 'quoteCurrency': 'KRW'})
    fx = Decimal(rate['rate'])
    if not fx.is_finite() or fx <= 0:
        raise ValueError('Invalid exchange rate')
    items = []
    for item in raw['items']:
        currency = item['currency']
        if currency not in ('USD', 'KRW'):
            raise ValueError('Unsupported currency')
        conversion = fx if currency == 'USD' else Decimal(1)
        value = Decimal(item['marketValue']['amount']) * conversion
        cost = Decimal(item['marketValue']['purchaseAmount']) * conversion
        items.append({'symbol': item['symbol'], 'name': item['name'], 'quantity': item['quantity'],
                      'value_krw': float(value), 'cost_krw': float(cost), 'currency': currency})
    return {'source': 'live', 'updated_at': now.isoformat(), 'fx': float(fx), 'items': items}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, data, content_type='application/json; charset=utf-8'):
        payload = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def valid_host(self):
        return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

    def do_GET(self):
        if not self.valid_host():
            return self.respond(403, {'error': 'Invalid host'})
        path = urlsplit(self.path).path
        if path == '/api/state':
            try:
                return self.respond(200, {'budget': current_budget(), 'token': TOKEN, 'snapshot': SNAPSHOT, 'connection': connection_state(), 'auto_trading_enabled': auto_trading_enabled()})
            except (ValueError, KeyError, OSError):
                return self.respond(500, {'error': '투자금 설정 파일을 확인하세요: data/settings.json'})
        assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'application/javascript'), '/style.css': ('style.css', 'text/css')}
        if path not in assets:
            return self.respond(404, {'error': 'Not found'})
        filename, mime = assets[path]
        self.respond(200, (STATIC / filename).read_bytes(), mime + '; charset=utf-8')

    def do_POST(self):
        global SNAPSHOT, CLIENT, CLIENT_STARTED
        if not self.valid_host() or self.headers.get('X-Dashboard-Token') != TOKEN:
            return self.respond(403, {'error': '화면을 새로고침한 뒤 다시 시도하세요.'})
        path = urlsplit(self.path).path
        if path == '/api/settings':
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 1024:
                    raise ValueError('잘못된 요청입니다.')
                data = json.loads(self.rfile.read(size))
                return self.respond(200, {'budget': save_budget(data['monthly_budget_krw'])})
            except (ValueError, KeyError, TypeError):
                return self.respond(400, {'error': '투자금은 1,000~100,000,000원 사이 정수로 입력하세요.'})
            except OSError:
                return self.respond(500, {'error': '설정 저장에 실패했습니다. 폴더 쓰기 권한을 확인하세요.'})
        if path == '/api/connection':
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 4096:
                    raise ValueError('잘못된 요청입니다.')
                data = json.loads(self.rfile.read(size))
                save_connection_settings(
                    data['client_id'], data['client_secret'], data.get('account_seq', '')
                )
                # Discard a previous client so the next check uses the saved account.
                CLIENT, CLIENT_STARTED, SNAPSHOT = None, None, None
                return self.respond(200, {'connection': connection_state()})
            except (ValueError, KeyError, TypeError):
                return self.respond(400, {'error': 'Client ID와 Client Secret을 입력해 주세요.'})
            except OSError:
                return self.respond(500, {'error': '연결 설정 저장에 실패했습니다. 폴더 쓰기 권한을 확인하세요.'})
        if path == '/api/auto-trading':
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 128:
                    raise ValueError('잘못된 요청입니다.')
                data = json.loads(self.rfile.read(size))
                return self.respond(200, {'auto_trading_enabled': save_auto_trading(data['enabled'])})
            except (ValueError, KeyError, TypeError):
                return self.respond(400, {'error': '자동거래 설정값이 올바르지 않습니다.'})
            except OSError:
                return self.respond(500, {'error': '자동거래 설정 저장에 실패했습니다. 폴더 쓰기 권한을 확인하세요.'})
        if path == '/api/refresh':
            try:
                SNAPSHOT = fetch_snapshot()
                return self.respond(200, {'snapshot': SNAPSHOT, 'connection': connection_state()})
            except Exception:
                # Never send tokens, account IDs or raw broker error bodies to the browser.
                return self.respond(502, {'error': '잔고 조회에 실패했습니다. .env의 토스 API 키·계좌 설정, 허용 IP와 네트워크를 확인하세요. 마지막 조회값은 유지됩니다.'})
        return self.respond(404, {'error': 'Not found'})


def serve(port: int = 8765, open_browser: bool = False):
    """Run the loopback dashboard and optionally open it in the default browser."""
    try:
        server = HTTPServer(('127.0.0.1', port), Handler)
    except OSError:
        if port == 0:
            raise
        server = HTTPServer(('127.0.0.1', 0), Handler)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'투자 대시보드: {url} (종료: Ctrl+C)', flush=True)
    if open_browser:
        threading.Timer(0.25, lambda: webbrowser.open(url, new=2)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='로컬 투자 대시보드')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--open-browser', action='store_true', help='기본 브라우저에서 대시보드를 엽니다.')
    args = parser.parse_args(argv)
    serve(args.port, args.open_browser)


if __name__ == '__main__':
    main()

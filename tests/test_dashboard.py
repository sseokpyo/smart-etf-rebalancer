import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from http.server import HTTPServer

from invest_bot import dashboard, preferences
from invest_bot.config import Settings


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path_patch = patch.object(preferences, 'SETTINGS_PATH', Path(self.temp.name) / 'settings.json')
        self.path_patch.start()
        self.server = HTTPServer(('127.0.0.1', 0), dashboard.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.path_patch.stop()
        self.temp.cleanup()

    def post(self, path, data, token=dashboard.TOKEN):
        req = Request(self.url + path, data=json.dumps(data).encode(), headers={'X-Dashboard-Token': token, 'Content-Type': 'application/json'})
        with urlopen(req) as response:
            return json.load(response)

    def test_saved_budget_is_read_by_cli_settings(self):
        self.assertEqual(self.post('/api/settings', {'monthly_budget_krw': 250000})['budget'], 250000)
        with patch.dict('os.environ', {'TOSS_CLIENT_ID': 'test', 'TOSS_CLIENT_SECRET': 'test', 'MONTHLY_BUDGET_KRW': '100000'}):
            self.assertEqual(Settings.from_env().monthly_budget_krw, 250000)

    def test_invalid_amounts_do_not_overwrite_saved_budget(self):
        preferences.save_budget(100000)
        for value in [-1, 0, True, 'NaN', 'Infinity', 1000.5, 100000001]:
            with self.subTest(value=value), self.assertRaises(HTTPError) as error:
                self.post('/api/settings', {'monthly_budget_krw': value})
            self.assertEqual(error.exception.code, 400)
            self.assertEqual(preferences.budget(), 100000)

    def test_missing_token_cannot_save(self):
        with self.assertRaises(HTTPError) as error:
            self.post('/api/settings', {'monthly_budget_krw': 250000}, token='wrong')
        self.assertEqual(error.exception.code, 403)

    def test_refresh_does_not_expose_secret_on_error(self):
        with patch.object(dashboard, 'fetch_snapshot', side_effect=RuntimeError('secret-value')):
            with self.assertRaises(HTTPError) as error:
                self.post('/api/refresh', {})
            self.assertNotIn('secret-value', error.exception.read().decode())

    def test_assets_and_no_order_route(self):
        for path in ['/', '/style.css', '/app.js', '/api/state']:
            with urlopen(self.url + path) as response:
                self.assertEqual(response.status, 200)
        with self.assertRaises(HTTPError) as error:
            self.post('/api/orders', {})
        self.assertEqual(error.exception.code, 404)

    def test_connection_state_does_not_expose_credentials(self):
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(dashboard.connection_state(), 'not_configured')
        with patch.dict('os.environ', {'TOSS_CLIENT_ID': 'private-client', 'TOSS_CLIENT_SECRET': 'private-secret'}, clear=True):
            self.assertEqual(dashboard.connection_state(), 'ready')


if __name__ == '__main__':
    unittest.main()

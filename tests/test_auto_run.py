from decimal import Decimal
import unittest
from unittest.mock import patch

from invest_bot.auto_run import main
from invest_bot.config import Settings


def settings():
    return Settings('id', 'secret', None, True, Decimal('500000'), Decimal('.02'), Decimal('1'), 252, Decimal('.05'))


class AutoRunTests(unittest.TestCase):
    def test_monthly_runner_creates_plan_when_automatic_trading_is_off(self):
        with patch('invest_bot.auto_run.Settings.from_env', return_value=settings()), \
             patch('invest_bot.auto_run.auto_trading_enabled', return_value=False), \
             patch('invest_bot.auto_run.run') as run:
            main()
        run.assert_called_once()
        self.assertFalse(run.call_args.kwargs['live'])
        self.assertTrue(run.call_args.args[0].dry_run)

    def test_monthly_runner_sends_orders_only_when_automatic_trading_is_on(self):
        with patch('invest_bot.auto_run.Settings.from_env', return_value=settings()), \
             patch('invest_bot.auto_run.auto_trading_enabled', return_value=True), \
             patch('invest_bot.auto_run.run') as run:
            main()
        run.assert_called_once()
        self.assertTrue(run.call_args.kwargs['live'])
        self.assertFalse(run.call_args.args[0].dry_run)

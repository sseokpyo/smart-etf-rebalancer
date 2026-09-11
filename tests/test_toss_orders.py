from decimal import Decimal
import unittest
from unittest.mock import patch

from invest_bot.toss import TossClient


class TossOrderTests(unittest.TestCase):
    def test_sell_uses_market_quantity_order(self):
        client = TossClient('id', 'secret', '1')
        with patch.object(client, '_request', return_value={'orderId': 'abc'}) as request:
            client.sell_quantity('TQQQ', Decimal('1.25'), 'rebalance-202609-TQQQ-sell')
        request.assert_called_once_with(
            'POST', '/api/v1/orders', account=True,
            json={'symbol': 'TQQQ', 'side': 'SELL', 'orderType': 'MARKET', 'quantity': '1.25', 'clientOrderId': 'rebalance-202609-TQQQ-sell'},
        )

    def test_sellable_quantity_is_requested_before_a_sale(self):
        client = TossClient('id', 'secret', '1')
        with patch.object(client, '_request', return_value={'sellableQuantity': '3.75'}) as request:
            quantity = client.sellable_quantity('TQQQ')
        self.assertEqual(quantity, Decimal('3.75'))
        request.assert_called_once_with('GET', '/api/v1/sellable-quantity', account=True, params={'symbol': 'TQQQ'})


if __name__ == '__main__':
    unittest.main()

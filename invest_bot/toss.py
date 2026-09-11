from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import requests


BASE_URL = "https://openapi.tossinvest.com"


@dataclass(frozen=True)
class Holding:
    value_usd: Decimal
    quantity: Decimal


class TossClient:
    def __init__(self, client_id: str, client_secret: str, account_seq: str | None = None) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.account_seq = account_seq
        self.session = requests.Session()
        self.token: str | None = None

    def _request(self, method: str, path: str, *, account: bool = False, **kwargs: Any) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if account:
            if not self.account_seq:
                raise RuntimeError("Account sequence has not been selected.")
            headers["X-Tossinvest-Account"] = str(self.account_seq)
        response = self.session.request(method, f"{BASE_URL}{path}", headers=headers, timeout=20, **kwargs)
        if not response.ok:
            raise RuntimeError(f"Toss API {response.status_code}: {response.text}")
        body = response.json()
        return body.get("result", body)

    def authenticate(self) -> None:
        result = self._request("POST", "/oauth2/token", data={"grant_type": "client_credentials", "client_id": self.client_id, "client_secret": self.client_secret})
        self.token = result["access_token"]

    def select_account(self) -> str:
        if self.account_seq:
            return self.account_seq
        accounts = self._request("GET", "/api/v1/accounts")
        brokerage = next((a for a in accounts if a["accountType"] == "BROKERAGE"), None)
        if not brokerage:
            raise RuntimeError("No BROKERAGE account returned by Toss API.")
        self.account_seq = str(brokerage["accountSeq"])
        return self.account_seq

    def candles(self, symbol: str, count: int = 200) -> list[Decimal]:
        # The endpoint returns at most 200 newest-first candles. Drawdown needs a
        # 252-day window, so follow nextBefore and de-duplicate its inclusive edge.
        by_timestamp: dict[str, dict[str, Any]] = {}
        before: str | None = None
        while len(by_timestamp) < count:
            needed = count - len(by_timestamp)
            params: dict[str, Any] = {"symbol": symbol, "interval": "1d", "count": min(200, needed + (1 if before else 0)), "adjusted": "true"}
            if before:
                params["before"] = before
            result = self._request("GET", "/api/v1/candles", params=params)
            candles = result["candles"]
            if not candles:
                break
            for candle in candles:
                by_timestamp[candle["timestamp"]] = candle
            next_before = result.get("nextBefore")
            if not next_before or next_before == before:
                break
            before = next_before
        if len(by_timestamp) < count:
            raise RuntimeError(f"Toss returned only {len(by_timestamp)} of {count} daily candles for {symbol}.")
        ordered = [by_timestamp[key] for key in sorted(by_timestamp)][-count:]
        return [Decimal(candle["closePrice"]) for candle in ordered]

    def holdings_usd(self) -> dict[str, Decimal]:
        return {symbol: holding.value_usd for symbol, holding in self.holdings().items()}

    def holdings(self) -> dict[str, Holding]:
        result = self._request("GET", "/api/v1/holdings", account=True)
        return {
            item["symbol"]: Holding(Decimal(item["marketValue"]["amount"]), Decimal(str(item["quantity"])))
            for item in result["items"]
            if item["marketCountry"] == "US" and Decimal(str(item["quantity"])) > 0
        }

    def usd_per_krw(self) -> Decimal:
        result = self._request("GET", "/api/v1/exchange-rate", params={"baseCurrency": "USD", "quoteCurrency": "KRW"})
        return ONE / Decimal(result["rate"])

    def buying_power_usd(self) -> Decimal:
        result = self._request("GET", "/api/v1/buying-power", account=True, params={"currency": "USD"})
        return Decimal(result["amount"])

    def buy_amount(self, symbol: str, amount_usd: Decimal, client_order_id: str) -> dict[str, Any]:
        payload = {"symbol": symbol, "side": "BUY", "orderType": "MARKET", "orderAmount": str(amount_usd), "clientOrderId": client_order_id}
        return self._request("POST", "/api/v1/orders", account=True, json=payload)

    def sellable_quantity(self, symbol: str) -> Decimal:
        result = self._request("GET", "/api/v1/sellable-quantity", account=True, params={"symbol": symbol})
        return Decimal(str(result["sellableQuantity"]))

    def sell_quantity(self, symbol: str, quantity: Decimal, client_order_id: str) -> dict[str, Any]:
        if quantity <= 0:
            raise ValueError("Sell quantity must be positive.")
        payload = {"symbol": symbol, "side": "SELL", "orderType": "MARKET", "quantity": str(quantity), "clientOrderId": client_order_id}
        return self._request("POST", "/api/v1/orders", account=True, json=payload)


ONE = Decimal("1")

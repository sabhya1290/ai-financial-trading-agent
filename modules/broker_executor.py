

from __future__ import annotations

from typing import Optional, Dict, Any

from config.settings import (
    ALPACA_API_KEY,
    ALPACA_SECRET,
    ALPACA_BASE_URL,
)
from modules.risk_manager import TradeOrder
from utils.logger import get_logger, log_event

logger = get_logger("broker_executor")



_api = None

def _get_api():
    """Return a cached Alpaca REST client.  Initialised once on first call."""
    global _api
    if _api is not None:
        return _api
    try:
        import alpaca_trade_api as tradeapi  # type: ignore
        _api = tradeapi.REST(
            key_id     = ALPACA_API_KEY,
            secret_key = ALPACA_SECRET,
            base_url   = ALPACA_BASE_URL,
        )
        logger.info("Alpaca client connected to %s", ALPACA_BASE_URL)
    except ImportError:
        logger.error(
            "alpaca-trade-api not installed. Run: pip install alpaca-trade-api"
        )
        _api = _MockAlpacaAPI()   # fall back to a mock for unit tests
    return _api



def get_current_price(ticker: str) -> Optional[float]:
    """
    Fetch the latest trade price for *ticker* from Alpaca.
    Returns None if the request fails (market closed, bad ticker, etc.).
    """
    api = _get_api()
    try:
        trade = api.get_latest_trade(ticker)
        price = float(trade.price)
        logger.debug("Latest price for %s: $%.2f", ticker, price)
        return price
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch price for %s: %s", ticker, exc)
        return None


def execute_order(order: TradeOrder) -> Dict[str, Any]:
    """
    Submit a validated TradeOrder to Alpaca and return the broker response.

    BUY  → bracket order  (market entry + stop-loss + take-profit legs)
    SELL → simple market order to flatten the position

    Returns a dict summarising the outcome:
        {
            "success":    bool,
            "order_id":   str | None,
            "ticker":     str,
            "action":     str,
            "qty":        int,
            "fill_price": float | None,
            "error":      str | None,
        }
    """
    api = _get_api()

    try:
        if order.action == "BUY":
            alpaca_order = api.submit_order(
                symbol        = order.ticker,
                qty           = order.qty,
                side          = "buy",
                type          = "market",
                time_in_force = "day",
                order_class   = "bracket",
                stop_loss     = {"stop_price": str(order.stop_loss)},
                take_profit   = {"limit_price": str(order.take_profit)},
            )
        else:  # SELL — close position with a simple market order
            alpaca_order = api.submit_order(
                symbol        = order.ticker,
                qty           = order.qty,
                side          = "sell",
                type          = "market",
                time_in_force = "day",
            )

        order_id = alpaca_order.id
        log_event(
            logger, "ORDER_SUBMITTED",
            ticker=order.ticker, action=order.action,
            qty=order.qty, order_id=order_id,
            stop_loss=order.stop_loss, take_profit=order.take_profit,
        )

        return {
            "success":    True,
            "order_id":   order_id,
            "ticker":     order.ticker,
            "action":     order.action,
            "qty":        order.qty,
            "fill_price": order.entry_price,   # actual fill comes via webhook
            "error":      None,
        }

    except Exception as exc:  # noqa: BLE001
        logger.error("Order submission failed for %s: %s", order.ticker, exc)
        return {
            "success":    False,
            "order_id":   None,
            "ticker":     order.ticker,
            "action":     order.action,
            "qty":        order.qty,
            "fill_price": None,
            "error":      str(exc),
        }


def get_account_info() -> Dict[str, Any]:
    """Return Alpaca account details (equity, cash, buying power)."""
    api = _get_api()
    try:
        acct = api.get_account()
        return {
            "equity":        float(acct.equity),
            "cash":          float(acct.cash),
            "buying_power":  float(acct.buying_power),
            "daytrade_count": int(acct.daytrade_count),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch account info: %s", exc)
        return {}



class _MockAlpacaAPI:
    """
    Minimal stand-in for alpaca_trade_api.REST so that the rest of the
    codebase can be developed and tested without a real API connection.
    """
    class _FakeTrade:
        price = "150.00"

    class _FakeOrder:
        id = "mock-order-id-12345"

    class _FakeAccount:
        equity = "100000"
        cash   = "100000"
        buying_power = "100000"
        daytrade_count = 0

    def get_latest_trade(self, symbol):
        logger.warning("[MOCK] get_latest_trade('%s') → $150.00", symbol)
        return self._FakeTrade()

    def submit_order(self, **kwargs):
        logger.warning("[MOCK] submit_order %s", kwargs)
        return self._FakeOrder()

    def get_account(self):
        return self._FakeAccount()

"""
tests/test_modules.py — Unit tests for each agent module.

Run with:  pytest tests/ -v

These tests use mocking so they don't require real API keys or the
FinBERT model to be downloaded.
"""

from __future__ import annotations

import sys
import os
import importlib
from unittest.mock import MagicMock, patch

# Make sure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ─────────────────────────────────────────────────────────────────────────────
# ticker_detector
# ─────────────────────────────────────────────────────────────────────────────

class TestTickerDetector:
    def test_cashtag(self):
        from modules.ticker_detector import detect_tickers
        result = detect_tickers("$AAPL beats earnings estimates")
        assert "AAPL" in result

    def test_company_name(self):
        from modules.ticker_detector import detect_tickers
        result = detect_tickers("Microsoft announces new AI product line")
        assert "MSFT" in result

    def test_no_match(self):
        from modules.ticker_detector import detect_tickers
        result = detect_tickers("Weather forecast for Monday is sunny")
        assert result == []

    def test_multiple_tickers(self):
        from modules.ticker_detector import detect_tickers
        result = detect_tickers("Apple and $TSLA both surge after Fed decision")
        assert "AAPL" in result
        assert "TSLA" in result

    def test_not_in_watchlist(self):
        from modules.ticker_detector import detect_tickers
        # ZZZZ is not on the watchlist
        result = detect_tickers("$ZZZZ announces record profits")
        assert "ZZZZ" not in result


# ─────────────────────────────────────────────────────────────────────────────
# signal_generator
# ─────────────────────────────────────────────────────────────────────────────

class TestSignalGenerator:
    def setup_method(self):
        """Reset windows before each test."""
        from modules.signal_generator import reset_all_windows
        reset_all_windows()

    def test_buy_signal(self):
        from modules.signal_generator import generate_signal
        # Three strongly positive scores should trigger BUY
        generate_signal("AAPL", 0.8)
        generate_signal("AAPL", 0.9)
        result = generate_signal("AAPL", 0.85)
        assert result == "BUY"

    def test_sell_signal(self):
        from modules.signal_generator import generate_signal
        generate_signal("TSLA", -0.8)
        generate_signal("TSLA", -0.9)
        result = generate_signal("TSLA", -0.85)
        assert result == "SELL"

    def test_hold_signal(self):
        from modules.signal_generator import generate_signal
        result = generate_signal("MSFT", 0.1)
        assert result == "HOLD"

    def test_window_smoothing(self):
        from modules.signal_generator import generate_signal
        # Mix of positive and negative — should average to HOLD
        generate_signal("NVDA", 0.9)
        generate_signal("NVDA", -0.9)
        result = generate_signal("NVDA", 0.0)
        assert result == "HOLD"


# ─────────────────────────────────────────────────────────────────────────────
# risk_manager
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskManager:
    def setup_method(self):
        """Reset risk state before each test."""
        import modules.risk_manager as rm
        from dataclasses import field
        from datetime import date
        rm._state = rm.RiskState()

    def test_hold_returns_none(self):
        from modules.risk_manager import evaluate_trade
        assert evaluate_trade("AAPL", "HOLD", 150.0) is None

    def test_buy_approved(self):
        from modules.risk_manager import evaluate_trade
        order = evaluate_trade("AAPL", "BUY", 150.0)
        assert order is not None
        assert order.action == "BUY"
        assert order.qty >= 1
        assert order.stop_loss < 150.0
        assert order.take_profit > 150.0

    def test_sell_no_position_returns_none(self):
        from modules.risk_manager import evaluate_trade
        assert evaluate_trade("AAPL", "SELL", 150.0) is None

    def test_duplicate_buy_blocked(self):
        from modules.risk_manager import evaluate_trade, record_open_position
        record_open_position("AAPL", 6)
        order = evaluate_trade("AAPL", "BUY", 150.0)
        assert order is None

    def test_max_open_trades_blocks_buy(self):
        from modules.risk_manager import evaluate_trade, record_open_position
        import modules.risk_manager as rm
        from config.settings import MAX_OPEN_TRADES
        # Fill up to the limit
        for i in range(MAX_OPEN_TRADES):
            rm._state.open_positions[f"T{i}"] = 10
        order = evaluate_trade("NEWT", "BUY", 50.0)
        assert order is None

    def test_qty_calculation(self):
        from modules.risk_manager import evaluate_trade
        from config.settings import TRADE_SIZE_USD
        order = evaluate_trade("AAPL", "BUY", 100.0)
        assert order is not None
        assert order.qty == TRADE_SIZE_USD // 100


# ─────────────────────────────────────────────────────────────────────────────
# portfolio_manager
# ─────────────────────────────────────────────────────────────────────────────

class TestPortfolioManager:
    def setup_method(self, tmp_path=None):
        """Create a completely fresh portfolio for each test.

        Root cause of the flaky test: if /tmp/test_portfolio.json exists
        from a previous run, Portfolio._load() restores stale positions
        before the test even starts — so record_sell can't find a position
        that record_buy 'just' created (it was overwritten by _load).

        Fix: delete the file BEFORE constructing the Portfolio instance.
        """
        import os
        import modules.portfolio_manager as pm

        # Point to a temp file and wipe it so _load() finds nothing
        pm.PORTFOLIO_FILE = "/tmp/test_portfolio.json"
        if os.path.exists("/tmp/test_portfolio.json"):
            os.remove("/tmp/test_portfolio.json")

        pm.portfolio = pm.Portfolio()   # now _load() is a clean no-op
        self.portfolio = pm.portfolio

    def test_record_buy(self):
        self.portfolio.record_buy("AAPL", 10, 150.0)
        assert "AAPL" in self.portfolio.positions
        assert self.portfolio.positions["AAPL"].qty == 10

    def test_record_sell_pnl(self):
        self.portfolio.record_buy("AAPL", 10, 150.0)
        pnl = self.portfolio.record_sell("AAPL", 160.0)
        assert abs(pnl - 100.0) < 0.01        # 10 shares × $10 gain
        assert "AAPL" not in self.portfolio.positions
        assert abs(self.portfolio.realised_pnl - 100.0) < 0.01

    def test_unrealised_pnl(self):
        self.portfolio.record_buy("AAPL", 10, 150.0)
        upnl = self.portfolio.unrealised_pnl({"AAPL": 155.0})
        assert abs(upnl - 50.0) < 0.01

    def test_sell_no_position(self):
        pnl = self.portfolio.record_sell("FAKE", 100.0)
        assert pnl == 0.0

    def test_summary_keys(self):
        s = self.portfolio.summary()
        assert "open_positions" in s
        assert "realised_pnl" in s
        assert "net_pnl" in s
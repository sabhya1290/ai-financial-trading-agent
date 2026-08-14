

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config.settings import LOG_DIR
from utils.logger import get_logger, log_event

logger = get_logger("portfolio_manager")

PORTFOLIO_FILE = os.path.join(LOG_DIR, "portfolio.json")


@dataclass
class Position:
    ticker:      str
    qty:         int
    entry_price: float
    entry_time:  str = field(default_factory=lambda: _now_iso())
    stop_loss:   float = 0.0
    take_profit: float = 0.0


@dataclass
class TradeRecord:
    ticker:      str
    action:      str       # "BUY" | "SELL"
    qty:         int
    price:       float
    timestamp:   str = field(default_factory=lambda: _now_iso())
    pnl:         float = 0.0
    order_id:    Optional[str] = None
    headline:    str = ""
    sentiment:   str = ""
    score:       float = 0.0




class Portfolio:
    

    def __init__(self):
        self.positions:    Dict[str, Position]  = {}
        self.trade_history: List[TradeRecord]   = []
        self.realised_pnl:  float               = 0.0
        self._load()


    def record_buy(
        self,
        ticker:      str,
        qty:         int,
        price:       float,
        order_id:    Optional[str] = None,
        headline:    str = "",
        sentiment:   str = "",
        score:       float = 0.0,
        stop_loss:   float = 0.0,
        take_profit: float = 0.0,
    ) -> None:

        self.positions[ticker] = Position(
            ticker=ticker, qty=qty, entry_price=price,
            stop_loss=stop_loss, take_profit=take_profit,
        )
        rec = TradeRecord(
            ticker=ticker, action="BUY", qty=qty, price=price,
            order_id=order_id, headline=headline,
            sentiment=sentiment, score=score,
        )
        self.trade_history.append(rec)
        log_event(
            logger, "POSITION_OPENED",
            ticker=ticker, qty=qty, price=price,
            stop_loss=stop_loss, take_profit=take_profit,
        )
        self._save()

    def record_sell(
        self,
        ticker:    str,
        price:     float,
        order_id:  Optional[str] = None,
        headline:  str = "",
        sentiment: str = "",
        score:     float = 0.0,
    ) -> float:
        
        pos = self.positions.pop(ticker, None)
        if pos is None:
            logger.warning("record_sell called for %s but no open position.", ticker)
            return 0.0

        pnl = (price - pos.entry_price) * pos.qty
        self.realised_pnl += pnl

        rec = TradeRecord(
            ticker=ticker, action="SELL", qty=pos.qty, price=price,
            pnl=pnl, order_id=order_id, headline=headline,
            sentiment=sentiment, score=score,
        )
        self.trade_history.append(rec)
        log_event(
            logger, "POSITION_CLOSED",
            ticker=ticker, qty=pos.qty,
            entry_price=pos.entry_price, exit_price=price,
            pnl=round(pnl, 2), total_realised_pnl=round(self.realised_pnl, 2),
        )
        self._save()
        return pnl


    def unrealised_pnl(self, current_prices: Dict[str, float]) -> float:
        
        total = 0.0
        for ticker, pos in self.positions.items():
            if ticker in current_prices:
                total += (current_prices[ticker] - pos.entry_price) * pos.qty
        return round(total, 2)

    def summary(self, current_prices: Optional[Dict[str, float]] = None) -> Dict:
        """Return a human-readable portfolio snapshot."""
        cp     = current_prices or {}
        u_pnl  = self.unrealised_pnl(cp)
        return {
            "open_positions":    len(self.positions),
            "positions":         {t: asdict(p) for t, p in self.positions.items()},
            "total_trades":      len(self.trade_history),
            "realised_pnl":      round(self.realised_pnl, 2),
            "unrealised_pnl":    u_pnl,
            "net_pnl":           round(self.realised_pnl + u_pnl, 2),
        }

    def print_summary(self, current_prices: Optional[Dict[str, float]] = None) -> None:
        s = self.summary(current_prices)
        print("\n" + "═" * 52)
        print("  PORTFOLIO SNAPSHOT")
        print("═" * 52)
        print(f"  Open positions   : {s['open_positions']}")
        print(f"  Total trades     : {s['total_trades']}")
        print(f"  Realised PnL     : ${s['realised_pnl']:,.2f}")
        print(f"  Unrealised PnL   : ${s['unrealised_pnl']:,.2f}")
        print(f"  Net PnL          : ${s['net_pnl']:,.2f}")
        if self.positions:
            print("\n  Current positions:")
            for ticker, pos in self.positions.items():
                cur = current_prices.get(ticker, pos.entry_price) if current_prices else pos.entry_price
                upnl = (cur - pos.entry_price) * pos.qty
                print(f"    {ticker:6s} {pos.qty:4d} shares @ ${pos.entry_price:.2f}"
                      f"  (now ${cur:.2f}, uPnL=${upnl:+.2f})")
        print("═" * 52 + "\n")

    def _save(self) -> None:
        """Persist portfolio state to JSON."""
        os.makedirs(LOG_DIR, exist_ok=True)
        data = {
            "positions":     {t: asdict(p) for t, p in self.positions.items()},
            "trade_history": [asdict(r) for r in self.trade_history],
            "realised_pnl":  self.realised_pnl,
        }
        with open(PORTFOLIO_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self) -> None:
        """Restore portfolio state from JSON if it exists."""
        if not os.path.exists(PORTFOLIO_FILE):
            return
        try:
            with open(PORTFOLIO_FILE) as f:
                data = json.load(f)
            self.realised_pnl = data.get("realised_pnl", 0.0)
            for t, pd in data.get("positions", {}).items():
                self.positions[t] = Position(**pd)
            for rd in data.get("trade_history", []):
                self.trade_history.append(TradeRecord(**rd))
            logger.info(
                "Portfolio loaded: %d positions, %d trades, PnL=$%.2f",
                len(self.positions), len(self.trade_history), self.realised_pnl,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load portfolio state: %s", exc)


portfolio = Portfolio()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()



from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Optional

from config.settings import (
    MAX_OPEN_TRADES,
    TRADE_SIZE_USD,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    MAX_DAILY_LOSS_USD,
)
from utils.logger import get_logger, log_event

logger = get_logger("risk_manager")



@dataclass
class TradeOrder:
    ticker:       str
    action:       str          
    qty:          int          
    entry_price:  float        
    stop_loss:    float        
    take_profit:  float        
    reason:       str = ""     


@dataclass
class RiskState:
    open_positions: Dict[str, int] = field(default_factory=dict)
    daily_loss:     float = 0.0
    session_date:   date  = field(default_factory=date.today)
    trading_halted: bool  = False

_state = RiskState()


def evaluate_trade(
    ticker: str,
    signal: str,
    current_price: float,
) -> Optional[TradeOrder]:
  

    _refresh_daily_state()

    if signal == "HOLD":
        return None

    if _state.trading_halted:
        logger.warning("Trading is HALTED (daily loss limit reached). Skipping %s %s.", signal, ticker)
        return None

    if signal == "BUY":
        if ticker in _state.open_positions:
            logger.info("Skipping BUY %s — already holding a position.", ticker)
            return None

        if len(_state.open_positions) >= MAX_OPEN_TRADES:
            logger.warning(
                "Skipping BUY %s — max open trades (%d) reached.", ticker, MAX_OPEN_TRADES
            )
            return None

        qty        = _calculate_qty(current_price)
        stop_loss  = round(current_price * (1 - STOP_LOSS_PCT),  2)
        take_profit= round(current_price * (1 + TAKE_PROFIT_PCT), 2)

        order = TradeOrder(
            ticker=ticker, action="BUY", qty=qty,
            entry_price=current_price,
            stop_loss=stop_loss, take_profit=take_profit,
            reason="Positive sentiment signal",
        )
        log_event(logger, "TRADE_APPROVED", **order.__dict__)
        return order


    if signal == "SELL":
        if ticker not in _state.open_positions:
            logger.info("Skipping SELL %s — no open position.", ticker)
            return None

        qty = _state.open_positions[ticker]
        order = TradeOrder(
            ticker=ticker, action="SELL", qty=qty,
            entry_price=current_price,
            stop_loss=0.0, take_profit=0.0,
            reason="Negative sentiment signal",
        )
        log_event(logger, "TRADE_APPROVED", **order.__dict__)
        return order

    return None   


def record_open_position(ticker: str, qty: int) -> None:
    _state.open_positions[ticker] = qty
    logger.info("Position opened: %s × %d shares.", ticker, qty)


def record_closed_position(ticker: str, pnl: float) -> None:
    _state.open_positions.pop(ticker, None)
    if pnl < 0:
        _state.daily_loss += abs(pnl)
        if _state.daily_loss >= MAX_DAILY_LOSS_USD:
            _state.trading_halted = True
            logger.critical(
                "Daily loss limit $%.2f reached — halting all trading for today.",
                MAX_DAILY_LOSS_USD,
            )
    logger.info("Position closed: %s  PnL=$%.2f  daily_loss=$%.2f", ticker, pnl, _state.daily_loss)


def get_state() -> RiskState:
    return _state



def _calculate_qty(price: float) -> int:
   
    if price <= 0:
        return 1
    return max(1, int(TRADE_SIZE_USD / price))


def _refresh_daily_state() -> None:

    today = date.today()
    if _state.session_date != today:
        logger.info("New trading day — resetting daily loss counter.")
        _state.session_date  = today
        _state.daily_loss    = 0.0
        _state.trading_halted= False

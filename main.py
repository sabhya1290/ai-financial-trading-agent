"""
main.py — FinBERT Sentiment Trading Agent — main entry point.

Run this script to start the agent:

    python main.py

The agent loops continuously (configurable interval) and performs the
full pipeline on every cycle:

  1.  Fetch live headlines       → news_fetcher
  2.  Detect stock tickers       → ticker_detector
  3.  Score sentiment (FinBERT)  → sentiment_scorer
  4.  Generate trade signals     → signal_generator
  5.  Validate against risk rules→ risk_manager
  6.  Execute orders on Alpaca   → broker_executor
  7.  Update portfolio state     → portfolio_manager
  8.  Log every event            → utils.logger

Press Ctrl-C to stop gracefully.
"""

from __future__ import annotations

import signal
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List

# ── Module imports ────────────────────────────────────────────────────────────
from config.settings import NEWS_POLL_INTERVAL
from modules.news_fetcher     import fetch_headlines
from modules.ticker_detector  import detect_tickers
from modules.sentiment_scorer import score_headlines
from modules.signal_generator import generate_signal
from modules.risk_manager     import evaluate_trade, record_open_position, record_closed_position
from modules.broker_executor  import execute_order, get_current_price, get_account_info
from modules.portfolio_manager import portfolio
from utils.logger             import get_logger, log_event

logger = get_logger("main")


# ── Graceful shutdown handler ─────────────────────────────────────────────────

_running = True

def _handle_shutdown(signum, frame):
    global _running
    logger.info("Shutdown signal received — finishing current cycle then exiting.")
    _running = False

signal.signal(signal.SIGINT,  _handle_shutdown)
signal.signal(signal.SIGTERM, _handle_shutdown)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def run_cycle() -> None:
    """
    Execute a single full pipeline cycle.
    Called once per NEWS_POLL_INTERVAL seconds.
    """
    cycle_start = datetime.now(timezone.utc)
    logger.info("── Cycle start at %s ──────────────────────────────", cycle_start.strftime("%H:%M:%S"))

    # ── Step 1: Fetch headlines ───────────────────────────────────────────────
    headlines_raw = fetch_headlines()
    if not headlines_raw:
        logger.info("No new headlines this cycle.")
        return

    # ── Step 2: Filter headlines that mention a watchlist ticker ─────────────
    # We build a flat list of (ticker, headline_dict) pairs for processing.
    tagged: List[Dict] = []
    for item in headlines_raw:
        tickers = detect_tickers(item["headline"])
        for ticker in tickers:
            tagged.append({**item, "ticker": ticker})

    if not tagged:
        logger.info("No watchlist tickers found in %d headlines.", len(headlines_raw))
        return

    logger.info("Found %d ticker-tagged headlines from %d total.", len(tagged), len(headlines_raw))

    # ── Step 3: Batch-score sentiment ────────────────────────────────────────
    texts        = [t["headline"] for t in tagged]
    sentiments   = score_headlines(texts)   # same order as tagged

    # ── Steps 4-7: Per-headline signal → risk → execute ───────────────────────
    for item, sentiment in zip(tagged, sentiments):
        ticker     = item["ticker"]
        headline   = item["headline"]
        label      = sentiment["label"]
        score      = sentiment["score"]
        probability= sentiment["probability"]

        log_event(
            logger, "HEADLINE_PROCESSED",
            ticker=ticker, headline=headline,
            sentiment=label, score=score, probability=probability,
        )

        # Step 4: Generate trade signal from rolling window
        signal = generate_signal(ticker, score)

        if signal == "HOLD":
            logger.info("[%s] HOLD  (score=%.3f, label=%s)", ticker, score, label)
            continue

        # Step 5: Get current market price
        price = get_current_price(ticker)
        if price is None:
            logger.warning("[%s] Cannot fetch price — skipping.", ticker)
            continue

        # Step 6: Risk management validation
        order = evaluate_trade(ticker, signal, price)
        if order is None:
            continue   # blocked by risk rules

        # Step 7: Submit order to Alpaca paper trading
        result = execute_order(order)

        if result["success"]:
            if order.action == "BUY":
                portfolio.record_buy(
                    ticker    = ticker,
                    qty       = order.qty,
                    price     = price,
                    order_id  = result["order_id"],
                    headline  = headline,
                    sentiment = label,
                    score     = score,
                    stop_loss   = order.stop_loss,
                    take_profit = order.take_profit,
                )
                record_open_position(ticker, order.qty)

            elif order.action == "SELL":
                pnl = portfolio.record_sell(
                    ticker    = ticker,
                    price     = price,
                    order_id  = result["order_id"],
                    headline  = headline,
                    sentiment = label,
                    score     = score,
                )
                record_closed_position(ticker, pnl)

    # ── Step 8: Print portfolio summary at end of cycle ───────────────────────
    portfolio.print_summary()

    elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
    logger.info("── Cycle complete in %.1f s ───────────────────────────────\n", elapsed)


# ── Agent loop ────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("═══════════════════════════════════════════════")
    logger.info("  FinBERT Sentiment Trading Agent  — starting  ")
    logger.info("  Poll interval : %d s                         ", NEWS_POLL_INTERVAL)
    logger.info("═══════════════════════════════════════════════")

    # Print Alpaca account details on startup so we know the connection works
    acct = get_account_info()
    if acct:
        logger.info(
            "Alpaca account  equity=$%.2f  cash=$%.2f  buying_power=$%.2f",
            acct.get("equity", 0), acct.get("cash", 0), acct.get("buying_power", 0),
        )

    while _running:
        try:
            run_cycle()
        except Exception as exc:          # noqa: BLE001
            # Log but don't crash — keep the agent alive through transient errors
            logger.exception("Unhandled error in cycle: %s", exc)

        if _running:
            logger.info("Sleeping %d s until next cycle …\n", NEWS_POLL_INTERVAL)
            # Sleep in 1-second ticks so Ctrl-C is responsive
            for _ in range(NEWS_POLL_INTERVAL):
                if not _running:
                    break
                time.sleep(1)

    logger.info("Agent stopped cleanly.")
    portfolio.print_summary()
    sys.exit(0)


if __name__ == "__main__":
    main()

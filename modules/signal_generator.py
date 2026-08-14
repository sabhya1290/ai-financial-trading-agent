

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional, Deque

from config.settings import (
    BUY_SCORE_THRESHOLD,
    SELL_SCORE_THRESHOLD,
    SIGNAL_WINDOW_SIZE,
)
from utils.logger import get_logger, log_event

logger = get_logger("signal_generator")

_score_windows: Dict[str, Deque[float]] = defaultdict(
    lambda: deque(maxlen=SIGNAL_WINDOW_SIZE)
)



def generate_signal(ticker: str, sentiment_score: float) -> str:

    window = _score_windows[ticker]
    window.append(sentiment_score)

    composite = sum(window) / len(window)
    n         = len(window)

    if composite >= BUY_SCORE_THRESHOLD:
        signal = "BUY"
    elif composite <= SELL_SCORE_THRESHOLD:
        signal = "SELL"
    else:
        signal = "HOLD"

    log_event(
        logger, "SIGNAL_GENERATED",
        ticker=ticker,
        new_score=round(sentiment_score, 4),
        composite=round(composite, 4),
        window_size=n,
        signal=signal,
    )
    return signal


def get_window(ticker: str) -> List[float]:
    return list(_score_windows[ticker])


def reset_window(ticker: str) -> None:

    _score_windows[ticker].clear()
    logger.debug("Score window reset for %s.", ticker)


def reset_all_windows() -> None:

    _score_windows.clear()
    logger.info("All score windows reset.")

"""
settings.py — Central configuration for the FinBERT Trading Agent.

All API keys, thresholds, and tunable parameters live here so that
no other module contains hard-coded magic numbers.
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads a .env file in the project root if present

# ──────────────────────────────────────────────
# API CREDENTIALS  (set these in your .env file)
# ──────────────────────────────────────────────
NEWS_API_KEY     = os.getenv("NEWS_API_KEY", "YOUR_NEWSAPI_KEY")
FINNHUB_API_KEY  = os.getenv("FINNHUB_API_KEY", "YOUR_FINNHUB_KEY")
ALPACA_API_KEY   = os.getenv("ALPACA_API_KEY", "YOUR_ALPACA_KEY")
ALPACA_SECRET    = os.getenv("ALPACA_SECRET",  "YOUR_ALPACA_SECRET")

# Alpaca paper-trading base URL (use live URL for real trading)
ALPACA_BASE_URL  = "https://paper-api.alpaca.markets"

# ──────────────────────────────────────────────
# NEWS FETCHER
# ──────────────────────────────────────────────
NEWS_SOURCE          = "finnhub"          # "newsapi" | "finnhub"
NEWS_POLL_INTERVAL   = 60                 # seconds between news fetches
NEWS_MAX_HEADLINES   = 20                 # max headlines per fetch cycle
NEWS_LOOKBACK_HOURS  = 1                  # how far back to look for news

# ──────────────────────────────────────────────
# TICKER DETECTION
# ──────────────────────────────────────────────
# Watchlist: only trade these tickers to keep the demo focused.
# Expand to any S&P 500 list for production use.
WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META",
    "TSLA", "NVDA", "JPM", "BAC", "GS",
    "NFLX", "AMD", "INTC", "ORCL", "IBM",
]

# ──────────────────────────────────────────────
# SENTIMENT SCORING (FinBERT)
# ──────────────────────────────────────────────
FINBERT_MODEL        = "ProsusAI/finbert"  # HuggingFace model ID
SENTIMENT_BATCH_SIZE = 8                   # headlines per inference batch
# Score thresholds that convert probability → numeric score in [-1, +1]
STRONG_POSITIVE_THRESHOLD = 0.70           # probability ≥ this → strong buy
STRONG_NEGATIVE_THRESHOLD = 0.70           # probability ≥ this → strong sell

# ──────────────────────────────────────────────
# SIGNAL GENERATION
# ──────────────────────────────────────────────
BUY_SCORE_THRESHOLD  =  0.50   # composite score above this → BUY
SELL_SCORE_THRESHOLD = -0.50   # composite score below this → SELL
# Aggregation window: combine N recent headlines before signalling
SIGNAL_WINDOW_SIZE   = 3

# ──────────────────────────────────────────────
# RISK MANAGEMENT
# ──────────────────────────────────────────────
MAX_OPEN_TRADES      = 5        # max simultaneous positions
TRADE_SIZE_USD       = 1_000    # fixed dollar amount per trade
STOP_LOSS_PCT        = 0.02     # 2 % stop-loss below entry price
TAKE_PROFIT_PCT      = 0.05     # 5 % take-profit above entry price
MAX_DAILY_LOSS_USD   = 3_000    # halt trading if daily loss exceeds this

# ──────────────────────────────────────────────
# LOGGING
# ──────────────────────────────────────────────
LOG_DIR   = os.path.join(os.path.dirname(__file__), "..", "logs")
LOG_LEVEL = "INFO"              # DEBUG | INFO | WARNING | ERROR

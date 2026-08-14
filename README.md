# FinBERT Sentiment Trading Agent

An autonomous trading agent that fetches live financial news, scores headline
sentiment using FinBERT, and executes paper trades on Alpaca based on the
resulting signals — all with built-in risk management.

---

## Architecture

```
finbert_trader/
├── config/
│   └── settings.py          ← All tunable parameters & API keys
├── modules/
│   ├── news_fetcher.py       ← Pulls headlines from Finnhub or NewsAPI
│   ├── ticker_detector.py   ← Maps headlines to watchlist tickers
│   ├── sentiment_scorer.py  ← FinBERT inference (HuggingFace)
│   ├── signal_generator.py  ← Rolling-window BUY / SELL / HOLD logic
│   ├── risk_manager.py      ← Position limits, stop-loss, daily-loss guard
│   ├── broker_executor.py   ← Alpaca paper-trading REST client
│   └── portfolio_manager.py ← Position tracking, PnL, persistence
├── utils/
│   └── logger.py            ← Console + JSON file logger
├── tests/
│   └── test_modules.py      ← pytest unit tests (no API keys needed)
├── logs/                    ← Auto-created; agent.log + portfolio.json
├── main.py                  ← Entry point — the agent loop
├── requirements.txt
└── .env.example
```

### Pipeline (one cycle)

```
Finnhub / NewsAPI
      │
      ▼
 news_fetcher        ← fetch up to N headlines from the last hour
      │
      ▼
 ticker_detector     ← cashtag regex + company-name lookup + (opt) spaCy NER
      │
      ▼
 sentiment_scorer    ← ProsusAI/finbert → label + score ∈ [-1, +1]
      │
      ▼
 signal_generator    ← rolling mean of last SIGNAL_WINDOW_SIZE scores
      │                  mean ≥  0.50 → BUY
      │                  mean ≤ -0.50 → SELL
      │                  else        → HOLD
      ▼
 risk_manager        ← max open trades · stop-loss calc · daily-loss halt
      │
      ▼
 broker_executor     ← Alpaca bracket order (BUY) or market order (SELL)
      │
      ▼
 portfolio_manager   ← records trade, updates PnL, persists to JSON
      │
      ▼
    logger           ← structured JSON log line for every event
```

---

## Quick-start

### 1. Clone & install

```bash
git clone <your-repo-url>
cd finbert_trader
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

> FinBERT (~440 MB) downloads automatically from HuggingFace on first run.

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and fill in your keys:
#   FINNHUB_API_KEY  — free at https://finnhub.io
#   ALPACA_API_KEY   — free paper-trading account at https://alpaca.markets
#   ALPACA_SECRET
```

### 3. Run tests (no API keys needed)

```bash
pytest tests/ -v
```

### 4. Start the agent

```bash
python main.py
```

The agent will:
- Print a startup banner with Alpaca account info
- Fetch headlines every 60 seconds (configurable in `settings.py`)
- Log every decision to `logs/agent.log`
- Save portfolio state to `logs/portfolio.json`

---

## Key configuration knobs (`config/settings.py`)

| Parameter | Default | What it does |
|---|---|---|
| `NEWS_SOURCE` | `"finnhub"` | Switch to `"newsapi"` if preferred |
| `WATCHLIST` | 15 tickers | Only trade these symbols |
| `NEWS_POLL_INTERVAL` | 60 s | How often to fetch news |
| `SIGNAL_WINDOW_SIZE` | 3 | Headlines to average before signalling |
| `BUY_SCORE_THRESHOLD` | 0.50 | Composite score above this → BUY |
| `SELL_SCORE_THRESHOLD` | -0.50 | Composite score below this → SELL |
| `TRADE_SIZE_USD` | $1,000 | Fixed dollar size per trade |
| `STOP_LOSS_PCT` | 2 % | Stop-loss distance from entry |
| `TAKE_PROFIT_PCT` | 5 % | Take-profit distance from entry |
| `MAX_OPEN_TRADES` | 5 | Maximum simultaneous positions |
| `MAX_DAILY_LOSS_USD` | $3,000 | Halt trading if losses reach this |

---

## Extending the agent

**Add more tickers:** extend `WATCHLIST` and `COMPANY_TO_TICKER` in
`ticker_detector.py`.

**Use a GPU:** change `device=-1` to `device=0` in `sentiment_scorer.py`
for ~10× faster inference.

**Live trading:** change `ALPACA_BASE_URL` to `https://api.alpaca.markets`
and fund a live account — all other code is identical.

**Add a Telegram / Slack alert:** call a webhook inside `portfolio_manager.py`
after `record_buy` / `record_sell`.

---

## Disclaimer

This project is for **educational purposes only**.  
Past performance of any strategy does not guarantee future results.  
All trades are simulated on Alpaca's paper-trading environment.

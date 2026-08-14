

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List

import requests

from config.settings import (
    FINNHUB_API_KEY,
    NEWS_API_KEY,          
    NEWS_LOOKBACK_HOURS,
    NEWS_MAX_HEADLINES,
    NEWS_SOURCE,
)
from utils.logger import get_logger

logger = get_logger("news_fetcher")

_DEMO_HEADLINES: List[Dict[str, Any]] = [
    {
        "headline": "Federal Reserve signals potential rate cuts later this year",
        "source": "Demo Data",
        "url": "",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    },
    {
        "headline": "S&P 500 closes at record high amid strong earnings season",
        "source": "Demo Data",
        "url": "",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    },
    {
        "headline": "Tech sector leads market rally as AI investments surge",
        "source": "Demo Data",
        "url": "",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    },
    {
        "headline": "Oil prices stabilise after weeks of volatility",
        "source": "Demo Data",
        "url": "",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    },
    {
        "headline": "Global markets cautious ahead of key economic data releases",
        "source": "Demo Data",
        "url": "",
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    },
]



def fetch_headlines() -> List[Dict[str, Any]]:
    """
    Return up to NEWS_MAX_HEADLINES financial headlines.

    Tries each source in priority order and returns as soon as one succeeds.
    Falls back to static demo headlines if every live source fails.
    """
    sources = [
        ("Finnhub",       _fetch_finnhub),
        ("Yahoo Finance", _fetch_yahoo_finance),
        ("GNews",         _fetch_gnews),
    ]

    for name, fetcher in sources:
        try:
            results = fetcher()
            if results:
                logger.info("fetch_headlines: got %d items from %s.", len(results), name)
                return results[:NEWS_MAX_HEADLINES]
            logger.warning("fetch_headlines: %s returned 0 items, trying next source.", name)
        except Exception as exc:  # noqa: BLE001
            logger.warning("fetch_headlines: %s raised an exception (%s), trying next source.", name, exc)

    # All live sources failed — return demo data so the UI never breaks
    logger.error("fetch_headlines: all sources failed. Returning demo headlines.")
    return _DEMO_HEADLINES[:NEWS_MAX_HEADLINES]



def _fetch_finnhub() -> List[Dict[str, Any]]:
    """
    Fetch from Finnhub /news endpoint.

    Fixes vs. original:
    - Validates that the API key is present before making the request.
    - Filters by lookback window AFTER slicing so the slice cap is not wasted.
    - Skips items with empty headlines.
    - Tries both "general" and "forex" categories if the first returns nothing.
    """
    if not FINNHUB_API_KEY:
        logger.warning("Finnhub: FINNHUB_API_KEY is not set, skipping.")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_LOOKBACK_HOURS)
    results: List[Dict[str, Any]] = []

    for category in ("general", "forex", "merger"):
        if len(results) >= NEWS_MAX_HEADLINES:
            break

        url = "https://finnhub.io/api/v1/news"
        params = {"category": category, "token": FINNHUB_API_KEY}

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            raw: List[Dict] = resp.json()
        except requests.RequestException as exc:
            logger.warning("Finnhub (%s): request failed: %s", category, exc)
            continue

        if not isinstance(raw, list):
            logger.warning("Finnhub (%s): unexpected response type %s.", category, type(raw))
            continue

        for item in raw:
            headline = (item.get("headline") or "").strip()
            if not headline:
                continue

            published = datetime.fromtimestamp(
                item.get("datetime", 0) or 0, tz=timezone.utc
            )

            if published < cutoff:
                continue

            results.append({
                "headline":     headline,
                "source":       item.get("source") or "Finnhub",
                "url":          item.get("url") or "",
                "published_at": published.strftime("%Y-%m-%d"),
            })

            if len(results) >= NEWS_MAX_HEADLINES:
                break

    return results



def _fetch_yahoo_finance() -> List[Dict[str, Any]]:
    """
    Fetch from Yahoo Finance's public RSS feed.

    No API key needed. Parses the RSS XML directly.
    """
    url = "https://feeds.finance.yahoo.com/rss/2.0/headline"
    params = {"s": "^GSPC,^DJI,AAPL,MSFT,GOOGL,AMZN,TSLA", "region": "US", "lang": "en-US"}

    try:
        resp = requests.get(url, params=params, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Yahoo Finance: request failed: %s", exc)
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as exc:
        logger.warning("Yahoo Finance: XML parse error: %s", exc)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_LOOKBACK_HOURS)
    results: List[Dict[str, Any]] = []

    # RSS items live at channel > item
    for item in root.iter("item"):
        headline = (item.findtext("title") or "").strip()
        if not headline:
            continue

        pub_raw = item.findtext("pubDate") or ""
        try:
            published = parsedate_to_datetime(pub_raw).astimezone(timezone.utc)
        except Exception:  # noqa: BLE001
            published = datetime.now(timezone.utc)

        if published < cutoff:
            continue

        results.append({
            "headline":     headline,
            "source":       "Yahoo Finance",
            "url":          item.findtext("link") or "",
            "published_at": published.strftime("%Y-%m-%d"),
        })

        if len(results) >= NEWS_MAX_HEADLINES:
            break

    return results



def _fetch_gnews() -> List[Dict[str, Any]]:
    """
    Fetch from GNews /search endpoint.

    Requires GNEWS_API_KEY to be set in config/settings.py.
    Free tier allows 100 requests/day.
    """
    # GNews key may not exist in older settings files — guard gracefully
    gnews_key: str = getattr(__import__("config.settings", fromlist=["GNEWS_API_KEY"]), "GNEWS_API_KEY", "")
    if not gnews_key:
        logger.warning("GNews: GNEWS_API_KEY is not set, skipping.")
        return []

    url = "https://gnews.io/api/v4/search"
    params = {
        "q":        "stock market OR earnings OR finance OR economy",
        "lang":     "en",
        "country":  "us",
        "max":      NEWS_MAX_HEADLINES,
        "sortby":   "publishedAt",
        "apikey":   gnews_key,
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("GNews: request failed: %s", exc)
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=NEWS_LOOKBACK_HOURS)
    results: List[Dict[str, Any]] = []

    for article in data.get("articles") or []:
        headline = (article.get("title") or "").strip()
        if not headline:
            continue

        pub_raw = article.get("publishedAt") or ""
        try:
            # GNews uses ISO-8601: "2026-03-31T12:00:00Z"
            published = datetime.strptime(pub_raw, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            published = datetime.now(timezone.utc)

        if published < cutoff:
            continue

        results.append({
            "headline":     headline,
            "source":       (article.get("source") or {}).get("name") or "GNews",
            "url":          article.get("url") or "",
            "published_at": published.strftime("%Y-%m-%d"),
        })

    return results
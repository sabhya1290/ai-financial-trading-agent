

from __future__ import annotations

import re
from typing import List, Dict

from config.settings import WATCHLIST
from utils.logger import get_logger

logger = get_logger("ticker_detector")


COMPANY_TO_TICKER: Dict[str, str] = {
    # Big Tech
    "apple":      "AAPL",
    "microsoft":  "MSFT",
    "google":     "GOOGL",
    "alphabet":   "GOOGL",
    "amazon":     "AMZN",
    "meta":       "META",
    "facebook":   "META",
    "tesla":      "TSLA",
    "nvidia":     "NVDA",
    "netflix":    "NFLX",
    "amd":        "AMD",
    "advanced micro": "AMD",
    "intel":      "INTC",
    "oracle":     "ORCL",
    "ibm":        "IBM",
    # Finance
    "jpmorgan":   "JPM",
    "jp morgan":  "JPM",
    "bank of america": "BAC",
    "goldman":    "GS",
    "goldman sachs": "GS",
}

_CASHTAG_RE = re.compile(r"\$([A-Z]{1,5})\b")


def detect_tickers(headline: str) -> List[str]:
    
    found: List[str] = []

    for match in _CASHTAG_RE.finditer(headline):
        ticker = match.group(1).upper()
        if ticker in WATCHLIST and ticker not in found:
            found.append(ticker)

    lower = headline.lower()
    for name, ticker in COMPANY_TO_TICKER.items():
        if name in lower and ticker in WATCHLIST and ticker not in found:
            found.append(ticker)

    if not found:
        found.extend(_spacy_detect(headline))

    if found:
        logger.debug("Detected tickers %s in: %r", found, headline)
    else:
        logger.debug("No watchlist ticker found in: %r", headline)

    return found




_nlp = None 

def _spacy_detect(headline: str) -> List[str]:
    
    global _nlp
    try:
        if _nlp is None:
            import spacy  # type: ignore
            _nlp = spacy.load("en_core_web_sm")
    except (ImportError, OSError):
        return []   

    doc    = _nlp(headline)
    result = []
    for ent in doc.ents:
        if ent.label_ == "ORG":
            key = ent.text.lower()
            if key in COMPANY_TO_TICKER:
                ticker = COMPANY_TO_TICKER[key]
                if ticker in WATCHLIST and ticker not in result:
                    result.append(ticker)
    return result

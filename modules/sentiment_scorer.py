

from __future__ import annotations

from typing import List, Dict, Any

from config.settings import (
    FINBERT_MODEL,
    SENTIMENT_BATCH_SIZE,
)
from utils.logger import get_logger

logger = get_logger("sentiment_scorer")



_pipeline = None

def _get_pipeline():
    """Return the HuggingFace sentiment-analysis pipeline (loads once)."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    logger.info("Loading FinBERT model '%s' … (first load may take ~30 s)", FINBERT_MODEL)
    from transformers import pipeline  # type: ignore

    _pipeline = pipeline(
        task             = "text-classification",
        model            = FINBERT_MODEL,
        tokenizer        = FINBERT_MODEL,
        top_k            = None,       # return all label scores, not just top-1
        truncation       = True,
        max_length       = 512,
        device           = -1,         # -1 = CPU; set to 0 for CUDA GPU
    )
    logger.info("FinBERT model loaded.")
    return _pipeline



def _labels_to_result(label_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convert the raw [{label, score}, …] list from the HuggingFace pipeline
    into our unified result format.

    Numeric sentiment score formula:
        score = P(positive) - P(negative)

    This produces a value in [-1, +1] that encodes both direction and
    confidence in a single number, making it easy to threshold later.
    """
    probs = {item["label"].lower(): item["score"] for item in label_scores}

    p_pos = probs.get("positive", 0.0)
    p_neg = probs.get("negative", 0.0)
    p_neu = probs.get("neutral",  0.0)

    # Dominant label
    dominant = max(probs, key=probs.get)        # type: ignore[arg-type]

    return {
        "label":       dominant,
        "score":       round(p_pos - p_neg, 4),
        "probability": round(probs[dominant], 4),
        "p_positive":  round(p_pos, 4),
        "p_neutral":   round(p_neu, 4),
        "p_negative":  round(p_neg, 4),
    }



def score_headlines(headlines: List[str]) -> List[Dict[str, Any]]:
    """
    Run FinBERT over a list of headline strings.

    Returns a list (same length & order as input) of dicts, each with:
        label        — dominant sentiment class
        score        — numeric score in [-1, +1]
        probability  — softmax confidence of dominant label
        p_positive   — raw positive probability
        p_neutral    — raw neutral probability
        p_negative   — raw negative probability

    Example
    -------
    >>> results = score_headlines(["Apple beats Q3 earnings estimates"])
    >>> results[0]
    {'label': 'positive', 'score': 0.82, 'probability': 0.91, ...}
    """
    if not headlines:
        return []

    pipe = _get_pipeline()
    results: List[Dict[str, Any]] = []

    # Process in batches to avoid OOM on CPU with long lists
    for i in range(0, len(headlines), SENTIMENT_BATCH_SIZE):
        batch = headlines[i : i + SENTIMENT_BATCH_SIZE]
        try:
            raw_outputs = pipe(batch)      # list of [{"label":…,"score":…}, …]
            for label_scores in raw_outputs:
                results.append(_labels_to_result(label_scores))
        except Exception as exc:           # noqa: BLE001
            logger.warning("FinBERT inference failed on batch: %s", exc)
            # Fill with neutral placeholders so the pipeline doesn't stall
            for _ in batch:
                results.append({
                    "label": "neutral", "score": 0.0, "probability": 1.0,
                    "p_positive": 0.0, "p_neutral": 1.0, "p_negative": 0.0,
                })

    logger.debug("Scored %d headlines.", len(results))
    return results


def score_single(headline: str) -> Dict[str, Any]:
    """Convenience wrapper to score a single headline string."""
    return score_headlines([headline])[0]

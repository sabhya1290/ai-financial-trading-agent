import time
import sys
import os
from datetime import datetime
from typing import Optional

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from modules.news_fetcher     import fetch_headlines
    NEWS_AVAILABLE = True
except ImportError:
    NEWS_AVAILABLE = False

try:
    from modules.ticker_detector  import detect_tickers
    TICKER_AVAILABLE = True
except ImportError:
    TICKER_AVAILABLE = False

try:
    from modules.sentiment_scorer import score_headlines
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False

try:
    from modules.signal_generator import generate_signal, reset_all_windows
    SIGNAL_AVAILABLE = True
except ImportError:
    SIGNAL_AVAILABLE = False

try:
    from modules.risk_manager import evaluate_trade, record_open_position, record_closed_position
    RISK_AVAILABLE = True
except ImportError:
    RISK_AVAILABLE = False

try:
    from modules.broker_executor  import execute_order, get_current_price, get_account_info
    BROKER_AVAILABLE = True
except ImportError:
    BROKER_AVAILABLE = False

try:
    from modules.portfolio_manager import portfolio
    PORTFOLIO_AVAILABLE = True
except ImportError:
    PORTFOLIO_AVAILABLE = False

st.set_page_config(
    page_title  = "FinBERT Trading Dashboard",
    page_icon   = "📈",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

st.markdown("""
<style>
/* ── Base ─────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background-color: #0d0f14;
    color: #c9d1d9;
}
.stApp { background-color: #0d0f14; }

/* ── Sidebar ──────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #161b22;
    border-right: 1px solid #21262d;
}
section[data-testid="stSidebar"] * { color: #c9d1d9 !important; }

/* ── Cards ────────────────────────────────────────────────── */
.card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 14px;
}
.card-green  { border-left: 4px solid #3fb950; }
.card-red    { border-left: 4px solid #f85149; }
.card-gray   { border-left: 4px solid #6e7681; }
.card-blue   { border-left: 4px solid #388bfd; }

/* ── Headline list items ──────────────────────────────────── */
.headline-item {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    cursor: pointer;
    font-size: 13px;
    line-height: 1.5;
    transition: border-color 0.15s;
}
.headline-item:hover  { border-color: #388bfd; }
.headline-item.active { border-color: #3fb950; background: #1a2332; }

/* ── Big decision badge ───────────────────────────────────── */
.decision-buy  { background:#1a3f25; color:#3fb950; padding:10px 22px; border-radius:8px; font-family:'IBM Plex Mono',monospace; font-size:22px; font-weight:600; display:inline-block; }
.decision-sell { background:#3f1a1a; color:#f85149; padding:10px 22px; border-radius:8px; font-family:'IBM Plex Mono',monospace; font-size:22px; font-weight:600; display:inline-block; }
.decision-hold { background:#2a2d35; color:#8b949e; padding:10px 22px; border-radius:8px; font-family:'IBM Plex Mono',monospace; font-size:22px; font-weight:600; display:inline-block; }

/* ── Sentiment badge ──────────────────────────────────────── */
.badge-pos  { background:#1a3f25; color:#3fb950; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:500; }
.badge-neg  { background:#3f1a1a; color:#f85149; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:500; }
.badge-neu  { background:#2a2d35; color:#8b949e; padding:3px 10px; border-radius:20px; font-size:12px; font-weight:500; }

/* ── Metric value ─────────────────────────────────────────── */
.metric-label { font-size:11px; color:#6e7681; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:4px; }
.metric-value { font-size:22px; font-weight:600; font-family:'IBM Plex Mono',monospace; }
.metric-green { color:#3fb950; }
.metric-red   { color:#f85149; }
.metric-white { color:#e6edf3; }
.metric-blue  { color:#388bfd; }

/* ── Timeline ─────────────────────────────────────────────── */
.timeline-item {
    display:flex; align-items:flex-start; gap:10px;
    padding:8px 0; border-bottom:1px solid #21262d; font-size:13px;
}
.timeline-dot {
    width:8px; height:8px; border-radius:50%;
    margin-top:5px; flex-shrink:0;
}
.dot-green { background:#3fb950; }
.dot-red   { background:#f85149; }
.dot-blue  { background:#388bfd; }
.dot-gray  { background:#6e7681; }

/* ── Progress bar ─────────────────────────────────────────── */
.prob-bar-bg { background:#21262d; border-radius:4px; height:8px; margin:4px 0; }
.prob-bar-fill-pos { background:#3fb950; border-radius:4px; height:8px; }
.prob-bar-fill-neg { background:#f85149; border-radius:4px; height:8px; }
.prob-bar-fill-neu { background:#6e7681; border-radius:4px; height:8px; }

/* ── Buttons ──────────────────────────────────────────────── */
div.stButton > button {
    border-radius: 8px;
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 500;
    font-size: 14px;
    border: 1px solid #30363d;
    background: #21262d;
    color: #c9d1d9;
    transition: all 0.15s;
}
div.stButton > button:hover {
    background: #2d333b;
    border-color: #8b949e;
    color: #e6edf3;
}

/* ── Scrollable feed ──────────────────────────────────────── */
.news-scroll {
    max-height: 480px;
    overflow-y: auto;
    padding-right: 4px;
}
.news-scroll::-webkit-scrollbar       { width:4px; }
.news-scroll::-webkit-scrollbar-track { background:#0d0f14; }
.news-scroll::-webkit-scrollbar-thumb { background:#30363d; border-radius:2px; }

/* ── Section header ───────────────────────────────────────── */
.section-header {
    font-size:11px; font-weight:600; color:#6e7681;
    text-transform:uppercase; letter-spacing:0.1em;
    margin:18px 0 10px; border-bottom:1px solid #21262d; padding-bottom:6px;
}
/* ── Mono text ─────────────────────────────────────────────── */
.mono { font-family:'IBM Plex Mono',monospace; font-size:13px; }

/* ── Input fields ─────────────────────────────────────────── */
div[data-testid="stTextInput"] input {
    background:#161b22; border:1px solid #30363d;
    color:#c9d1d9; border-radius:8px;
}
div[data-testid="stTextInput"] input:focus { border-color:#388bfd; }

/* ── Remove default Streamlit padding ────────────────────── */
.block-container { padding-top:1.5rem; padding-bottom:1rem; }
</style>
""", unsafe_allow_html=True)


defaults = {
    "headlines":         [],         # list of headline dicts from news_fetcher
    "selected_idx":      None,       # index of currently selected headline
    "analysis":          None,       # dict with full AI analysis result
    "pending_order":     None,       # TradeOrder waiting for confirmation
    "auto_execute_at":   None,       # timestamp when auto-execute fires
    "timeline":          [],         # activity log entries
    "custom_headline":   "",         # user-typed headline
    "mode":              "Fast",     # Fast / Explain / Auto
    "fetching":          False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def add_timeline(text: str, color: str = "blue"):
    st.session_state.timeline.insert(0, {
        "text":  text,
        "color": color,
        "time":  datetime.now().strftime("%H:%M:%S"),
    })
    # Keep only the last 20 entries
    st.session_state.timeline = st.session_state.timeline[:20]


def analyse_headline(headline: str, pos_threshold: float, neg_threshold: float) -> dict:
    """
    Calls your existing modules in sequence and returns a unified result dict.
    This is the only place where agent logic is invoked from the UI.
    """
    result = {
        "headline":    headline,
        "tickers":     [],
        "label":       "neutral",
        "score":       0.0,
        "p_positive":  0.0,
        "p_neutral":   1.0,
        "p_negative":  0.0,
        "probability": 0.0,
        "signal":      "HOLD",
        "confidence":  "Low",
        "order":       None,
        "risk_pass":   False,
        "price":       None,
        "error":       None,
    }

    # Step 1 — detect ticker
    if TICKER_AVAILABLE:
        try:
            result["tickers"] = detect_tickers(headline)
        except Exception as e:
            result["error"] = f"Ticker detection failed: {e}"

    # Step 2 — FinBERT sentiment
    if SENTIMENT_AVAILABLE:
        try:
            sent = score_headlines([headline])[0]
            result.update({
                "label":       sent["label"],
                "score":       sent["score"],
                "p_positive":  sent.get("p_positive", 0.0),
                "p_neutral":   sent.get("p_neutral",  1.0),
                "p_negative":  sent.get("p_negative", 0.0),
                "probability": sent["probability"],
            })
        except Exception as e:
            result["error"] = f"Sentiment scoring failed: {e}"
    else:
        import random
        result.update({
            "label":       random.choice(["positive", "neutral", "negative"]),
            "score":       round(random.uniform(-1, 1), 3),
            "p_positive":  round(random.uniform(0, 1), 3),
            "p_neutral":   round(random.uniform(0, 1), 3),
            "p_negative":  round(random.uniform(0, 1), 3),
            "probability": round(random.uniform(0.5, 0.99), 3),
        })

    ticker = result["tickers"][0] if result["tickers"] else "UNKNOWN"
    score  = result["score"]

    if SIGNAL_AVAILABLE and ticker != "UNKNOWN":
        try:
            signal = generate_signal(ticker, score)
        except Exception:
            signal = "BUY" if score >= pos_threshold else ("SELL" if score <= -neg_threshold else "HOLD")
    else:
        signal = "BUY" if score >= pos_threshold else ("SELL" if score <= -neg_threshold else "HOLD")

    result["signal"] = signal

    prob = result["probability"]
    result["confidence"] = "High" if prob >= 0.80 else ("Medium" if prob >= 0.60 else "Low")

    # Step 4 — risk check
    if RISK_AVAILABLE and ticker != "UNKNOWN" and signal != "HOLD":
        try:
            price = get_current_price(ticker) if BROKER_AVAILABLE else 150.0
            result["price"] = price or 150.0
            order = evaluate_trade(ticker, signal, result["price"])
            result["order"]     = order
            result["risk_pass"] = order is not None
        except Exception as e:
            result["error"] = f"Risk check failed: {e}"
    else:
        result["risk_pass"] = signal == "HOLD"

    return result


with st.sidebar:
    st.markdown("## ⚙️ Controls")

    # Mode selector
    st.markdown('<div class="section-header">Mode</div>', unsafe_allow_html=True)
    mode = st.radio(
        "Trading mode",
        ["Fast", "Explain", "Auto"],
        index=["Fast", "Explain", "Auto"].index(st.session_state.mode),
        label_visibility="collapsed",
    )
    st.session_state.mode = mode

    mode_descriptions = {
        "Fast":    "🟢 Instant analysis. Manual confirm.",
        "Explain": "🔵 Full AI reasoning shown.",
        "Auto":    "🟡 Auto-executes after timer.",
    }
    st.caption(mode_descriptions[mode])

    # Sentiment thresholds
    st.markdown('<div class="section-header">Sentiment Thresholds</div>', unsafe_allow_html=True)
    pos_threshold = st.slider("Positive threshold (BUY)", 0.1, 1.0, 0.50, 0.05,
                               help="Score above this → BUY signal")
    neg_threshold = st.slider("Negative threshold (SELL)", 0.1, 1.0, 0.50, 0.05,
                               help="Score below -this → SELL signal")

    # Risk management
    st.markdown('<div class="section-header">Risk Management</div>', unsafe_allow_html=True)
    max_trade_usd   = st.number_input("Max trade size ($)", 100, 50000, 1000, 100)
    stop_loss_pct   = st.slider("Stop loss (%)", 1, 20, 2)
    max_open_trades = st.slider("Max open trades", 1, 20, 5)

    # Auto execution timer
    st.markdown('<div class="section-header">Execution</div>', unsafe_allow_html=True)
    auto_timer   = st.slider("Auto-execute timer (s)", 5, 60, 15)
    auto_enabled = st.toggle("Enable auto trading", value=(mode == "Auto"))

    # Reset signal windows
    st.markdown("---")
    if st.button("🔄 Reset signal windows", use_container_width=True):
        if SIGNAL_AVAILABLE:
            reset_all_windows()
        st.session_state.analysis     = None
        st.session_state.pending_order= None
        add_timeline("Signal windows reset", "gray")
        st.success("Windows reset.")


st.markdown("""
<div style="display:flex; align-items:center; justify-content:space-between;
            padding:12px 0 18px; border-bottom:1px solid #21262d; margin-bottom:20px;">
  <div>
    <span style="font-size:20px; font-weight:600; font-family:'IBM Plex Mono',monospace; color:#e6edf3;">
      📈 FinBERT Trading Dashboard
    </span>
    <span style="font-size:12px; color:#6e7681; margin-left:14px;">Paper Trading — AI Sentiment Engine</span>
  </div>
</div>
""", unsafe_allow_html=True)

left_col, right_col = st.columns([1, 1.6], gap="large")


with left_col:

    st.markdown('<div class="section-header">📰 News Feed</div>', unsafe_allow_html=True)

    fetch_col, custom_col = st.columns([1, 1])

    with fetch_col:
        if st.button("⬇ Fetch Live News", use_container_width=True):
            if NEWS_AVAILABLE:
                with st.spinner("Fetching headlines..."):
                    try:
                        st.session_state.headlines = fetch_headlines()
                        add_timeline(f"Fetched {len(st.session_state.headlines)} headlines", "blue")
                    except Exception as e:
                        st.error(f"Fetch failed: {e}")
            else:
                st.session_state.headlines = [
                    {"headline": "Apple beats Q3 earnings estimates by 12%",       "source": "Demo", "published_at": datetime.now()},
                    {"headline": "Tesla reports record vehicle deliveries in Q2",    "source": "Demo", "published_at": datetime.now()},
                    {"headline": "Microsoft Azure cloud revenue surges 28%",        "source": "Demo", "published_at": datetime.now()},
                    {"headline": "NVIDIA misses revenue guidance for next quarter", "source": "Demo", "published_at": datetime.now()},
                    {"headline": "Goldman Sachs cuts year-end S&P 500 target",      "source": "Demo", "published_at": datetime.now()},
                    {"headline": "Amazon Web Services outage affects thousands",    "source": "Demo", "published_at": datetime.now()},
                    {"headline": "Meta platforms ad revenue grows 20% year on year","source": "Demo", "published_at": datetime.now()},
                    {"headline": "Intel faces supply chain disruptions in Q3",      "source": "Demo", "published_at": datetime.now()},
                ]
                add_timeline("Loaded demo headlines", "blue")

    with custom_col:
        custom_input = st.text_input("✏ Custom headline", placeholder="Type any headline...",
                                      label_visibility="collapsed")
        if custom_input and st.button("Analyse ↗", use_container_width=True):
            st.session_state.custom_headline = custom_input
            with st.spinner("Running analysis..."):
                st.session_state.analysis = analyse_headline(
                    custom_input, pos_threshold, neg_threshold
                )
            add_timeline(f"Custom: {custom_input[:40]}...", "blue")
            st.session_state.selected_idx = None

    if not st.session_state.headlines:
        st.markdown("""
        <div class="card card-gray" style="text-align:center; padding:30px 20px;">
            <div style="font-size:28px; margin-bottom:8px;">📡</div>
            <div style="color:#6e7681; font-size:13px;">
                Click "Fetch Live News" to load headlines<br>or type a custom one above
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption(f"{len(st.session_state.headlines)} headlines loaded")
        st.markdown('<div class="news-scroll">', unsafe_allow_html=True)

        for i, item in enumerate(st.session_state.headlines):
            headline_text = item.get("headline", "")
            source        = item.get("source", "")
            is_selected   = st.session_state.selected_idx == i
            css_class     = "headline-item active" if is_selected else "headline-item"

            if st.button(
                f"**{headline_text[:80]}{'…' if len(headline_text) > 80 else ''}**\n\n_{source}_",
                key=f"hl_{i}",
                use_container_width=True,
            ):
                st.session_state.selected_idx = i
                st.session_state.pending_order = None
                st.session_state.auto_execute_at = None
                with st.spinner("Analysing with FinBERT..."):
                    st.session_state.analysis = analyse_headline(
                        headline_text, pos_threshold, neg_threshold
                    )
                add_timeline(f"Selected: {headline_text[:50]}…", "blue")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


with right_col:

    analysis = st.session_state.analysis

    st.markdown('<div class="section-header">🧠 AI Insight</div>', unsafe_allow_html=True)

    if analysis is None:
        st.markdown("""
        <div class="card card-gray" style="text-align:center; padding:40px 20px;">
            <div style="font-size:32px; margin-bottom:10px;">🤖</div>
            <div style="color:#6e7681; font-size:14px;">
                Select a headline from the feed<br>to see the AI analysis here
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        signal  = analysis["signal"]
        label   = analysis["label"]
        score   = analysis["score"]
        tickers = analysis["tickers"]
        ticker  = tickers[0] if tickers else "—"
        conf    = analysis["confidence"]
        risk_ok = analysis["risk_pass"]
        prob    = analysis["probability"]

        signal_color = {"BUY": "green", "SELL": "red", "HOLD": "gray"}[signal]
        label_color  = {"positive": "green", "negative": "red", "neutral": "gray"}[label]

        card_class = f"card card-{signal_color}"
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)

        st.markdown(f"""
        <div style="font-size:14px; color:#8b949e; margin-bottom:10px; line-height:1.5;">
            {analysis['headline'][:120]}{'…' if len(analysis['headline']) > 120 else ''}
        </div>
        """, unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f"""
            <div class="metric-label">Ticker</div>
            <div class="metric-value metric-blue mono">{ticker}</div>
            """, unsafe_allow_html=True)
        with m2:
            color_map = {"positive": "metric-green", "negative": "metric-red", "neutral": "metric-white"}
            st.markdown(f"""
            <div class="metric-label">Sentiment</div>
            <div class="metric-value {color_map[label]}">{label.capitalize()}</div>
            """, unsafe_allow_html=True)
        with m3:
            score_color = "metric-green" if score > 0 else ("metric-red" if score < 0 else "metric-white")
            st.markdown(f"""
            <div class="metric-label">Score</div>
            <div class="metric-value {score_color} mono">{score:+.3f}</div>
            """, unsafe_allow_html=True)
        with m4:
            conf_colors = {"High": "metric-green", "Medium": "metric-blue", "Low": "metric-white"}
            st.markdown(f"""
            <div class="metric-label">Confidence</div>
            <div class="metric-value {conf_colors[conf]}">{conf}</div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Decision + risk row
        d_col, r_col = st.columns([1, 1])
        with d_col:
            st.markdown(f"""
            <div class="metric-label">Decision</div>
            <div class="decision-{signal.lower()}">{signal}</div>
            """, unsafe_allow_html=True)
        with r_col:
            risk_icon  = "✅" if risk_ok else "❌"
            risk_text  = "PASS" if risk_ok else "FAIL"
            risk_color = "metric-green" if risk_ok else "metric-red"
            st.markdown(f"""
            <div class="metric-label">Risk Check</div>
            <div class="metric-value {risk_color}" style="font-size:18px;">{risk_icon} {risk_text}</div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        explain_open = (mode == "Explain")
        with st.expander("🔍 Show AI Reasoning", expanded=explain_open):
            st.markdown("**Raw FinBERT probabilities**")

            p_pos = analysis["p_positive"]
            p_neu = analysis["p_neutral"]
            p_neg = analysis["p_negative"]

            for lbl, val, bar_class in [
                ("Positive", p_pos, "prob-bar-fill-pos"),
                ("Neutral",  p_neu, "prob-bar-fill-neu"),
                ("Negative", p_neg, "prob-bar-fill-neg"),
            ]:
                st.markdown(f"""
                <div style="margin-bottom:8px;">
                  <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:3px;">
                    <span style="color:#8b949e;">{lbl}</span>
                    <span class="mono" style="color:#c9d1d9;">{val:.1%}</span>
                  </div>
                  <div class="prob-bar-bg">
                    <div class="{bar_class}" style="width:{val*100:.1f}%;"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("**Thresholds used**")
            st.markdown(f"""
            <div class="card card-gray mono" style="font-size:12px; padding:10px 14px; line-height:2;">
                BUY  threshold : score ≥ +{pos_threshold:.2f}<br>
                SELL threshold : score ≤ -{neg_threshold:.2f}<br>
                Computed score : {score:+.4f}<br>
                Dominant label : {label} (p={prob:.3f})
            </div>
            """, unsafe_allow_html=True)

            if tickers:
                st.markdown("**Detected tickers**")
                st.markdown(" ".join(
                    f'<span class="badge-pos">{t}</span>' for t in tickers
                ), unsafe_allow_html=True)

            if analysis.get("error"):
                st.warning(f"⚠ {analysis['error']}")

        if signal != "HOLD" and risk_ok and analysis.get("order") is not None:
            st.markdown('<div class="section-header">⚡ Trade Confirmation</div>',
                        unsafe_allow_html=True)

            order = analysis["order"]
            price = analysis.get("price", 0)

            color = "#3fb950" if signal == "BUY" else "#f85149"
            st.markdown(f"""
            <div class="card" style="border-left:4px solid {color}; margin-bottom:10px;">
                <div style="font-size:14px; color:#8b949e; margin-bottom:8px;">AI suggests:</div>
                <div style="font-size:18px; font-weight:600; color:{color}; font-family:'IBM Plex Mono',monospace;">
                    {signal} {ticker}
                </div>
                <div style="font-size:12px; color:#8b949e; margin-top:6px; line-height:2; font-family:'IBM Plex Mono',monospace;">
                    Qty: {order.qty} shares &nbsp;|&nbsp; ~${order.qty * price:,.0f}<br>
                    Stop-loss: ${order.stop_loss:.2f} &nbsp;|&nbsp; Take-profit: ${order.take_profit:.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Auto-execute countdown (Auto mode)
            if auto_enabled or mode == "Auto":
                if st.session_state.auto_execute_at is None:
                    st.session_state.auto_execute_at = time.time() + auto_timer
                    st.session_state.pending_order   = order

                remaining = st.session_state.auto_execute_at - time.time()

                if remaining > 0:
                    st.info(f"⏳ Auto executing in **{int(remaining)}s** … confirm or cancel below.")
                else:
                    # Auto execute
                    if st.session_state.pending_order is not None:
                        result = execute_order(st.session_state.pending_order) if BROKER_AVAILABLE else {"success": True, "order_id": "AUTO-DEMO"}
                        if result.get("success"):
                            add_timeline(f"AUTO {signal} {ticker} × {order.qty}", signal_color)
                            if PORTFOLIO_AVAILABLE:
                                if signal == "BUY":
                                    portfolio.record_buy(ticker, order.qty, price or 150.0)
                                    if RISK_AVAILABLE:
                                        record_open_position(ticker, order.qty)
                                else:
                                    portfolio.record_sell(ticker, price or 150.0)
                        st.session_state.pending_order   = None
                        st.session_state.auto_execute_at = None
                        st.session_state.analysis        = None
                        st.rerun()

            # Manual confirm / cancel buttons
            btn_confirm, btn_cancel, _ = st.columns([1, 1, 1])
            with btn_confirm:
                if st.button(f"✅ Confirm {signal}", use_container_width=True, type="primary"):
                    result = execute_order(order) if BROKER_AVAILABLE else {"success": True, "order_id": "MANUAL-DEMO"}
                    if result.get("success"):
                        add_timeline(f"{signal} {ticker} × {order.qty} confirmed", signal_color)
                        if PORTFOLIO_AVAILABLE:
                            if signal == "BUY":
                                portfolio.record_buy(ticker, order.qty, price or 150.0)
                                if RISK_AVAILABLE:
                                    record_open_position(ticker, order.qty)
                            else:
                                pnl = portfolio.record_sell(ticker, price or 150.0)
                                if RISK_AVAILABLE:
                                    record_closed_position(ticker, pnl)
                        st.success(f"Trade executed! Order ID: {result.get('order_id', '—')}")
                        st.session_state.pending_order   = None
                        st.session_state.auto_execute_at = None
                    else:
                        st.error(f"Execution failed: {result.get('error')}")

            with btn_cancel:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.pending_order   = None
                    st.session_state.auto_execute_at = None
                    add_timeline(f"Cancelled {signal} {ticker}", "gray")
                    st.rerun()

        elif signal == "HOLD":
            st.markdown("""
            <div class="card card-gray" style="padding:12px 18px; font-size:13px; color:#8b949e;">
                🟰 Signal is <b>HOLD</b> — no trade action taken.
            </div>
            """, unsafe_allow_html=True)
        elif not risk_ok:
            st.markdown("""
            <div class="card card-red" style="padding:12px 18px; font-size:13px;">
                ⛔ Risk check failed — trade blocked by risk manager.
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">💼 Portfolio</div>', unsafe_allow_html=True)

    if PORTFOLIO_AVAILABLE:
        summary = portfolio.summary()
        acct    = get_account_info() if BROKER_AVAILABLE else {}
    else:
        summary = {
            "open_positions":  2,
            "total_trades":    7,
            "realised_pnl":    482.50,
            "unrealised_pnl": -123.40,
            "net_pnl":         359.10,
            "positions": {
                "AAPL": {"ticker": "AAPL", "qty": 6,  "entry_price": 182.50},
                "MSFT": {"ticker": "MSFT", "qty": 2,  "entry_price": 415.20},
            },
        }
        acct = {"equity": 100000, "cash": 97500, "buying_power": 200000}

    p1, p2, p3 = st.columns(3)
    with p1:
        cash = acct.get("cash", 0)
        st.markdown(f"""
        <div class="card" style="padding:14px 16px;">
          <div class="metric-label">Cash</div>
          <div class="metric-value metric-white">${cash:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with p2:
        net = summary["net_pnl"]
        color = "metric-green" if net >= 0 else "metric-red"
        sign  = "+" if net >= 0 else ""
        st.markdown(f"""
        <div class="card" style="padding:14px 16px;">
          <div class="metric-label">Net P&L</div>
          <div class="metric-value {color}">{sign}${net:,.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    with p3:
        st.markdown(f"""
        <div class="card" style="padding:14px 16px;">
          <div class="metric-label">Open Trades</div>
          <div class="metric-value metric-blue">{summary['open_positions']}</div>
        </div>
        """, unsafe_allow_html=True)

    # Open positions table
    positions = summary.get("positions", {})
    if positions:
        st.markdown("**Open positions**")
        for ticker_sym, pos in positions.items():
            entry = pos.get("entry_price", 0)
            qty   = pos.get("qty", 0)
            value = entry * qty
            st.markdown(f"""
            <div class="card" style="padding:10px 14px; margin-bottom:6px; display:flex; justify-content:space-between;">
              <div>
                <span class="mono" style="color:#388bfd; font-weight:600;">{ticker_sym}</span>
                <span style="color:#6e7681; font-size:12px; margin-left:8px;">{qty} shares @ ${entry:.2f}</span>
              </div>
              <span class="mono" style="color:#8b949e; font-size:13px;">~${value:,.0f}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="color:#6e7681; font-size:13px; padding:8px 0;">No open positions.</div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">📜 Activity Timeline</div>', unsafe_allow_html=True)

    if not st.session_state.timeline:
        st.markdown('<div style="color:#6e7681; font-size:13px; padding:6px 0;">No activity yet.</div>',
                    unsafe_allow_html=True)
    else:
        dot_map = {"green": "dot-green", "red": "dot-red", "blue": "dot-blue", "gray": "dot-gray"}
        for entry in st.session_state.timeline[:8]:
            dot = dot_map.get(entry["color"], "dot-gray")
            st.markdown(f"""
            <div class="timeline-item">
              <div class="timeline-dot {dot}"></div>
              <div style="flex:1; color:#c9d1d9;">{entry['text']}</div>
              <div style="color:#6e7681; font-size:11px; font-family:'IBM Plex Mono',monospace; white-space:nowrap;">
                {entry['time']}
              </div>
            </div>
            """, unsafe_allow_html=True)
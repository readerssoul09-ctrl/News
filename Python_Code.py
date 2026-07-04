import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components


REFRESH_SECONDS = 300
TWO_YEARS_AGO = (date.today() - timedelta(days=730)).strftime("%Y-%m-%d")

st.set_page_config(page_title="News Intelligence Dashboard", layout="wide")

st.markdown(f"<meta http-equiv='refresh' content='{REFRESH_SECONDS}'>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%); }
    .block-container { padding-top: 1.4rem; max-width: 1280px; }
    .dashboard-title { font-size: 2.45rem; font-weight: 850; color: #111827; }
    .dashboard-subtitle { color: #667085; font-size: 1rem; margin-bottom: 1rem; }
    .news-card {
        background: rgba(255,255,255,0.96); border: 1px solid #e5e7eb;
        border-left: 5px solid #2563eb; border-radius: 14px;
        padding: 18px 20px; margin-bottom: 16px;
        box-shadow: 0 8px 26px rgba(15,23,42,0.07);
    }
    .news-card:hover {
        border-color: #bfdbfe; box-shadow: 0 14px 32px rgba(15,23,42,0.11);
        transform: translateY(-1px); transition: all 160ms ease;
    }
    .news-title { color: #111827; font-size: 1.12rem; font-weight: 800; margin: 10px 0 8px; line-height: 1.35; }
    .news-brief {
        color: #374151; font-size: 0.95rem; line-height: 1.5; font-style: italic;
        background: #f8fafc; border-radius: 10px; padding: 10px 14px; margin-top: 8px;
    }
    .news-brief div { margin-bottom: 4px; }
    .news-meta { color: #667085; font-size: 0.82rem; margin-top: 10px; }
    .badge {
        display: inline-block; padding: 5px 10px; border-radius: 999px;
        font-size: 0.76rem; font-weight: 800; margin: 0 6px 6px 0;
    }
    .bullish { background: #dcfce7; color: #166534; }
    .bearish { background: #fee2e2; color: #991b1b; }
    .neutral { background: #f1f5f9; color: #475569; }
    .industry { background: #dbeafe; color: #1d4ed8; }
    .company { background: #fef3c7; color: #92400e; }
    .highlight {
        background: linear-gradient(90deg, #fff7ed, #fffbeb);
        border: 1px solid #fed7aa; color: #9a3412;
        padding: 2px 7px; border-radius: 8px; font-weight: 750;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


BULLISH_WORDS = [
    "gain", "gains", "rise", "rises", "surge", "surges", "jump", "jumps",
    "beat", "beats", "growth", "profit", "profits", "record", "upgrade",
    "strong", "expansion", "approval", "wins", "rally", "raises", "buyback",
    "dividend", "investment", "positive", "higher", "outperform"
]

BEARISH_WORDS = [
    "fall", "falls", "drop", "drops", "plunge", "plunges", "loss", "losses",
    "miss", "misses", "weak", "downgrade", "fraud", "probe", "lawsuit",
    "default", "decline", "declines", "layoff", "cuts", "warning", "debt",
    "bankruptcy", "slowdown", "negative", "recall", "lower", "underperform"
]

INDUSTRY_KEYWORDS = {
    "Technology": ["ai", "software", "semiconductor", "chip", "cloud", "cyber", "data center", "tech"],
    "Banking & Finance": ["bank", "loan", "credit", "deposit", "lender", "nbfc", "insurance", "fintech"],
    "Pharmaceuticals & Healthcare": ["pharma", "drug", "vaccine", "fda", "clinical", "hospital", "healthcare"],
    "Energy": ["oil", "gas", "renewable", "solar", "wind", "power", "coal", "energy"],
    "Automobiles": ["auto", "vehicle", "car", "ev", "battery", "tesla", "automaker"],
    "Real Estate": ["real estate", "housing", "property", "reit", "construction"],
    "Consumer Goods": ["retail", "consumer", "fmcg", "brand", "sales", "demand"],
    "Metals & Mining": ["steel", "copper", "aluminium", "mining", "metal", "iron ore"],
    "Telecom": ["telecom", "5g", "network", "spectrum", "broadband"],
    "Aviation": ["airline", "aviation", "aircraft", "airport", "boeing", "airbus"],
}

INDUSTRIES = list(INDUSTRY_KEYWORDS.keys())

COUNTRY_QUERIES = {
    "India": "India economy RBI Sensex Nifty business markets",
    "United States": "US economy Federal Reserve S&P 500 Nasdaq business markets",
    "China": "China economy PBOC yuan business markets",
    "European Union": "European Union economy ECB eurozone business markets",
    "Japan": "Japan economy BOJ Nikkei yen business markets",
    "United Kingdom": "UK economy Bank of England FTSE business markets",
}

MARKET_TICKERS = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow Jones": "^DJI",
    "Nifty 50": "^NSEI",
    "Sensex": "^BSESN",
    "Gold": "GC=F",
    "Crude Oil": "CL=F",
    "Bitcoin": "BTC-USD",
    "USD/INR": "USDINR=X",
}


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def google_news_url(query, region, recent=True):
    final_query = f"{query} when:1d" if recent else query
    encoded = urllib.parse.quote_plus(final_query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-{region}&gl={region}&ceid={region}:en"


def parse_datetime(value):
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return datetime.now(timezone.utc)


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def fetch_google_news(query, region="IN", limit=15, recent=True):
    url = google_news_url(query, region, recent)

    try:
        response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except Exception as error:
        return pd.DataFrame(), f"Could not load Google News RSS: {error}"

    try:
        root = ET.fromstring(response.content)
    except Exception as error:
        return pd.DataFrame(), f"Could not read news feed: {error}"

    rows = []
    for item in root.findall(".//item")[:limit]:
        title = clean_text(item.findtext("title"))
        summary = clean_text(item.findtext("description"))
        link = clean_text(item.findtext("link"))
        published = clean_text(item.findtext("pubDate"))
        source_node = item.find("source")
        source = clean_text(source_node.text if source_node is not None else "Google News")

        rows.append({
            "title": title,
            "summary": summary,
            "link": link,
            "published": published,
            "published_dt": parse_datetime(published),
            "source": source,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("published_dt", ascending=False).head(limit)

    return df, None


@st.cache_data(ttl=REFRESH_SECONDS, show_spinner=False)
def fetch_market_metrics():
    rows = []

    for name, ticker in MARKET_TICKERS.items():
        encoded = urllib.parse.quote(ticker, safe="")
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=2d&interval=1d"

        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            result = response.json()["chart"]["result"][0]
            meta = result["meta"]

            price = float(meta.get("regularMarketPrice", 0))
            previous = float(meta.get("chartPreviousClose", 0))
            change = price - previous if previous else 0
            change_pct = (change / previous * 100) if previous else 0

            rows.append({
                "Metric": name,
                "Ticker": ticker,
                "Price": round(price, 2),
                "Change": round(change, 2),
                "Change %": round(change_pct, 2),
            })
        except Exception:
            rows.append({
                "Metric": name,
                "Ticker": ticker,
                "Price": "N/A",
                "Change": "N/A",
                "Change %": "N/A",
            })

    return pd.DataFrame(rows)


def clock_component():
    components.html(
        f"""
        <div style="background:linear-gradient(135deg,#111827,#334155);color:white;border-radius:14px;
        padding:18px 22px;box-shadow:0 14px 38px rgba(15,23,42,0.18);font-family:Arial;">
            <div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;">
                <div><div style="font-size:13px;opacity:.78;">Live Clock</div><div id="live-clock" style="font-size:26px;font-weight:800;">--:--:--</div></div>
                <div><div style="font-size:13px;opacity:.78;">Auto Refresh Countdown</div><div id="countdown" style="font-size:26px;font-weight:800;">05:00</div></div>
                <div><div style="font-size:13px;opacity:.78;">Refresh Cycle</div><div style="font-size:26px;font-weight:800;">5 min</div></div>
            </div>
        </div>
        <script>
        let remaining = {REFRESH_SECONDS};
        function pad(v) {{ return String(v).padStart(2, "0"); }}
        function updateClock() {{
            const now = new Date();
            document.getElementById("live-clock").textContent = pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
        }}
        function updateCountdown() {{
            const m = Math.floor(remaining / 60);
            const s = remaining % 60;
            document.getElementById("countdown").textContent = pad(m) + ":" + pad(s);
            remaining -= 1;
            if (remaining < 0) remaining = {REFRESH_SECONDS};
        }}
        updateClock(); updateCountdown();
        setInterval(updateClock, 1000); setInterval(updateCountdown, 1000);
        </script>
        """,
        height=125,
    )


def streaming_metrics_component(total, bullish, bearish, neutral):
    components.html(
        f"""
        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:8px 0 20px;font-family:Arial;">
            <div style="background:white;border:1px solid #e5e7eb;border-radius:14px;padding:18px;">
                <div style="color:#667085;font-size:12px;font-weight:700;text-transform:uppercase;">Total Headlines</div>
                <div class="metric-value" data-target="{total}" style="font-size:32px;font-weight:850;">0</div>
                <div style="color:#667085;font-size:13px;font-style:italic;">recent Google News items</div>
            </div>
            <div style="background:white;border:1px solid #e5e7eb;border-radius:14px;padding:18px;">
                <div style="color:#667085;font-size:12px;font-weight:700;text-transform:uppercase;">Bullish</div>
                <div class="metric-value" data-target="{bullish}" style="font-size:32px;font-weight:850;color:#15803d;">0</div>
                <div style="color:#667085;font-size:13px;font-style:italic;">positive signal</div>
            </div>
            <div style="background:white;border:1px solid #e5e7eb;border-radius:14px;padding:18px;">
                <div style="color:#667085;font-size:12px;font-weight:700;text-transform:uppercase;">Bearish</div>
                <div class="metric-value" data-target="{bearish}" style="font-size:32px;font-weight:850;color:#b91c1c;">0</div>
                <div style="color:#667085;font-size:13px;font-style:italic;">risk signal</div>
            </div>
            <div style="background:white;border:1px solid #e5e7eb;border-radius:14px;padding:18px;">
                <div style="color:#667085;font-size:12px;font-weight:700;text-transform:uppercase;">Neutral</div>
                <div class="metric-value" data-target="{neutral}" style="font-size:32px;font-weight:850;color:#475569;">0</div>
                <div style="color:#667085;font-size:13px;font-style:italic;">watchlist items</div>
            </div>
        </div>
        <script>
        document.querySelectorAll(".metric-value").forEach((el) => {{
            const target = Number(el.dataset.target);
            let current = 0;
            const step = Math.max(1, Math.ceil(target / 24));
            const timer = setInterval(() => {{
                current += step;
                if (current >= target) {{ current = target; clearInterval(timer); }}
                el.textContent = current;
            }}, 28);
        }});
        </script>
        """,
        height=160,
    )


def sentiment_score(text):
    text = text.lower()
    bullish = sum(1 for word in BULLISH_WORDS if word in text)
    bearish = sum(1 for word in BEARISH_WORDS if word in text)
    return bullish - bearish


def sentiment_label(score):
    if score > 0:
        return "Bullish"
    if score < 0:
        return "Bearish"
    return "Neutral"


def detect_industry(text):
    lowered = text.lower()
    scores = {
        industry: sum(1 for keyword in keywords if keyword in lowered)
        for industry, keywords in INDUSTRY_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Broad Market"


def detect_company(title):
    headline = re.sub(r"\s+-\s+.*$", "", title)
    candidates = re.findall(r"\b[A-Z][A-Za-z&.\-]*(?:\s+[A-Z][A-Za-z&.\-]*){0,3}", headline)
    ignored = {"India", "China", "United States", "US", "UK", "EU", "Fed", "RBI", "Market", "Markets", "Stocks", "Shares", "Economy", "Business"}

    for candidate in candidates:
        candidate = candidate.strip()
        if len(candidate) > 2 and candidate not in ignored:
            return candidate

    return "Market / Multiple Companies"


def make_brief_lines(row):
    summary = clean_text(row["summary"] if row["summary"] else row["title"])
    if len(summary) > 180:
        summary = summary[:177].rsplit(" ", 1)[0] + "..."

    if row["view"] == "Bullish":
        market_read = "Market read: The headline carries a positive tone and may support sentiment."
    elif row["view"] == "Bearish":
        market_read = "Market read: The headline points to pressure, risk, or weaker sentiment."
    else:
        market_read = "Market read: The headline is mixed or informational, so it should be watched."

    return [
        f"What happened: {summary}",
        market_read,
        f"Most affected: {row['company']}, with impact mainly linked to {row['industry']}.",
        "Why it matters: This can influence investor attention, sector movement, and short-term market narrative.",
    ]


def enrich_news(df):
    if df.empty:
        return df

    df = df.copy()
    combined = df["title"].fillna("") + " " + df["summary"].fillna("")
    df["score"] = combined.apply(sentiment_score)
    df["view"] = df["score"].apply(sentiment_label)
    df["industry"] = combined.apply(detect_industry)
    df["company"] = df["title"].apply(detect_company)
    df["brief_lines"] = df.apply(make_brief_lines, axis=1)
    return df


def filter_news(df, sentiment_filter, industry_filter):
    if df.empty:
        return df

    filtered = df.copy()
    if sentiment_filter != "All":
        filtered = filtered[filtered["view"] == sentiment_filter]
    if industry_filter != "All":
        filtered = filtered[filtered["industry"] == industry_filter]

    return filtered


def badge_class(value):
    if value == "Bullish":
        return "bullish"
    if value == "Bearish":
        return "bearish"
    return "neutral"


def show_news_cards(df):
    if df.empty:
        st.warning("No news found. Try a broader query, another region, or reset filters.")
        return

    for _, row in df.iterrows():
        brief_html = "".join(f"<div>{html.escape(line)}</div>" for line in row["brief_lines"])

        st.markdown(
            f"""
            <div class="news-card">
                <span class="badge {badge_class(row['view'])}">{html.escape(row['view'])}</span>
                <span class="badge company">{html.escape(row['company'])}</span>
                <span class="badge industry">{html.escape(row['industry'])}</span>
                <div class="news-title">{html.escape(row['title'])}</div>
                <div class="news-brief">{brief_html}</div>
                <div class="news-meta">
                    Source: <span class="highlight">{html.escape(row['source'])}</span>
                    &nbsp;|&nbsp; Published: {html.escape(row['published'])}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if row["link"]:
            st.link_button("Open source", row["link"])


def extract_deal_info(text):
    text = clean_text(text)
    acquirer = "Not clearly mentioned"
    target = "Not clearly mentioned"

    patterns = [
        r"(.+?)\s+to\s+buy\s+(.+?)(?:\s+for|\s+in|\s+as|,|$)",
        r"(.+?)\s+acquires\s+(.+?)(?:\s+for|\s+in|\s+as|,|$)",
        r"(.+?)\s+buys\s+(.+?)(?:\s+for|\s+in|\s+as|,|$)",
        r"(.+?)\s+merges\s+with\s+(.+?)(?:\s+for|\s+in|\s+as|,|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            acquirer = clean_text(match.group(1))[:90].strip(" -:,.")
            target = clean_text(match.group(2))[:90].strip(" -:,.")
            break

    value_patterns = [
        r"\$\s?\d+(?:\.\d+)?\s?(?:billion|bn|million|mn|trillion)",
        r"₹\s?\d+(?:\.\d+)?\s?(?:crore|lakh crore|billion|million)",
        r"\d+(?:\.\d+)?x\s?(?:revenue|sales|ebitda|earnings)",
        r"\d+(?:\.\d+)?\s?times\s?(?:revenue|sales|ebitda|earnings)",
    ]

    values = []
    for pattern in value_patterns:
        values.extend(re.findall(pattern, text, flags=re.IGNORECASE))

    return target, acquirer, ", ".join(values) if values else "Not available"


def market_metrics_panel():
    st.markdown("#### Stock Market Metrics")
    metrics = fetch_market_metrics()

    if metrics.empty:
        st.warning("Market metrics are temporarily unavailable.")
        return

    cols = st.columns(3)
    for index, row in metrics.iterrows():
        with cols[index % 3]:
            change = row["Change"]
            change_pct = row["Change %"]
            delta = "N/A" if change == "N/A" else f"{change} ({change_pct}%)"
            st.metric(label=f"{row['Metric']} ({row['Ticker']})", value=row["Price"], delta=delta)

    with st.expander("View all market metrics"):
        st.dataframe(metrics, use_container_width=True, hide_index=True)


def market_news_tab(news_count, region, custom_query):
    market_metrics_panel()

    query = custom_query or "stock market business economy corporate earnings"
    df, error = fetch_google_news(query, region, news_count, recent=True)

    if error:
        st.error(error)
        return

    df = enrich_news(df)
    total = len(df)
    bullish = int((df["view"] == "Bullish").sum()) if not df.empty else 0
    bearish = int((df["view"] == "Bearish").sum()) if not df.empty else 0
    neutral = int((df["view"] == "Neutral").sum()) if not df.empty else 0

    streaming_metrics_component(total, bullish, bearish, neutral)

    col1, col2 = st.columns(2)
    with col1:
        sentiment_filter = st.selectbox("Filter by sentiment", ["All", "Bullish", "Bearish", "Neutral"])
    with col2:
        industry_options = ["All"] + sorted(df["industry"].dropna().unique().tolist()) if not df.empty else ["All"]
        industry_filter = st.selectbox("Filter by industry", industry_options)

    st.markdown("#### Highlighted Headlines")
    show_news_cards(filter_news(df, sentiment_filter, industry_filter))


def industry_news_tab(news_count, region):
    industry_rows = []
    industry_news = {}

    for industry in INDUSTRIES:
        df, error = fetch_google_news(f"{industry} industry business news", region, 5, recent=True)
        if error or df.empty:
            continue

        df = enrich_news(df)
        industry_news[industry] = df
        industry_rows.append({
            "Industry": industry,
            "Average Score": round(float(df["score"].mean()), 2),
            "Bullish News": int((df["view"] == "Bullish").sum()),
            "Bearish News": int((df["view"] == "Bearish").sum()),
        })

    if not industry_rows:
        st.warning("No industry news found.")
        return

    ranking = pd.DataFrame(industry_rows).sort_values("Average Score", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Top 3 Industries")
        st.dataframe(ranking.head(3), use_container_width=True, hide_index=True)
    with col2:
        st.markdown("### Bottom 3 Industries")
        st.dataframe(ranking.tail(3).sort_values("Average Score"), use_container_width=True, hide_index=True)

    selected = st.selectbox("Select industry to inspect", ranking["Industry"].tolist())
    show_news_cards(industry_news[selected].head(news_count))


def ma_news_tab(news_count, region):
    st.markdown(f"#### M&A News From The Past 2 Years")
    st.caption(f"Coverage filter starts from {TWO_YEARS_AGO}. Results are grouped by industry and shown in chronological order.")

    industry_deals = {}
    ranking_rows = []

    for industry in INDUSTRIES:
        query = f'{industry} merger acquisition acquires takeover buyout deal value after:{TWO_YEARS_AGO}'
        df, error = fetch_google_news(query, region, news_count, recent=False)

        if error or df.empty:
            continue

        enriched = enrich_news(df)
        deals = []

        for _, row in enriched.iterrows():
            full_text = f"{row['title']} {row['summary']}"
            target, acquirer, deal_value = extract_deal_info(full_text)

            deals.append({
                "date": row["published_dt"],
                "published": row["published"],
                "headline": row["title"],
                "target": target,
                "acquirer": acquirer,
                "deal_value": deal_value,
                "brief_lines": row["brief_lines"],
                "source": row["source"],
                "link": row["link"],
                "industry": industry,
                "score": row["score"],
            })

        deals = sorted(deals, key=lambda item: item["date"])
        industry_deals[industry] = deals

        ranking_rows.append({
            "Industry": industry,
            "Deal Headlines": len(deals),
            "Avg Sentiment Score": round(sum(item["score"] for item in deals) / len(deals), 2) if deals else 0,
            "Deals With Value Mentioned": sum(1 for item in deals if item["deal_value"] != "Not available"),
        })

    if not ranking_rows:
        st.warning("No M&A news found for the selected region.")
        return

    ranking = pd.DataFrame(ranking_rows).sort_values(
        ["Deal Headlines", "Deals With Value Mentioned", "Avg Sentiment Score"],
        ascending=[False, False, False],
    )

    st.markdown("### M&A Industry Ranking")
    st.dataframe(ranking, use_container_width=True, hide_index=True)

    top_industry = ranking.iloc[0]["Industry"]
    st.success(f"Top M&A industry by headline count: {top_industry}")

    selected_industry = st.selectbox("Select M&A industry", ranking["Industry"].tolist())
    selected_deals = industry_deals.get(selected_industry, [])

    order = st.radio("Chronological order", ["Oldest first", "Newest first"], horizontal=True)
    if order == "Newest first":
        selected_deals = list(reversed(selected_deals))

    for row in selected_deals:
        brief_html = "".join(f"<div>{html.escape(line)}</div>" for line in row["brief_lines"])

        st.markdown(
            f"""
            <div class="news-card">
                <span class="badge industry">M&A</span>
                <span class="badge company">{html.escape(row['industry'])}</span>
                <div class="news-title">{html.escape(row['headline'])}</div>
                <div><b>Target:</b> {html.escape(row['target'])}</div>
                <div><b>Acquirer:</b> {html.escape(row['acquirer'])}</div>
                <div><b>Deal value / multiples:</b> {html.escape(row['deal_value'])}</div>
                <div class="news-brief">{brief_html}</div>
                <div class="news-meta">
                    Source: <span class="highlight">{html.escape(row['source'])}</span>
                    &nbsp;|&nbsp; Published: {html.escape(row['published'])}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if row["link"]:
            st.link_button("Open source", row["link"])


def macro_news_tab(news_count, region):
    for country, query in COUNTRY_QUERIES.items():
        with st.expander(country, expanded=country in ["India", "United States", "China"]):
            df, error = fetch_google_news(query, region, max(5, news_count // 2), recent=True)
            if error:
                st.error(error)
                continue
            show_news_cards(enrich_news(df))


def main():
    st.markdown('<div class="dashboard-title">News Intelligence Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-subtitle">Recent market news, stock metrics, M&A tracking, industry ranking, live clock, and 5-minute auto-refresh.</div>',
        unsafe_allow_html=True,
    )

    clock_component()

    refreshed_at = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")
    st.caption(f"Last refreshed: {refreshed_at}")

    with st.sidebar:
        st.header("Controls")
        news_count = st.slider("Number of news items", 10, 15, 12)
        region = st.selectbox("Google News region", ["US", "IN", "GB", "SG", "AU"], index=1)
        custom_query = st.text_input("Custom market query", placeholder="Example: Indian IT stocks earnings")

        if st.button("Refresh now"):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.subheader("Customization Recommendations")
        st.write(
            "- Add portfolio company names in the custom query.\n"
            "- Use IN region for India-focused market coverage.\n"
            "- Review bearish news first during market hours.\n"
            "- Track one sector at a time for cleaner signals.\n"
            "- Open the original source before making investment decisions."
        )

    tab1, tab2, tab3, tab4 = st.tabs([
        "Market News",
        "Industry News",
        "M&A News",
        "Macro News",
    ])

    with tab1:
        market_news_tab(news_count, region, custom_query)

    with tab2:
        industry_news_tab(news_count, region)

    with tab3:
        ma_news_tab(news_count, region)

    with tab4:
        macro_news_tab(news_count, region)


if __name__ == "__main__":
    main()

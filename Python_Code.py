import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components


REFRESH_SECONDS = 300

st.set_page_config(
    page_title="News Intelligence Dashboard",
    layout="wide"
)

st.markdown(
    f"<meta http-equiv='refresh' content='{REFRESH_SECONDS}'>",
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);
    }

    .block-container {
        padding-top: 1.4rem;
        max-width: 1280px;
    }

    .dashboard-title {
        font-size: 2.45rem;
        font-weight: 850;
        color: #111827;
        letter-spacing: 0;
        margin-bottom: 0.1rem;
    }

    .dashboard-subtitle {
        color: #667085;
        font-size: 1rem;
        margin-bottom: 1rem;
    }

    .news-card {
        background: rgba(255, 255, 255, 0.96);
        border: 1px solid #e5e7eb;
        border-left: 5px solid #2563eb;
        border-radius: 14px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 8px 26px rgba(15, 23, 42, 0.07);
    }

    .news-card:hover {
        border-color: #bfdbfe;
        box-shadow: 0 14px 32px rgba(15, 23, 42, 0.11);
        transform: translateY(-1px);
        transition: all 160ms ease;
    }

    .news-title {
        color: #111827;
        font-size: 1.12rem;
        font-weight: 800;
        margin: 10px 0 8px 0;
        line-height: 1.35;
    }

    .news-brief {
        color: #374151;
        font-size: 0.95rem;
        line-height: 1.5;
        font-style: italic;
        background: #f8fafc;
        border-radius: 10px;
        padding: 10px 14px;
        margin-top: 8px;
    }

    .news-brief div {
        margin-bottom: 4px;
    }

    .news-meta {
        color: #667085;
        font-size: 0.82rem;
        margin-top: 10px;
    }

    .badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 800;
        margin: 0 6px 6px 0;
    }

    .bullish {
        background: #dcfce7;
        color: #166534;
    }

    .bearish {
        background: #fee2e2;
        color: #991b1b;
    }

    .neutral {
        background: #f1f5f9;
        color: #475569;
    }

    .industry {
        background: #dbeafe;
        color: #1d4ed8;
    }

    .company {
        background: #fef3c7;
        color: #92400e;
    }

    .highlight {
        background: linear-gradient(90deg, #fff7ed, #fffbeb);
        border: 1px solid #fed7aa;
        color: #9a3412;
        padding: 2px 7px;
        border-radius: 8px;
        font-weight: 750;
    }
    </style>
    """,
    unsafe_allow_html=True
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


def clock_component():
    components.html(
        f"""
        <style>
        .timer-box {{
            background: linear-gradient(135deg, #111827, #334155);
            color: white;
            border-radius: 14px;
            padding: 18px 22px;
            box-shadow: 0 14px 38px rgba(15, 23, 42, 0.18);
            font-family: Arial, sans-serif;
        }}
        .timer-wrap {{
            display: flex;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }}
        .timer-label {{
            font-size: 13px;
            opacity: 0.78;
        }}
        .timer-value {{
            font-size: 26px;
            font-weight: 800;
        }}
        </style>

        <div class="timer-box">
            <div class="timer-wrap">
                <div>
                    <div class="timer-label">Live Clock</div>
                    <div id="live-clock" class="timer-value">--:--:--</div>
                </div>
                <div>
                    <div class="timer-label">Auto Refresh Countdown</div>
                    <div id="countdown" class="timer-value">05:00</div>
                </div>
                <div>
                    <div class="timer-label">Refresh Cycle</div>
                    <div class="timer-value">5 min</div>
                </div>
            </div>
        </div>

        <script>
        let refreshSeconds = {REFRESH_SECONDS};
        let remaining = refreshSeconds;

        function pad(value) {{
            return String(value).padStart(2, "0");
        }}

        function updateClock() {{
            const now = new Date();
            document.getElementById("live-clock").textContent =
                pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
        }}

        function updateCountdown() {{
            const minutes = Math.floor(remaining / 60);
            const seconds = remaining % 60;
            document.getElementById("countdown").textContent = pad(minutes) + ":" + pad(seconds);
            remaining -= 1;
            if (remaining < 0) {{
                remaining = refreshSeconds;
            }}
        }}

        updateClock();
        updateCountdown();
        setInterval(updateClock, 1000);
        setInterval(updateCountdown, 1000);
        </script>
        """,
        height=125
    )


def streaming_metrics_component(total, bullish, bearish, neutral):
    components.html(
        f"""
        <style>
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 14px;
            margin: 8px 0 20px 0;
            font-family: Arial, sans-serif;
        }}
        .metric-card {{
            background: rgba(255, 255, 255, 0.96);
            border: 1px solid #e5e7eb;
            border-radius: 14px;
            padding: 18px;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.07);
        }}
        .metric-label {{
            color: #667085;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .metric-value {{
            color: #111827;
            font-size: 2rem;
            font-weight: 850;
            margin-top: 4px;
        }}
        .metric-note {{
            color: #667085;
            font-size: 0.8rem;
            margin-top: 4px;
            font-style: italic;
        }}
        </style>

        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Total Headlines</div>
                <div class="metric-value" data-target="{total}">0</div>
                <div class="metric-note">recent Google News items</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Bullish</div>
                <div class="metric-value" data-target="{bullish}" style="color:#15803d;">0</div>
                <div class="metric-note">positive market signal</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Bearish</div>
                <div class="metric-value" data-target="{bearish}" style="color:#b91c1c;">0</div>
                <div class="metric-note">risk or pressure signal</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Neutral</div>
                <div class="metric-value" data-target="{neutral}" style="color:#475569;">0</div>
                <div class="metric-note">watchlist headlines</div>
            </div>
        </div>

        <script>
        const values = document.querySelectorAll(".metric-value");
        values.forEach((el) => {{
            const target = Number(el.dataset.target);
            let current = 0;
            const step = Math.max(1, Math.ceil(target / 24));
            const timer = setInterval(() => {{
                current += step;
                if (current >= target) {{
                    current = target;
                    clearInterval(timer);
                }}
                el.textContent = current;
            }}, 28);
        }});
        </script>
        """,
        height=160
    )


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def google_news_url(query, region):
    recent_query = f"{query} when:1d"
    encoded = urllib.parse.quote_plus(recent_query)
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
def fetch_google_news(query, region="IN", limit=15):
    url = google_news_url(query, region)

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
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
    candidates = re.findall(
        r"\b[A-Z][A-Za-z&.\-]*(?:\s+[A-Z][A-Za-z&.\-]*){0,3}",
        headline
    )

    ignored = {
        "India", "China", "United States", "US", "UK", "EU", "Fed", "RBI",
        "Market", "Markets", "Stocks", "Shares", "Economy", "Business"
    }

    for candidate in candidates:
        candidate = candidate.strip()
        if len(candidate) > 2 and candidate not in ignored:
            return candidate

    return "Market / Multiple Companies"


def make_brief_lines(row):
    summary = clean_text(row["summary"] if row["summary"] else row["title"])

    if len(summary) > 180:
        summary = summary[:177].rsplit(" ", 1)[0] + "..."

    view = row["view"]
    company = row["company"]
    industry = row["industry"]

    if view == "Bullish":
        market_read = "Market read: The headline carries a positive tone and may support sentiment."
    elif view == "Bearish":
        market_read = "Market read: The headline points to pressure, risk, or weaker sentiment."
    else:
        market_read = "Market read: The headline is mixed or informational, so it should be watched."

    return [
        f"What happened: {summary}",
        market_read,
        f"Most affected: {company}, with impact mainly linked to {industry}.",
        "Why it matters: This can influence investor attention, sector movement, and short-term market narrative."
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
        safe_title = html.escape(str(row["title"]))
        safe_source = html.escape(str(row["source"]))
        safe_published = html.escape(str(row["published"]))
        safe_company = html.escape(str(row["company"]))
        safe_industry = html.escape(str(row["industry"]))
        safe_view = html.escape(str(row["view"]))

        brief_html = ""
        for line in row["brief_lines"]:
            brief_html += f"<div>{html.escape(line)}</div>"

        st.markdown(
            f"""
            <div class="news-card">
                <span class="badge {badge_class(row['view'])}">{safe_view}</span>
                <span class="badge company">{safe_company}</span>
                <span class="badge industry">{safe_industry}</span>
                <div class="news-title">{safe_title}</div>
                <div class="news-brief">{brief_html}</div>
                <div class="news-meta">
                    Source: <span class="highlight">{safe_source}</span>
                    &nbsp;|&nbsp; Published: {safe_published}
                </div>
            </div>
            """,
            unsafe_allow_html=True
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

    deal_value = ", ".join(values) if values else "Not available"
    return target, acquirer, deal_value


def market_news_tab(news_count, region, custom_query):
    query = custom_query or "stock market business economy corporate earnings"
    df, error = fetch_google_news(query, region, news_count)

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
        df, error = fetch_google_news(f"{industry} industry business news", region, 5)
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
    query = "merger acquisition acquires takeover buyout stake purchase deal value multiple"
    df, error = fetch_google_news(query, region, news_count)

    if error:
        st.error(error)
        return

    if df.empty:
        st.warning("No M&A news found.")
        return

    rows = []
    for _, row in df.iterrows():
        full_text = f"{row['title']} {row['summary']}"
        target, acquirer, deal_value = extract_deal_info(full_text)
        row_copy = row.copy()
        row_copy["view"] = sentiment_label(sentiment_score(full_text))
        row_copy["industry"] = detect_industry(full_text)
        row_copy["company"] = detect_company(row["title"])
        row_copy["brief_lines"] = make_brief_lines(row_copy)

        rows.append({
            "date": row["published_dt"],
            "published": row["published"],
            "headline": row["title"],
            "target": target,
            "acquirer": acquirer,
            "deal_value": deal_value,
            "brief_lines": row_copy["brief_lines"],
            "source": row["source"],
            "link": row["link"],
        })

    rows = sorted(rows, key=lambda item: item["date"], reverse=True)

    for row in rows:
        brief_html = ""
        for line in row["brief_lines"]:
            brief_html += f"<div>{html.escape(line)}</div>"

        st.markdown(
            f"""
            <div class="news-card">
                <span class="badge industry">M&A</span>
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
            unsafe_allow_html=True
        )

        if row["link"]:
            st.link_button("Open source", row["link"])


def macro_news_tab(news_count, region):
    for country, query in COUNTRY_QUERIES.items():
        with st.expander(country, expanded=country in ["India", "United States", "China"]):
            df, error = fetch_google_news(query, region, max(5, news_count // 2))
            if error:
                st.error(error)
                continue
            show_news_cards(enrich_news(df))


def main():
    st.markdown('<div class="dashboard-title">News Intelligence Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-subtitle">Recent Google News dashboard with local no-API classification, live clock, streaming metrics, and 5-minute auto-refresh.</div>',
        unsafe_allow_html=True
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
        "Macro News"
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

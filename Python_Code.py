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
    .main {
        background: #f6f8fb;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    .dashboard-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #101828;
        margin-bottom: 0.2rem;
    }
    .dashboard-subtitle {
        color: #667085;
        font-size: 1rem;
        margin-bottom: 1rem;
    }
    .timer-box {
        background: linear-gradient(135deg, #101828, #344054);
        color: white;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(16, 24, 40, 0.14);
    }
    .news-card {
        background: white;
        border: 1px solid #e4e7ec;
        border-radius: 10px;
        padding: 18px;
        margin-bottom: 14px;
        box-shadow: 0 3px 12px rgba(16, 24, 40, 0.06);
    }
    .news-title {
        color: #101828;
        font-size: 1.1rem;
        font-weight: 750;
        margin: 8px 0;
    }
    .news-meta {
        color: #667085;
        font-size: 0.85rem;
        margin-top: 8px;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        margin-right: 6px;
    }
    .bullish {
        background: #dcfae6;
        color: #067647;
    }
    .bearish {
        background: #fee4e2;
        color: #b42318;
    }
    .neutral {
        background: #eef2f6;
        color: #475467;
    }
    .industry {
        background: #e0f2fe;
        color: #026aa2;
    }
    .company {
        background: #fef3c7;
        color: #92400e;
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
        <div class="timer-box">
            <div style="display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:13px;opacity:0.78;">Live Clock</div>
                    <div id="live-clock" style="font-size:26px;font-weight:800;">--:--:--</div>
                </div>
                <div>
                    <div style="font-size:13px;opacity:0.78;">Auto Refresh Countdown</div>
                    <div id="countdown" style="font-size:26px;font-weight:800;">05:00</div>
                </div>
                <div>
                    <div style="font-size:13px;opacity:0.78;">Refresh Cycle</div>
                    <div style="font-size:26px;font-weight:800;">5 min</div>
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
            const clock = document.getElementById("live-clock");
            if (clock) {{
                clock.textContent =
                    pad(now.getHours()) + ":" +
                    pad(now.getMinutes()) + ":" +
                    pad(now.getSeconds());
            }}
        }}

        function updateCountdown() {{
            const countdown = document.getElementById("countdown");
            const minutes = Math.floor(remaining / 60);
            const seconds = remaining % 60;

            if (countdown) {{
                countdown.textContent = pad(minutes) + ":" + pad(seconds);
            }}

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
        height=130
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


def brief_news(row):
    text = row["summary"] if row["summary"] else row["title"]
    text = clean_text(text)
    if len(text) > 240:
        text = text[:237].rsplit(" ", 1)[0] + "..."
    return text


def enrich_news(df):
    if df.empty:
        return df

    df = df.copy()
    combined = df["title"].fillna("") + " " + df["summary"].fillna("")
    df["score"] = combined.apply(sentiment_score)
    df["view"] = df["score"].apply(sentiment_label)
    df["industry"] = combined.apply(detect_industry)
    df["company"] = df["title"].apply(detect_company)
    df["brief"] = df.apply(brief_news, axis=1)
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
        st.markdown(
            f"""
            <div class="news-card">
                <span class="badge {badge_class(row['view'])}">{row['view']}</span>
                <span class="badge company">{row['company']}</span>
                <span class="badge industry">{row['industry']}</span>
                <div class="news-title">{row['title']}</div>
                <div>{row['brief']}</div>
                <div class="news-meta">Source: {row['source']} | Published: {row['published']}</div>
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

    col1, col2, col3 = st.columns(3)
    col1.metric("Bullish", int((df["view"] == "Bullish").sum()) if not df.empty else 0)
    col2.metric("Bearish", int((df["view"] == "Bearish").sum()) if not df.empty else 0)
    col3.metric("Neutral", int((df["view"] == "Neutral").sum()) if not df.empty else 0)

    sentiment_filter = st.selectbox("Filter by sentiment", ["All", "Bullish", "Bearish", "Neutral"])
    industry_options = ["All"] + sorted(df["industry"].dropna().unique().tolist()) if not df.empty else ["All"]
    industry_filter = st.selectbox("Filter by industry", industry_options)

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
        rows.append({
            "date": row["published_dt"],
            "published": row["published"],
            "headline": row["title"],
            "target": target,
            "acquirer": acquirer,
            "deal_value": deal_value,
            "brief": brief_news(row),
            "source": row["source"],
            "link": row["link"],
        })

    rows = sorted(rows, key=lambda item: item["date"], reverse=True)

    for row in rows:
        st.markdown(
            f"""
            <div class="news-card">
                <span class="badge industry">M&A</span>
                <div class="news-title">{row['headline']}</div>
                <div><b>Target:</b> {row['target']}</div>
                <div><b>Acquirer:</b> {row['acquirer']}</div>
                <div><b>Deal value / multiples:</b> {row['deal_value']}</div>
                <div style="margin-top:8px;">{row['brief']}</div>
                <div class="news-meta">Source: {row['source']} | Published: {row['published']}</div>
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
        '<div class="dashboard-subtitle">Recent Google News dashboard with local no-API classification, live clock, and 5-minute auto-refresh.</div>',
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

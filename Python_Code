import re
import urllib.parse
from datetime import datetime, timezone

import feedparser
import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="AI News Dashboard",
    page_icon="📰",
    layout="wide"
)


COUNTRIES = {
    "India": "India economy OR India markets OR RBI OR Nifty OR Sensex",
    "United States": "US economy OR Federal Reserve OR S&P 500 OR Nasdaq OR Treasury",
    "China": "China economy OR PBOC OR yuan OR China markets",
    "European Union": "European Union economy OR ECB OR eurozone markets",
    "Japan": "Japan economy OR BOJ OR Nikkei OR yen",
    "United Kingdom": "UK economy OR Bank of England OR FTSE",
}

INDUSTRIES = [
    "Technology",
    "Banking",
    "Pharmaceuticals",
    "Energy",
    "Automobiles",
    "Real Estate",
    "Consumer Goods",
    "Metals",
    "Telecom",
    "Aviation",
]

BULLISH_WORDS = [
    "gain", "rise", "surge", "jump", "beat", "growth", "profit", "record",
    "upgrade", "strong", "expansion", "deal", "approval", "wins", "rally",
    "raises", "buyback", "dividend", "investment", "positive"
]

BEARISH_WORDS = [
    "fall", "drop", "plunge", "loss", "miss", "weak", "downgrade", "fraud",
    "probe", "lawsuit", "default", "decline", "layoff", "cuts", "warning",
    "debt", "bankruptcy", "slowdown", "negative", "recall"
]

INDUSTRY_KEYWORDS = {
    "Technology": ["ai", "software", "semiconductor", "chip", "cloud", "data center", "cyber"],
    "Banking": ["bank", "lender", "credit", "loan", "deposit", "nbfc", "fed", "rbi"],
    "Pharmaceuticals": ["pharma", "drug", "vaccine", "fda", "clinical", "healthcare", "hospital"],
    "Energy": ["oil", "gas", "renewable", "solar", "wind", "power", "coal", "energy"],
    "Automobiles": ["auto", "ev", "vehicle", "car", "battery", "tesla", "automaker"],
    "Real Estate": ["real estate", "housing", "property", "reit", "construction"],
    "Consumer Goods": ["retail", "consumer", "fmcg", "brand", "sales", "demand"],
    "Metals": ["steel", "copper", "aluminium", "mining", "metal", "iron ore"],
    "Telecom": ["telecom", "5g", "network", "spectrum", "broadband"],
    "Aviation": ["airline", "aviation", "aircraft", "airport", "boeing", "airbus"],
}


def google_news_rss_url(query, language="en", region="US"):
    encoded_query = urllib.parse.quote_plus(query)
    return (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}&hl={language}-{region}&gl={region}&ceid={region}:{language}"
    )


@st.cache_data(ttl=900)
def fetch_news(query, limit=15, language="en", region="US"):
    url = google_news_rss_url(query, language, region)

    try:
        response = requests.get(
            url,
            timeout=12,
            headers={"User-Agent": "Mozilla/5.0 News Dashboard"}
        )
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except Exception:
        feed = feedparser.parse(url)

    rows = []
    for entry in feed.entries[:limit]:
        title = clean_text(entry.get("title", ""))
        summary = clean_text(entry.get("summary", ""))
        link = entry.get("link", "")

        published_raw = entry.get("published", "")
        published_dt = parse_date(entry)

        source = "Google News"
        if hasattr(entry, "source") and isinstance(entry.source, dict):
            source = entry.source.get("title", source)
        elif " - " in title:
            source = title.rsplit(" - ", 1)[-1].strip()

        rows.append({
            "title": title,
            "summary": summary,
            "source": source,
            "link": link,
            "published": published_raw,
            "published_dt": published_dt,
        })

    return pd.DataFrame(rows)


def parse_date(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def clean_text(text):
    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sentiment_score(text):
    lowered = text.lower()
    bullish = sum(1 for word in BULLISH_WORDS if word in lowered)
    bearish = sum(1 for word in BEARISH_WORDS if word in lowered)
    return bullish - bearish


def classify_sentiment(text):
    score = sentiment_score(text)
    if score > 0:
        return "Bullish"
    if score < 0:
        return "Bearish"
    return "Neutral"


def detect_industry(text):
    lowered = text.lower()
    scores = {}

    for industry, keywords in INDUSTRY_KEYWORDS.items():
        scores[industry] = sum(1 for keyword in keywords if keyword in lowered)

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Broad Market"


def detect_company(title):
    title = re.sub(r"\s+-\s+.*$", "", title)
    candidates = re.findall(r"\b[A-Z][A-Za-z&.\-]*(?:\s+[A-Z][A-Za-z&.\-]*){0,3}", title)

    ignored = {
        "India", "China", "United States", "US", "UK", "EU", "Fed", "RBI",
        "Google News", "Market", "Markets", "Stocks", "Shares"
    }

    for candidate in candidates:
        candidate = candidate.strip()
        if len(candidate) > 2 and candidate not in ignored:
            return candidate

    return "Market / Multiple Companies"


def brief_explanation(row):
    text = row["summary"] or row["title"]
    text = clean_text(text)

    if len(text) > 220:
        text = text[:217].rsplit(" ", 1)[0] + "..."

    return text


def enrich_news(df):
    if df.empty:
        return df

    enriched = df.copy()
    combined = enriched["title"].fillna("") + " " + enriched["summary"].fillna("")

    enriched["sentiment"] = combined.apply(classify_sentiment)
    enriched["score"] = combined.apply(sentiment_score)
    enriched["industry"] = combined.apply(detect_industry)
    enriched["company"] = enriched["title"].apply(detect_company)
    enriched["brief"] = enriched.apply(brief_explanation, axis=1)

    return enriched


def extract_deal_info(text):
    lowered = text.lower()

    target = "Not clear"
    acquirer = "Not clear"

    patterns = [
        r"(.+?)\s+to\s+buy\s+(.+?)(?:\s+for|\s+in|\s+as|,|$)",
        r"(.+?)\s+acquires\s+(.+?)(?:\s+for|\s+in|\s+as|,|$)",
        r"(.+?)\s+buys\s+(.+?)(?:\s+for|\s+in|\s+as|,|$)",
        r"(.+?)\s+merges\s+with\s+(.+?)(?:\s+for|\s+in|\s+as|,|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            acquirer = clean_entity(match.group(1))
            target = clean_entity(match.group(2))
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

    if "stake" in lowered and target == "Not clear":
        target = "Stake purchase mentioned"

    return target, acquirer, deal_value


def clean_entity(text):
    text = clean_text(text)
    text = re.sub(r"^(report:|exclusive:|breaking:)\s*", "", text, flags=re.IGNORECASE)
    text = text[:80].strip(" -:,.")
    return text if text else "Not clear"


def display_news_cards(df):
    if df.empty:
        st.warning("No news found. Try a broader query or different region.")
        return

    for _, row in df.iterrows():
        badge_color = {
            "Bullish": "green",
            "Bearish": "red",
            "Neutral": "gray"
        }.get(row["sentiment"], "gray")

        with st.container(border=True):
            top_line = f"**{row['sentiment']}** | {row['company']} | {row['industry']} | Source: {row['source']}"
            st.markdown(f":{badge_color}[{top_line}]")
            st.subheader(row["title"])
            st.write(row["brief"])
            st.caption(f"Published: {row['published']}")
            st.link_button("Open news", row["link"])


def market_dashboard_tab(news_count, region, language, custom_query):
    query = custom_query or "stock market business economy corporate earnings"
    df = enrich_news(fetch_news(query, news_count, language, region))

    st.subheader("Top Market News")
    display_news_cards(df)

    if not df.empty:
        st.subheader("Quick Read")
        col1, col2, col3 = st.columns(3)
        col1.metric("Bullish", int((df["sentiment"] == "Bullish").sum()))
        col2.metric("Bearish", int((df["sentiment"] == "Bearish").sum()))
        col3.metric("Neutral", int((df["sentiment"] == "Neutral").sum()))

        st.bar_chart(df["industry"].value_counts())


def industry_tab(news_count, region, language):
    st.subheader("Industry News Ranking")

    industry_frames = []
    for industry in INDUSTRIES:
        df = enrich_news(fetch_news(f"{industry} industry business news", 5, language, region))
        if not df.empty:
            avg_score = df["score"].mean()
            industry_frames.append({
                "industry": industry,
                "average_score": round(avg_score, 2),
                "bullish_count": int((df["sentiment"] == "Bullish").sum()),
                "bearish_count": int((df["sentiment"] == "Bearish").sum()),
                "news": df
            })

    if not industry_frames:
        st.warning("No industry news found.")
        return

    ranking = pd.DataFrame([
        {
            "Industry": item["industry"],
            "Average Score": item["average_score"],
            "Bullish News": item["bullish_count"],
            "Bearish News": item["bearish_count"],
        }
        for item in industry_frames
    ]).sort_values("Average Score", ascending=False)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Top 3 Industries")
        st.dataframe(ranking.head(3), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("#### Bottom 3 Industries")
        st.dataframe(ranking.tail(3).sort_values("Average Score"), use_container_width=True, hide_index=True)

    selected_industry = st.selectbox("View industry details", ranking["Industry"].tolist())
    selected_news = next(item["news"] for item in industry_frames if item["industry"] == selected_industry)
    display_news_cards(selected_news.head(news_count))


def ma_tab(news_count, region, language):
    st.subheader("M&A News - Chronological")

    query = (
        "merger OR acquisition OR acquires OR takeover OR buyout OR stake purchase "
        "deal value multiple business"
    )

    df = fetch_news(query, news_count, language, region)

    if df.empty:
        st.warning("No M&A news found.")
        return

    records = []
    for _, row in df.iterrows():
        full_text = f"{row['title']} {row['summary']}"
        target, acquirer, deal_value = extract_deal_info(full_text)
        records.append({
            "Date": row["published_dt"].strftime("%Y-%m-%d"),
            "Target": target,
            "Acquirer": acquirer,
            "Deal Value / Multiple": deal_value,
            "Brief Intro": brief_explanation(row),
            "Source": row["source"],
            "Headline": row["title"],
            "Link": row["link"],
        })

    deal_df = pd.DataFrame(records).sort_values("Date", ascending=False)

    for _, row in deal_df.iterrows():
        with st.container(border=True):
            st.caption(row["Date"])
            st.subheader(row["Headline"])
            st.write(f"**Target:** {row['Target']}")
            st.write(f"**Acquirer:** {row['Acquirer']}")
            st.write(f"**Deal value / multiples:** {row['Deal Value / Multiple']}")
            st.write(row["Brief Intro"])
            st.caption(f"Source: {row['Source']}")
            st.link_button("Open deal news", row["Link"])


def macro_tab(news_count, region, language):
    st.subheader("Macro News by Country")

    for country, query in COUNTRIES.items():
        with st.expander(country, expanded=country in ["India", "United States", "China"]):
            df = enrich_news(fetch_news(query, max(5, news_count // 2), language, region))
            display_news_cards(df)


def recommendations_panel():
    st.sidebar.divider()
    st.sidebar.subheader("Smart Customization Ideas")
    st.sidebar.write(
        "- Add your portfolio companies to the search query.\n"
        "- Use India region for NSE/BSE-heavy news.\n"
        "- Track one industry at a time before market open.\n"
        "- Treat Neutral headlines as watchlist items, not signals.\n"
        "- For stronger accuracy, manually review original links before trading."
    )


def main():
    st.title("AI News Dashboard")
    st.caption("Google News-powered market monitor with no paid API key required.")

    with st.sidebar:
        st.header("Controls")
        news_count = st.slider("News count", min_value=10, max_value=15, value=12)
        region = st.selectbox("Google News region", ["US", "IN", "GB", "SG", "AU"], index=0)
        language = st.selectbox("Language", ["en"], index=0)
        custom_query = st.text_input(
            "Custom market query",
            placeholder="Example: Indian IT stocks earnings"
        )

        st.info(
            "Classification is heuristic-based. It uses keyword scoring, source extraction, "
            "company detection, and industry matching locally without an AI API."
        )

        recommendations_panel()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Market News",
        "Industry News",
        "M&A News",
        "Macro News"
    ])

    with tab1:
        market_dashboard_tab(news_count, region, language, custom_query)

    with tab2:
        industry_tab(news_count, region, language)

    with tab3:
        ma_tab(news_count, region, language)

    with tab4:
        macro_tab(news_count, region, language)


if __name__ == "__main__":
    main()

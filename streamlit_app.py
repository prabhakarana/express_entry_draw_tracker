import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")
st.title("🍁 Canada Express Entry Draw Tracker (Live + Fallback)")
st.markdown("Real-time ITA history by category, CRS, and draw date. Falls back to 2025 data if Canada.ca is unreachable.")

@st.cache_data(ttl=3600)
def fetch_draws():
    base_url = "https://www.canada.ca"
    main_url = base_url + "/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(main_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = [
            base_url + a["href"]
            for a in soup.select("a[href*='rounds-invitations']") if "date" in a["href"]
        ]
        draws = []
        for link in links:
            r = requests.get(link, headers=headers, timeout=10)
            s = BeautifulSoup(r.text, "html.parser")
            title = s.find("h1").text.strip()
            paras = s.find_all("p")
            date = title.split(":")[0].strip()
            category = next((p.text for p in paras if "round of invitations" in p.text.lower()), "Unknown")
            crs = next((p.text for p in paras if "lowest-ranked candidate invited" in p.text.lower()), "")
            itas = next((p.text for p in paras if "invitations to apply" in p.text.lower()), "")
            crs_score = next((int(word) for word in crs.split() if word.isdigit()), None)
            invitations = next((int(word.replace(",", "")) for word in itas.split() if word.replace(",", "").isdigit()), None)
            draws.append({
                "Draw Date": pd.to_datetime(date, errors='coerce'),
                "Category": category.strip(),
                "CRS Score": crs_score,
                "ITAs Issued": invitations,
                "URL": link
            })
        df = pd.DataFrame(draws)
        return df.dropna(subset=["Draw Date"])
    except Exception as e:
        st.warning(f"⚠️ Live data unavailable. Using fallback data. Reason: {e}")
        return pd.read_csv("fallback_draw_data_2025.csv", parse_dates=["Draw Date"])

# Load data
df = fetch_draws()

if df.empty:
    st.error("No draw data available.")
else:
    df["Year"] = df["Draw Date"].dt.year
    df["Quarter"] = df["Draw Date"].dt.to_period("Q").astype(str)
    pivot = df.groupby("Category").agg(
        Total_ITAs=pd.NamedAgg(column="ITAs Issued", aggfunc="sum"),
        Lowest_CRS=pd.NamedAgg(column="CRS Score", aggfunc="min"),
        Last_Draw=pd.NamedAgg(column="Draw Date", aggfunc="max")
    ).sort_values("Total_ITAs", ascending=False).reset_index()
    pivot["Last_Draw"] = pivot["Last_Draw"].dt.strftime("%B %d, %Y")
    df["Draw Date"] = df["Draw Date"].dt.strftime("%B %d, %Y")

    st.markdown("### 🧾 Draw Summary by Category")
    st.dataframe(pivot, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📅 Total Invitations by Year")
        st.dataframe(df.groupby("Year")["ITAs Issued"].sum().reset_index(), use_container_width=True)

    with col2:
        st.markdown("### 📆 Total Invitations by Quarter")
        st.dataframe(df.groupby("Quarter")["ITAs Issued"].sum().reset_index(), use_container_width=True)

    st.markdown("### 📜 Draw History")
    st.dataframe(df[["Draw Date", "Category", "ITAs Issued", "CRS Score"]].sort_values(by="Draw Date", ascending=False), use_container_width=True)

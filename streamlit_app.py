import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

LIVE_JSON_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
FALLBACK_JSON_PATH = "ee_rounds_123_en.json"

@st.cache_data
def load_data():
    try:
        response = requests.get(LIVE_JSON_URL, timeout=10)
        response.raise_for_status()
        rounds = response.json()["rounds"]
    except Exception as e:
        st.warning(f"⚠️ Live data not reachable. Loading fallback. Reason: {e}")
        if os.path.exists(FALLBACK_JSON_PATH):
            with open(FALLBACK_JSON_PATH, "r", encoding="utf-8") as f:
                import json
                rounds = json.load(f)["rounds"]
        else:
            st.error("Fallback JSON not found.")
            st.stop()

    data = []
    for r in rounds:
        try:
            data.append({
                "Draw #": int(r.get("drawNumber", 0)),
                "Draw Date": pd.to_datetime(r.get("drawDate"), errors='coerce'),
                "Category": r.get("drawName", ""),
                "ITAs Issued": int(r.get("drawSize", 0)),
                "CRS Score": int(r.get("drawCRS", 0))
            })
        except:
            continue
    df = pd.DataFrame(data)
    return df.dropna(subset=["Draw Date"])

df = load_data()
df["Year"] = df["Draw Date"].dt.year
df["Quarter"] = df["Draw Date"].dt.to_period("Q").astype(str)

# Sidebar Filters
st.sidebar.title("🔍 Filter Options")
year_options = sorted(df["Year"].unique(), reverse=True)
selected_years = st.sidebar.multiselect("Select Year(s)", year_options, default=year_options)

filtered = df[df["Year"].isin(selected_years)]

# Summary Table
st.subheader("🧾 Draw Summary by Category")
pivot = filtered.groupby("Category").agg(
    Total_ITAs=pd.NamedAgg(column="ITAs Issued", aggfunc="sum"),
    Lowest_CRS=pd.NamedAgg(column="CRS Score", aggfunc="min"),
    Last_Draw=pd.NamedAgg(column="Draw Date", aggfunc="max")
).sort_values("Total_ITAs", ascending=False).reset_index()
pivot["Last_Draw"] = pivot["Last_Draw"].dt.strftime("%b %d, %Y")
st.dataframe(pivot, use_container_width=True)

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("📅 Total Invitations by Year")
    yearly = filtered.groupby("Year")["ITAs Issued"].sum().reset_index()
    fig1, ax1 = plt.subplots()
    sns.barplot(data=yearly, x="Year", y="ITAs Issued", ax=ax1, palette="Blues_d")
    st.pyplot(fig1)

with col2:
    st.subheader("📆 Total Invitations by Quarter")
    quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
    fig2, ax2 = plt.subplots()
    sns.barplot(data=quarterly, x="Quarter", y="ITAs Issued", ax=ax2, palette="Greens_d")
    plt.xticks(rotation=45)
    st.pyplot(fig2)

# Draw History Table with Download
st.subheader("📜 Filtered Draw History")
draw_table = filtered.sort_values("Draw #", ascending=False).reset_index(drop=True)
draw_table["Draw Date"] = draw_table["Draw Date"].dt.strftime("%b %d, %Y")
st.dataframe(draw_table[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]], use_container_width=True)

csv = draw_table.to_csv(index=False).encode("utf-8")
st.download_button("📥 Download CSV", data=csv, file_name="express_entry_draws.csv", mime="text/csv")

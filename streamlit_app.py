import streamlit as st
import pandas as pd
import json
import os
import altair as alt
import requests

st.set_page_config(layout="wide")

# URLs and file paths
DATA_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
FALLBACK_FILE = "data/ee_rounds_123_en.json"  # relative to root of your Git repo

@st.cache_data
def load_data():
    try:
        response = requests.get(DATA_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception:
        st.warning("⚠️ Could not fetch live data. Using fallback file.")
        if os.path.exists(FALLBACK_FILE):
            with open(FALLBACK_FILE, "r") as f:
                data = json.load(f)
        else:
            st.error("❌ Fallback data file not found. Please add it under `data/`.")
            return pd.DataFrame()

    rounds = data.get("rounds", [])
    df = pd.DataFrame([{
        "Draw #": r.get("drawNumber"),
        "Draw Date": pd.to_datetime(r.get("drawDate"), errors="coerce"),
        "Category": r.get("drawType"),
        "ITAs Issued": pd.to_numeric(r.get("drawSize"), errors="coerce"),
        "CRS Score": pd.to_numeric(r.get("drawScore"), errors="coerce")
    } for r in rounds])

    return df.dropna(subset=["Draw Date", "ITAs Issued"])

df = load_data()

if df.empty:
    st.stop()

# Sidebar
st.sidebar.header("📅 Filter by Year")
years = df["Draw Date"].dt.year.sort_values(ascending=False).unique()
selected_years = st.sidebar.multiselect("Select years to include:", years, default=years[:1])
filtered = df[df["Draw Date"].dt.year.isin(selected_years)]

# Yearly Summary
st.subheader("📊 Total Invitations by Year")
if not filtered.empty:
    yearly = filtered.groupby(filtered["Draw Date"].dt.year)["ITAs Issued"].sum().reset_index()
    chart = alt.Chart(yearly).mark_bar().encode(
        x=alt.X("Draw Date:O", title="Year"),
        y=alt.Y("ITAs Issued:Q"),
        tooltip=["Draw Date", "ITAs Issued"]
    ).properties(title="Total Invitations by Year")
    st.altair_chart(chart, use_container_width=True)
else:
    st.info("No data for selected years.")

# Quarterly Summary
st.subheader("📈 Total Invitations by Quarter")
filtered["Quarter"] = filtered["Draw Date"].dt.to_period("Q").astype(str)
quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
st.dataframe(quarterly)

chart2 = alt.Chart(quarterly).mark_bar().encode(
    x="Quarter",
    y="ITAs Issued",
    tooltip=["Quarter", "ITAs Issued"]
).properties(title="Quarterly Invitations")
st.altair_chart(chart2, use_container_width=True)

# Draw Table
st.subheader("📜 Filtered Draw History")
filtered_sorted = filtered.sort_values("Draw #", ascending=False).reset_index(drop=True)
st.dataframe(filtered_sorted[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]])

# CSV Download
csv_data = filtered_sorted.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv_data, file_name="filtered_draw_history.csv", mime="text/csv")

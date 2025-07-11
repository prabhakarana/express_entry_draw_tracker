import streamlit as st
import pandas as pd
import requests
import json
from jsonpath_ng import parse as jsonpath_parse
import matplotlib.pyplot as plt
import os

st.set_page_config(layout="wide")
st.markdown("🍁 **# Express Entry Draw Tracker (Canada)**")
st.markdown("Live tracking of Express Entry ITAs, CRS scores, and draw types.")

# JSON URL and fallback
LIVE_JSON_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
FALLBACK_FILE = os.path.join("data", "ee_rounds_123_en.json")

# --- Helper Functions ---
def parse_int_safe(value):
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0

def load_data():
    try:
        res = requests.get(LIVE_JSON_URL, timeout=10)
        res.raise_for_status()
        data = res.json()
        st.success("✅ Live data loaded.")
    except:
        try:
            with open(FALLBACK_FILE, "r") as f:
                data = json.load(f)
            st.warning("⚠️ Could not fetch live data. Using fallback JSON.")
        except:
            st.error("❌ Failed to load fallback JSON data.")
            return pd.DataFrame()
    
    path_expr = jsonpath_parse("$.rounds[*]")
    draws = [match.value for match in path_expr.find(data)]
    return transform_data(draws)

def transform_data(draws):
    records = []
    for d in draws:
        try:
            records.append({
                "Draw #": d.get("drawNumber"),
                "Draw Date": pd.to_datetime(d.get("drawDate")),
                "Category": d.get("drawName"),
                "ITAs Issued": parse_int_safe(d.get("drawSize")),
                "CRS Score": parse_int_safe(d.get("drawCRS"))
            })
        except:
            continue

    df = pd.DataFrame(records)
    df["Year"] = df["Draw Date"].dt.year
    df["Quarter"] = df["Draw Date"].dt.to_period("Q").astype(str)
    return df.sort_values("Draw Date", ascending=False)

# --- Load and Prepare Data ---
df = load_data()
if df.empty:
    st.stop()

# --- Sidebar Filter ---
st.sidebar.header("🔍 Filter Options")
years = sorted(df["Year"].unique(), reverse=True)
default_years = years[:5]  # Prefill only most recent 5 years
selected_years = st.sidebar.multiselect("Select Year(s)", years, default=default_years)
filtered_df = df[df["Year"].isin(selected_years)]

if filtered_df.empty:
    st.info("No data available for the selected year(s).")
    st.stop()

# --- Draw Summary ---
st.subheader("📊 Draw Summary by Category")
summary = (
    filtered_df.groupby("Category")
    .agg(
        Total_ITAs=pd.NamedAgg(column="ITAs Issued", aggfunc="sum"),
        Lowest_CRS=pd.NamedAgg(column="CRS Score", aggfunc="min"),
        Last_Draw=pd.NamedAgg(column="Draw Date", aggfunc="max")
    )
    .reset_index()
    .sort_values("Total_ITAs", ascending=False)
)
summary["Last_Draw"] = summary["Last_Draw"].dt.strftime("%b %d, %Y")
st.dataframe(summary, use_container_width=True)

# --- Total by Year ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("📅 Total Invitations by Year")
    year_summary = filtered_df.groupby("Year")["ITAs Issued"].sum().reset_index()
    fig, ax = plt.subplots()
    ax.bar(year_summary["Year"].astype(str), year_summary["ITAs Issued"])
    ax.set_ylabel("ITAs Issued")
    st.pyplot(fig)

# --- Total by Quarter ---
with col2:
    st.subheader("📅 Total Invitations by Quarter")
    quarter_summary = filtered_df.groupby("Quarter")["ITAs Issued"].sum().reset_index()
    fig, ax = plt.subplots()
    ax.bar(quarter_summary["Quarter"], quarter_summary["ITAs Issued"], color="seagreen")
    ax.set_ylabel("ITAs Issued")
    plt.xticks(rotation=45)
    st.pyplot(fig)

# --- Full Draw Table ---
st.subheader("📋 Filtered Draw History")
st.dataframe(
    filtered_df[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]],
    use_container_width=True
)

# --- Download Option ---
st.download_button(
    label="📥 Download CSV",
    data=filtered_df.to_csv(index=False),
    file_name="express_entry_draws_filtered.csv",
    mime="text/csv"
)

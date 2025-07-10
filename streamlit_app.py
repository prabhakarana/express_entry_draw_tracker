import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import requests
import json
from jsonpath_ng import parse
from datetime import datetime

# ---------------------------
# Constants and Fallback Path
# ---------------------------
LIVE_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
FALLBACK_FILE = "ee_rounds_123_en.json"

# ---------------------------
# Utility Functions
# ---------------------------
def load_json_data():
    try:
        res = requests.get(LIVE_URL, timeout=10)
        res.raise_for_status()
        st.success("✅ Live data loaded.")
        return res.json()
    except Exception:
        st.warning("⚠️ Could not fetch live data. Using fallback.")
        try:
            with open(FALLBACK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            st.error("❌ Failed to load fallback JSON data.")
            return None

def extract_draws(json_data):
    path_expr = parse('$.rounds[*]')
    return [match.value for match in path_expr.find(json_data)]

def transform_data(draws):
    records = []
    for d in draws:
        try:
            records.append({
                "Draw #": d.get("drawNumber"),
                "Draw Date": pd.to_datetime(d.get("drawDate")),
                "Category": d.get("drawName"),
                "ITAs Issued": int(d.get("drawSize", 0)),
                "CRS Score": int(d.get("drawCRS", 0))
            })
        except Exception:
            continue
    df = pd.DataFrame(records)
    df["Year"] = df["Draw Date"].dt.year
    df["Quarter"] = df["Draw Date"].dt.to_period("Q").astype(str)
    return df.sort_values("Draw Date", ascending=False)

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Express Entry Tracker", layout="wide")
st.title("🍁 Express Entry Draw Tracker (Canada)")
st.markdown("Live tracking of Express Entry ITAs, CRS scores, and draw types.")

data_json = load_json_data()
if not data_json:
    st.stop()

draws = extract_draws(data_json)
df = transform_data(draws)

# Filter sidebar
with st.sidebar:
    st.markdown("🔍 **Filter Options**")
    selected_years = st.multiselect("Select Year(s)", sorted(df["Year"].unique(), reverse=True), default=sorted(df["Year"].unique(), reverse=True))

filtered_df = df[df["Year"].isin(selected_years)]

# Summary Table
st.subheader("📋 Draw Summary by Category")
summary = filtered_df.groupby("Category").agg(
    Total_ITAs=pd.NamedAgg(column="ITAs Issued", aggfunc="sum"),
    Lowest_CRS=pd.NamedAgg(column="CRS Score", aggfunc="min"),
    Last_Draw=pd.NamedAgg(column="Draw Date", aggfunc="max")
).reset_index()
summary["Last_Draw"] = summary["Last_Draw"].dt.strftime("%b %d, %Y")
st.dataframe(summary.sort_values("Total_ITAs", ascending=False), use_container_width=True)

# Charts
col1, col2 = st.columns(2)

with col1:
    st.subheader("📅 Total Invitations by Year")
    year_summary = filtered_df.groupby("Year")["ITAs Issued"].sum().reset_index()
    fig, ax = plt.subplots()
    ax.bar(year_summary["Year"].astype(str), year_summary["ITAs Issued"])
    ax.set_ylabel("ITAs Issued")
    st.pyplot(fig)

with col2:
    st.subheader("📆 Total Invitations by Quarter")
    quarter_summary = filtered_df.groupby("Quarter")["ITAs Issued"].sum().reset_index()
    fig, ax = plt.subplots()
    ax.bar(quarter_summary["Quarter"], quarter_summary["ITAs Issued"], color="green")
    ax.set_ylabel("ITAs Issued")
    plt.xticks(rotation=45)
    st.pyplot(fig)

# Download
csv = filtered_df.to_csv(index=False)
st.download_button("📥 Download CSV", csv, file_name="express_entry_draws.csv", mime="text/csv")

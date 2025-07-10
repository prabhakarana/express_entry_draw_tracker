import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json
import os

st.set_page_config(layout="wide")
st.markdown("## 🍁 Express Entry Draw Tracker (Canada)")
st.caption("Live tracking of Express Entry ITAs, CRS scores, and draw types.")

DATA_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
FALLBACK_FILE = "data/ee_rounds_123_en.json"

@st.cache_data
def load_data():
    try:
        response = requests.get(DATA_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        st.success("✅ Live data loaded.")
    except Exception as e:
        st.warning("⚠️ Could not fetch live data. Using existing file.")
        if os.path.exists(FALLBACK_FILE):
            with open(FALLBACK_FILE, "r") as f:
                data = json.load(f)
        else:
            st.error("❌ Data file not found. Please run the scraper.")
            return pd.DataFrame()

    rounds = data.get("rounds", [])
    records = []
    for r in rounds:
        try:
            records.append({
                "Draw #": r.get("drawNumber"),
                "Draw Date": pd.to_datetime(r.get("drawDate"), errors="coerce"),
                "Category": r.get("drawName"),
                "ITAs Issued": pd.to_numeric(r.get("drawSize"), errors="coerce"),
                "CRS Score": pd.to_numeric(r.get("drawCRS"), errors="coerce")
            })
        except Exception as err:
            st.write(f"Skipping row due to error: {err}")
    df = pd.DataFrame(records)
    df = df.dropna(subset=["Draw Date", "ITAs Issued"])
    return df

df = load_data()

# Sidebar filter
st.sidebar.header("🔍 Filter Options")
if not df.empty:
    years = df["Draw Date"].dt.year.dropna().astype(int).unique()
    years = sorted(years, reverse=True)
    selected_years = st.sidebar.multiselect("Select Year(s)", years, default=years[:1])
    filtered = df[df["Draw Date"].dt.year.isin(selected_years)]
else:
    st.info("No data available.")
    filtered = pd.DataFrame()

# Draw History Table
if not filtered.empty:
    st.subheader("📜 Filtered Draw History")
    filtered_sorted = filtered.sort_values("Draw #", ascending=False).reset_index(drop=True)
    st.dataframe(filtered_sorted)

    # Total Invitations by Quarter
    st.subheader("📈 Total Invitations by Quarter")
    filtered["Quarter"] = filtered["Draw Date"].dt.to_period("Q").astype(str)
    quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
    fig1, ax1 = plt.subplots()
    sns.barplot(data=quarterly, x="Quarter", y="ITAs Issued", ax=ax1)
    ax1.set_title("Total Invitations by Quarter")
    ax1.set_xlabel("Quarter")
    ax1.set_ylabel("Total ITAs")
    plt.xticks(rotation=45)
    st.pyplot(fig1)

    # Total ITAs by Year
    st.subheader("📊 Total Invitations by Year")
    yearly = filtered.groupby(filtered["Draw Date"].dt.year)["ITAs Issued"].sum().reset_index()
    yearly.columns = ["Year", "Total ITAs"]
    fig2, ax2 = plt.subplots()
    sns.barplot(data=yearly, x="Year", y="Total ITAs", ax=ax2)
    ax2.set_title("Total ITAs by Year")
    ax2.set_ylabel("ITAs")
    st.pyplot(fig2)

    # Download Button
    csv = filtered_sorted.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV", data=csv, file_name="express_entry_filtered.csv", mime="text/csv")
else:
    st.info("No data available for the selected year(s).")

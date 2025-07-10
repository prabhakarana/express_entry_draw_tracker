import subprocess
import os
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

# Automatically run the scraper to update data
SCRAPER_SCRIPT = "scrape_express_entry_draws.py"
CSV_FILE = "express_entry_draws.csv"

try:
    subprocess.run(["python", SCRAPER_SCRIPT], check=True)
except Exception as e:
    st.warning("⚠️ Could not fetch live data. Using existing file.")

@st.cache_data
def load_data():
    if not os.path.exists(CSV_FILE):
        st.error("❌ Data file not found. Please run the scraper.")
        st.stop()
    df = pd.read_csv(CSV_FILE)
    df["Draw Date"] = pd.to_datetime(df["Draw Date"], errors="coerce")
    df = df.dropna(subset=["Draw Date", "ITAs Issued"])
    df["Year"] = df["Draw Date"].dt.year
    df["Quarter"] = df["Draw Date"].dt.to_period("Q").astype(str)
    return df

df = load_data()

# Sidebar filters
st.sidebar.header("🔍 Filter Options")
years = sorted(df["Year"].unique(), reverse=True)
selected_years = st.sidebar.multiselect("Select Year(s)", years, default=years[:1])

filtered = df[df["Year"].isin(selected_years)]

# Title and Summary
st.title("🍁 Express Entry Draw Tracker (Canada)")
st.markdown("Live tracking of Express Entry ITAs, CRS scores, and draw types.")

# Yearly Chart
if not filtered.empty:
    yearly_summary = filtered.groupby("Year")["ITAs Issued"].sum().reset_index()
    st.subheader("📊 Total Invitations by Year")
    chart = alt.Chart(yearly_summary).mark_bar().encode(
        x=alt.X("Year:O", title="Year"),
        y=alt.Y("ITAs Issued:Q", title="Total ITAs"),
        tooltip=["Year", "ITAs Issued"]
    )
    text = chart.mark_text(
        align='center', baseline='bottom', dy=-5
    ).encode(text='ITAs Issued:Q')
    st.altair_chart(chart + text, use_container_width=True)
else:
    st.info("No data available for the selected year(s).")

# Quarterly Chart
st.subheader("📈 Total Invitations by Quarter")
quarter_summary = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
chart_q = alt.Chart(quarter_summary).mark_bar().encode(
    x=alt.X("Quarter:O", title="Quarter"),
    y=alt.Y("ITAs Issued:Q", title="Total ITAs"),
    tooltip=["Quarter", "ITAs Issued"]
)
text_q = chart_q.mark_text(
    align='center', baseline='bottom', dy=-5
).encode(text='ITAs Issued:Q')
st.altair_chart(chart_q + text_q, use_container_width=True)

# Draw History Table
st.subheader("📜 Filtered Draw History")
filtered_sorted = filtered.sort_values("Draw #", ascending=False).reset_index(drop=True)
filtered_sorted["Draw Date"] = filtered_sorted["Draw Date"].dt.strftime("%B %d, %Y")
st.dataframe(
    filtered_sorted[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]],
    use_container_width=True
)

# Download button
csv_data = filtered_sorted.to_csv(index=False).encode("utf-8")
st.download_button("⬇️ Download CSV", data=csv_data, file_name="express_entry_draws.csv", mime="text/csv")

# Footer
st.markdown("---")
st.caption("📬 Updated from Canada.ca. Built with Streamlit. Auto-refreshes via BeautifulSoup scraper.")

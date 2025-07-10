
import streamlit as st
import pandas as pd
import numpy as np
import requests
from io import StringIO, BytesIO
import altair as alt

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

# Load data from official source or fallback CSV
@st.cache_data(ttl=3600)
def load_data():
    url = "https://www.canada.ca/content/dam/ircc/documents/json/ee-draws-table.json"
    fallback_file = "fallback_draw_data_2025.csv"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        df = pd.DataFrame(res.json()["data"]["rows"])
        df.columns = ["Draw #", "Draw Date", "Category", "Invitations issued", "CRS Score"]
        df["Draw Date"] = pd.to_datetime(df["Draw Date"])
    except:
        df = pd.read_csv(fallback_file)
        df["Draw Date"] = pd.to_datetime(df["Draw Date"], errors="coerce")
        df = df.dropna(subset=["Draw Date"])
    return df

df = load_data()

# Sidebar - Filter by year
st.sidebar.header("📅 Filter by Year")
df["Year"] = df["Draw Date"].dt.year
years = sorted(df["Year"].unique(), reverse=True)
selected_years = st.sidebar.multiselect("Select years to include:", years, default=years)

filtered = df[df["Year"].isin(selected_years)]

# Total Invitations by Year
st.markdown("## 📊 Total Invitations by Year")
yearly = filtered.groupby(filtered["Draw Date"].dt.year)["Invitations issued"].sum().reset_index(name="ITAs Issued")
chart_year = alt.Chart(yearly).mark_bar().encode(x="Draw Date:O", y="ITAs Issued:Q")
st.altair_chart(chart_year, use_container_width=True)

# Total Invitations by Quarter
st.markdown("## 📈 Total Invitations by Quarter")
filtered["Quarter"] = filtered["Draw Date"].dt.to_period("Q").astype(str)
quarterly = filtered.groupby("Quarter")["Invitations issued"].sum().reset_index(name="ITAs Issued")
st.dataframe(quarterly, use_container_width=True)
chart_quarter = alt.Chart(quarterly).mark_bar().encode(x="Quarter:O", y="ITAs Issued:Q")
st.altair_chart(chart_quarter, use_container_width=True)

# Filtered Draw History Table
st.markdown("## 📜 Filtered Draw History")
export_df = filtered[["Draw #", "Draw Date", "Category", "Invitations issued", "CRS Score"]].sort_values(by="Draw #", ascending=False)
export_df["Draw Date"] = export_df["Draw Date"].dt.strftime("%b %d, %Y")
st.dataframe(export_df, use_container_width=True)

# Export Buttons - right aligned below table
col1, col2, col3 = st.columns([8, 1, 1])
with col2:
    csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("📄 CSV", csv, "draw_history.csv", "text/csv")
with col3:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        export_df.to_excel(writer, index=False, sheet_name="DrawHistory")
        writer.book.close()
    st.download_button("📊 Excel", buffer.getvalue(), "draw_history.xlsx", "application/vnd.ms-excel")

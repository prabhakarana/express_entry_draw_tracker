
import streamlit as st
import pandas as pd
import altair as alt
import os
from io import BytesIO

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")
st.title("📊 Express Entry Draw Tracker")

# Load data
@st.cache_data
def load_data():
    try:
        url = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds.json"
        df = pd.read_json(url)
        df = df["Rounds of invitations"]
        df = pd.json_normalize(df)
        df.rename(columns={
            "DrawNumber": "Draw #",
            "DrawDate": "Draw Date",
            "DrawCategory": "Category",
            "InvitationsIssued": "ITAs Issued",
            "CrsScore": "CRS Score"
        }, inplace=True)
        df["Draw Date"] = pd.to_datetime(df["Draw Date"])
    except:
        fallback_path = "/mnt/data/fallback_draw_data_2025.csv"
        df = pd.read_csv(fallback_path)
        df["Draw Date"] = pd.to_datetime(df["Draw Date"])
    return df

df = load_data()

# Sidebar filter by year
st.sidebar.markdown("### 📅 Filter by Year")
df["Year"] = df["Draw Date"].dt.year
years = sorted(df["Year"].unique(), reverse=True)
selected_years = st.sidebar.multiselect("Select years to include:", years, default=years)
filtered = df[df["Year"].isin(selected_years)]

# Charts
st.markdown("## 📈 Total Invitations by Year")
yearly = filtered.groupby(filtered["Draw Date"].dt.year)["ITAs Issued"].sum().reset_index(name="ITAs Issued")
bar = alt.Chart(yearly).mark_bar().encode(
    x=alt.X("Draw Date:O", title="Year"),
    y=alt.Y("ITAs Issued:Q"),
    tooltip=["Draw Date", "ITAs Issued"]
)
labels = alt.Chart(yearly).mark_text(dy=-5).encode(
    x="Draw Date:O", y="ITAs Issued:Q", text="ITAs Issued:Q"
)
st.altair_chart(alt.layer(bar, labels), use_container_width=True)

st.markdown("## 📉 Total Invitations by Quarter")
quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
st.dataframe(quarterly, use_container_width=True)
chart_q = alt.Chart(quarterly).mark_bar().encode(
    x=alt.X("Quarter:O"), y="ITAs Issued:Q", tooltip=["Quarter", "ITAs Issued"]
)
labels_q = alt.Chart(quarterly).mark_text(dy=-5).encode(
    x="Quarter:O", y="ITAs Issued:Q", text="ITAs Issued:Q"
)
st.altair_chart(alt.layer(chart_q, labels_q), use_container_width=True)

# Filtered Draw History
st.markdown("## 🧾 Filtered Draw History")
export_df = filtered[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]].copy()
export_df = export_df.sort_values(by="Draw #", ascending=False)
st.dataframe(export_df, use_container_width=True)

# Download buttons
col_csv, col_xlsx, _ = st.columns([1, 1, 8])
with col_csv:
    csv = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("📄 CSV", data=csv, file_name="draw_history.csv", mime="text/csv")

with col_xlsx:
    try:
        import xlsxwriter
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            export_df.to_excel(writer, index=False, sheet_name="DrawHistory")
        st.download_button("📊 Excel", data=buffer.getvalue(), file_name="draw_history.xlsx",
                           mime="application/vnd.ms-excel")
    except ImportError:
        st.warning("xlsxwriter not available for Excel export.")

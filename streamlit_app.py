
import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

# Load data
df = pd.read_csv("draw_history.csv")

# Convert and sort date
df["Draw Date"] = pd.to_datetime(df["Draw Date"])
df.sort_values("Draw Date", ascending=False, inplace=True)

# Sidebar filters
st.sidebar.header("Filter Options")
min_date, max_date = df["Draw Date"].min(), df["Draw Date"].max()
date_range = st.sidebar.date_input("Select Draw Date Range", [min_date, max_date])
filtered = df[(df["Draw Date"] >= pd.to_datetime(date_range[0])) & (df["Draw Date"] <= pd.to_datetime(date_range[1]))]

# Charts
st.markdown("### 📅 Total Invitations by Year")
yearly = filtered.groupby(filtered["Draw Date"].dt.year)["Invitations issued"].sum().reset_index(name="ITAs Issued")
year_chart = alt.Chart(yearly).mark_bar().encode(x="Draw Date:O", y="ITAs Issued:Q")
st.altair_chart(year_chart, use_container_width=True)

st.markdown("### 📅 Total Invitations by Quarter")
filtered["Quarter"] = filtered["Draw Date"].dt.to_period("Q").astype(str)
quarterly = filtered.groupby("Quarter")["Invitations issued"].sum().reset_index(name="ITAs Issued")
quarter_chart = alt.Chart(quarterly).mark_bar().encode(x="Quarter:O", y="ITAs Issued:Q")
st.altair_chart(quarter_chart, use_container_width=True)

# Filtered Draw History
st.markdown("### 🧾 Filtered Draw History")
display_df = filtered[["Draw #", "Draw Date", "Round type", "Invitations issued", "CRS score of lowest-ranked candidate invited"]].copy()
display_df.rename(columns={
    "Draw #": "Draw #",
    "Draw Date": "Draw Date",
    "Round type": "Category",
    "Invitations issued": "ITAs Issued",
    "CRS score of lowest-ranked candidate invited": "CRS Score"
}, inplace=True)
display_df["Draw Date"] = display_df["Draw Date"].dt.strftime("%b %d, %Y")

st.dataframe(display_df, use_container_width=True)

# Export buttons aligned right
col1, col2 = st.columns([8, 1])
with col2:
    col_csv, col_excel = st.columns(2)
    with col_csv:
        csv = display_df.to_csv(index=False).encode("utf-8")
        st.download_button("📄 CSV", data=csv, file_name="draw_history.csv", mime="text/csv")
    with col_excel:
        try:
            import xlsxwriter
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                display_df.to_excel(writer, index=False, sheet_name="DrawHistory")
            st.download_button("📊 Excel", data=buffer.getvalue(), file_name="draw_history.xlsx",
                               mime="application/vnd.ms-excel")
        except ImportError:
            st.error("xlsxwriter is not installed.")

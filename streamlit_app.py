import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

# Load the CSV
csv_file = "fallback_draw_data_2025.csv"

try:
    df = pd.read_csv(csv_file)
except FileNotFoundError:
    st.error(f"CSV file '{csv_file}' not found.")
    st.stop()

# Validate required columns
required_cols = ["Draw Date", "Category", "Invitations issued", "CRS score of lowest-ranked candidate invited"]
if not all(col in df.columns for col in required_cols):
    st.error("CSV missing one or more required columns.")
    st.stop()

# Rename columns for internal consistency
df.rename(columns={
    "Invitations issued": "ITAs Issued",
    "CRS score of lowest-ranked candidate invited": "CRS Score"
}, inplace=True)

# Convert Draw Date to datetime
df["Draw Date"] = pd.to_datetime(df["Draw Date"], errors="coerce")
df = df.dropna(subset=["Draw Date"])

filtered = df.copy()

st.title("📜 Filtered Draw History")

# Summary Bar Charts
col1, col2 = st.columns(2)

with col1:
    yearly = filtered.groupby(filtered["Draw Date"].dt.year)["ITAs Issued"].sum().reset_index()
    st.markdown("### 📅 Total Invitations by Year")
    st.dataframe(yearly, use_container_width=True)

    chart = alt.Chart(yearly).mark_bar().encode(
        x=alt.X("Draw Date:O", title="Year"),
        y=alt.Y("ITAs Issued:Q")
    )
    st.altair_chart(chart, use_container_width=True)

with col2:
    quarterly = filtered.groupby(filtered["Draw Date"].dt.to_period("Q"))["ITAs Issued"].sum().reset_index()
    quarterly["Quarter"] = quarterly["Draw Date"].astype(str)
    st.markdown("### 📊 Total Invitations by Quarter")
    st.dataframe(quarterly[["Quarter", "ITAs Issued"]], use_container_width=True)

    chart_q = alt.Chart(quarterly).mark_bar().encode(
        x=alt.X("Quarter:O"),
        y=alt.Y("ITAs Issued:Q")
    )
    st.altair_chart(chart_q, use_container_width=True)

# Table Display
st.markdown("### 📋 Filtered Draw History")
display_df = filtered[["Draw Date", "Category", "ITAs Issued", "CRS Score"]].copy()
display_df["Draw Date"] = display_df["Draw Date"].dt.strftime("%b %d, %Y")

# Add draw number from original index
start_num = 355  # Adjust this based on your dataset
display_df.insert(0, "Draw #", [f"#{start_num - i}" for i in range(len(display_df))])

st.dataframe(display_df, use_container_width=True)

# Export Buttons
col_csv, col_xlsx, _ = st.columns([1, 1, 8])

with col_csv:
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("📄 CSV", data=csv, file_name="draw_history.csv", mime="text/csv")

with col_xlsx:
    try:
        import xlsxwriter
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            display_df.to_excel(writer, index=False, sheet_name="DrawHistory")
            writer.close()
        st.download_button("📊 Excel", data=buffer.getvalue(), file_name="draw_history.xlsx", mime="application/vnd.ms-excel")
    except ImportError:
        st.warning("Install `xlsxwriter` to enable Excel export.")

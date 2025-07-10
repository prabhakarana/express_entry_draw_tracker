
import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

# Set page config
st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

# Load Data
CSV_FILE = "fallback_draw_data_2025.csv"

try:
    df = pd.read_csv(CSV_FILE)
    df["Draw Date"] = pd.to_datetime(df["Draw Date"], errors='coerce')
except Exception as e:
    st.error("CSV missing one or more required columns or file not found.")
    st.stop()

required_columns = {"Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score", "Quarter"}
if not required_columns.issubset(df.columns):
    st.error("CSV missing one or more required columns.")
    st.stop()

# Yearly Summary
yearly = df.groupby(df["Draw Date"].dt.year)["ITAs Issued"].sum().reset_index(name="ITAs Issued")

st.markdown("### 📊 Total Invitations by Year")
chart = alt.Chart(yearly).mark_bar().encode(
    x="Draw Date:O",
    y="ITAs Issued:Q",
    tooltip=["Draw Date", "ITAs Issued"]
)
st.altair_chart(chart, use_container_width=True)

# Quarterly Summary
quarterly = df.groupby("Quarter")["ITAs Issued"].sum().reset_index()
st.markdown("### 📈 Total Invitations by Quarter")
st.dataframe(quarterly, use_container_width=True)
chart_q = alt.Chart(quarterly).mark_bar().encode(
    x=alt.X("Quarter:O"),
    y="ITAs Issued:Q",
    tooltip=["Quarter", "ITAs Issued"]
)
st.altair_chart(chart_q, use_container_width=True)

# Filtered Table
st.markdown("### 📜 Filtered Draw History")
export_df = df[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]].sort_values(by="Draw Date", ascending=False)
export_df["Draw Date"] = pd.to_datetime(export_df["Draw Date"], errors='coerce').dt.strftime('%b %d, %Y')

# Reorder and reset index
export_df.set_index("Draw #", inplace=True)
export_df.index.name = "Draw #"
st.dataframe(export_df, use_container_width=True)

# Export Buttons
col1, col2 = st.columns([8, 1])
with col2:
    col_csv, col_xlsx = st.columns(2)
    with col_csv:
        csv = export_df.to_csv().encode("utf-8")
        st.download_button("📄 CSV", data=csv, file_name="draw_history.csv", mime="text/csv")
    with col_xlsx:
        try:
            import xlsxwriter
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                export_df.to_excel(writer, sheet_name="DrawHistory")
                writer.save()
            st.download_button("📘 Excel", data=buffer.getvalue(), file_name="draw_history.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except ImportError:
            st.warning("xlsxwriter is not installed.")

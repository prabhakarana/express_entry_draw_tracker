
import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

# Load data
try:
    df = pd.read_csv("fallback_draw_data_2025.csv")
    expected_columns = {"Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"}
    if not expected_columns.issubset(set(df.columns)):
        st.error("CSV missing one or more required columns.")
        st.stop()

    df["Draw Date"] = pd.to_datetime(df["Draw Date"], errors='coerce')
    df = df.dropna(subset=["Draw Date"])
except Exception as e:
    st.error(f"Failed to load CSV: {e}")
    st.stop()

# Sidebar filters
st.sidebar.header("Filter by Category")
selected_categories = st.sidebar.multiselect("Choose draw categories:", df["Category"].unique(), default=df["Category"].unique())

filtered = df[df["Category"].isin(selected_categories)].copy()

# Yearly bar chart
st.markdown("## 📊 Total Invitations by Year")
yearly = filtered.groupby(filtered["Draw Date"].dt.year)["ITAs Issued"].sum().reset_index(name="ITAs Issued")
chart = alt.Chart(yearly).mark_bar().encode(
    x="Draw Date:O",
    y="ITAs Issued:Q",
    tooltip=["Draw Date", "ITAs Issued"]
)
st.altair_chart(chart, use_container_width=True)

# Quarterly chart
st.markdown("## 📈 Total Invitations by Quarter")
filtered["Quarter"] = filtered["Draw Date"].dt.to_period("Q").astype(str)
quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
st.dataframe(quarterly, use_container_width=True)

chart_q = alt.Chart(quarterly).mark_bar().encode(
    x=alt.X("Quarter:O", sort=None),
    y="ITAs Issued:Q",
    tooltip=["Quarter", "ITAs Issued"]
)
st.altair_chart(chart_q, use_container_width=True)

# Draw History Section
st.markdown("## 🧾 Filtered Draw History")
export_df = filtered[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]].sort_values(by="Draw Date", ascending=False)
export_df["Draw Date"] = export_df["Draw Date"].dt.strftime("%b %d, %Y")

st.dataframe(export_df, use_container_width=True)

# Export Buttons
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
        st.download_button("📊 Excel", data=buffer.getvalue(), file_name="draw_history.xlsx", mime="application/vnd.ms-excel")
    except Exception as e:
        st.error(f"Excel export failed: {e}")

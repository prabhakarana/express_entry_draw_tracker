
import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

st.set_page_config(layout="wide", page_title="Express Entry Draw Tracker")

st.markdown("<h1 style='font-size: 36px;'>📊 Total Invitations by Year</h1>", unsafe_allow_html=True)

# Load CSV
csv_file = "fallback_draw_data_2025.csv"
try:
    df = pd.read_csv(csv_file)

    # Validate required columns
    required_cols = {"Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score", "Quarter"}
    if not required_cols.issubset(df.columns):
        st.error("CSV missing one or more required columns.")
        st.stop()

    # Parse Draw Date
    df["Draw Date"] = pd.to_datetime(df["Draw Date"], errors="coerce")
    df = df.dropna(subset=["Draw Date"])

    # Filter Section
    years = df["Draw Date"].dt.year.sort_values().unique().tolist()
    selected_years = st.sidebar.multiselect(
        "Choose draw years:",
        options=years,
        default=years,
        key="year_filter"
    )

    filtered = df[df["Draw Date"].dt.year.isin(selected_years)]

    # Total Invitations by Year
    yearly = (
        filtered.groupby(filtered["Draw Date"].dt.year)["ITAs Issued"]
        .sum()
        .reset_index(name="ITAs Issued")
        .rename(columns={"Draw Date": "Year"})
    )
    chart_y = (
        alt.Chart(yearly)
        .mark_bar()
        .encode(x=alt.X("Year:O"), y="ITAs Issued", tooltip=["Year", "ITAs Issued"])
    )
    labels_y = chart_y.mark_text(dy=-5).encode(text="ITAs Issued")
    st.altair_chart(chart_y + labels_y, use_container_width=True)

    # Total Invitations by Quarter
    st.markdown("<h1 style='font-size: 28px;'>📈 Total Invitations by Quarter</h1>", unsafe_allow_html=True)
    quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
    st.dataframe(quarterly, use_container_width=True)
    chart_q = (
        alt.Chart(quarterly)
        .mark_bar()
        .encode(x=alt.X("Quarter:O"), y="ITAs Issued", tooltip=["Quarter", "ITAs Issued"])
    )
    labels_q = chart_q.mark_text(dy=-5).encode(text="ITAs Issued")
    st.altair_chart(chart_q + labels_q, use_container_width=True)

    # Filtered Draw History
    st.markdown("<h1 style='font-size: 28px;'>📜 Filtered Draw History</h1>", unsafe_allow_html=True)

    export_df = filtered[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]].copy()
    export_df["Draw Date"] = pd.to_datetime(export_df["Draw Date"], errors="coerce").dt.strftime("%b %d, %Y")
    export_df = export_df.sort_values("Draw Date", ascending=False).reset_index(drop=True)

    # Display table
    st.dataframe(export_df, use_container_width=True)

    # Download buttons aligned right
    col_spacer, col_csv, col_excel = st.columns([6, 1, 1])
    with col_csv:
        csv_data = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("🗂️ CSV", data=csv_data, file_name="draw_history.csv", mime="text/csv")
    with col_excel:
        try:
            import xlsxwriter
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                export_df.to_excel(writer, index=False, sheet_name="DrawHistory")
                writer.close()
            st.download_button("📁 Excel", data=buffer.getvalue(), file_name="draw_history.xlsx", mime="application/vnd.ms-excel")
        except Exception as e:
            st.warning("Excel export failed: " + str(e))

except FileNotFoundError:
    st.error(f"CSV file '{csv_file}' not found.")
except Exception as e:
    st.error(f"An unexpected error occurred: {str(e)}")

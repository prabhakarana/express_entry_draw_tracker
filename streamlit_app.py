import streamlit as st
import pandas as pd
import requests
import json
from jsonpath_ng import parse as jsonpath_parse
import matplotlib.pyplot as plt
import os

st.set_page_config(layout="wide")

# --- Sidebar Page Selector ---
page = st.sidebar.selectbox("📂 Select Page", ["Express Entry Draws", "OINP Summary"])

# --- Express Entry Section ---
if page == "Express Entry Draws":
    st.markdown("🍁 **# Express Entry Draw Tracker (Canada)**")
    st.markdown("Live tracking of Express Entry ITAs, CRS scores, and draw types.")

    # JSON URL and fallback
    LIVE_JSON_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
    FALLBACK_FILE = "data/ee_rounds_123_en.json"

    def parse_int_safe(value):
        try:
            return int(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0

    def load_data():
        try:
            res = requests.get(LIVE_JSON_URL, timeout=10)
            res.raise_for_status()
            data = res.json()
            st.success("✅ Live data loaded.")
        except:
            try:
                with open(FALLBACK_FILE, "r") as f:
                    data = json.load(f)
                st.warning("⚠️ Could not fetch live data. Using fallback JSON.")
            except:
                st.error("❌ Failed to load fallback JSON data.")
                return pd.DataFrame()
        
        path_expr = jsonpath_parse("$.rounds[*]")
        draws = [match.value for match in path_expr.find(data)]
        return transform_data(draws)

    def transform_data(draws):
        records = []
        for d in draws:
            try:
                records.append({
                    "Draw #": d.get("drawNumber"),
                    "Draw Date": pd.to_datetime(d.get("drawDate")),
                    "Category": d.get("drawName"),
                    "ITAs Issued": parse_int_safe(d.get("drawSize")),
                    "CRS Score": parse_int_safe(d.get("drawCRS"))
                })
            except:
                continue

        df = pd.DataFrame(records)
        df["Year"] = df["Draw Date"].dt.year
        df["Quarter"] = df["Draw Date"].dt.to_period("Q").astype(str)
        return df.sort_values("Draw Date", ascending=False)

    df = load_data()
    if df.empty:
        st.stop()

    st.sidebar.header("🔍 Filter Options")
    years = sorted(df["Year"].unique(), reverse=True)
    selected_years = st.sidebar.multiselect("Select Year(s)", years, default=years)
    filtered_df = df[df["Year"].isin(selected_years)]

    if filtered_df.empty:
        st.info("No data available for the selected year(s).")
        st.stop()

    st.subheader("📊 Draw Summary by Category")
    summary = (
        filtered_df.groupby("Category")
        .agg(
            Total_ITAs=pd.NamedAgg(column="ITAs Issued", aggfunc="sum"),
            Lowest_CRS=pd.NamedAgg(column="CRS Score", aggfunc="min"),
            Last_Draw=pd.NamedAgg(column="Draw Date", aggfunc="max")
        )
        .reset_index()
        .sort_values("Total_ITAs", ascending=False)
    )
    summary["Last_Draw"] = summary["Last_Draw"].dt.strftime("%b %d, %Y")
    st.dataframe(summary, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📅 Total Invitations by Year")
        year_summary = filtered_df.groupby("Year")["ITAs Issued"].sum().reset_index()
        fig, ax = plt.subplots()
        ax.bar(year_summary["Year"].astype(str), year_summary["ITAs Issued"])
        ax.set_ylabel("ITAs Issued")
        st.pyplot(fig)

    with col2:
        st.subheader("📅 Total Invitations by Quarter")
        quarter_summary = filtered_df.groupby("Quarter")["ITAs Issued"].sum().reset_index()
        fig, ax = plt.subplots()
        ax.bar(quarter_summary["Quarter"], quarter_summary["ITAs Issued"], color="seagreen")
        ax.set_ylabel("ITAs Issued")
        plt.xticks(rotation=45)
        st.pyplot(fig)

    st.subheader("📋 Filtered Draw History")
    st.dataframe(
        filtered_df[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]],
        use_container_width=True
    )

    st.download_button(
        label="📥 Download CSV",
        data=filtered_df.to_csv(index=False),
        file_name="express_entry_draws_filtered.csv",
        mime="text/csv"
    )

# --- OINP Summary Section ---
elif page == "OINP Summary":
    st.markdown("🍁 **# Ontario Immigrant Nominee Program (OINP) Summary**")
    st.caption("Year-wise nomination counts by stream. Source: Ontario.ca")

    try:
        with open("data/oinp_all.json") as f:
            oinp_data = json.load(f)
        df = pd.DataFrame(oinp_data)
    except Exception as e:
        st.error(f"❌ Failed to load OINP data: {e}")
        st.stop()

    years = sorted(df["year"].unique(), reverse=True)
    selected_years = st.sidebar.multiselect("📅 Select Year(s)", years, default=years)

    streams = sorted(df["stream"].unique())
    selected_streams = st.sidebar.multiselect("🧭 Select Stream(s)", streams, default=streams)

    filtered = df[
        df["year"].isin(selected_years) &
        df["stream"].isin(selected_streams)
    ]

    if filtered.empty:
        st.warning("No data to display with current filters.")
        st.stop()

    st.subheader("📋 Nomination Summary")
    st.dataframe(filtered.sort_values(["year", "stream"]), use_container_width=True)

    st.subheader("📊 Total Nominations by Stream")
    chart_df = (
        filtered.groupby("stream")["nominations"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    st.bar_chart(chart_df.set_index("stream"))

    st.subheader("📈 Top Streams Over Time")
    top_streams = chart_df.head(5)["stream"].tolist()
    trend_df = (
        filtered[filtered["stream"].isin(top_streams)]
        .groupby(["year", "stream"])["nominations"]
        .sum()
        .reset_index()
        .pivot(index="year", columns="stream", values="nominations")
    )
    st.line_chart(trend_df)

    st.download_button(
        label="📥 Download Filtered Data (CSV)",
        data=filtered.to_csv(index=False),
        file_name="oinp_filtered_data.csv",
        mime="text/csv"
    )

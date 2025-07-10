# streamlit_app.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import altair as alt
from io import BytesIO

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

dark_mode = st.sidebar.checkbox("🌙 Enable Dark Mode", value=False)
if dark_mode:
    st.markdown("<style>body { background-color: #111; color: #eee; }</style>", unsafe_allow_html=True)

st.title("🍁 Canada Express Entry Draw Tracker (Live + Fallback)")
st.markdown("Real-time ITA history by category, CRS, and draw date. Falls back to 2025 data if Canada.ca is unreachable.")

@st.cache_data(ttl=3600)
def fetch_draws():
    base_url = "https://www.canada.ca"
    url = base_url + "/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = [base_url + a["href"] for a in soup.select("a[href*='rounds-invitations']") if "date" in a["href"]]
        draws = []
        for link in links:
            r = requests.get(link, headers=headers, timeout=10)
            s = BeautifulSoup(r.text, "html.parser")
            title = s.find("h1").text.strip()
            date = title.split(":")[0].strip()
            paras = s.find_all("p")
            category = next((p.text for p in paras if "round of invitations" in p.text.lower()), "Unknown")
            crs = next((p.text for p in paras if "lowest-ranked candidate invited" in p.text.lower()), "")
            itas = next((p.text for p in paras if "invitations to apply" in p.text.lower()), "")
            crs_score = next((int(word) for word in crs.split() if word.isdigit()), None)
            invitations = next((int(word.replace(",", "")) for word in itas.split() if word.replace(",", "").isdigit()), None)
            draws.append({
                "Draw Date": pd.to_datetime(date, errors='coerce'),
                "Category": category.strip(),
                "CRS Score": crs_score,
                "ITAs Issued": invitations,
                "URL": link
            })
        return pd.DataFrame(draws).dropna(subset=["Draw Date"])
    except Exception as e:
        st.warning(f"⚠️ Live data unavailable. Using fallback data. Reason: {e}")
        return pd.read_csv("fallback_draw_data_2025.csv", parse_dates=["Draw Date"])

df = fetch_draws()

if df.empty:
    st.error("No draw data available.")
else:
    df["Year"] = df["Draw Date"].dt.year
    df["Quarter"] = df["Draw Date"].dt.to_period("Q").astype(str)

    with st.sidebar:
        st.markdown("### 🔍 Filter Options")
        selected_year = st.multiselect("Filter by Year", sorted(df["Year"].unique()), default=sorted(df["Year"].unique()))
        crs_min, crs_max = int(df["CRS Score"].min()), int(df["CRS Score"].max())
        selected_crs = st.slider("CRS Score Range", crs_min, crs_max, (crs_min, crs_max))

    filtered = df[(df["Year"].isin(selected_year)) & (df["CRS Score"].between(*selected_crs))]

    pivot = filtered.groupby("Category").agg(
        Total_ITAs=("ITAs Issued", "sum"),
        Lowest_CRS=("CRS Score", "min"),
        Last_Draw=("Draw Date", "max")
    ).reset_index().sort_values(by="Total_ITAs", ascending=False)

    pivot["Last_Draw"] = pivot["Last_Draw"].dt.strftime("%B %d, %Y")

    st.markdown("### 🧾 Draw Summary by Category")
    st.dataframe(pivot, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        yearly = filtered.groupby("Year")["ITAs Issued"].sum().reset_index()
        st.markdown("### 📅 Total Invitations by Year")
        st.dataframe(yearly, use_container_width=True)
        chart = alt.Chart(yearly).mark_bar().encode(
            x=alt.X("Year:O"), y="ITAs Issued:Q", tooltip=["Year", "ITAs Issued"]
        )
        labels = alt.Chart(yearly).mark_text(dy=-5).encode(x="Year:O", y="ITAs Issued:Q", text="ITAs Issued:Q")
        st.altair_chart(alt.layer(chart, labels), use_container_width=True)

    with col2:
        quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
        st.markdown("### 📆 Total Invitations by Quarter")
        st.dataframe(quarterly, use_container_width=True)
        chart_q = alt.Chart(quarterly).mark_bar().encode(
            x=alt.X("Quarter:O"), y="ITAs Issued:Q", tooltip=["Quarter", "ITAs Issued"]
        )
        labels_q = alt.Chart(quarterly).mark_text(dy=-5).encode(x="Quarter:O", y="ITAs Issued:Q", text="ITAs Issued:Q")
        st.altair_chart(alt.layer(chart_q, labels_q), use_container_width=True)

    st.markdown("### 📜 Filtered Draw History")
    export_df = filtered[["Draw Date", "Category", "ITAs Issued", "CRS Score"]].sort_values(by="Draw Date", ascending=False)
    export_df["Draw Date"] = pd.to_datetime(export_df["Draw Date"]).dt.strftime("%b %d, %Y")
    export_df.reset_index(drop=True, inplace=True)
    export_df.index = [f"#{len(export_df)-i}" for i in range(len(export_df))]
    export_df.index.name = "Draw #"

    st.dataframe(export_df, use_container_width=True)

    col_csv, col_xlsx, _ = st.columns([1, 1, 8])
    with col_csv:
        csv = export_df.to_csv().encode("utf-8")
        st.download_button("📥 CSV", data=csv, file_name="draw_history.csv", mime="text/csv")

    with col_xlsx:
        try:
            import xlsxwriter
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                export_df.to_excel(writer, index=True, sheet_name="DrawHistory")
                writer.save()
            st.download_button("📥 Excel", data=buffer.getvalue(), file_name="draw_history.xlsx", mime="application/vnd.ms-excel")
        except ImportError:
            st.warning("Install `xlsxwriter` to enable Excel export.")

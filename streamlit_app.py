
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import altair as alt
from io import BytesIO
import base64

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide", initial_sidebar_state="expanded")

# Load theme toggle
dark_mode = st.sidebar.checkbox("🌙 Enable Dark Mode", value=False)
if dark_mode:
    st.markdown("<style>body { background-color: #111; color: #eee; }</style>", unsafe_allow_html=True)

st.title("🍁 Canada Express Entry Draw Tracker (Live + Fallback)")
st.markdown("Real-time ITA history by category, CRS, and draw date. Falls back to 2025 data if Canada.ca is unreachable.")

@st.cache_data(ttl=3600)
def fetch_draws():
    base_url = "https://www.canada.ca"
    main_url = base_url + "/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations.html"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(main_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = [
            base_url + a["href"]
            for a in soup.select("a[href*='rounds-invitations']") if "date" in a["href"]
        ]
        draws = []
        for link in links:
            r = requests.get(link, headers=headers, timeout=10)
            s = BeautifulSoup(r.text, "html.parser")
            title = s.find("h1").text.strip()
            paras = s.find_all("p")
            date = title.split(":")[0].strip()
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
        df = pd.DataFrame(draws)
        return df.dropna(subset=["Draw Date"])
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
        selected_year = st.multiselect("Filter by Year", options=sorted(df["Year"].unique()), default=sorted(df["Year"].unique()))
        crs_min, crs_max = int(df["CRS Score"].min()), int(df["CRS Score"].max())
        selected_crs = st.slider("CRS Score Range", min_value=crs_min, max_value=crs_max, value=(crs_min, crs_max))

    filtered = df[(df["Year"].isin(selected_year)) & (df["CRS Score"].between(*selected_crs))]

    pivot = filtered.groupby("Category").agg(
        Total_ITAs=pd.NamedAgg(column="ITAs Issued", aggfunc="sum"),
        Lowest_CRS=pd.NamedAgg(column="CRS Score", aggfunc="min"),
        Last_Draw=pd.NamedAgg(column="Draw Date", aggfunc="max")
    ).sort_values("Total_ITAs", ascending=False).reset_index()
    pivot["Last_Draw"] = pivot["Last_Draw"].dt.strftime("%B %d, %Y")
    filtered["Draw Date"] = pd.to_datetime(filtered["Draw Date"]).dt.strftime("%B %d, %Y")

    st.markdown("### 🧾 Draw Summary by Category")
    st.dataframe(pivot, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        yearly = filtered.groupby("Year")["ITAs Issued"].sum().reset_index()
        st.markdown("### 📅 Total Invitations by Year")
        st.dataframe(yearly, use_container_width=True)

        bar = alt.Chart(yearly).mark_bar(color="#1E88E5").encode(
            x="Year:O", y="ITAs Issued:Q", tooltip=["Year", "ITAs Issued"]
        )
        label = alt.Chart(yearly).mark_text(dy=-5, fontSize=12).encode(
            x="Year:O", y="ITAs Issued:Q", text="ITAs Issued:Q"
        )
        st.altair_chart(alt.layer(bar, label), use_container_width=True)

    with col2:
        quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
        st.markdown("### 📆 Total Invitations by Quarter")
        st.dataframe(quarterly, use_container_width=True)

        bar_q = alt.Chart(quarterly).mark_bar(color="#43A047").encode(
            x="Quarter:O", y="ITAs Issued:Q", tooltip=["Quarter", "ITAs Issued"]
        )
        label_q = alt.Chart(quarterly).mark_text(dy=-5, fontSize=12).encode(
            x="Quarter:O", y="ITAs Issued:Q", text="ITAs Issued:Q"
        )
        st.altair_chart(alt.layer(bar_q, label_q), use_container_width=True)

    st.markdown("### ⬇️ Export Draw History")
    export_df = filtered[["Draw Date", "Category", "ITAs Issued", "CRS Score"]].sort_values(by="Draw Date", ascending=False)

    def convert_df(df):
        return df.to_csv(index=False).encode("utf-8")

    csv = convert_df(export_df)
    st.download_button("📥 Download CSV", data=csv, file_name="draw_history.csv", mime="text/csv")

    try:
        import xlsxwriter
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            export_df.to_excel(writer, index=False, sheet_name="DrawHistory")
        st.download_button("📥 Download Excel", data=buffer.getvalue(), file_name="draw_history.xlsx", mime="application/vnd.ms-excel")
    except ImportError:
        st.warning("Install xlsxwriter to enable Excel export.")

    st.markdown("### 📜 Filtered Draw History")
    st.dataframe(export_df, use_container_width=True)

    st.info("📧 Email alert and auto-summary features require external backend setup (e.g., via GitHub Actions, Zapier, or AWS Lambda).")

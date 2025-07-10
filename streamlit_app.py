import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import altair as alt
from io import BytesIO

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

# Dark mode toggle
dark_mode = st.sidebar.checkbox("🌙 Enable Dark Mode", value=False)
if dark_mode:
    st.markdown("<style>body { background-color: #111; color: #eee; }</style>", unsafe_allow_html=True)

st.title("Canada Express Entry Draw Tracker")
st.markdown("Real-time ITA history by category, CRS, and draw date. Falls back to local 2025 data if live fetch fails.")

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
        st.markdown("### Filter Options")
        selected_year = st.multiselect("Filter by Year", options=sorted(df["Year"].unique()), default=sorted(df["Year"].unique()))
        crs_min, crs_max = int(df["CRS Score"].min()), int(df["CRS Score"].max())
        selected_crs = st.slider("CRS Score Range", min_value=crs_min, max_value=crs_max, value=(crs_min, crs_max))

    filtered = df[(df["Year"].isin(selected_year)) & (df["CRS Score"].between(*selected_crs))]

    pivot = filtered.groupby("Category").agg(
        Total_ITAs=pd.NamedAgg(column="ITAs Issued", aggfunc="sum"),
        Lowest_CRS=pd.NamedAgg(column="CRS Score", aggfunc="min"),
        Last_Draw=pd.NamedAgg(column="Draw Date", aggfunc="max")
    ).sort_values("Total_ITAs", ascending=False).reset_index()
    pivot["Last_Draw"] = pivot["Last_Draw"].dt.strftime("%b %d, %Y")

    st.markdown("## 🧾 Draw Summary by Category")
    st.dataframe(pivot, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        yearly = filtered.groupby("Year")["ITAs Issued"].sum().reset_index()
        st.markdown("## 📅 Total Invitations by Year")
        chart = alt.Chart(yearly).mark_bar(size=40).encode(
            x=alt.X("Year:O", title="Year"),
            y=alt.Y("ITAs Issued:Q", title="Invitations"),
            tooltip=["Year", "ITAs Issued"]
        )
        labels = chart.mark_text(
            align='center', dy=-10, size=12
        ).encode(text="ITAs Issued:Q")
        st.altair_chart(chart + labels, use_container_width=True)

    with col2:
        quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
        st.markdown("## 📆 Total Invitations by Quarter")
        chart_q = alt.Chart(quarterly).mark_bar(size=35).encode(
            x=alt.X("Quarter:O", title="Quarter"),
            y=alt.Y("ITAs Issued:Q", title="Invitations"),
            tooltip=["Quarter", "ITAs Issued"]
        )
        labels_q = chart_q.mark_text(
            align='center', dy=-10, size=12
        ).encode(text="ITAs Issued:Q")
        st.altair_chart(chart_q + labels_q, use_container_width=True)

    export_df = filtered[["Draw Date", "Category", "ITAs Issued", "CRS Score"]].sort_values(by="Draw Date", ascending=False)

    st.markdown("## 📜 Filtered Draw History")
    st.dataframe(export_df, use_container_width=True)

    # Right-aligned buttons
    col1, col2, spacer, spacer2, btn1, btn2 = st.columns([0.5, 0.5, 2, 2, 1, 1])
    with btn1:
        csv = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 CSV", data=csv, file_name="draw_history.csv", mime="text/csv")

    with btn2:
        try:
            import xlsxwriter
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                export_df.to_excel(writer, index=False, sheet_name="DrawHistory")
            st.download_button("📥 Excel", data=buffer.getvalue(), file_name="draw_history.xlsx", mime="application/vnd.ms-excel")
        except ImportError:
            st.warning("Install `xlsxwriter` to enable Excel export.")

    st.info("📧 Email alerts run automatically on weekdays at 8am and 6pm EST using GitHub Actions.")

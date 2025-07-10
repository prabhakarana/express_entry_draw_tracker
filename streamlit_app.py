import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import altair as alt
from io import BytesIO
import base64

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide", initial_sidebar_state="expanded")

# Dark mode toggle
dark_mode = st.sidebar.checkbox("🌙 Enable Dark Mode", value=False)
if dark_mode:
    st.markdown("<style>body { background-color: #111; color: #eee; }</style>", unsafe_allow_html=True)

st.title("🍁 Canada Express Entry Draw Tracker (Live + Fallback)")
st.markdown("Tracks real-time ITA history by CRS, category & quarter. Falls back to offline data if live source fails.")

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
        st.warning(f"⚠️ Live data unavailable. Using fallback. Reason: {e}")
        return pd.read_csv("fallback_draw_data_2025.csv", parse_dates=["Draw Date"])

df = fetch_draws()

if df.empty:
    st.error("No draw data available.")
else:
    df["Year"] = df["Draw Date"].dt.year
    df["Quarter"] = df["Draw Date"].dt.to_period("Q").astype(str)
    df["Draw Date"] = df["Draw Date"].dt.strftime("%b %d, %Y")

    # Filters
    with st.sidebar:
        st.markdown("### 🔍 Filter Options")
        selected_years = st.multiselect("Filter by Year", options=sorted(df["Year"].unique()), default=sorted(df["Year"].unique()))
        crs_min, crs_max = int(df["CRS Score"].min()), int(df["CRS Score"].max())
        selected_crs = st.slider("CRS Score Range", crs_min, crs_max, (crs_min, crs_max))

    # Filter data
    filtered = df[(df["Year"].isin(selected_years)) & (df["CRS Score"].between(*selected_crs))]

    # Summary by Category
    pivot = filtered.groupby("Category").agg(
        Total_ITAs=pd.NamedAgg(column="ITAs Issued", aggfunc="sum"),
        Lowest_CRS=pd.NamedAgg(column="CRS Score", aggfunc="min"),
        Last_Draw=pd.NamedAgg(column="Draw Date", aggfunc="max")
    ).sort_values("Total_ITAs", ascending=False).reset_index()

    st.markdown("### 🧾 Summary by Category")
    st.dataframe(pivot, use_container_width=True)

    # Yearly Summary
    yearly = filtered.groupby("Year")["ITAs Issued"].sum().reset_index()
    st.markdown("### 📅 Total Invitations by Year")
    st.dataframe(yearly, use_container_width=True)
    bar1 = alt.Chart(yearly).mark_bar().encode(
        x=alt.X("Year:O", sort=None),
        y="ITAs Issued:Q",
        tooltip=["Year", "ITAs Issued"]
    ).properties(height=300)
    text1 = bar1.mark_text(dy=-10, size=12).encode(text="ITAs Issued:Q")
    st.altair_chart(bar1 + text1, use_container_width=True)

    # Quarterly Summary
    quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
    quarterly = quarterly.sort_values("Quarter")
    st.markdown("### 📆 Total Invitations by Quarter")
    st.dataframe(quarterly, use_container_width=True)
    bar2 = alt.Chart(quarterly).mark_bar(color="green").encode(
        x=alt.X("Quarter:O", sort=["Q1", "Q2", "Q3", "Q4"]),
        y="ITAs Issued:Q",
        tooltip=["Quarter", "ITAs Issued"]
    ).properties(height=300)
    text2 = bar2.mark_text(dy=-10, size=12).encode(text="ITAs Issued:Q")
    st.altair_chart(bar2 + text2, use_container_width=True)

    # Export Buttons
    st.markdown("### ⬇️ Export Filtered Draws")
    export_df = filtered[["Draw Date", "Category", "ITAs Issued", "CRS Score"]].sort_values(by="Draw Date", ascending=False)

    def convert_df(df): return df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download CSV", convert_df(export_df), "draw_history.csv", "text/csv")

    try:
        import xlsxwriter
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            export_df.to_excel(writer, sheet_name="Draws", index=False)
            writer.save()
        st.download_button("📥 Download Excel", output.getvalue(), "draw_history.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except:
        st.warning("⚠️ Install `xlsxwriter` to enable Excel export.")

    # Final Table
    st.markdown("### 📜 Full Filtered Draw History")
    st.dataframe(export_df, use_container_width=True)

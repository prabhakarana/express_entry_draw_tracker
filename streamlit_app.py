import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

st.title("🍁 Canada Express Entry Draw Tracker (Live)")
st.markdown("Real-time ITA history by category, CRS, and draw date. Data fetched from [Canada.ca](https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations.html)")

@st.cache_data(ttl=3600)
def fetch_draws():
    base_url = "https://www.canada.ca"
    main_url = base_url + "/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/rounds-invitations.html"
    response = requests.get(main_url)
    soup = BeautifulSoup(response.text, "html.parser")

    links = [
        base_url + a["href"]
        for a in soup.select("a[href*='rounds-invitations']") if "date" in a["href"]
    ]

    draws = []
    for link in links:
        try:
            r = requests.get(link)
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
        except Exception as e:
            continue
    return pd.DataFrame(draws)

df = fetch_draws()
if df.empty:
    st.warning("No data found.")
else:
    pivot = df.groupby("Category").agg(
        Total_ITAs=pd.NamedAgg(column="ITAs Issued", aggfunc="sum"),
        Lowest_CRS=pd.NamedAgg(column="CRS Score", aggfunc="min"),
        Last_Draw=pd.NamedAgg(column="Draw Date", aggfunc="max")
    ).sort_values("Total_ITAs", ascending=False).reset_index()

    st.dataframe(pivot)

    st.subheader("📅 Draw History")
    st.dataframe(df.sort_values("Draw Date", ascending=False).reset_index(drop=True))

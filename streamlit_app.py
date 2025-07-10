import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
from datetime import datetime
import os

st.set_page_config(layout="wide")

# URLs
data_url = "https://www.canada.ca/content/dam/ircc/documents/json/express-entry-rounds.json"
fallback_path = "fallback_draw_data_2025.csv"

@st.cache_data
def load_data():
    try:
        df_raw = pd.read_json(data_url)
        rounds = df_raw["rounds"]
        data = []
        for r in rounds:
            row = {
                "Draw #": r.get("drawNumber", ""),
                "Draw Date": pd.to_datetime(r.get("drawDate", ""), errors="coerce"),
                "Category": r.get("drawType", ""),
                "ITAs Issued": int(r.get("drawSize", 0)),
                "CRS Score": int(r.get("drawScore", 0))
            }
            data.append(row)
        df = pd.DataFrame(data)
    except Exception:
        st.warning("Live data not reachable. Loading fallback data.")
        if os.path.exists(fallback_path):
            df = pd.read_csv(fallback_path)
            df["Draw Date"] = pd.to_datetime(df["Draw Date"], errors="coerce")
        else:
            st.error("Fallback file not found. Cannot continue.")
            st.stop()
    return df

# Load and clean
df = load_data()
df = df.dropna(subset=["Draw Date", "ITAs Issued"])
df["Year"] = df["Draw Date"].dt.year
df["Quarter"] = df["Draw Date"].dt.to_period("Q").astype(str)

# Sidebar Filters
st.sidebar.header("📅 Filter by Year")
years = df["Year"].sort_values(ascending=False).unique()
selected_years = st.sidebar.multiselect("Select years to include:", years, default=years[:1])

filtered = df[df["Year"].isin(selected_years)]

# Total Invitations by Year
st.subheader("📊 Total Invitations by Year")
if not filtered.empty:
    yearly = filtered.groupby("Year")["ITAs Issued"].sum().reset_index()
    bar_chart = alt.Chart(yearly).mark_bar().encode(
        x=alt.X("Year:O", title="Year"),
        y=alt.Y("ITAs Issued:Q", title="ITAs Issued"),
        tooltip=["Year", "ITAs Issued"]
    ).properties(width=700, height=400)
    st.altair_chart(bar_chart)
else:
    st.info("No data for selected years.")

# Total Invitations by Quarter
st.subheader("📈 Total Invitations by Quarter")
quarterly = filtered.groupby("Quarter")["ITAs Issued"].sum().reset_index()
st.dataframe(quarterly)

fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(quarterly["Quarter"], quarterly["ITAs Issued"], color="steelblue")
ax.set_xlabel("Quarter")
ax.set_ylabel("ITAs Issued")
ax.set_title("Quarterly Invitations")
plt.xticks(rotation=45)
st.pyplot(fig)

# Draw History Table
st.subheader("📜 Filtered Draw History")
filtered_sorted = filtered.sort_values("Draw #", ascending=False).reset_index(drop=True)
st.dataframe(filtered_sorted[["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]])

# Download as CSV
csv_data = filtered_sorted.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV", data=csv_data, file_name="filtered_draw_history.csv", mime="text/csv")


import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
import os

st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

st.title("🍁 Express Entry Draw Tracker (Canada)")
st.markdown("Live tracking of Express Entry ITAs, CRS scores, and draw types.")

# Load Data
@st.cache_data
def load_data():
    # Try live data
    url = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
    try:
        df = pd.read_json(url)
        st.success("✅ Live data loaded.")
        return df
    except Exception as e:
        st.warning("⚠️ Could not fetch live data. Using fallback file.")

        fallback_file = "ee_rounds_123_en.json"
        if not os.path.exists(fallback_file):
            st.error(f"❌ Fallback file not found: {fallback_file}")
            st.stop()

        try:
            with open(fallback_file, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            df = pd.json_normalize(json_data["Rounds of Invitation"])
            st.success("✅ Fallback JSON file loaded.")
            return df
        except Exception as e:
            st.error(f"❌ Failed to load fallback JSON. Error: {e}")
            st.stop()

df = load_data()

# Data transformation
df["year"] = pd.to_datetime(df["drawDate"]).dt.year
df["quarter"] = pd.to_datetime(df["drawDate"]).dt.to_period("Q").astype(str)
df["drawCRS"] = pd.to_numeric(df["drawCRS"], errors="coerce")
df["drawSize"] = pd.to_numeric(df["drawSize"], errors="coerce")

# Sidebar filters
years = sorted(df["year"].dropna().unique(), reverse=True)
selected_years = st.sidebar.multiselect("📅 Select Year(s)", options=years, default=years)

filtered_df = df[df["year"].isin(selected_years)]

# Summary Table
st.subheader("📊 Summary of ITAs by Category and Year")
summary = (
    filtered_df.groupby(["year", "drawName"])
    .agg({"drawSize": "sum", "drawCRS": "min"})
    .reset_index()
    .rename(columns={"drawSize": "Total ITAs", "drawCRS": "Min CRS"})
)
st.dataframe(summary)

# Draw History Table
st.subheader("📜 Filtered Draw History")
st.dataframe(
    filtered_df[["drawNumber", "drawDate", "drawName", "drawSize", "drawCRS"]]
    .rename(columns={
        "drawNumber": "Draw #",
        "drawDate": "Draw Date",
        "drawName": "Category",
        "drawSize": "ITAs Issued",
        "drawCRS": "CRS Score"
    })
    .sort_values("Draw Date", ascending=False),
    use_container_width=True,
)

# Bar Chart - Total ITAs by Quarter
st.subheader("📈 Total Invitations by Quarter")
quarter_summary = (
    filtered_df.groupby("quarter")["drawSize"].sum().reset_index()
)
fig, ax = plt.subplots()
ax.bar(quarter_summary["quarter"], quarter_summary["drawSize"])
ax.set_xlabel("Quarter")
ax.set_ylabel("Total ITAs")
ax.set_title("Total ITAs by Quarter")
plt.xticks(rotation=45)
st.pyplot(fig)

# Bar Chart - Total ITAs by Year
st.subheader("📊 Total Invitations by Year")
year_summary = (
    filtered_df.groupby("year")["drawSize"].sum().reset_index()
)
fig2, ax2 = plt.subplots()
ax2.bar(year_summary["year"].astype(str), year_summary["drawSize"])
ax2.set_xlabel("Year")
ax2.set_ylabel("ITAs")
ax2.set_title("Total ITAs by Year")
st.pyplot(fig2)

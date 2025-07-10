import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import altair as alt
import json

# Page settings
st.set_page_config(page_title="Express Entry Draw Tracker", layout="wide")

# Title
st.title("🍁 Express Entry Draw Tracker (Canada)")
st.markdown("Live tracking of Express Entry ITAs, CRS scores, and draw types.")

# Load fallback JSON file
fallback_file = "ee_rounds_123_en.json"
try:
    with open(fallback_file, "r") as file:
        json_data = json.load(file)
    st.success("✅ Live data loaded.")
except Exception as e:
    st.error("❌ Failed to load fallback JSON data.")
    st.stop()

# Normalize and preprocess
df = pd.json_normalize(json_data["rounds"])
df['drawDate'] = pd.to_datetime(df['date'])
df['year'] = df['drawDate'].dt.year
df['quarter'] = df['drawDate'].dt.to_period("Q").astype(str)
df['ITAs'] = pd.to_numeric(df['invited'], errors='coerce')
df['CRS'] = pd.to_numeric(df['drawCRS'], errors='coerce')
df['Category'] = df['drawName']

# Sidebar Filters
st.sidebar.header("🔍 Filter Options")
years = st.sidebar.multiselect("Select Year(s)", sorted(df['year'].unique()), default=sorted(df['year'].unique()))
filtered_df = df[df['year'].isin(years)]

# KPI Metrics
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("🧮 Total ITAs", f"{int(filtered_df['ITAs'].sum()):,}")
col2.metric("📅 Total Draws", filtered_df.shape[0])
col3.metric("🏆 Max ITAs", f"{int(filtered_df['ITAs'].max()):,}")
col4.metric("🎯 Lowest CRS", int(filtered_df['CRS'].min()))
col5.metric("🏷️ Top Category", filtered_df['Category'].value_counts().idxmax())

# Draw History Table
st.subheader("📜 Filtered Draw History")
st.dataframe(filtered_df[['drawDate', 'Category', 'ITAs', 'CRS']].sort_values(by="drawDate", ascending=False), use_container_width=True)

# Chart: Total ITAs by Quarter
st.subheader("📈 Total Invitations by Quarter")
quarterly = filtered_df.groupby("quarter")["ITAs"].sum().reset_index()
fig1, ax1 = plt.subplots()
ax1.bar(quarterly['quarter'], quarterly['ITAs'])
ax1.set_xlabel("Quarter")
ax1.set_ylabel("Total ITAs")
ax1.set_title("Total Invitations by Quarter")
plt.xticks(rotation=45)
st.pyplot(fig1)

# Chart: Total ITAs by Year
st.subheader("📊 Total Invitations by Year")
yearly = filtered_df.groupby("year")["ITAs"].sum().reset_index()
fig2, ax2 = plt.subplots()
ax2.bar(yearly['year'].astype(str), yearly['ITAs'])
ax2.set_xlabel("Year")
ax2.set_ylabel("ITAs")
ax2.set_title("Total ITAs by Year")
st.pyplot(fig2)

# Chart: Min CRS by Category
st.subheader("📉 Lowest CRS Score by Category")
min_crs_by_category = filtered_df.groupby("Category")["CRS"].min().reset_index()
fig3, ax3 = plt.subplots()
ax3.barh(min_crs_by_category["Category"], min_crs_by_category["CRS"])
ax3.set_xlabel("CRS Score")
ax3.set_title("Lowest CRS by Category")
st.pyplot(fig3)

# Download button
st.download_button("📥 Download CSV", data=filtered_df.to_csv(index=False), file_name="express_entry_draws.csv")

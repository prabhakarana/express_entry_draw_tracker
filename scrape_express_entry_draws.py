import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL of the Express Entry rounds page
url = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/policies-operational-instructions-agreements/ministerial-instructions/express-entry-rounds.html"

# Fetch the page
response = requests.get(url)
response.raise_for_status()  # Raise error for bad response

# Parse HTML
soup = BeautifulSoup(response.content, "html.parser")

# Find the first table (adjust index if necessary)
tables = soup.find_all("table")
if not tables:
    raise Exception("No table found on the page.")

# Read the HTML table using pandas
df = pd.read_html(str(tables[0]))[0]

# Rename columns for clarity (optional based on real column headers)
df.columns = [col.strip() for col in df.columns]

# Example cleanup if column names are:
# ['Draw number', 'Date', 'Round type', 'Number of invitations issued', 'CRS score of lowest-ranked candidate invited']
rename_map = {
    'Draw number': 'Draw #',
    'Date': 'Draw Date',
    'Round type': 'Category',
    'Number of invitations issued': 'ITAs Issued',
    'CRS score of lowest-ranked candidate invited': 'CRS Score'
}
df.rename(columns=rename_map, inplace=True)

# Clean fields
df["Draw Date"] = pd.to_datetime(df["Draw Date"], errors='coerce')
df["ITAs Issued"] = pd.to_numeric(df["ITAs Issued"].str.replace(",", ""), errors='coerce')
df["CRS Score"] = pd.to_numeric(df["CRS Score"], errors='coerce')

# Drop rows with no date
df = df.dropna(subset=["Draw Date"])

# Save to CSV
df.to_csv("express_entry_draws.csv", index=False)
print("✅ Data saved to express_entry_draws.csv")

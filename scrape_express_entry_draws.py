import requests
from bs4 import BeautifulSoup
import pandas as pd

URL = "https://www.canada.ca/en/immigration-refugees-citizenship/corporate/mandate/policies-operational-instructions-agreements/ministerial-instructions/express-entry-rounds.html"
CSV_FILE = "express_entry_draws.csv"

def scrape_express_entry_table():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    if not table:
        raise ValueError("Draw table not found on the page.")

    rows = table.find_all("tr")
    headers = [th.text.strip() for th in rows[0].find_all("th")]

    data = []
    for row in rows[1:]:
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cols) == len(headers):
            data.append(cols)

    df = pd.DataFrame(data, columns=headers)

    # Rename and clean columns
    df.columns = ["Draw #", "Draw Date", "Category", "ITAs Issued", "CRS Score"]
    df["ITAs Issued"] = df["ITAs Issued"].str.replace(",", "").astype(int)
    df["CRS Score"] = df["CRS Score"].str.extract("(\d+)").astype(float)
    df["Draw #"] = df["Draw #"].str.extract("(\d+)").astype(int)

    df.to_csv(CSV_FILE, index=False)
    print(f"✅ Scraped and saved {len(df)} records to {CSV_FILE}")

if __name__ == "__main__":
    scrape_express_entry_table()

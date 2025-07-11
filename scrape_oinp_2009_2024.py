import os
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup

OUTPUT_FILE = "data/oinp_all.json"
VALID_COLUMNS = ['Stream', 'Number of nominations']
YEAR_RANGE = range(2009, 2025)

def fetch_page(year):
    if year == 2009:
        url = "https://www.ontario.ca/page/2009-2014-ontario-immigrant-nominee-program-updates"
    else:
        url = f"https://www.ontario.ca/page/{year}-ontario-immigrant-nominee-program-updates"
    print(f"\nFetching {year}...", end=' ')
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def extract_valid_draws(html, year):
    try:
        dfs = pd.read_html(html)
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

    print(f"✅ Found {len(dfs)} table(s)")
    data = []
    for i, df in enumerate(dfs):
        print(f"⚠️ Table {i} Columns: {list(df.columns)}")
        if list(df.columns) == VALID_COLUMNS:
            print(f"✅ Keeping table {i}")
            for _, row in df.iterrows():
                data.append({
                    "year": year,
                    "stream": row["Stream"],
                    "nominations": int(row["Number of nominations"])
                })
        else:
            print(f"⚠️ Skipping table {i} – doesn't match draw format")
    return data

def load_existing():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

def deduplicate(existing, new_data):
    combined = {f"{d['year']}_{d['stream']}": d for d in existing}
    for item in new_data:
        key = f"{item['year']}_{item['stream']}"
        combined[key] = item
    return list(combined.values())

def main():
    os.makedirs("data", exist_ok=True)
    existing_data = load_existing()
    all_new_data = []

    for year in YEAR_RANGE:
        html = fetch_page(year)
        if not html:
            continue
        year_data = extract_valid_draws(html, year)
        all_new_data.extend(year_data)

    if all_new_data:
        final_data = deduplicate(existing_data, all_new_data)
        save_data(final_data)
        print(f"\n✅ Saved {len(final_data)} total entries to {OUTPUT_FILE}")
    else:
        print("\n❌ No new data to process.")

if __name__ == "__main__":
    main()

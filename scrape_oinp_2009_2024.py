import requests
import pandas as pd
import json
import os
from datetime import datetime
import re

OUTPUT_FILE = "data/oinp_all.json"

def fetch_tables(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        dfs = pd.read_html(res.text)
        print(f"✅ Fetched {len(dfs)} table(s)")
        return dfs
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def clean_stream_name(name):
    name = str(name)
    fixes = {
        "JobOffer": "Job Offer",
        "stream": "",
        "Stream": "",
        "Graduatestream": "Graduate Stream",
        "ExpressEntry": "Express Entry",
        "Entrepreneurstream": "Entrepreneur Stream"
    }
    for k, v in fixes.items():
        name = name.replace(k, v)
    name = re.sub(r'\s+', ' ', name).strip()
    return name.title()

def extract_valid_draws(tbl, year):
    expected_cols = {"Stream", "Number of nominations"}
    if expected_cols.issubset(set(tbl.columns)):
        rows = []
        for _, row in tbl.iterrows():
            try:
                nominations_raw = row["Number of nominations"]
                if pd.isna(nominations_raw):
                    continue
                nominations = int(str(nominations_raw).replace(',', '').strip())
                rows.append({
                    "year": year,
                    "stream": clean_stream_name(row["Stream"]),
                    "nominations": nominations
                })
            except Exception as e:
                print(f"⚠️ Skipping row: {e}")
        return rows
    return []

def main():
    os.makedirs("data", exist_ok=True)
    all_data = []
    seen_keys = set()

    for year in range(2009, 2025):
        print(f"\n📅 Fetching {year}...")
        if year <= 2014:
            url = "https://www.ontario.ca/page/2009-2014-ontario-immigrant-nominee-program-updates"
        else:
            url = f"https://www.ontario.ca/page/{year}-ontario-immigrant-nominee-program-updates"

        dfs = fetch_tables(url)
        for i, df in enumerate(dfs):
            print(f"🔍 Table {i} Columns: {list(df.columns)}")
            rows = extract_valid_draws(df, year)
            for row in rows:
                key = (row["year"], row["stream"])
                if key not in seen_keys:
                    all_data.append(row)
                    seen_keys.add(key)

    if all_data:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(all_data, f, indent=2)
        print(f"\n✅ Saved {len(all_data)} cleaned & deduplicated entries to {OUTPUT_FILE}")
    else:
        print("\n⚠️ No usable data found.")

if __name__ == "__main__":
    main()

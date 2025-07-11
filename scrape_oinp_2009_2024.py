import requests
import pandas as pd
import json
import os
from datetime import datetime

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

def extract_valid_draws(tbl, year):
    expected_cols = {"Stream", "Number of nominations"}
    if expected_cols.issubset(set(tbl.columns)):
        print(f"✅ Keeping table with columns: {list(tbl.columns)}")
        rows = []
        for _, row in tbl.iterrows():
            try:
                nominations_raw = row["Number of nominations"]
                if pd.isna(nominations_raw):
                    continue
                nominations = int(str(nominations_raw).replace(',', '').strip())
                rows.append({
                    "year": year,
                    "stream": str(row["Stream"]).strip(),
                    "nominations": nominations
                })
            except Exception as e:
                print(f"⚠️  Skipping row due to error: {e}")
        return rows
    else:
        print(f"⚠️  Skipping table — doesn't match draw format")
        return []

def load_existing_data(file_path):
    if os.path.exists(file_path):
        with open(file_path) as f:
            return json.load(f)
    return []

def save_data(file_path, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved {len(data)} entries to {file_path}")

def main():
    all_data = load_existing_data("data/oinp_all.json")
    existing_keys = {(entry["year"], entry["stream"]) for entry in all_data}
    new_entries = []

    for year in range(2009, 2025):
        print(f"\n📅 Fetching {year}...")
        if year <= 2014:
            url = "https://www.ontario.ca/page/2009-2014-ontario-immigrant-nominee-program-updates"
        else:
            url = f"https://www.ontario.ca/page/{year}-ontario-immigrant-nominee-program-updates"

        dfs = fetch_tables(url)
        for i, df in enumerate(dfs):
            print(f"🔎 Table {i} Columns: {list(df.columns)}")
            valid_rows = extract_valid_draws(df, year)
            for row in valid_rows:
                key = (row["year"], row["stream"])
                if key not in existing_keys:
                    new_entries.append(row)
                    existing_keys.add(key)

    if new_entries:
        all_data.extend(new_entries)
        save_data("data/oinp_all.json", all_data)
        print(f"✅ Added {len(new_entries)} new entries.")
    else:
        print("⚠️ No new data to process.")

if __name__ == "__main__":
    main()

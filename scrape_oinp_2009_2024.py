import requests
import pandas as pd
import os
import json
from datetime import datetime

OUTPUT_FILE = "data/oinp_all.json"
HISTORICAL_YEARS = list(range(2009, 2025))  # 2009–2024
BASE_URL = "https://www.ontario.ca/page/{}-ontario-immigrant-nominee-program-updates"

def fetch_tables(year):
    url = BASE_URL.format("2009-2014" if year <= 2014 else year)
    print(f"\nFetching {year}... ", end="")

    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        dfs = pd.read_html(res.text)
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

    print(f"✅ Found {len(dfs)} table(s)")
    usable_tables = []

    for idx, df in enumerate(dfs):
        print(f"🔍 Table {idx} Columns: {df.columns.tolist()}")

        cols = [str(c).lower() for c in df.columns]
        if any("stream" in c for c in cols) and any("noi" in c or "invitation" in c for c in cols):
            print(f"✅ Usable table {idx} ✔️")
            df["year"] = year
            usable_tables.append(df)
        else:
            print(f"⚠️ Skipping table {idx} — doesn't match draw format")

    return usable_tables

def normalize_table(df):
    df.columns = [str(c).strip().lower().replace('\n', ' ') for c in df.columns]
    df = df.rename(columns={
        "stream": "stream",
        "draw date": "draw_date",
        "noi": "nois",
        "nois": "nois",
        "invitations": "nois"
    })
    return df[["stream", "draw_date", "nois", "year"]].dropna(how="any")

def deduplicate(existing, new_rows):
    existing_set = set(json.dumps(r, sort_keys=True) for r in existing)
    for row in new_rows:
        row_str = json.dumps(row, sort_keys=True)
        if row_str not in existing_set:
            existing.append(row)
    return existing

def main():
    all_data = []

    # Load existing
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r") as f:
            all_data = json.load(f)

    total_rows_added = 0
    for year in HISTORICAL_YEARS:
        tables = fetch_tables(year)
        if not tables:
            continue

        for tbl in tables:
            try:
                norm = normalize_table(tbl)
                rows = norm.to_dict(orient="records")
                before = len(all_data)
                all_data = deduplicate(all_data, rows)
                added = len(all_data) - before
                total_rows_added += added
                print(f"➕ {added} new rows added")
            except Exception as e:
                print(f"⚠️ Error processing table: {e}")

    if total_rows_added > 0:
        os.makedirs("data", exist_ok=True)
        with open(OUTPUT_FILE, "w") as f:
            json.dump(all_data, f, indent=2)
        print(f"\n✅ Saved {len(all_data)} total unique rows to {OUTPUT_FILE}")
    else:
        print("\n⚠️ No new data to process.")

if __name__ == "__main__":
    main()

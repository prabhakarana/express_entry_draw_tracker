# scrape_oinp_2009_2024.py
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json

def parse_int_safe(value):
    try:
        return int(str(value).replace(",", "").strip())
    except:
        return 0

def fetch_oinp_updates(year):
    url = f"https://www.ontario.ca/page/{year}-ontario-immigrant-nominee-program-updates"
    print(f"Fetching {year}...", end=" ")
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        tables = soup.find_all("table")
        records = []
        for tbl in tables:
            try:
                df_tbl = pd.read_html(str(tbl))[0]
                df_tbl.columns = [c.strip().lower().replace("\n", " ") for c in df_tbl.columns]
                if 'date' in df_tbl.columns and 'stream' in df_tbl.columns:
                    df_tbl['year'] = year
                    records.append(df_tbl)
            except:
                continue
        if records:
            print("✅")
            return pd.concat(records, ignore_index=True)
        else:
            print("⚠️ No usable tables")
    except Exception as e:
        print(f"❌ Error: {e}")
    return pd.DataFrame()

def main():
    os.makedirs("data", exist_ok=True)
    all_years = list(range(2009, 2025))
    all_data = [fetch_oinp_updates(y) for y in all_years]
    df = pd.concat([d for d in all_data if not d.empty], ignore_index=True)

    if df.empty:
        print("\n❌ No data to process.")
        return

    notice_col = df.filter(regex="notice|nominations|nois", axis=1).columns[0]
    df["notices_issued"] = df[notice_col].apply(parse_int_safe)
    df.rename(columns={
        'date': 'Draw Date',
        'stream': 'Stream',
        'crs score range': 'CRS Range',
        'crs range': 'CRS Range'
    }, inplace=True)

    df["Draw Date"] = pd.to_datetime(df["Draw Date"], errors='coerce')
    df["Draw Date"] = df["Draw Date"].dt.strftime("%Y-%m-%d")
    df = df[["Draw Date", "Stream", "notices_issued", "CRS Range", "year"]]

    # Load existing if available
    all_file = "data/oinp_all.json"
    if os.path.exists(all_file):
        with open(all_file, "r") as f:
            existing = json.load(f)
    else:
        existing = []

    existing_keys = {(d["Draw Date"], d["Stream"]) for d in existing}
    new_records = [r for r in df.to_dict(orient="records") if (r["Draw Date"], r["Stream"]) not in existing_keys]
    
    combined = existing + new_records
    combined.sort(key=lambda x: (x["Draw Date"], x["Stream"]))

    with open(all_file, "w") as f:
        json.dump(combined, f, indent=2)

    print(f"\n✅ Appended {len(new_records)} historical record(s) to: {all_file}")

if __name__ == "__main__":
    main()

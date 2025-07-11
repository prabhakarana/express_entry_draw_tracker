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

def fetch_oinp_page(url, label):
    print(f"Fetching {label}...", end=" ")
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
                    df_tbl['year'] = pd.to_datetime(df_tbl['date'], errors='coerce').dt.year.fillna(datetime.now().year).astype(int)
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

def fetch_oinp_updates(year):
    url = f"https://www.ontario.ca/page/{year}-ontario-immigrant-nominee-program-updates"
    return fetch_oinp_page(url, str(year))

def main():
    os.makedirs("data", exist_ok=True)

    # Step 1: Scrape 2009–2014 (hardcoded page)
    df_grouped = fetch_oinp_page(
        "https://www.ontario.ca/page/2009-2014-ontario-immigrant-nominee-program-updates",
        "2009–2014"
    )

    # Step 2: Scrape each year from 2015–2024
    dfs_yearly = [fetch_oinp_updates(y) for y in range(2015, 2025)]

    # Combine all into one DataFrame
    df = pd.concat([df_grouped] + [d for d in dfs_yearly if not d.empty], ignore_index=True)

    if df.empty:
        print("\n❌ No data to process.")
        return

    # Step 3: Normalize column names and data
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

    # Step 4: Append to master file (oinp_all.json) with deduplication
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

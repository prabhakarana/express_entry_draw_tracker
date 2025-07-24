
import requests
import pandas as pd
import json
import os

# JSON URL and fallback
LIVE_JSON_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
FALLBACK_FILE = "data/ee_rounds_123_en.json"
CSV_OUTPUT_FILE = "fallback_draw_data_2025.csv"

# Save a local fallback JSON
def fetch_and_save_json():
    try:
        res = requests.get(LIVE_JSON_URL, timeout=10)
        res.raise_for_status()
        data = res.json()
        with open(FALLBACK_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print("✅ JSON fetched and saved locally.")
        return data.get("rounds", [])
    except Exception as e:
        print(f"⚠️ Failed to fetch live JSON: {e}")
        if os.path.exists(FALLBACK_FILE):
            with open(FALLBACK_FILE, "r") as f:
                return json.load(f).get("rounds", [])
        else:
            print("❌ No fallback available.")
            return []

# Convert JSON rounds to CSV
def save_draws_to_csv(rounds):
    data = []
    for d in rounds:
        try:
            data.append({
                "Draw #": int(str(d.get("drawNumber", "0")).split()[0]),
                "Draw Date": d.get("drawDateFull", d.get("drawDate")),
                "Category": d.get("drawName", "N/A"),
                "ITAs Issued": int(str(d.get("drawSize", "0")).replace(",", "")),
                "CRS Score": int(str(d.get("drawCRS", "0")).replace(",", ""))
            })
        except:
            continue

    df = pd.DataFrame(data)
    df["Draw Date"] = pd.to_datetime(df["Draw Date"])
    df = df.drop_duplicates(subset=["Draw #"], keep="last")
    df = df.sort_values("Draw Date", ascending=False)
    df.to_csv(CSV_OUTPUT_FILE, index=False)
    print(f"✅ Saved {len(df)} draws to {CSV_OUTPUT_FILE}")

if __name__ == "__main__":
    rounds = fetch_and_save_json()
    if rounds:
        save_draws_to_csv(rounds)

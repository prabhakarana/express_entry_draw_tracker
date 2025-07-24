
import requests
import pandas as pd
import re

json_url = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
csv_file = "fallback_draw_data_2025.csv"

def safe_draw_number(raw):
    match = re.search(r"\d+", str(raw))
    return int(match.group()) if match else 0

res = requests.get(json_url)
res.raise_for_status()

rounds = res.json().get("rounds", [])

data = []
for d in rounds:
    data.append({
        "Draw #": safe_draw_number(d.get("drawNumber")),
        "Draw Date": d.get("drawDateFull", d.get("drawDate")),
        "Category": d.get("drawName", "N/A"),
        "ITAs Issued": int(str(d.get("drawSize", "0")).replace(",", "")),
        "CRS Score": int(str(d.get("drawCRS", "0")).replace(",", ""))
    })

df = pd.DataFrame(data)
df["Draw Date"] = pd.to_datetime(df["Draw Date"])
df = df.drop_duplicates(subset=["Draw #"], keep="last")
df = df.sort_values("Draw Date", ascending=False)

df.to_csv(csv_file, index=False)
print(f"✅ Saved {len(df)} draws to {csv_file}")

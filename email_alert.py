
import os
import json
import requests
import pandas as pd
from datetime import datetime
import smtplib
from email.message import EmailMessage

# JSON URL and fallback
LIVE_JSON_URL = "https://www.canada.ca/content/dam/ircc/documents/json/ee_rounds_123_en.json"
FALLBACK_FILE = "data/ee_rounds_123_en.json"
LAST_SENT_FILE = "last_sent.json"

# Load JSON from URL or fallback
def load_json_data():
    try:
        res = requests.get(LIVE_JSON_URL, timeout=10)
        res.raise_for_status()
        data = res.json()
        print("✅ Live JSON loaded.")
    except:
        with open(FALLBACK_FILE, "r") as f:
            data = json.load(f)
        print("⚠️ Using fallback JSON.")
    return data.get("rounds", [])

# Load last sent draw date
def load_last_sent_date():
    if os.path.exists(LAST_SENT_FILE):
        with open(LAST_SENT_FILE, "r") as f:
            last_sent = json.load(f)
        return pd.to_datetime(last_sent.get("last_draw_date", "2000-01-01"))
    return pd.to_datetime("2000-01-01")

# Save latest sent draw date
def update_last_sent_date(latest_date):
    with open(LAST_SENT_FILE, "w") as f:
        json.dump({"last_draw_date": str(latest_date.date())}, f)

# Fetch and transform draw data
draws = load_json_data()
df = pd.DataFrame([{
    "Draw #": int(str(d.get("drawNumber", "0")).split()[0]),
    "Draw Date": d.get("drawDateFull", d.get("drawDate")),
    "Category": d.get("drawName", "N/A"),
    "ITAs Issued": int(str(d.get("drawSize", "0")).replace(",", "")),
    "CRS Score": int(str(d.get("drawCRS", "0")).replace(",", ""))
} for d in draws])

df["Draw Date"] = pd.to_datetime(df["Draw Date"])
df = df.drop_duplicates(subset=["Draw #"], keep="last").sort_values("Draw Date")

# Compare and send alert
last_sent_date = load_last_sent_date()
new_draws = df[df["Draw Date"] > last_sent_date]

if not new_draws.empty or os.getenv("TEST_EMAIL", "false").lower() == "true":
    print(f"📬 {len(new_draws)} new draw(s) detected. Sending email alert...")

    contents = []
    for _, draw in new_draws.iterrows():
        contents.append(
            f"🧾 Category: {draw['Category']}\n"
            f"📅 Date: {draw['Draw Date'].date()}\n"
            f"🎯 CRS: {draw['CRS Score']}\n"
            f"🎟️ ITAs Issued: {draw['ITAs Issued']}\n"
            "-----------------------------\n"
        )

    content = "\n".join(contents) if contents else "This is a test email from Express Entry Draw Tracker."

    subject = f"{len(new_draws)} New Express Entry Draw(s)" if contents else "Test Email – Express Entry Draw Tracker"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = os.getenv("EMAIL_TO")
    msg.set_content(content)

    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.zoho.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASSWORD")

        with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)

        print("✅ Email sent successfully.")
        update_last_sent_date(new_draws["Draw Date"].max() if not new_draws.empty else datetime.today())

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
else:
    print("No new draw found. No email sent.")

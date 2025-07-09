import smtplib
import json
from email.message import EmailMessage
from datetime import datetime
import os

EMAIL_FROM = os.environ["EMAIL_FROM"]
EMAIL_TO = os.environ["EMAIL_TO"]
SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]

with open("fallback_draw_data_2025.csv", "r") as f:
    lines = f.readlines()[1:]
    latest = lines[0].strip().split(",")
    latest_draw = {
        "date": latest[0],
        "category": latest[1],
        "itas": latest[2],
        "crs_score": latest[3]
    }

try:
    with open("last_sent.json", "r") as f:
        last = json.load(f)
except FileNotFoundError:
    last = {}

if latest_draw["date"] != last.get("date"):
    msg = EmailMessage()
    msg["Subject"] = f"🇨🇦 New Express Entry Draw – {latest_draw['date']}"
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.set_content(f"""
New Express Entry Draw Detected!

🗓 Date: {latest_draw['date']}
📦 Category: {latest_draw['category']}
📊 CRS Cutoff: {latest_draw['crs_score']}
📬 ITAs Issued: {latest_draw['itas']}
""")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(msg)

    with open("last_sent.json", "w") as f:
        json.dump(latest_draw, f)
    print("✅ Email sent.")
else:
    print("No new draw.")

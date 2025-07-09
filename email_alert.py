import os
import json
import smtplib
import pandas as pd
from email.message import EmailMessage
from datetime import datetime

# Load fallback data
fallback_file = "fallback_draw_data_2025.csv"
df = pd.read_csv(fallback_file)
df["Draw Date"] = pd.to_datetime(df["Draw Date"])
df.sort_values(by="Draw Date", ascending=False, inplace=True)

# Load last sent info
try:
    with open("last_sent.json", "r") as f:
        last_sent = json.load(f)
    last_draw_date = pd.to_datetime(last_sent["last_draw_date"])
except (FileNotFoundError, KeyError, ValueError):
    last_draw_date = pd.Timestamp.min

# Get latest draw
latest_draw = df.iloc[0]
latest_draw_date = latest_draw["Draw Date"]

# Check for new draw
if latest_draw_date > last_draw_date:
    print("📫 New draw detected. Sending email alert...")

    # Build subject and HTML content
    subject = f"New Express Entry Draw – {latest_draw_date.date()}"
    html_content = (
        f"<h2>📢 New Express Entry Draw – {latest_draw_date.date()}</h2>\n"
        f"<ul>\n"
        f"<li><b>📄 Category:</b> {latest_draw['Category']}</li>\n"
        f"<li><b>📅 Date:</b> {latest_draw['Draw Date'].date()}</li>\n"
        f"<li><b>🎯 CRS:</b> {latest_draw['CRS Score']}</li>\n"
        f"<li><b>🎟️ ITAs Issued:</b> {latest_draw['ITAs Issued']}</li>\n"
        f"</ul>"
    )

    # Build email
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = os.getenv("EMAIL_TO")

    # Plain text fallback
    msg.set_content("New Express Entry Draw detected. Check your email client for the full HTML version.")

    # HTML version
    msg.add_alternative(html_content, subtype="html")

    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.zoho.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASS")

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

        print("✅ Email alert sent.")

        # Update last_sent.json
        with open("last_sent.json", "w") as f:
            json.dump({"last_draw_date": latest_draw_date.strftime("%Y-%m-%d")}, f)

        print("📝 last_sent.json updated.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
else:
    print("✅ No new draw found. No email sent.")

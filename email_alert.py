import os
import json
import pandas as pd
from datetime import datetime
import smtplib
from email.message import EmailMessage

# Paths
csv_path = "fallback_draw_data_2025.csv"
last_sent_path = "last_sent.json"

# Load draw data
df = pd.read_csv(csv_path)
df["Draw Date"] = pd.to_datetime(df["Draw Date"])

# Load last sent record
if os.path.exists(last_sent_path):
    with open(last_sent_path, "r") as f:
        last_sent = json.load(f)
    last_draw_date = pd.to_datetime(last_sent.get("last_draw_date", "2000-01-01"))
else:
    last_draw_date = pd.to_datetime("2000-01-01")

# Get most recent draw
latest_draw = df.sort_values("Draw Date", ascending=False).iloc[0]
latest_draw_date = latest_draw["Draw Date"]

# Check for new draw
if latest_draw_date > last_draw_date or os.getenv("TEST_EMAIL", "false").lower() == "true":
    print("📬 New draw detected. Sending email alert...")

    # Build email content
    subject = f"New Express Entry Draw - {latest_draw['Draw Date'].date()}"
    content = (
        f"🧾 Category: {latest_draw['Category']}\n"
        f"📅 Date: {latest_draw['Draw Date'].date()}\n"
        f"🎯 CRS: {latest_draw['CRS Score']}\n"
        f"🎟️ ITAs Issued: {latest_draw['ITAs Issued']}\n"
    )

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

        # ✅ Secure SSL Connection (Zoho)
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
            smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)

        print("✅ Email sent successfully.")

        # Update last sent record
        with open(last_sent_path, "w") as f:
            json.dump({"last_draw_date": str(latest_draw_date.date())}, f)

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
else:
    print("No new draw found. No email sent.")

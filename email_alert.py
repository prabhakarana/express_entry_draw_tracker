import os
import smtplib
import ssl
from email.mime.text import MIMEText
import pandas as pd
from datetime import datetime

# --- Configuration from GitHub Secrets ---
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT", "465")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
TEST_EMAIL = os.getenv("TEST_EMAIL", "false").lower() == "true"

# --- Load latest draw data ---
csv_path = "fallback_draw_data_2025.csv"  # Adjust path if needed
df = pd.read_csv(csv_path)
df['Draw Date'] = pd.to_datetime(df['Draw Date'])

# --- Identify most recent draw ---
latest_draw = df.sort_values(by="Draw Date", ascending=False).iloc[0]
latest_draw_date = latest_draw['Draw Date'].strftime("%Y-%m-%d")
category = latest_draw['Category']
itas = latest_draw['ITAs Issued']
crs = latest_draw['CRS Score']

# --- Prepare email content ---
subject = f"🧾 Express Entry Draw Update - {latest_draw_date}"
body = (
    f"🗓️ Draw Date: {latest_draw_date}\n"
    f"📋 Category: {category}\n"
    f"🎯 ITAs Issued: {itas}\n"
    f"📊 CRS Score: {crs}\n"
    "\nData Source: canada.ca (via fallback or real-time scraping)\n"
)

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, int(SMTP_PORT), context=context) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        print(f"✅ Email sent: {subject}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- Check for new draw logic (simplified for fallback) ---
today = datetime.utcnow().date()
draw_date = latest_draw['Draw Date'].date()

if TEST_EMAIL:
    print("🧪 TEST_EMAIL=true, sending test alert.")
    send_email("✅ Express Entry Test Email", "This is a test email to verify setup.")
elif (today - draw_date).days <= 1:
    print("📬 New draw detected. Sending email alert...")
    send_email(subject, body)
else:
    print("⏸️ No new draw. Email not sent.")

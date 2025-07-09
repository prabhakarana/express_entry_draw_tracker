
import os
import smtplib
import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import json

# Load fallback data
csv_path = "fallback_draw_data_2025.csv"
df = pd.read_csv(csv_path)
df["Draw Date"] = pd.to_datetime(df["Draw Date"])

# Load last sent draw info
last_sent_file = "last_sent.json"
if os.path.exists(last_sent_file):
    with open(last_sent_file, "r") as f:
        last_sent = json.load(f)
else:
    last_sent = {"last_draw_date": "2000-01-01"}

last_draw_date = pd.to_datetime(last_sent["last_draw_date"])
latest_draw = df[df["Draw Date"] > last_draw_date].sort_values("Draw Date", ascending=False)

if not latest_draw.empty or os.getenv("TEST_EMAIL", "false").lower() == "true":
    print("New draw detected. Sending email alert...")

    # Prepare email
    msg = MIMEMultipart()
    msg["From"] = os.getenv("EMAIL_SENDER")
    msg["To"] = os.getenv("EMAIL_RECEIVER")
    msg["Subject"] = "New Express Entry Draw Alert"

    if latest_draw.empty:
        content = "This is a test email to confirm your alert system works."
    else:
        latest = latest_draw.iloc[0]
        content = f"""
        A new Express Entry draw has been detected!

        Draw Date: {latest['Draw Date'].strftime('%B %d, %Y')}
        Category: {latest['Category']}
        CRS Score: {latest['CRS Score']}
        ITAs Issued: {latest['ITAs Issued']}
        """

    msg.attach(MIMEText(content, "plain"))

    try:
        server = smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT", "587")))
        server.starttls()
        server.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))
        server.send_message(msg)
        server.quit()
        print("Email sent successfully.")

        if not latest_draw.empty:
            # Update last sent record
            with open(last_sent_file, "w") as f:
                json.dump({"last_draw_date": latest["Draw Date"].strftime("%Y-%m-%d")}, f)
    except Exception as e:
        print(f"Failed to send email: {e}")
else:
    print("No new draw found. No email sent.")

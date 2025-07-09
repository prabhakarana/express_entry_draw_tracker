import os
import smtplib
import json
from datetime import datetime
from email.message import EmailMessage

# Load latest draw info
with open("draw_data.json", "r") as f:
    draw_data = json.load(f)

latest_draw = draw_data[0]

# Load last sent info
with open("last_sent.json", "r") as f:
    last_sent = json.load(f)

last_sent_date = datetime.strptime(last_sent["last_draw_date"], "%Y-%m-%d").date()
new_draw_date = datetime.strptime(latest_draw["Draw Date"], "%Y-%m-%d").date()

if new_draw_date > last_sent_date:
    print("📬 New draw detected. Sending email alert...")

    # Subject line — fallback if emoji breaks
    subject = f"New Express Entry Draw – {latest_draw['Draw Date']}"

    # Plain-text fallback
    plain_text = f"""New Express Entry Draw – {latest_draw['Draw Date']}
Category: {latest_draw['Category']}
Date: {latest_draw['Draw Date']}
CRS: {latest_draw['CRS Score']}
ITAs Issued: {latest_draw['ITAs Issued']}
"""

    # HTML version
    html_content = f"""
    <html>
    <body>
    <h2>📣 New Express Entry Draw – {latest_draw['Draw Date']}</h2>
    <ul>
        <li><b>🧾 Category:</b> {latest_draw['Category']}</li>
        <li><b>📅 Date:</b> {latest_draw['Draw Date']}</li>
        <li><b>🎯 CRS:</b> {latest_draw['CRS Score']}</li>
        <li><b>🎟️ ITAs Issued:</b> {latest_draw['ITAs Issued']}</li>
    </ul>
    </body>
    </html>
    """

    # Create email
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = os.getenv("EMAIL_TO")

    msg.set_content(plain_text)
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
            smtp.send_message(msg)
        print("✅ Email sent successfully.")

        # Update the last_sent.json
        with open("last_sent.json", "w") as f:
            json.dump({"last_draw_date": latest_draw["Draw Date"]}, f)
        print("✅ last_sent.json updated.")

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
else:
    print("📭 No new draw found. No email sent.")

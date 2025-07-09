import os
import json
import csv
import smtplib
from datetime import datetime
from email.message import EmailMessage

FALLBACK_CSV = "fallback_draw_data_2025.csv"
LAST_SENT_FILE = "last_sent.json"

# Load latest draw data
def load_draw_data():
    data = []
    if os.path.exists("draw_data.json"):
        with open("draw_data.json", "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ draw_data.json is invalid. Falling back to CSV.")
    if not data:
        with open(FALLBACK_CSV, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["Draw Date"] = datetime.strptime(row["Draw Date"], "%Y-%m-%d")
                data.append(row)
    else:
        for row in data:
            row["Draw Date"] = datetime.strptime(row["Draw Date"], "%Y-%m-%d")
    return data

# Load last sent draw date
def load_last_sent():
    if os.path.exists(LAST_SENT_FILE):
        with open(LAST_SENT_FILE, "r") as f:
            return json.load(f).get("last_draw_date")
    return None

# Save new last sent date
def save_last_sent(date_str):
    with open(LAST_SENT_FILE, "w") as f:
        json.dump({"last_draw_date": date_str}, f)

# Send email
def send_email(draw):
    subject = f"New Express Entry Draw – {draw['Draw Date'].date()}"
    html_content = f"""\
    <html>
        <body>
            <h2>📢 New Express Entry Draw – {draw['Draw Date'].date()}</h2>
            <ul>
                <li><b>🧾 Category:</b> {draw['Category']}</li>
                <li><b>📅 Date:</b> {draw['Draw Date'].date()}</li>
                <li><b>🎯 CRS:</b> {draw['CRS Score']}</li>
                <li><b>🎟️ ITAs Issued:</b> {draw['ITAs Issued']}</li>
            </ul>
        </body>
    </html>
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = os.getenv("EMAIL_TO")
    msg.set_content("This is an HTML email. Please view it in an HTML-compatible client.")
    msg.add_alternative(html_content, subtype="html")

    try:
        with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
            server.send_message(msg)
            print("✅ Email sent successfully.")
            return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# Main execution
draw_data = load_draw_data()
if not draw_data:
    print("⚠️ No draw data found.")
    exit(1)

latest_draw = draw_data[0]
last_sent = load_last_sent()

if str(latest_draw["Draw Date"].date()) != last_sent:
    print("📬 New draw detected. Sending email alert...")
    success = send_email(latest_draw)
    if success:
        save_last_sent(str(latest_draw["Draw Date"].date()))
else:
    print("ℹ️ No new draw. No email sent.")

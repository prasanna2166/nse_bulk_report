import os
import time
import smtplib
import pytz
import requests
import pandas as pd
from datetime import datetime
from io import StringIO
from tabulate import tabulate
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Config ---
WATCHLIST_FILES = {
    "Large Cap": "largecap_watchlist.csv",
    "Small Cap": "smallcap_watchlist.csv",
}

BULK_URL = "https://archives.nseindia.com/content/equities/bulk.csv"
BLOCK_URL = "https://archives.nseindia.com/content/equities/block.csv"

# --- Time Handling ---
IST = pytz.timezone("Asia/Kolkata")
now = datetime.now(IST)
today_str = now.strftime("%d-%b-%Y").upper()
today_human = now.strftime("%Y-%m-%d")

# --- Email Secrets from Environment ---
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO", "").split(",")  # comma-separated list
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_SUBJECT = f"Mutual Fund Deal Tracker Report - {today_human}"

# --- Fetch CSV from NSE using Session ---
def fetch_nse_csv_with_session(url):
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/csv",
        "Referer": "https://www.nseindia.com",
    }

    try:
        with requests.Session() as session:
            session.get("https://www.nseindia.com", headers=headers, timeout=10)
            time.sleep(2)  # simulate browser delay
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return pd.read_csv(StringIO(response.text))
    except requests.exceptions.HTTPError as http_err:
        raise Exception(f"{http_err.response.status_code} Client Error: Forbidden for url: {url}")

# --- Load Watchlist ---
def load_watchlist(file):
    df = pd.read_csv(file)
    return set(df["Symbol"].str.upper())

# --- Process Deal Data ---
def process_deals(deal_type, watchlist_name, watchlist_symbols, url, output):
    try:
        df = fetch_nse_csv_with_session(url)
        df.columns = [col.strip() for col in df.columns]
        df["Date"] = df["Date"].str.strip().str.upper()
        df_today = df[df["Date"] == today_str]

        df_today["Symbol"] = df_today["Symbol"].str.upper()
        df_today["Client Name"] = df_today["Client Name"].astype(str)

        filtered = df_today[
            (df_today["Symbol"].isin(watchlist_symbols)) &
            (df_today["Client Name"].str.contains("mutual fund", case=False))
        ]

        if filtered.empty:
            output.append(f"<p>❌ No mutual fund deals found today in <b>{deal_type}</b> list for <b>{watchlist_name}</b>.</p>")
        else:
            table_html = filtered[[
                "Date",
                "Symbol",
                "Client Name",
                "Buy/Sell",
                "Quantity Traded",
                "Trade Price / Wght. Avg. Price"
            ]].to_html(index=False, border=0, justify="center", classes="styled-table")
            output.append(f"<h3>🎯 {deal_type} Deals — {watchlist_name}</h3>{table_html}")
    except Exception as e:
        output.append(f"<p><b>⚠️ Error fetching or processing {deal_type.lower()} deals for {watchlist_name}:</b> {e}</p>")

# --- Generate HTML Report ---
def generate_html_report():
    output = []
    output.append(f"<h2>📊 Mutual Fund Deal Tracker - {today_human}</h2>")

    for category, file in WATCHLIST_FILES.items():
        symbols = load_watchlist(file)
        output.append(f"<h3>🔍 {category} Watchlist</h3>")

        process_deals("Bulk", category, symbols, BULK_URL, output)
        process_deals("Block", category, symbols, BLOCK_URL, output)

    # Add some basic styling
    style = """
    <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }
    .styled-table {
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 14px;
        min-width: 400px;
        border: 1px solid #ddd;
    }
    .styled-table th, .styled-table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: center;
    }
    .styled-table th {
        background-color: #f2f2f2;
    }
    </style>
    """
    return style + "\n".join(output)

# --- Send Email ---
def send_email(subject, html_body, from_addr, to_addrs, smtp_server, smtp_port, login, password):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)

    part = MIMEText(html_body, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(login, password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"[❌] Failed to send email: {e}")

# --- Main ---
if __name__ == "__main__":
    report_html = generate_html_report()
    # print(report_html)  # Uncomment if you want to debug in console

    send_email(
        EMAIL_SUBJECT,
        report_html,
        EMAIL_FROM,
        EMAIL_TO,
        SMTP_SERVER,
        SMTP_PORT,
        EMAIL_FROM,
        EMAIL_PASSWORD,
    )

import pandas as pd
from datetime import datetime
from tabulate import tabulate
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import requests
from io import StringIO
import os

# === Config ===
WATCHLIST_FILES = {
    "Large Cap": "largecap_watchlist.csv",
    "Small Cap": "smallcap_watchlist.csv"
}

BULK_URL = "https://archives.nseindia.com/content/equities/bulk.csv"
BLOCK_URL = "https://archives.nseindia.com/content/equities/block.csv"

# Email Config from environment variables (with defaults)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_TO = os.getenv("EMAIL_TO")  # can be comma-separated for multiple recipients

if not all([EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO]):
    print("[❌] ERROR: Please set EMAIL_FROM, EMAIL_PASSWORD, and EMAIL_TO environment variables.")
    sys.exit(1)

EMAIL_SUBJECT = f"Mutual Fund Deal Tracker Report - {datetime.today().date()}"

today_str = datetime.today().strftime("%d-%b-%Y").upper()


def fetch_nse_csv_with_session(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/114.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Referer": "https://www.nseindia.com/"
    }

    with requests.Session() as session:
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=5)
        response.raise_for_status()

        df = pd.read_csv(StringIO(response.text))
        return df


def load_watchlist(file):
    df = pd.read_csv(file)
    return set(df["Symbol"].str.upper())


def process_deals(csv_url, deal_type, watchlist_name, watchlist_symbols, output_io):
    try:
        df = fetch_nse_csv_with_session(csv_url)

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
            print(f"[❌] No mutual fund deals found today in {deal_type} list for {watchlist_name}.", file=output_io)
        else:
            print(f"\n🎯 {deal_type} Deals — Mutual Funds Buying {watchlist_name} Stocks:", file=output_io)
            print(tabulate(
                filtered[[
                    "Date",
                    "Symbol",
                    "Client Name",
                    "Buy/Sell",
                    "Quantity Traded",
                    "Trade Price / Wght. Avg. Price"
                ]],
                headers="keys",
                tablefmt="pretty",
                showindex=False,
                file=output_io
            ))
    except Exception as e:
        print(f"[⚠️] Error fetching or processing {deal_type.lower()} deals for {watchlist_name}: {e}", file=output_io)


def generate_report():
    output_io = io.StringIO()
    print(f"===== Mutual Fund Deal Tracker ({datetime.today().date()}) =====", file=output_io)

    for category, file in WATCHLIST_FILES.items():
        symbols = load_watchlist(file)
        process_deals(BULK_URL, "Bulk", category, symbols, output_io)
        process_deals(BLOCK_URL, "Block", category, symbols, output_io)

    report = output_io.getvalue()
    output_io.close()
    return report


def send_email(subject, body, from_addr, to_addrs, smtp_server, smtp_port, login, password):
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_addrs
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(login, password)
        # to_addrs can be comma-separated string; convert to list
        recipient_list = [addr.strip() for addr in to_addrs.split(",")]
        server.sendmail(from_addr, recipient_list, msg.as_string())
        server.quit()
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"[❌] Failed to send email: {e}")


if __name__ == "__main__":
    report_html = generate_report()
    send_email(
        EMAIL_SUBJECT,
        report_html,
        EMAIL_FROM,
        EMAIL_TO,
        SMTP_SERVER,
        SMTP_PORT,
        EMAIL_FROM,
        EMAIL_PASSWORD
    )

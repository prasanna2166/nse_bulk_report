import pandas as pd
from datetime import datetime
from tabulate import tabulate
import io
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === Config ===
WATCHLIST_FILES = {
    "Small Cap": "smallcap_watchlist.csv"
    "Large Cap": "largecap_watchlist.csv" 
}

BULK_URL = "https://archives.nseindia.com/content/equities/bulk.csv"
BLOCK_URL = "https://archives.nseindia.com/content/equities/block.csv"

# Read from environment variables (GitHub Actions Secrets)
EMAIL_FROM = os.environ.get("EMAIL_FROM")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_TO = os.environ.get("EMAIL_TO")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_SUBJECT = f"Mutual Fund Deal Tracker Report - {datetime.today().date()}"

today_str = datetime.today().strftime("%d-%b-%Y").upper()


def load_watchlist(file):
    df = pd.read_csv(file)
    return set(df["Symbol"].str.upper())


def process_deals(csv_url, deal_type, watchlist_name, watchlist_symbols, output_io):
    try:
        df = pd.read_csv(csv_url)
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


def send_email(subject, body, from_addr, to_addr, smtp_server, smtp_port, login, password):
    msg = MIMEMultipart("alternative")
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject

    # Convert plain text to HTML-friendly version
    html_body = "<pre style='font-family: monospace; font-size: 14px'>" + body + "</pre>"
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(login, password)
        server.sendmail(from_addr, to_addr, msg.as_string())
        server.quit()
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"[❌] Failed to send email: {e}")


if __name__ == "__main__":
    report_text = generate_report()

    # Send the email
    if EMAIL_FROM and EMAIL_PASSWORD and EMAIL_TO:
        send_email(
            EMAIL_SUBJECT,
            report_text,
            EMAIL_FROM,
            EMAIL_TO,
            SMTP_SERVER,
            SMTP_PORT,
            EMAIL_FROM,
            EMAIL_PASSWORD
        )
    else:
        print("[❌] Missing environment variables for email configuration.")

import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === Config ===
WATCHLIST_FILES = {
    "Large Cap": "largecap_watchlist.csv",
    "Small Cap": "smallcap_watchlist.csv"
}

BULK_URL = "https://archives.nseindia.com/content/equities/bulk.csv"
BLOCK_URL = "https://archives.nseindia.com/content/equities/block.csv"

# Email Config - fill these out
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_FROM = "prasannanike@gmail.com"
EMAIL_PASSWORD = "gxhjzpfztfkbbcbf"
EMAIL_TO = "gknprasanna@gmail.com"
EMAIL_SUBJECT = f"Mutual Fund Deal Tracker Report - {datetime.today().date()}"

today_str = datetime.today().strftime("%d-%b-%Y").upper()

def load_watchlist(file):
    df = pd.read_csv(file)
    return set(df["Symbol"].str.upper())

def format_html_table(df, title):
    if df.empty:
        return f"<p><strong>{title}:</strong> No mutual fund deals found today.</p>"
    else:
        df = df[[
            "Date", "Symbol", "Client Name", "Buy/Sell",
            "Quantity Traded", "Trade Price / Wght. Avg. Price"
        ]]
        html_table = df.to_html(index=False, border=1, classes="styled-table")
        return f"<h3>{title}</h3>{html_table}<br>"

def process_deals_html(csv_url, deal_type, watchlist_name, watchlist_symbols):
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

        title = f"{deal_type} Deals – {watchlist_name}"
        return format_html_table(filtered, title)

    except Exception as e:
        return f"<p><strong>{deal_type} Deals – {watchlist_name}:</strong> Error occurred: {e}</p>"

def generate_html_report():
    html = [
        f"<html><head><style>.styled-table {{ border-collapse: collapse; width: 100%; }}",
        ".styled-table th, .styled-table td {{ border: 1px solid #ddd; padding: 8px; }}",
        ".styled-table th {{ background-color: #f2f2f2; }}</style></head><body>",
        f"<h2>📈 Mutual Fund Deal Tracker ({datetime.today().date()})</h2>"
    ]

    for category, file in WATCHLIST_FILES.items():
        symbols = load_watchlist(file)
        html.append(process_deals_html(BULK_URL, "Bulk", category, symbols))
        html.append(process_deals_html(BLOCK_URL, "Block", category, symbols))

    html.append("</body></html>")
    return "".join(html)

def send_email(subject, html_body, from_addr, to_addr, smtp_server, smtp_port, login, password):
    msg = MIMEMultipart("alternative")
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject

    part = MIMEText(html_body, "html")
    msg.attach(part)

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
    html_report = generate_html_report()

    send_email(
        EMAIL_SUBJECT,
        html_report,
        EMAIL_FROM,
        EMAIL_TO,
        SMTP_SERVER,
        SMTP_PORT,
        EMAIL_FROM,
        EMAIL_PASSWORD
    )

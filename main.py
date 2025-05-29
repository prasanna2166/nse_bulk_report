import os
import time
import smtplib
import pytz
import requests
import pandas as pd
from datetime import datetime
from io import StringIO
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
EMAIL_TO = os.getenv("EMAIL_TO", "").split(",")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
EMAIL_SUBJECT = f"Mutual Fund Deal Tracker Report - {today_human}"

# --- Diagnostic CSV Fetch ---
def diagnose_url_access(url, session, headers):
    log = [f"<p><b>🧪 Diagnosing URL:</b> <a href='{url}'>{url}</a></p>"]
    try:
        response = session.get(url, headers=headers, timeout=10)
        log.append(f"<p>Status Code: {response.status_code}</p>")
        log.append(f"<pre>Headers Sent: {headers}</pre>")
        log.append(f"<pre>Response Headers: {dict(response.headers)}</pre>")
        if response.status_code == 403:
            log.append("<p style='color:red;'>❌ 403 Forbidden. Likely due to missing cookies, headers, or bot detection.</p>")
        elif response.status_code == 200:
            log.append("<p style='color:green;'>✅ Successfully fetched CSV.</p>")
    except Exception as e:
        log.append(f"<p>⚠️ Exception: {e}</p>")
    return "\n".join(log)

# --- Load Watchlist ---
def load_watchlist(file):
    df = pd.read_csv(file)
    return set(df["Symbol"].str.upper())

# --- Fetch NSE CSV ---
def fetch_nse_csv_with_diagnostics(url, output):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "text/csv",
        "Referer": "https://www.nseindia.com",
        "Cookie": "nsit=70CpxzVMFVUGSmOLFLCr_Jxs; nseappid=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJhcGkubnNlIiwiYXVkIjoiYXBpLm5zZSIsImlhdCI6MTc0ODU0NjI5MCwiZXhwIjoxNzQ4NTUzNDkwfQ.SsP2nRmYWuJRW-GuFBNILP7i9OnaMBY9jpbx4np6oZA; AKA_A2=A; bm_sz=EA6FCE31C4E0D35DEAE22C7F3AA987F6~YAAQtozQF11/GNWWAQAAlgF7HRt76HIfwUmuy71VGmF5Y4aFt5TlhzF8qWw/F8STZr8d/5nIP3+B5NvGl63LY5sVEQHsPMW3KPiTdLkqh6bpCZwOUvACxpHY3bgCUW8XI4T/s1Qiygpi9BDaJi8Em1sWvHyiXes7gXemADPMSy9Lws5cSHcxZzUJl4VkGbQVQnUbSV5Gg6t2LPhnNLf5CVplMJ7/Zxzn8U2tWUef6v3DcaBA0Flry/gIlYxKwLE5/S6JRMq67Vz5aFyanfU9FT661XtJeoYm1+1DQ1SLtPuV40eK7ZC9xP/q+QwvdfZRslYHh64TY6vBE7llAGxkLSb3QGioANKz2dlGtCvAGxcXohQ+VPsYioVrA/uTFL0qnEcegK7fa9a+1ABTW8jOt0OVLcnyySNygzU=~3490103~3752515; _ga=GA1.1.517744285.1748546291; _ga_87M7PJ3R97=GS2.1.s1748546290$o1$g1$t1748546290$j60$l0$h0; ak_bmsc=632029501DF57D3B29E139CAB2E6290E~000000000000000000000000000000~YAAQtozQF2t/GNWWAQAAaAR7HRvB9AD8EGssl0NyhWR/iZulFAny7yUT30OxSEfkMuGyE0GJfgiUiSGdtylBxfSlWLAfm8y86fpyXB+VEfhjc3N7gZgadOdC3YqM7eA2Xd4/NBkl6OEjnlDQUxHnhmPuS5sC7Ny7oM5/2YPjZj8lkD+9CHE/b8W8HjHYJGOwCE/bLsug+eqQP8c6HXg/B6VIZ0oBV69kpe+322WRtDkKufyZ9mD8d+Lqeq+oxA1oJh6VyM6VijUMqnKR/Oz2+kyPaMun8X+/GuNrq3h9BvmY9XNAb+WEh8Z9KNz125hJwLWILS6i7fXfKlD4+NID3XBtYLGQrFSjmyvyeG9NS53pX2EwDS4459Xc94b9tpdtsN6prC1gdaarjmr+pYajl7JqMKB6TUaqZ4n4WNa7rhBhoCfVkRl8AMj3ZcfSkR485I6cCH8hC4+sKCC8R1UHIQ==; _abck=0B29B696959D93C04F51445ABB5BFBCF~-1~YAAQtozQF3l/GNWWAQAAcQd7HQ1rc9MNN4y3rDl26/ECXnWdOWyKLjp+Qnc4PLz0U/F1Y011tY/eF1uoD/eYJcZ9/miRSrXcaTeMPdRZqRtieDDMhFPoclU8e3425CLjchwPuqTsAuLdT+KrT72jtR5BEGdtyumJnJvKQIo1T3qbMWMEcpZL3NkdgIys6jmbLKGubs9BXRfwmibif1XWhLpgMP1T5jn6lIvrS7vVZYHd0fFNxoKHvT8nZwbWraim4Xad0l8tcXG1GTu4VDknsmD5AyucrdcC6lWyk9dnJhUdIyPNUA7XsMeWHKqVAF77jYovk83u/1gCMi8VyGy8vGSiWPj1AB20juVQgd2wfe6YX9op7y60Wh9/QVp0EItdiFyTkHyVtxaUD/Wx+vj9IHwzkr7gEQBnTkfClqB0J+h7HE4GBgph9HgNPGFtP73jOLBXU9QzgkYXzNCHRlHcTBwZxhuZKKviLYRAzqmR5nx+/NLGpulsaV2F7/gwjrF2Zlrmp9ZJyQxeuUgrx4grGx7V+J3o8ssQjIqGr5BtCLilY7kLQq82WuzmkQdaimszMF1gI0KCR08jLnmRgO47mfrTMDdo0UHMyg==~-1~||0||~-1; RT="z=1&dm=nseindia.com&si=dc7a3dd0-80f7-492e-8d35-d470cec55583&ss=mb9rbc22&sl=1&se=8c&tt=uw&bcn=%2F%2F684d0d47.akstat.io%2F&ld=1vs&nu=kpaxjfo&cl=6vj"; bm_sv=B7A4D82D7E6C6072BE221525B10A6631~YAAQtozQF+d/GNWWAQAA/yN7HRsVcrx5KImaFa+dGcyel4F//R3KP/vl5wfklvo5coon57rCbl+IrQpHDV+I5SonXc97/WjbbsuaHyzms2G/X7gSSDXtuVINsNJ6NRfR2wjnvGm1t/Bib7fbBfmEtvQtIkUlOZ4F/ONlZ19vHUSahj5ZqsoCZ2i+9s/ZRVY8X9KqgEljqY+I+iXqr8cAVt5UvWOCE5XaAOqaEc1VIA5nwlV7QC0Fys/iV9W/SxVPlYE=~1"
    }
    with requests.Session() as session:
        try:
            # Hit homepage to get cookies
            home_resp = session.get("https://www.nseindia.com", headers=headers, timeout=10)
            output.append(f"<p>🌐 Homepage status: {home_resp.status_code}</p>")
            time.sleep(2)
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return pd.read_csv(StringIO(response.text))
        except Exception as e:
            output.append(diagnose_url_access(url, session, headers))
            raise

# --- Process Deals ---
def process_deals(deal_type, watchlist_name, watchlist_symbols, url, output):
    try:
        df = fetch_nse_csv_with_diagnostics(url, output)
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
            output.append(f"<p>❌ No mutual fund deals in <b>{deal_type}</b> list for <b>{watchlist_name}</b>.</p>")
        else:
            table_html = filtered[[
                "Date",
                "Symbol",
                "Client Name",
                "Buy/Sell",
                "Quantity Traded",
                "Trade Price / Wght. Avg. Price"
            ]].to_html(index=False, border=0, classes="styled-table")
            output.append(f"<h3>🎯 {deal_type} Deals — {watchlist_name}</h3>{table_html}")
    except Exception as e:
        output.append(f"<p><b>⚠️ Error in {deal_type.lower()} deals for {watchlist_name}:</b> {e}</p>")

# --- Report Builder ---
def generate_html_report():
    output = [f"<h2>📊 Mutual Fund Deal Tracker - {today_human}</h2>"]

    for category, file in WATCHLIST_FILES.items():
        symbols = load_watchlist(file)
        output.append(f"<h3>🔍 {category} Watchlist</h3>")
        process_deals("Bulk", category, symbols, BULK_URL, output)
        process_deals("Block", category, symbols, BLOCK_URL, output)

    style = """
    <style>
    body { font-family: Arial; line-height: 1.6; padding: 20px; }
    .styled-table {
        border-collapse: collapse;
        font-size: 14px;
        min-width: 400px;
        border: 1px solid #ddd;
    }
    .styled-table th, .styled-table td {
        border: 1px solid #ddd;
        padding: 8px;
    }
    .styled-table th {
        background-color: #f2f2f2;
    }
    </style>
    """
    return style + "\n".join(output)

# --- Email Sender ---
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
        print("✅ Email sent.")
    except Exception as e:
        print(f"[❌] Email send failed: {e}")

# --- Main ---
if __name__ == "__main__":
    report_html = generate_html_report()
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

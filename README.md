# Mutual Fund Bulk Deal Tracker (Pure Python)

Tracks NSE bulk deals daily to detect when Mutual Funds invest in small-cap stocks.

## Features
- ✅ No Selenium or browser automation
- ✅ Uses only `requests`, `pandas`, and `beautifulsoup4`
- ✅ Filters deals where `Client Name` contains 'Mutual Fund'
- ✅ Matches your own small-cap watchlist

## Setup

Install requirements:

```bash
pip install requests beautifulsoup4 pandas tabulate lxml
```

## Run

```bash
python main.py
```

Edit `smallcap_watchlist.csv` to track your own list of symbols.

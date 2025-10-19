# Exchange Rate Scraper

Automated scraper that collects daily exchange rates  for EUR to TND and EUR to MAD currency pairs.

## What it does

- Scrapes exchange rates daily 
- Saves rates to CSV file
- Automatically emails the results to specified recipients
- Runs via GitHub Actions (no need to keep script running locally)

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Configure email credentials in GitHub secrets
3. The scraper runs automatically via GitHub Actions 
name: Sheets Scraper

on:
  schedule:
    - cron: '0 * * * *'  # Run every hour
  workflow_dispatch:  # Allow manual triggers

jobs:
  scrape:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
        
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        
    - name: Run Sheets Scraper
      env:
        GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
        DAMADAM_USERNAME: ${{ secrets.DAMADAM_USERNAME }}
        DAMADAM_PASSWORD: ${{ secrets.DAMADAM_PASSWORD }}
      run: python scripts/run_sheets.py
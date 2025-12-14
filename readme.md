# DamaDam Scraper v4.0 - Modular Architecture

Complete rewrite with modular, maintainable architecture

## 🎯 Overview

Advanced automation bot that scrapes DamaDam.pk user profiles and stores results in Google Sheets.

### Key Features

- ✅ **Modular Architecture**: Separate files for each concern (auth, browser, scraping, etc.)
- 🍪 **Cookie Persistence**: Reuses login sessions to avoid repeated login
- 🔄 **Dual Environment**: Works locally and in GitHub Actions
- 📊 **Duplicate Detection**: Only appends new profiles, tracks duplicates with notes
- ⚡ **Adaptive Delays**: Smart rate limiting to avoid suspension
- 📝 **Detailed Logging**: Rich console output with timestamps and status icons

---

## 📋 Project Structure

```text
damadam-scraper/
├── config.py              # Configuration & environment variables
├── logger.py              # Logging & console output
├── browser.py             # Browser setup & cookie management
├── auth.py                # Login & authentication
├── sheets.py              # Google Sheets operations
├── scraper.py             # Profile scraping logic
├── main.py                # Main orchestration
├── requirements.txt       # Python dependencies
├── .env.example           # Example environment variables
├── .env                   # Local credentials (git-ignored)
├── credentials.json       # Google Service Account (git-ignored)
├── damadam_cookies.pkl    # Session cookies (git-ignored)
└── .github/
    └── workflows/
        └── scraper.yml    # GitHub Actions workflow
```

---

## 🚀 Quick Start

### 1. Local Setup

```bash
# Clone repository
git clone <repo-url>
cd damadam-scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file in root directory:

```env
# DamaDam Credentials
DAMADAM_USERNAME=your_username
DAMADAM_PASSWORD=your_password

# Optional: Second account
DAMADAM_USERNAME_2=
DAMADAM_PASSWORD_2=

# Google Sheets
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/xxxxx/edit
GOOGLE_APPLICATION_CREDENTIALS=credentials.json

# Scraping Settings (optional)
MAX_PROFILES_PER_RUN=0
BATCH_SIZE=20
MIN_DELAY=0.3
MAX_DELAY=0.5
PAGE_LOAD_TIMEOUT=30
SHEET_WRITE_DELAY=1.0
```

### 3. Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new Service Account
3. Create JSON key
4. Save as `credentials.json` in root directory
5. Share your Google Sheet with the service account email

### 4. Run Locally

```bash
# Run with defaults
python main.py

# Run with specific profiles count
python main.py --max-profiles 10

# Run with custom batch size
python main.py --batch-size 15
```

---

## 🔐 GitHub Actions Setup

### 1. Add Secrets

Go to **Settings > Secrets and variables > Actions** and add:

- `DAMADAM_USERNAME` - DamaDam username
- `DAMADAM_PASSWORD` - DamaDam password
- `GOOGLE_SHEET_URL` - Google Sheet URL
- `GOOGLE_CREDENTIALS_JSON` - Raw JSON content (copy entire file)

### 2. Workflow File

See `.github/workflows/scraper.yml` - Configure schedule or trigger manually.

---

## 📊 Google Sheets Structure

### Profiles Sheet

All scraped profiles go here:

| NICK NAME | TAGS | CITY | GENDER | ... | STATUS   | POSTS | ... |
|-----------|------|------|--------|-----|----------|-------|-----|
| user1     |      | KHI  | Male   | ... | Verified | 42    | ... |

**Status values:**

- `Verified` - Account is active
- `Unverified` - Account not verified
- `Banned` - Account suspended

### RunList Sheet

List of targets to scrape:

| Nickname | Status     | Remarks          | Source |
|----------|------------|------------------|--------|
| target1  | ⚡ Pending | Ready to scrape  | RunList|
| target2  | Done 💀    | New @ 10:30 AM   | Manual |

**Status values:**

- `⚡ Pending` - Waiting to scrape
- `Done 💀` - Successfully processed
- `Error 💥` - Encountered error

---

## 🔧 Module Guide

### config.py

Central configuration hub. All settings defined once here.

**Key exports:**

- Environment variables validation
- Sheet names & column definitions
- Status constants
- URL patterns

### logger.py

Console output with timestamps and rich formatting.

**Key functions:**

- `log_msg()` - Auto-detects log level from message
- `get_pkt_time()` - Pakistan timezone timestamp
- `print_header()` - Formatted panel output

### browser.py

Chrome WebDriver management and cookie persistence.

**Key functions:**

- `setup_browser()` - Initialize Chrome with anti-detection
- `save_cookies()` / `load_cookies()` - Session persistence
- `test_session_validity()` - Check if cached session works

### auth.py

DamaDam login with fallback logic.

**Key functions:**

- `authenticate()` - Main auth orchestration
- `perform_login()` - Submit login form
- `verify_login_status()` - Check if logged in

### sheets.py

Google Sheets API operations and data management.

**Key class:**

- `SheetsManager` - Manages all sheet operations
  - `get_pending_runlist()` - Get targets to scrape
  - `is_duplicate()` - Check for existing profile
  - `append_profile()` - Add new profile to end
  - `add_note_to_cell()` - Track duplicates with notes

### scraper.py

Profile data extraction from DamaDam pages.

**Key functions:**

- `scrape_profile()` - Main scraping orchestration
- `_detect_account_status()` - Verified/Unverified/Banned
- `_extract_profile_fields()` - Parse profile data
- `_scrape_recent_post()` - Get latest post info

### main.py

Master orchestration and progress tracking.

**Workflow:**

1. Parse arguments
2. Setup browser
3. Authenticate
4. Connect to Sheets
5. Process each target (with duplicate detection)
6. Update status and report

---

## 🔄 Workflow: Duplicate Handling

**New Profile:**

```text
RunList: target1 (Pending)
  ↓
Scraper: Profile found
  ↓
SheetsManager: Check if duplicate → NO
  ↓
Append to Profiles sheet (end of table)
  ↓
RunList: target1 → "Done 💀" + "New profile"
```

**Duplicate Profile:**

```text
RunList: target1 (Pending)
  ↓
Scraper: Profile found
  ↓
SheetsManager: Check if duplicate → YES (row 42)
  ↓
Add note to Profiles row 42: "Duplicate @ 2:30 PM"
  ↓
RunList: target1 → "Done 💀" + "Duplicate (row 42)"
```

---

## 🍪 Cookie Behavior

### Local Mode

- **First run**: No cookies → Login → Save cookies
- **Subsequent runs**: Load cookies → Test validity → Reuse or refresh

### CI/CD Mode

- Cookies stored in memory during run
- Fresh login on every GitHub Actions run (runners are ephemeral)

### Clear Cookies

```python
from browser import clear_cookies
clear_cookies()  # Delete damadam_cookies.pkl
```

---

## ⚙️ Advanced Configuration

### Adjust Rate Limiting

In `config.py`:

```python
MIN_DELAY = 0.5  # Minimum delay between requests (seconds)
MAX_DELAY = 1.0  # Maximum delay between requests
```

### Limit Profiles Per Run

```bash
python main.py --max-profiles 5  # Only process 5 profiles
```

### Batch Pause

```python
BATCH_SIZE = 20  # Pause after every 20 profiles
```

---

## 🐛 Troubleshooting

### "No saved cookies found"

- Normal on first run
- Script will perform fresh login
- Cookies saved for future runs

### "Session expired"

- Cached cookies no longer valid
- Fresh login performed automatically

### "429 API Quota Exceeded"

- Hit Google Sheets rate limit
- Script waits 60 seconds automatically
- Retries up to 3 times

### Login Fails

- Check credentials in `.env`
- Verify DamaDam account is active
- Clear cookies: `python -c "from browser import clear_cookies; clear_cookies()"`

### "Page not found" (404)

- Profile doesn't exist
- Account deleted
- Username typo in RunList

---

## 📈 Monitoring

Check Google Sheet Dashboard for:

- Profiles processed
- New profiles added
- Duplicates detected
- Errors encountered
- Last run timestamp

---

## 📝 Notes

- **Do NOT commit** `credentials.json` or `.env` to GitHub
- Use GitHub Secrets for sensitive data
- Cookies are automatically managed (local only)
- Profile data always appends (no overwrites)
- Duplicates tracked via cell notes

---

## 📞 Support

For issues or improvements, create an issue in the repository.

---

**Version**: 4.0  
**Architecture**: Modular  
**Environment**: Local + GitHub Actions  
**Last Updated**: 2025

# DamaDam Scraper v4.0 - Complete Setup Guide

Step-by-step instructions to get the scraper running locally and on GitHub Actions

---

## 📋 Prerequisites

- Windows/Linux/Mac with Python 3.9+
- Chrome browser installed
- DamaDam.pk account
- Google account with Sheets access
- GitHub account (for automation)

---

## 🎯 Phase 1: Local Machine Setup

### Step 1.1: Clone Repository

```bash
git clone https://github.com/yourname/damadam-scraper.git
cd damadam-scraper
```

### Step 1.2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 1.3: Install Python Packages

```bash
pip install -r requirements.txt
```

### Step 1.4: Download ChromeDriver

1. Go to [ChromeDriver Downloads](https://googlechromelabs.github.io/chrome-for-testing/)
2. Download version matching your Chrome version
3. Extract `chromedriver.exe` to project root directory
4. Verify: `chromedriver --version`

### Step 1.5: Create Configuration File

```bash
# Copy template
cp .env.example .env

# Edit .env with your values
# Windows: Open with Notepad
notepad .env

# Mac/Linux: Use nano or vi
nano .env
```

**Fill in your values:**

```env
DAMADAM_USERNAME=your_damadam_username
DAMADAM_PASSWORD=your_damadam_password
GOOGLE_SHEET_URL=your_google_sheet_url
GOOGLE_APPLICATION_CREDENTIALS=credentials.json
```

---

## 🔐 Phase 2: Google Service Account Setup

### Step 2.1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a Project"** > **"NEW PROJECT"**
3. Enter name: `DamaDam Scraper`
4. Click **CREATE**

### Step 2.2: Enable Google Sheets API

1. In left menu, click **"APIs & Services"** > **"Library"**
2. Search for: `Google Sheets API`
3. Click on it
4. Click **ENABLE**

### Step 2.3: Create Service Account

1. Go to **"APIs & Services"** > **"Credentials"** (left menu)
2. Click **CREATE CREDENTIALS** > **"Service Account"**
3. Enter **Service account name**: `damadam-scraper`
4. Click **CREATE AND CONTINUE**
5. Click **CONTINUE** (optional roles)
6. Click **DONE**

### Step 2.4: Create Service Account Key

1. In "Service Accounts" list, click the account you just created
2. Go to **KEYS** tab
3. Click **ADD KEY** > **Create new key**
4. Choose **JSON** format
5. Click **CREATE**
6. File downloads automatically as `xxxxx.json`
7. **Rename to `credentials.json`** and place in project root

### Step 2.5: Share Google Sheet

1. Open your Google Sheet
2. Click **SHARE** button (top right)
3. Get service account email from `credentials.json`:
   - Open file, look for `"client_email": "xxx@yyy.iam.gserviceaccount.com"`
4. Paste email in share dialog
5. Click **SHARE**

### Step 2.6: Verify Setup

```bash
# Test if you can read the sheet
python -c "from sheets import authenticate_google, SheetsManager; auth = authenticate_google(); print('✅ Google Auth Works')"
```

---

## 🎬 Phase 3: First Run

### Step 3.1: Prepare Google Sheet

Create a Google Sheet with these worksheets:

1. **Profiles** (for scraped data)
   - Headers will auto-initialize on first run
   - Columns: NICK NAME, TAGS, CITY, GENDER, MARRIED, AGE, JOINED, FOLLOWERS, STATUS, POSTS, INTRO, SOURCE, DATETIME SCRAP, LAST POST, LAST POST TIME, IMAGE, PROFILE LINK, POST URL

2. **RunList** (for targets)
   - Headers: Nickname, Status, Remarks, Source
   - Add nicknames you want to scrape

### Step 3.2: Test Authentication

```bash
# Test DamaDam login
python -c "from browser import setup_browser; from auth import authenticate; d = setup_browser(); r = authenticate(d); print('✅ Login OK' if r else '❌ Login Failed'); d.quit()"
```

### Step 3.3: Run Scraper

```bash
# Run with all pending targets
python main.py

# Run with limit (5 profiles only)
python main.py --max-profiles 5

# Run with custom batch size
python main.py --batch-size 10
```

---

## ☁️ Phase 4: GitHub Actions Setup

### Step 4.1: Push to GitHub

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

**Make sure `.gitignore` includes:**

```gitignore
.env
credentials.json
damadam_cookies.pkl
__pycache__/
venv/
```

### Step 4.2: Add Secrets to GitHub

1. Go to your GitHub repository
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret** and add:

| Secret Name | Value |
|---|---|
| `DAMADAM_USERNAME` | Your DamaDam username |
| `DAMADAM_PASSWORD` | Your DamaDam password |
| `GOOGLE_SHEET_URL` | Your Google Sheet URL |
| `GOOGLE_CREDENTIALS_JSON` | **Raw JSON content** from credentials.json file |

**For GOOGLE_CREDENTIALS_JSON:**

1. Open `credentials.json` in text editor
2. Copy entire content (all text including `{` and `}`)
3. Paste into GitHub secret

### Step 4.3: Enable GitHub Actions

1. Go to **Actions** tab
2. If workflow exists, you're ready
3. If not, create `.github/workflows/scraper.yml` (use provided template)

### Step 4.4: Test Workflow

1. Go to **Actions** tab
2. Select **"DamaDam Scraper"** workflow
3. Click **Run workflow** > **Run workflow**
4. Watch the logs as it runs

---

## ✅ Verification Checklist

- [ ] Python 3.9+ installed
- [ ] Virtual environment created and activated
- [ ] `requirements.txt` packages installed
- [ ] `chromedriver.exe` in root directory
- [ ] `.env` file created with credentials
- [ ] `credentials.json` in root directory
- [ ] Google Sheet created with Profiles + RunList sheets
- [ ] Google service account email added to sheet share
- [ ] Local first run successful
- [ ] GitHub secrets configured
- [ ] GitHub workflow triggered successfully

---

## 🧪 Testing Commands

```bash
# Test Python environment
python --version

# Test imports
python -c "import selenium, gspread, rich; print('✅ All imports OK')"

# Test Google auth
python -c "from sheets import authenticate_google; c = authenticate_google(); print('✅ Google auth works')"

# Test browser
python -c "from browser import setup_browser; d = setup_browser(); print(f'✅ Browser OK: {d.current_url}'); d.quit()"

# Test DamaDam login
python main.py --max-profiles 1
```

---

## 🐛 Common Issues & Solutions

### Issue: "ModuleNotFoundError: No module named 'selenium'"

**Solution:** Install requirements: `pip install -r requirements.txt`

### Issue: "chromedriver: command not found"

**Solution:**

- Download ChromeDriver matching your Chrome version
- Place in project root directory
- On Mac/Linux, make executable: `chmod +x chromedriver`

### Issue: "DAMADAM_USERNAME not set"

**Solution:** Check `.env` file has correct credentials

### Issue: "Google credentials not found"

**Solution:**

- Download credentials.json from Google Cloud Console
- Place in project root
- Verify service account has access to sheet

### Issue: "Profile not found" (404 error)

**Solution:**

- Check nickname spelling in RunList
- Verify profile exists on DamaDam.pk

### Issue: GitHub Actions workflow fails

**Solution:**

- Check GitHub secrets are correctly added
- Verify Google Sheets URL is correct
- Check DamaDam credentials are correct

---

## 📊 Next Steps

Once working:

1. **Add more targets** to RunList sheet

2. **Schedule automation** (workflow runs every 6 hours by default)

3. **Monitor progress** in Profiles sheet

4. **Track duplicates** via cell notes

5. **Adjust settings** for your needs

---

## 🔄 Architecture Overview

```text
.env + credentials.json
         ↓
    config.py (load settings)
         ↓
    ┌─────────────────────────────────────────────┐
    │              main.py (orchestration)          │
    ├──────────┬──────────┬──────────┬────────────┤
    ↓          ↓          ↓          ↓            ↓
 browser.py  auth.py   sheets.py  scraper.py  logger.py
    ↓          ↓          ↓          ↓            ↓
 Chrome     Login      Google      Profile    Console
 Driver             Sheets API     Data       Output
    ↓                    ↓
 damadam.pk     Google Sheets
              (Profiles + RunList)
```

---

## 📚 Documentation Files

- **README.md** - Full feature documentation

- **config.py** - Configuration reference

- **SETUP_GUIDE.md** - This file (step-by-step)

---

## 💡 Pro Tips

1. **First Login Takes Time**: Chrome starts fresh, so first run may take longer

2. **Cookies Speed Things Up**: After first login, subsequent runs reuse cookies

3. **Batch Sizes Matter**: Smaller batches = safer but slower

4. **Test with Small Runs**: Use `--max-profiles 1` to test

5. **Monitor Rate Limits**: If hitting limits, increase MIN_DELAY and MAX_DELAY

---

## Ready to scrape? 🚀

```bash
python main.py
```

Good luck! 💪

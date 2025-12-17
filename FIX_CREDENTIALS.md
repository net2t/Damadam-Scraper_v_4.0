# 🔧 Fix: Invalid JSON Credentials Error

## ❌ Current Error

```
Error: Invalid JSON in credentials: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)
```

This error occurs because the `GOOGLE_CREDENTIALS_JSON` secret in GitHub is not properly formatted.

---

## ✅ Solution

### **Step 1: Get Your Credentials JSON**

1. Open your `credentials.json` file (the file you downloaded from Google Cloud)
2. The content should look like this:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

### **Step 2: Copy the ENTIRE JSON**

**Important**: You need to copy the **entire content** including:
- Opening brace `{`
- All properties and values
- Closing brace `}`

**Do NOT**:
- Remove any quotes
- Remove any newlines
- Modify any formatting
- Add extra spaces

### **Step 3: Add to GitHub Secrets**

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `GOOGLE_CREDENTIALS_JSON`
5. Value: Paste the **entire JSON content** from Step 2
6. Click **Add secret**

### **Step 4: Verify Other Secrets**

Make sure these secrets are also set:

| Secret Name | Example Value |
|-------------|---------------|
| `DAMADAM_USERNAME` | `your_username` |
| `DAMADAM_PASSWORD` | `your_password` |
| `GOOGLE_SHEET_URL` | `https://docs.google.com/spreadsheets/d/abc123.../edit` |

---

## 🧪 Test Locally First

Before using GitHub Actions, test locally:

```bash
# 1. Create .env file
cp .env_example .env

# 2. Edit .env with your credentials
nano .env

# 3. Make sure credentials.json exists
ls credentials.json

# 4. Test target mode
python main.py --mode target --max-profiles 1

# 5. If successful, test online mode
python main.py --mode online
```

---

## 🔍 Common Issues

### **Issue 1: Spaces or Formatting**

❌ **Wrong**:
```
GOOGLE_CREDENTIALS_JSON={
  "type": "service_account",
  ...
}
```

✅ **Correct**:
```
GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}
```

The JSON should be copied as-is from the credentials file, with no extra spaces or newlines added by you.

### **Issue 2: Missing Quotes**

Your original `credentials.json` file is valid JSON. The error happens when:
- You manually typed the JSON instead of copying
- You removed quotes from property names
- You modified the formatting

**Solution**: Copy directly from the `credentials.json` file.

### **Issue 3: File vs Secret Confusion**

- **Local development**: Uses `credentials.json` file
- **GitHub Actions**: Uses `GOOGLE_CREDENTIALS_JSON` secret

Make sure:
- Local has `credentials.json` file
- GitHub has `GOOGLE_CREDENTIALS_JSON` secret with same content

---

## ✅ Verification Checklist

Before running the scraper, verify:

- [ ] `credentials.json` file exists locally
- [ ] Can open and view `credentials.json` (valid JSON)
- [ ] Copied entire JSON to GitHub Secret
- [ ] Secret name is exactly `GOOGLE_CREDENTIALS_JSON`
- [ ] Other secrets are set (`DAMADAM_USERNAME`, etc.)
- [ ] Google Sheet is shared with service account email
- [ ] Service account has "Editor" permissions

---

## 🚀 After Fixing

Once you've updated the secret:

1. Go to **Actions** tab
2. Select **Target Mode Scraper** or **Online Mode Scraper**
3. Click **Run workflow**
4. Check logs for success

You should see:
```
✅ Google Credentials: Raw JSON found
✅ VALIDATION PASSED
```

Instead of:
```
❌ Invalid JSON in credentials
```

---

## 📞 Still Having Issues?

If you still see the error:

1. **Check the secret value**:
   - Go to Settings → Secrets
   - Delete `GOOGLE_CREDENTIALS_JSON`
   - Re-add it carefully

2. **Verify JSON is valid**:
   ```bash
   # On your local machine
   python -c "import json; print(json.load(open('credentials.json')))"
   ```
   
   If this works, your JSON is valid.

3. **Check workflow logs**:
   - The error message shows which character failed
   - Character 1 usually means the opening brace is wrong

4. **Test with a minimal JSON**:
   Try this in the secret first:
   ```json
   {"test":"value"}
   ```
   
   If this works, your secret setup is correct, and the issue is with the credentials JSON format.

---

## 💡 Pro Tip

Use this command to get JSON on one line (optional):

```bash
# Linux/Mac
cat credentials.json | jq -c .

# Windows PowerShell
Get-Content credentials.json | ConvertFrom-Json | ConvertTo-Json -Compress
```

But honestly, just copy the entire content from `credentials.json` as-is. The code will parse it correctly!

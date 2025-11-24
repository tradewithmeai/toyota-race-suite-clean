# Mac Build Instructions - URGENT HACKATHON BUILD
## For Mac Friend - Please Read Carefully!

**TIME CRITICAL:** This is the last day of the hackathon. We need the Mac build ASAP for judges.

---

## Prerequisites

1. **macOS 10.13 or later**
2. **Python 3.10 or later** - Check with: `python3 --version`
   - If not installed: Download from https://www.python.org/downloads/
3. **Xcode Command Line Tools** (optional but recommended)
   - Install with: `xcode-select --install`

---

## Step-by-Step Build Instructions

### 1. Get the Code
```bash
# If you received a zip file, unzip it
# If using git:
git clone [REPO_URL]
cd toyota-race-suite-clean
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

**VERIFY:** You should see `(venv)` at the start of your terminal prompt.

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

**TIME:** This takes 2-3 minutes. Don't worry if you see lots of output.

### 4. Quick Test (IMPORTANT!)
Before building, let's make sure the app works:

```bash
python -m src.app.main
```

**EXPECTED:** A window should open with a Toyota logo and loading screen.
**IF IT WORKS:** Press Ctrl+C to close it and continue to step 5.
**IF IT FAILS:** STOP and contact me immediately with the error message!

### 5. Build the .app Bundle

**IMPORTANT:** Before building, the spec file has been pre-configured with the correct paths.

```bash
chmod +x build_mac.sh
./build_mac.sh
```

**TIME:** 2-5 minutes. You'll see lots of output - this is normal.

**WHAT TO LOOK FOR:**
- Should say "Building .app bundle..."
- Lots of "INFO: Loading module..." messages
- Should end with "BUILD SUCCESSFUL!"

### 6. Test the Built App
```bash
open dist/ToyotaRaceSuite.app
```

**EXPECTED:** App should launch and show the loading screen with Toyota logo.

**IF YOU GET A SECURITY WARNING:**
1. Go to System Preferences → Security & Privacy
2. Click "Open Anyway"
3. Try again

### 7. Take Screenshots (CRITICAL!)
Please take screenshots of:
1. The app running (showing the main window)
2. The terminal showing "BUILD SUCCESSFUL"
3. The `dist` folder contents: `ls -lh dist/`

### 8. Package for Sending
```bash
# Zip the app bundle
cd dist
zip -r ToyotaRaceSuite-Mac.zip ToyotaRaceSuite.app
```

### 9. Send Me These Files
**URGENT - Please send via fastest method (Dropbox/Google Drive/WeTransfer):**

1. ✅ `dist/ToyotaRaceSuite-Mac.zip` - THE BUILT APP
2. ✅ Screenshots from step 7
3. ✅ Build log - Run this to capture it:
   ```bash
   ./build_mac.sh 2>&1 | tee build_log.txt
   ```
   Then send `build_log.txt`

---

## Troubleshooting

### Problem: "python3: command not found"
**Solution:** Install Python from https://www.python.org/downloads/macos/

### Problem: "No module named 'dearpygui'"
**Solution:** Make sure you activated the venv: `source venv/bin/activate`

### Problem: "Permission denied" when running build_mac.sh
**Solution:** Run `chmod +x build_mac.sh` first

### Problem: App won't open - "damaged" error
**Solution:** Run: `xattr -cr dist/ToyotaRaceSuite.app`

### Problem: Build fails with "scipy" errors
**Solution:**
```bash
pip uninstall scipy
pip install scipy --no-cache-dir
```

### Problem: Build succeeds but app crashes on launch
**Solution:**
1. Run from terminal to see error: `dist/ToyotaRaceSuite.app/Contents/MacOS/ToyotaRaceSuite`
2. Send me the error output

---

## Expected File Sizes

- **ToyotaRaceSuite.app:** ~150-250 MB (normal!)
- **ToyotaRaceSuite-Mac.zip:** ~100-180 MB (compressed)

If your file sizes are dramatically different (< 50MB or > 500MB), let me know.

---

## Quick Reference Commands

```bash
# Full build from scratch (if anything goes wrong, start here)
rm -rf venv build dist
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller
./build_mac.sh

# Test the built app
open dist/ToyotaRaceSuite.app

# Package for sending
cd dist && zip -r ToyotaRaceSuite-Mac.zip ToyotaRaceSuite.app
```

---

## Testing Checklist

After building, please verify:

- [ ] App launches without errors
- [ ] Window shows Toyota logo
- [ ] No console errors printed
- [ ] App doesn't crash immediately
- [ ] Window is responsive (can click, drag)
- [ ] App size is reasonable (100-250MB zipped)
- [ ] Screenshots captured
- [ ] Zip file created
- [ ] Sent to me via [contact method]

---

## What the App Should Look Like

When working correctly:
1. Window opens (1600x900 pixels)
2. Shows Toyota logo animation
3. Loading screen appears
4. Says "Waiting for data file" or loads sample data
5. No crash, no freeze, no error dialogs

---

## Emergency Contact

**IF ANYTHING FAILS:**
- Text me immediately: [YOUR PHONE]
- Include:
  - Screenshot of error
  - Last 20 lines of terminal output
  - Your macOS version

**TIME CRITICAL:** We need this working TODAY.

---

## Additional Notes

- The app is built with DearPyGUI (OpenGL-based GUI)
- It should work on any Mac with OpenGL 3.3+ support
- If you have an M1/M2 Mac, it will build for ARM architecture (correct!)
- The build is platform-specific - this Mac build only works on Mac

---

## After You Send the Build

I'll test it and may need you to:
1. Try launching it on a different Mac (if available)
2. Rebuild with small tweaks
3. Create a DMG installer (optional, only if time permits)

**THANK YOU for the urgent help!** This is critical for the hackathon submission.

---

**Questions? Call/text me immediately - don't wait!**

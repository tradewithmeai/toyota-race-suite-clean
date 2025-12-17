# Cross-Platform Packaging Plan - Toyota Race Suite
## Critical Hackathon Deadline - Must Work First Time

**Status:** Planning Complete - Ready for Implementation
**Date:** 2025-11-24
**Deadline:** URGENT - Last day of 25-day hackathon

---

## Project Analysis Summary

### Application Type
- **Python 3.12 DearPyGUI Desktop Application**
- Real-time racing telemetry visualization
- Entry point: `src/app/main.py`
- Current launcher: `run.bat` (Windows only)

### Dependencies (from requirements.txt)
```
dearpygui>=1.9.0
numpy>=1.24.0
pandas>=2.0.0
scipy>=1.10.0
matplotlib>=3.7.0
pywin32>=306; sys_platform == 'win32'  # WINDOWS-SPECIFIC
pillow>=9.5.0
```

### Current Installed Versions (venv)
```
dearpygui==2.1.1
numpy==2.3.5
pandas==2.3.3
scipy==1.16.3
matplotlib==3.10.7
pillow==12.0.0
pywin32==311  # Windows only
```

---

## Critical Cross-Platform Issues Found

### 1. Windows-Specific Code (ALREADY MITIGATED)
- **File:** `src/app/win32_drop.py` - Uses pywin32 for drag-and-drop
- **Status:** Already disabled in `src/app/main.py:102-105`
- **Action Required:** Ensure pywin32 import doesn't crash on Mac

### 2. Path Handling
- **Status:** ✅ GOOD - Uses `os.path.join` throughout codebase
- **No hardcoded Windows paths found**

### 3. Platform Dependencies
- **pywin32:** Conditionally installed on Windows only
- **Action:** Ensure graceful degradation on Mac/Linux

---

## Recommended Strategy: PyInstaller

### Why PyInstaller for Hackathon?

**CRITICAL SUCCESS FACTORS:**
1. ✅ **Zero friction** - Judges double-click, app runs
2. ✅ **No Python required** - Bundles Python interpreter
3. ✅ **No pip install** - All dependencies embedded
4. ✅ **No version conflicts** - Isolated environment
5. ✅ **100% reliability** - If it builds, it works

**Trade-offs:**
- File size: ~150-250MB (acceptable for hackathon)
- Build time: 2-5 minutes per platform
- Need Mac machine for Mac build (friend available)

---

## Implementation Checklist

### Phase 1: Prepare Codebase (30 minutes)
- [ ] Create `run.sh` for Mac/Linux
- [ ] Create `run.command` for Mac (double-clickable)
- [ ] Verify pywin32 imports are try/except wrapped
- [ ] Test script launchers on Windows
- [ ] Commit changes

### Phase 2: PyInstaller Setup (15 minutes)
- [ ] Install PyInstaller: `pip install pyinstaller`
- [ ] Create `.spec` file with proper configuration
- [ ] Configure data files (assets/, data/sample/)
- [ ] Set icon (if available in assets/)
- [ ] Configure hidden imports for scipy/pandas

### Phase 3: Windows Build (10 minutes)
- [ ] Run PyInstaller on Windows
- [ ] Test executable on clean Windows machine (if possible)
- [ ] Verify sample data loads
- [ ] Create Windows release folder structure
- [ ] Zip for distribution

### Phase 4: Mac Build Preparation (20 minutes)
- [ ] Create Mac build script for friend
- [ ] Write detailed step-by-step instructions
- [ ] Include troubleshooting section
- [ ] Prepare testing checklist
- [ ] Send to friend with sample data

### Phase 5: Documentation (15 minutes)
- [ ] Create `JUDGES_README.txt` - dead simple instructions
- [ ] Update main README.md with binary installation
- [ ] Create quick start guide (3 steps max)
- [ ] Add system requirements
- [ ] Add troubleshooting FAQ

---

## PyInstaller Configuration

### Basic Command
```bash
pyinstaller --name="ToyotaRaceSuite" \
            --windowed \
            --onefile \
            --add-data="assets;assets" \
            --add-data="data/sample;data/sample" \
            --hidden-import=scipy.special._ufuncs_cxx \
            --hidden-import=scipy.linalg.cython_blas \
            --hidden-import=scipy.linalg.cython_lapack \
            --hidden-import=pandas._libs.tslibs.timedeltas \
            --icon=assets/icon.ico \
            src/app/main.py
```

### Spec File Considerations
- **--onefile**: Single executable (recommended for judges)
- **--windowed**: No console window (clean presentation)
- **Data files**: Bundle assets and sample data
- **Hidden imports**: scipy/pandas C extensions
- **Exclusions**: Exclude test files, docs, venv

---

## File Structure for Distribution

### Windows Release
```
ToyotaRaceSuite-Windows/
├── ToyotaRaceSuite.exe          # PyInstaller build
├── START_HERE.txt               # Judge instructions
├── README.txt                   # Quick guide
└── data/
    └── sample/                  # Sample telemetry (if small enough)
        ├── trajectories_interpolated/
        ├── metadata.json
        └── sector_map.json
```

### Mac Release
```
ToyotaRaceSuite-Mac/
├── ToyotaRaceSuite.app          # PyInstaller bundle
├── START_HERE.txt               # Judge instructions
├── README.txt                   # Quick guide
└── data/
    └── sample/
```

---

## Testing Protocol

### Windows Testing (You)
1. [ ] Clean build from scratch
2. [ ] Test on development machine
3. [ ] Verify sample data loads
4. [ ] Test playback controls
5. [ ] Test all UI interactions
6. [ ] Check performance (60fps target)
7. [ ] Test window resize
8. [ ] Test color customization

### Mac Testing (Friend)
1. [ ] Build on Mac
2. [ ] Test launch (double-click .app)
3. [ ] Verify sample data loads
4. [ ] Test basic playback
5. [ ] Check UI rendering
6. [ ] Verify no crashes
7. [ ] Report any errors immediately

---

## Fallback Plan (If PyInstaller Fails)

### Simple Script Distribution
1. Create `setup.sh` for Mac
2. Bundle Python 3.12 portable (Windows)
3. Create judge instructions with screenshots
4. Pre-install dependencies in vendor folder
5. Use `python -m pip install --target=vendor -r requirements.txt`

**Risk Level:** HIGHER - More failure points

---

## Judge Instructions Template

```
TOYOTA RACE SUITE - QUICK START
================================

WINDOWS:
1. Unzip folder
2. Double-click "ToyotaRaceSuite.exe"
3. Done! App will load with sample data

MAC:
1. Unzip folder
2. Double-click "ToyotaRaceSuite.app"
3. If security warning: Right-click > Open
4. Done! App will load with sample data

FIRST-TIME MAC USERS:
- Go to System Preferences > Security & Privacy
- Click "Open Anyway" if prompted

CONTROLS:
- Spacebar: Play/Pause
- Click cars: Select vehicle
- Scroll: Zoom in/out
- Right-drag: Pan view
- Number keys 1-9: Playback speed

LOADING YOUR OWN DATA:
- Drag and drop CSV file onto window (feature disabled for stability in v1.0)
- Or place CSV in data/raw/ folder and restart

REQUIREMENTS:
- Windows 10+ or macOS 10.13+
- 8GB RAM (16GB recommended)
- OpenGL 3.3+ compatible GPU

TROUBLESHOOTING:
- Windows: Run as Administrator if blocked
- Mac: Check Security & Privacy settings
- Both: Ensure data/sample folder exists

FOR HELP: [Your contact info]
```

---

## Critical Files to Create

1. **run.sh** - Unix launcher script
2. **run.command** - Mac double-clickable launcher
3. **toyota-race-suite.spec** - PyInstaller configuration
4. **build_windows.bat** - Automated Windows build
5. **build_mac.sh** - Mac build script for friend
6. **JUDGES_README.txt** - Dead simple instructions
7. **MAC_BUILD_INSTRUCTIONS.md** - Step-by-step for friend

---

## Timeline Estimate

| Task | Time | Priority |
|------|------|----------|
| Create launcher scripts | 15 min | P0 |
| Fix pywin32 imports | 10 min | P0 |
| Create PyInstaller spec | 20 min | P0 |
| Build Windows .exe | 5 min | P0 |
| Test Windows build | 10 min | P0 |
| Create Mac build instructions | 15 min | P0 |
| Send to Mac friend | 5 min | P0 |
| Create judge documentation | 20 min | P1 |
| Test and iterate | 30 min | P1 |
| **TOTAL** | **~2 hours** | |

---

## Risk Assessment

### High Risk Items
1. ❌ **Mac build untested** - Mitigate: Detailed friend instructions + testing checklist
2. ❌ **PyInstaller hidden imports** - Mitigate: Test thoroughly, common scipy/pandas imports included
3. ❌ **Large file size** - Mitigate: Acceptable for hackathon, ensure fast download link

### Medium Risk Items
1. ⚠️ **DearPyGUI on Mac** - Should work, but test ASAP
2. ⚠️ **Sample data size** - May need external download link
3. ⚠️ **Mac security warnings** - Documented in judge instructions

### Low Risk Items
1. ✅ **Code is cross-platform** - Already uses os.path.join
2. ✅ **No Windows-specific features enabled** - Drag-drop disabled
3. ✅ **Dependencies are pure Python or have Mac support**

---

## Communication with Mac Friend

### What to Send
1. Build script with exact commands
2. This planning document
3. Testing checklist
4. Expected output screenshots
5. Your phone number for emergency calls

### What to Request Back
1. Built .app file (zipped)
2. Screenshot of app running
3. Any error messages
4. Build log output
5. Confirmation of all tests passing

---

## Post-Build Checklist

### Before Sending to Judges
- [ ] Windows .exe tested and working
- [ ] Mac .app tested by friend (screenshots received)
- [ ] Sample data included and loading correctly
- [ ] README is crystal clear (test on non-technical person)
- [ ] File sizes reasonable for download
- [ ] Backup plan prepared (script distribution)
- [ ] Contact information included
- [ ] All files zipped and ready

### Submission Package
```
ToyotaRaceSuite-Submission.zip
├── ToyotaRaceSuite-Windows.zip
├── ToyotaRaceSuite-Mac.zip
├── START_HERE.txt
├── README.md
├── TROUBLESHOOTING.txt
└── source-code.zip (optional)
```

---

## Emergency Contacts

**Build Issues:** Need Mac build ASAP - friend on standby
**Testing:** Can test Windows immediately
**Deadline:** Last day - no room for major rewrites

---

## Success Criteria

✅ **MUST HAVE:**
1. Double-click to run on Windows
2. Double-click to run on Mac
3. Sample data loads automatically
4. No installation required
5. Clear judge instructions

✅ **NICE TO HAVE:**
1. Small file size
2. Fast startup
3. Professional icon
4. Installer package

---

## Next Steps (Immediate)

1. **CONFIRM APPROACH:** User approval for PyInstaller strategy
2. **START IMPLEMENTATION:** Create launcher scripts
3. **BUILD WINDOWS:** PyInstaller on dev machine
4. **TEST IMMEDIATELY:** Verify Windows build works
5. **PREP MAC BUILD:** Send instructions to friend
6. **PARALLEL TRACK:** Create judge documentation while friend builds

---

## Notes

- **Current state:** Development environment works on Windows
- **Git status:** Clean working directory, on main branch
- **Venv:** Active with all dependencies installed
- **Sample data:** Available in data/sample/ (verified)
- **Assets:** Present in assets/ folder (need to verify contents)

---

## IMPORTANT REMINDERS

🚨 **This is the last day of a 25-day hackathon**
🚨 **If judges can't run it, instant disqualification**
🚨 **Reliability > Features > Performance > File Size**
🚨 **Test everything twice**
🚨 **Have backup plan ready**

---

**END OF PLAN - READY TO EXECUTE**

#!/bin/bash
# Toyota Race Suite - macOS Build Script
# Builds standalone .app bundle using PyInstaller

echo "============================================"
echo "  Toyota Race Suite - macOS Build"
echo "============================================"
echo ""

cd "$(dirname "$0")"

# Check if venv exists
if [ ! -f "venv/bin/python" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if PyInstaller is installed
if ! venv/bin/pip show pyinstaller > /dev/null 2>&1; then
    echo "PyInstaller not found. Installing..."
    venv/bin/pip install pyinstaller
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install PyInstaller"
        exit 1
    fi
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist ToyotaRaceSuite.app

echo ""
echo "Building .app bundle (this may take 2-5 minutes)..."
echo ""

# Run PyInstaller
venv/bin/pyinstaller --clean --noconfirm ToyotaRaceSuite.spec

if [ $? -ne 0 ]; then
    echo ""
    echo "============================================"
    echo "  BUILD FAILED!"
    echo "============================================"
    echo ""
    exit 1
fi

# Check if app bundle was created
if [ ! -d "dist/ToyotaRaceSuite.app" ]; then
    echo ""
    echo "ERROR: App bundle not found in dist folder"
    exit 1
fi

echo ""
echo "============================================"
echo "  BUILD SUCCESSFUL!"
echo "============================================"
echo ""
echo "App bundle created: dist/ToyotaRaceSuite.app"
echo "Size: $(du -sh dist/ToyotaRaceSuite.app | cut -f1)"
echo ""
echo "You can now:"
echo "  1. Test: Open dist/ToyotaRaceSuite.app"
echo "  2. Distribute: Copy dist/ToyotaRaceSuite.app to release folder"
echo ""
echo "To create a DMG for distribution:"
echo "  hdiutil create -volname ToyotaRaceSuite -srcfolder dist/ToyotaRaceSuite.app -ov -format UDZO ToyotaRaceSuite.dmg"
echo ""

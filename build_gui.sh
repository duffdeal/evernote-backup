#!/bin/bash
# Build script for Evernote Backup GUI on Linux/macOS

set -e

echo "Building Evernote Backup GUI..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.9 or higher"
    exit 1
fi

echo "Installing dependencies..."
pip install -e .
pip install pyinstaller

echo
echo "Building executable with PyInstaller..."
pyinstaller evernote-backup-gui.spec --clean --noconfirm

echo
echo "============================================"
echo "Build completed successfully!"
echo
echo "Executable location: dist/EvernoteBackup"
echo "============================================"

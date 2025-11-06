@echo off
REM Build script for Evernote Backup GUI on Windows

echo Building Evernote Backup GUI...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9 or higher from python.org
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -e .
pip install pyinstaller

echo.
echo Building executable with PyInstaller...
pyinstaller evernote-backup-gui.spec --clean --noconfirm

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo ============================================
echo Build completed successfully!
echo.
echo Executable location: dist\EvernoteBackup.exe
echo ============================================
echo.
pause

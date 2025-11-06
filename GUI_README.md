# Evernote Backup GUI

A Windows GUI application for backing up and exporting Evernote notes.

## Features

- **Database Setup**: Initialize your backup database with OAuth or password authentication
- **Sync Notes**: Download and sync all your Evernote notes to a local SQLite database
- **Export Notes**: Export backed-up notes to ENEX format for archival or migration
- **Tools**: Database management, reauthorization, integrity checking, and more

## Installation

### Option 1: Run from Source

1. Ensure Python 3.9 or higher is installed
2. Install the package:
   ```bash
   pip install -e .
   ```
3. Run the GUI:
   ```bash
   evernote-backup-gui
   ```
   or
   ```bash
   python -m evernote_backup.gui
   ```

### Option 2: Build Windows Executable

1. Ensure Python 3.9 or higher is installed
2. Run the build script:
   ```cmd
   build_gui.bat
   ```
3. The executable will be created at `dist\EvernoteBackup.exe`
4. Double-click to run!

### Option 3: Download Pre-built Executable (if available)

Download the `EvernoteBackup.exe` file and run it directly - no installation needed!

## Usage Guide

### 1. Setup (First Time)

1. Open the **Setup** tab
2. Choose a location for your database file (default: `en_backup.db`)
3. Select your backend:
   - `evernote` - For international Evernote accounts
   - `china` - For Yinxiang (China) accounts
4. Choose authentication method:
   - **OAuth** (recommended): Your browser will open for authorization
   - **Password**: Enter username and password (Yinxiang only)
5. Click **Initialize Database**
6. Follow the authentication prompts

### 2. Sync Your Notes

1. Open the **Sync** tab
2. Select your database file
3. Adjust sync settings if needed:
   - **Max Chunk Results**: Notes per API request (default: 200)
   - **Download Workers**: Parallel download threads (default: 5)
   - **Memory Limit**: Cache memory limit in MB (default: 256)
   - **Include tasks**: Check to also sync tasks and reminders
4. Click **Start Sync**
5. Monitor progress in the log output

### 3. Export Your Notes

1. Open the **Export** tab
2. Select your database file
3. Choose output directory for ENEX files
4. Configure export options:
   - **Single note files**: Export each note as a separate file
   - **Include trash**: Include deleted notes
   - **No export date**: Don't add timestamps to filenames
   - **Overwrite**: Overwrite existing ENEX files
5. Click **Start Export**
6. Your notes will be exported as ENEX files

### 4. Tools & Management

The **Tools** tab provides additional utilities:

- **Reauth**: Refresh your authentication token
- **Check Database**: Verify database integrity
- **List Notebooks**: View all notebooks in your database
- **Test Connection**: Test connection to Evernote servers

## Tips

- **Regular Backups**: Run sync regularly to keep your backup up-to-date
- **Incremental Sync**: Subsequent syncs only download new/changed notes
- **Database Location**: Keep your database file in a safe location, consider backing it up
- **ENEX Format**: ENEX files can be imported back into Evernote or other note-taking apps

## Troubleshooting

### OAuth Not Working

- Ensure your firewall allows connections to localhost:10500
- Try a different port in the OAuth Port field
- Check that your default browser is set correctly

### Sync Errors

- Click **Reauth** in the Tools tab to refresh your token
- Check your internet connection
- Verify you have enough disk space

### Database Errors

- Use **Check Database** in the Tools tab
- If corrupted, you may need to reinitialize and sync again

## Building from Source

### Requirements

- Python 3.9 or higher
- pip (Python package manager)
- PyInstaller (for building executable)

### Build Commands

**Windows:**
```cmd
build_gui.bat
```

**Linux/macOS:**
```bash
chmod +x build_gui.sh
./build_gui.sh
```

### Manual Build

```bash
# Install dependencies
pip install -e .
pip install pyinstaller

# Build executable
pyinstaller evernote-backup-gui.spec --clean --noconfirm
```

The executable will be created in the `dist/` directory.

## Technical Details

- **GUI Framework**: tkinter (built-in Python GUI library)
- **Database**: SQLite
- **Packaging**: PyInstaller
- **Threading**: Operations run in background threads to prevent UI freezing
- **Logging**: Real-time log output for all operations

## Command-Line Alternative

This package also includes a full-featured CLI tool. See the main README.md for details:

```bash
evernote-backup --help
```

## License

MIT License - See LICENSE file for details

## Support

For issues, feature requests, or contributions, please visit:
https://github.com/vzhd1701/evernote-backup

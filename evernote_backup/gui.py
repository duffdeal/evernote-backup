"""Evernote Backup GUI - Windows application interface."""

import io
import logging
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional


class FakeTTY(io.StringIO):
    """A StringIO that pretends to be a TTY for GUI mode.

    This allows OAuth and other interactive features to work in GUI mode
    by making the code think it's running in an interactive terminal.
    """

    def __init__(self) -> None:
        super().__init__()
        self._log_widget = None

    def set_log_widget(self, widget: Optional['scrolledtext.ScrolledText']) -> None:
        """Set the log widget to write output to."""
        self._log_widget = widget

    def write(self, s: str) -> int:
        """Write to both the buffer and the log widget if available."""
        result = super().write(s)
        if self._log_widget and s.strip():  # Only log non-empty strings
            try:
                self._log_widget.after(0, self._append_to_widget, s)
            except Exception:
                pass  # Ignore errors if widget is not available
        return result

    def _append_to_widget(self, msg: str) -> None:
        """Append text to widget in main thread."""
        try:
            self._log_widget.configure(state="normal")
            self._log_widget.insert(tk.END, msg)
            if not msg.endswith('\n'):
                self._log_widget.insert(tk.END, '\n')
            self._log_widget.see(tk.END)
            self._log_widget.configure(state="disabled")
        except Exception:
            pass  # Ignore errors if widget is not available

    def isatty(self) -> bool:
        """Return True to indicate this is a TTY."""
        return True


# Fix for GUI mode: ensure stdout/stderr are not None and pretend to be TTY
# This is necessary when running as a GUI app on Windows
if sys.stdout is None:
    sys.stdout = FakeTTY()
if sys.stderr is None:
    sys.stderr = FakeTTY()
if not sys.stdout.isatty():
    # Replace with FakeTTY if not already a TTY
    sys.stdout = FakeTTY()
if not sys.stderr.isatty():
    sys.stderr = FakeTTY()

from evernote_backup import cli_app
from evernote_backup.cli_app_util import ProgramTerminatedError
from evernote_backup.config_defaults import (
    BACKEND,
    DATABASE_NAME,
    NETWORK_ERROR_RETRY_COUNT,
    OAUTH_HOST,
    OAUTH_LOCAL_PORT,
    SYNC_CHUNK_MAX_RESULTS,
    SYNC_DOWNLOAD_CACHE_MEMORY_LIMIT,
    SYNC_MAX_DOWNLOAD_WORKERS,
)

# Import click for context management
import click


def create_click_context():
    """Create a minimal Click context for GUI mode.

    This is necessary because cli_app functions expect to be running
    in a Click context to access parameters like 'verbose' and 'quiet'.
    """
    @click.command()
    @click.option('--verbose', is_flag=True, default=False)
    @click.option('--quiet', is_flag=True, default=False)
    def dummy_command(verbose, quiet):
        pass

    return dummy_command.make_context('gui', ['--quiet'])


# Set up logging for GUI
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """Custom logging handler to redirect logs to GUI text widget."""

    def __init__(self, text_widget: scrolledtext.ScrolledText) -> None:
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to the text widget."""
        msg = self.format(record)
        self.text_widget.after(0, self._append_text, msg)

    def _append_text(self, msg: str) -> None:
        """Append text to widget in main thread."""
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, msg + "\n")
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")


class EvernoteBackupGUI:
    """Main GUI application for Evernote Backup."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the GUI application."""
        self.root = root
        self.root.title("Evernote Backup")
        self.root.geometry("800x600")

        # Set icon if available
        try:
            # This will work when packaged with PyInstaller
            if getattr(sys, "frozen", False):
                icon_path = Path(sys._MEIPASS) / "icon.ico"  # type: ignore[attr-defined]
                if icon_path.exists():
                    self.root.iconbitmap(str(icon_path))
        except Exception:
            pass

        # Configure root grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook)
        self.sync_tab = ttk.Frame(self.notebook)
        self.export_tab = ttk.Frame(self.notebook)
        self.tools_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.setup_tab, text="Setup")
        self.notebook.add(self.sync_tab, text="Sync")
        self.notebook.add(self.export_tab, text="Export")
        self.notebook.add(self.tools_tab, text="Tools")

        # Initialize tabs
        self.create_setup_tab()
        self.create_sync_tab()
        self.create_export_tab()
        self.create_tools_tab()

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        status_bar.grid(row=1, column=0, sticky="ew", padx=5, pady=2)

        # Track running operations
        self.operation_running = False

    def create_setup_tab(self) -> None:
        """Create the database setup tab."""
        frame = self.setup_tab
        frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Title
        title = ttk.Label(
            frame, text="Initialize Database", font=("", 12, "bold")
        )
        title.grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Database path
        ttk.Label(frame, text="Database Path:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.db_path_var = tk.StringVar(value=DATABASE_NAME)
        ttk.Entry(frame, textvariable=self.db_path_var, width=50).grid(
            row=row, column=1, sticky="ew", padx=5, pady=5
        )
        ttk.Button(frame, text="Browse...", command=self.browse_database).grid(
            row=row, column=2, padx=5, pady=5
        )
        row += 1

        # Backend
        ttk.Label(frame, text="Backend:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.backend_var = tk.StringVar(value=BACKEND)
        backend_combo = ttk.Combobox(
            frame,
            textvariable=self.backend_var,
            values=["evernote", "china", "china:sandbox"],
            state="readonly",
        )
        backend_combo.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Auth method
        ttk.Label(frame, text="Authentication:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.auth_method_var = tk.StringVar(value="oauth")
        auth_frame = ttk.Frame(frame)
        auth_frame.grid(row=row, column=1, sticky="w", padx=5, pady=5)
        ttk.Radiobutton(
            auth_frame, text="OAuth (Browser)", variable=self.auth_method_var, value="oauth"
        ).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(
            auth_frame, text="Password (Yinxiang)", variable=self.auth_method_var, value="password"
        ).pack(side=tk.LEFT, padx=5)
        row += 1

        # Username (for password auth)
        ttk.Label(frame, text="Username:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.username_var = tk.StringVar()
        self.username_entry = ttk.Entry(frame, textvariable=self.username_var, width=50)
        self.username_entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        ttk.Label(frame, text="(For password auth)").grid(
            row=row, column=2, sticky="w", padx=5
        )
        row += 1

        # Password (for password auth)
        ttk.Label(frame, text="Password:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(frame, textvariable=self.password_var, show="*", width=50)
        self.password_entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
        ttk.Label(frame, text="(For password auth)").grid(
            row=row, column=2, sticky="w", padx=5
        )
        row += 1

        # OAuth settings
        ttk.Label(frame, text="OAuth Port:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.oauth_port_var = tk.StringVar(value=str(OAUTH_LOCAL_PORT))
        ttk.Entry(frame, textvariable=self.oauth_port_var, width=20).grid(
            row=row, column=1, sticky="w", padx=5, pady=5
        )
        row += 1

        # Force overwrite
        self.force_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Force overwrite existing database", variable=self.force_var
        ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Initialize button
        ttk.Button(
            frame, text="Initialize Database", command=self.init_database
        ).grid(row=row, column=1, pady=20)
        row += 1

        # Log output
        ttk.Label(frame, text="Log Output:").grid(
            row=row, column=0, sticky="nw", padx=5, pady=5
        )
        row += 1
        self.setup_log = scrolledtext.ScrolledText(
            frame, height=10, state="disabled", wrap=tk.WORD
        )
        self.setup_log.grid(
            row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5
        )
        frame.grid_rowconfigure(row, weight=1)

    def create_sync_tab(self) -> None:
        """Create the sync tab."""
        frame = self.sync_tab
        frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Title
        title = ttk.Label(frame, text="Sync Notes", font=("", 12, "bold"))
        title.grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Database path
        ttk.Label(frame, text="Database Path:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.sync_db_path_var = tk.StringVar(value=DATABASE_NAME)
        ttk.Entry(frame, textvariable=self.sync_db_path_var, width=50).grid(
            row=row, column=1, sticky="ew", padx=5, pady=5
        )
        ttk.Button(frame, text="Browse...", command=self.browse_sync_database).grid(
            row=row, column=2, padx=5, pady=5
        )
        row += 1

        # Sync options
        ttk.Label(frame, text="Max Chunk Results:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.max_chunk_var = tk.StringVar(value=str(SYNC_CHUNK_MAX_RESULTS))
        ttk.Entry(frame, textvariable=self.max_chunk_var, width=20).grid(
            row=row, column=1, sticky="w", padx=5, pady=5
        )
        row += 1

        ttk.Label(frame, text="Download Workers:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.workers_var = tk.StringVar(value=str(SYNC_MAX_DOWNLOAD_WORKERS))
        ttk.Entry(frame, textvariable=self.workers_var, width=20).grid(
            row=row, column=1, sticky="w", padx=5, pady=5
        )
        row += 1

        ttk.Label(frame, text="Memory Limit (MB):").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.memory_limit_var = tk.StringVar(
            value=str(SYNC_DOWNLOAD_CACHE_MEMORY_LIMIT)
        )
        ttk.Entry(frame, textvariable=self.memory_limit_var, width=20).grid(
            row=row, column=1, sticky="w", padx=5, pady=5
        )
        row += 1

        # Include tasks
        self.include_tasks_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Include tasks and reminders", variable=self.include_tasks_var
        ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Sync button
        ttk.Button(frame, text="Start Sync", command=self.start_sync).grid(
            row=row, column=1, pady=20
        )
        row += 1

        # Progress bar
        ttk.Label(frame, text="Progress:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.sync_progress = ttk.Progressbar(
            frame, mode="indeterminate", length=400
        )
        self.sync_progress.grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=5
        )
        row += 1

        # Log output
        ttk.Label(frame, text="Log Output:").grid(
            row=row, column=0, sticky="nw", padx=5, pady=5
        )
        row += 1
        self.sync_log = scrolledtext.ScrolledText(
            frame, height=10, state="disabled", wrap=tk.WORD
        )
        self.sync_log.grid(
            row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5
        )
        frame.grid_rowconfigure(row, weight=1)

    def create_export_tab(self) -> None:
        """Create the export tab."""
        frame = self.export_tab
        frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Title
        title = ttk.Label(frame, text="Export Notes", font=("", 12, "bold"))
        title.grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Database path
        ttk.Label(frame, text="Database Path:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.export_db_path_var = tk.StringVar(value=DATABASE_NAME)
        ttk.Entry(frame, textvariable=self.export_db_path_var, width=50).grid(
            row=row, column=1, sticky="ew", padx=5, pady=5
        )
        ttk.Button(frame, text="Browse...", command=self.browse_export_database).grid(
            row=row, column=2, padx=5, pady=5
        )
        row += 1

        # Output path
        ttk.Label(frame, text="Output Directory:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.output_path_var = tk.StringVar(value="./export")
        ttk.Entry(frame, textvariable=self.output_path_var, width=50).grid(
            row=row, column=1, sticky="ew", padx=5, pady=5
        )
        ttk.Button(frame, text="Browse...", command=self.browse_output_dir).grid(
            row=row, column=2, padx=5, pady=5
        )
        row += 1

        # Export options
        self.single_notes_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Export as single note files", variable=self.single_notes_var
        ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        self.include_trash_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Include trash", variable=self.include_trash_var
        ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        self.no_export_date_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="No export date in filenames", variable=self.no_export_date_var
        ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            frame, text="Overwrite existing files", variable=self.overwrite_var
        ).grid(row=row, column=1, sticky="w", padx=5, pady=5)
        row += 1

        # Export button
        ttk.Button(frame, text="Start Export", command=self.start_export).grid(
            row=row, column=1, pady=20
        )
        row += 1

        # Progress bar
        ttk.Label(frame, text="Progress:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.export_progress = ttk.Progressbar(
            frame, mode="indeterminate", length=400
        )
        self.export_progress.grid(
            row=row, column=1, columnspan=2, sticky="ew", padx=5, pady=5
        )
        row += 1

        # Log output
        ttk.Label(frame, text="Log Output:").grid(
            row=row, column=0, sticky="nw", padx=5, pady=5
        )
        row += 1
        self.export_log = scrolledtext.ScrolledText(
            frame, height=10, state="disabled", wrap=tk.WORD
        )
        self.export_log.grid(
            row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5
        )
        frame.grid_rowconfigure(row, weight=1)

    def create_tools_tab(self) -> None:
        """Create the tools/manage tab."""
        frame = self.tools_tab
        frame.grid_columnconfigure(1, weight=1)

        row = 0

        # Title
        title = ttk.Label(frame, text="Tools & Management", font=("", 12, "bold"))
        title.grid(row=row, column=0, columnspan=3, pady=10)
        row += 1

        # Database path
        ttk.Label(frame, text="Database Path:").grid(
            row=row, column=0, sticky="w", padx=5, pady=5
        )
        self.tools_db_path_var = tk.StringVar(value=DATABASE_NAME)
        ttk.Entry(frame, textvariable=self.tools_db_path_var, width=50).grid(
            row=row, column=1, sticky="ew", padx=5, pady=5
        )
        ttk.Button(frame, text="Browse...", command=self.browse_tools_database).grid(
            row=row, column=2, padx=5, pady=5
        )
        row += 1

        # Buttons
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=20)

        ttk.Button(button_frame, text="Reauth", command=self.reauth_database).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Check Database", command=self.check_database).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="List Notebooks", command=self.list_notebooks).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Test Connection", command=self.test_connection).pack(
            side=tk.LEFT, padx=5
        )
        row += 1

        # Log output
        ttk.Label(frame, text="Log Output:").grid(
            row=row, column=0, sticky="nw", padx=5, pady=5
        )
        row += 1
        self.tools_log = scrolledtext.ScrolledText(
            frame, height=15, state="disabled", wrap=tk.WORD
        )
        self.tools_log.grid(
            row=row, column=0, columnspan=3, sticky="nsew", padx=5, pady=5
        )
        frame.grid_rowconfigure(row, weight=1)

    # Browse functions
    def browse_database(self) -> None:
        """Browse for database file."""
        filename = filedialog.asksaveasfilename(
            title="Select Database File",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
        )
        if filename:
            self.db_path_var.set(filename)

    def browse_sync_database(self) -> None:
        """Browse for sync database file."""
        filename = filedialog.askopenfilename(
            title="Select Database File",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
        )
        if filename:
            self.sync_db_path_var.set(filename)

    def browse_export_database(self) -> None:
        """Browse for export database file."""
        filename = filedialog.askopenfilename(
            title="Select Database File",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
        )
        if filename:
            self.export_db_path_var.set(filename)

    def browse_tools_database(self) -> None:
        """Browse for tools database file."""
        filename = filedialog.askopenfilename(
            title="Select Database File",
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")],
        )
        if filename:
            self.tools_db_path_var.set(filename)

    def browse_output_dir(self) -> None:
        """Browse for output directory."""
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_path_var.set(dirname)

    # Operation functions
    def init_database(self) -> None:
        """Initialize the database."""
        if self.operation_running:
            messagebox.showwarning("Operation Running", "An operation is already in progress.")
            return

        db_path = Path(self.db_path_var.get())
        backend = self.backend_var.get()
        auth_method = self.auth_method_var.get()
        force = self.force_var.get()

        # Clear log
        self.setup_log.configure(state="normal")
        self.setup_log.delete(1.0, tk.END)
        self.setup_log.configure(state="disabled")

        # Set up logging
        log_handler = LogHandler(self.setup_log)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        # Add handler to root logger to capture all evernote_backup module logs
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.INFO)

        # Connect stdout to log widget to capture click.echo() messages
        if isinstance(sys.stdout, FakeTTY):
            sys.stdout.set_log_widget(self.setup_log)

        def run_init() -> None:
            """Run init in thread."""
            self.operation_running = True
            self.status_var.set("Initializing database...")
            try:
                # Prepare arguments
                user = self.username_var.get() if auth_method == "password" else None
                password = self.password_var.get() if auth_method == "password" else None
                oauth_port = int(self.oauth_port_var.get())

                if auth_method == "oauth":
                    logger.info("Starting OAuth authentication...")
                    logger.info("Your browser will open for authorization.")
                    logger.info("Please complete the authorization in your browser.")
                    logger.info(f"The callback will be received on localhost:{oauth_port}")
                else:
                    logger.info("Starting password authentication...")

                # Create Click context for GUI mode
                ctx = create_click_context()
                with ctx:
                    cli_app.init_db(
                        database=db_path,
                        auth_user=user,
                        auth_password=password,
                        auth_oauth_port=oauth_port,
                        auth_oauth_host=OAUTH_HOST,
                        auth_token=None,
                        backend=backend,
                        network_retry_count=NETWORK_ERROR_RETRY_COUNT,
                        use_system_ssl_ca=False,
                        custom_api_data=None,
                        force=force,
                    )
                self.status_var.set("Database initialized successfully!")
                messagebox.showinfo("Success", "Database initialized successfully!")
            except Exception as e:
                logger.exception("Error initializing database")
                self.status_var.set(f"Error: {e}")
                messagebox.showerror("Error", f"Failed to initialize database:\n{e}")
            finally:
                self.operation_running = False
                root_logger.removeHandler(log_handler)
                # Disconnect stdout from log widget
                if isinstance(sys.stdout, FakeTTY):
                    sys.stdout.set_log_widget(None)

        thread = threading.Thread(target=run_init, daemon=True)
        thread.start()

    def start_sync(self) -> None:
        """Start syncing notes."""
        if self.operation_running:
            messagebox.showwarning("Operation Running", "An operation is already in progress.")
            return

        db_path = Path(self.sync_db_path_var.get())
        if not db_path.exists():
            messagebox.showerror("Error", "Database file does not exist. Please initialize it first.")
            return

        # Clear log
        self.sync_log.configure(state="normal")
        self.sync_log.delete(1.0, tk.END)
        self.sync_log.configure(state="disabled")

        # Set up logging
        log_handler = LogHandler(self.sync_log)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.INFO)

        # Connect stdout to log widget
        if isinstance(sys.stdout, FakeTTY):
            sys.stdout.set_log_widget(self.sync_log)

        # Start progress bar
        self.sync_progress.start()

        def run_sync() -> None:
            """Run sync in thread."""
            self.operation_running = True
            self.status_var.set("Syncing notes...")
            try:
                max_chunk = int(self.max_chunk_var.get())
                workers = int(self.workers_var.get())
                memory_limit = int(self.memory_limit_var.get())
                include_tasks = self.include_tasks_var.get()

                # Create Click context for GUI mode
                ctx = create_click_context()
                with ctx:
                    cli_app.sync(
                        database=db_path,
                        max_chunk_results=max_chunk,
                        max_download_workers=workers,
                        download_cache_memory_limit=memory_limit,
                        network_retry_count=NETWORK_ERROR_RETRY_COUNT,
                        use_system_ssl_ca=False,
                        include_tasks=include_tasks,
                        token=None,
                    )
                self.status_var.set("Sync completed successfully!")
                messagebox.showinfo("Success", "Sync completed successfully!")
            except Exception as e:
                logger.exception("Error syncing notes")
                self.status_var.set(f"Error: {e}")
                messagebox.showerror("Error", f"Failed to sync notes:\n{e}")
            finally:
                self.operation_running = False
                self.sync_progress.stop()
                root_logger.removeHandler(log_handler)
                if isinstance(sys.stdout, FakeTTY):
                    sys.stdout.set_log_widget(None)

        thread = threading.Thread(target=run_sync, daemon=True)
        thread.start()

    def start_export(self) -> None:
        """Start exporting notes."""
        if self.operation_running:
            messagebox.showwarning("Operation Running", "An operation is already in progress.")
            return

        db_path = Path(self.export_db_path_var.get())
        if not db_path.exists():
            messagebox.showerror("Error", "Database file does not exist.")
            return

        output_path = Path(self.output_path_var.get())

        # Clear log
        self.export_log.configure(state="normal")
        self.export_log.delete(1.0, tk.END)
        self.export_log.configure(state="disabled")

        # Set up logging
        log_handler = LogHandler(self.export_log)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.INFO)

        # Connect stdout to log widget
        if isinstance(sys.stdout, FakeTTY):
            sys.stdout.set_log_widget(self.export_log)

        # Start progress bar
        self.export_progress.start()

        def run_export() -> None:
            """Run export in thread."""
            self.operation_running = True
            self.status_var.set("Exporting notes...")
            try:
                # Create Click context for GUI mode
                ctx = create_click_context()
                with ctx:
                    cli_app.export(
                        database=db_path,
                        output_path=output_path,
                        single_notes=self.single_notes_var.get(),
                        include_trash=self.include_trash_var.get(),
                        no_export_date=self.no_export_date_var.get(),
                        add_guid=False,
                        add_metadata=False,
                        overwrite=self.overwrite_var.get(),
                        notebooks=(),
                        tags=(),
                    )
                self.status_var.set("Export completed successfully!")
                messagebox.showinfo("Success", f"Export completed successfully!\nOutput: {output_path}")
            except Exception as e:
                logger.exception("Error exporting notes")
                self.status_var.set(f"Error: {e}")
                messagebox.showerror("Error", f"Failed to export notes:\n{e}")
            finally:
                self.operation_running = False
                self.export_progress.stop()
                root_logger.removeHandler(log_handler)
                if isinstance(sys.stdout, FakeTTY):
                    sys.stdout.set_log_widget(None)

        thread = threading.Thread(target=run_export, daemon=True)
        thread.start()

    def reauth_database(self) -> None:
        """Reauthorize the database."""
        if self.operation_running:
            messagebox.showwarning("Operation Running", "An operation is already in progress.")
            return

        db_path = Path(self.tools_db_path_var.get())
        if not db_path.exists():
            messagebox.showerror("Error", "Database file does not exist.")
            return

        # Clear log
        self.tools_log.configure(state="normal")
        self.tools_log.delete(1.0, tk.END)
        self.tools_log.configure(state="disabled")

        # Set up logging
        log_handler = LogHandler(self.tools_log)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.INFO)

        # Connect stdout to log widget
        if isinstance(sys.stdout, FakeTTY):
            sys.stdout.set_log_widget(self.tools_log)

        def run_reauth() -> None:
            """Run reauth in thread."""
            self.operation_running = True
            self.status_var.set("Reauthorizing...")
            try:
                # Create Click context for GUI mode
                ctx = create_click_context()
                with ctx:
                    cli_app.reauth(
                        database=db_path,
                        auth_user=None,
                        auth_password=None,
                        auth_oauth_port=OAUTH_LOCAL_PORT,
                        auth_oauth_host=OAUTH_HOST,
                        auth_token=None,
                        network_retry_count=NETWORK_ERROR_RETRY_COUNT,
                        use_system_ssl_ca=False,
                        custom_api_data=None,
                    )
                self.status_var.set("Reauthorization successful!")
                messagebox.showinfo("Success", "Reauthorization completed successfully!")
            except Exception as e:
                logger.exception("Error reauthorizing")
                self.status_var.set(f"Error: {e}")
                messagebox.showerror("Error", f"Failed to reauthorize:\n{e}")
            finally:
                self.operation_running = False
                root_logger.removeHandler(log_handler)
                if isinstance(sys.stdout, FakeTTY):
                    sys.stdout.set_log_widget(None)

        thread = threading.Thread(target=run_reauth, daemon=True)
        thread.start()

    def check_database(self) -> None:
        """Check database integrity."""
        db_path = Path(self.tools_db_path_var.get())
        if not db_path.exists():
            messagebox.showerror("Error", "Database file does not exist.")
            return

        # Clear log
        self.tools_log.configure(state="normal")
        self.tools_log.delete(1.0, tk.END)
        self.tools_log.configure(state="disabled")

        # Set up logging
        log_handler = LogHandler(self.tools_log)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.INFO)

        # Connect stdout to log widget
        if isinstance(sys.stdout, FakeTTY):
            sys.stdout.set_log_widget(self.tools_log)

        def run_check() -> None:
            """Run check in thread."""
            self.status_var.set("Checking database...")
            try:
                from evernote_backup.note_checker import check_notes

                # Create Click context for GUI mode
                ctx = create_click_context()
                with ctx:
                    with cli_app.get_storage(db_path) as storage:
                        issues = check_notes(storage)
                        if issues:
                            logger.warning(f"Found {len(issues)} issues in database")
                            for issue in issues:
                                logger.warning(f"  - {issue}")
                            messagebox.showwarning(
                                "Issues Found",
                                f"Found {len(issues)} issues in database. See log for details.",
                            )
                        else:
                            logger.info("Database check completed successfully - no issues found")
                            messagebox.showinfo("Success", "Database check completed successfully!")
                self.status_var.set("Check completed")
            except Exception as e:
                logger.exception("Error checking database")
                self.status_var.set(f"Error: {e}")
                messagebox.showerror("Error", f"Failed to check database:\n{e}")
            finally:
                root_logger.removeHandler(log_handler)
                if isinstance(sys.stdout, FakeTTY):
                    sys.stdout.set_log_widget(None)

        thread = threading.Thread(target=run_check, daemon=True)
        thread.start()

    def list_notebooks(self) -> None:
        """List notebooks in database."""
        db_path = Path(self.tools_db_path_var.get())
        if not db_path.exists():
            messagebox.showerror("Error", "Database file does not exist.")
            return

        # Clear log
        self.tools_log.configure(state="normal")
        self.tools_log.delete(1.0, tk.END)
        self.tools_log.configure(state="disabled")

        # Set up logging
        log_handler = LogHandler(self.tools_log)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.INFO)

        # Connect stdout to log widget
        if isinstance(sys.stdout, FakeTTY):
            sys.stdout.set_log_widget(self.tools_log)

        def run_list() -> None:
            """Run list in thread."""
            self.status_var.set("Listing notebooks...")
            try:
                from evernote_backup.note_lister import list_notebooks

                # Create Click context for GUI mode
                ctx = create_click_context()
                with ctx:
                    with cli_app.get_storage(db_path) as storage:
                        notebooks = list_notebooks(storage)
                        logger.info(f"Found {len(notebooks)} notebooks:")
                        for notebook in notebooks:
                            logger.info(f"  - {notebook.name} ({notebook.guid})")
                        messagebox.showinfo(
                            "Notebooks", f"Found {len(notebooks)} notebooks. See log for details."
                        )
                self.status_var.set("List completed")
            except Exception as e:
                logger.exception("Error listing notebooks")
                self.status_var.set(f"Error: {e}")
                messagebox.showerror("Error", f"Failed to list notebooks:\n{e}")
            finally:
                root_logger.removeHandler(log_handler)
                if isinstance(sys.stdout, FakeTTY):
                    sys.stdout.set_log_widget(None)

        thread = threading.Thread(target=run_list, daemon=True)
        thread.start()

    def test_connection(self) -> None:
        """Test connection to Evernote servers."""
        # Clear log
        self.tools_log.configure(state="normal")
        self.tools_log.delete(1.0, tk.END)
        self.tools_log.configure(state="disabled")

        # Set up logging
        log_handler = LogHandler(self.tools_log)
        log_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        root_logger = logging.getLogger()
        root_logger.addHandler(log_handler)
        root_logger.setLevel(logging.INFO)

        # Connect stdout to log widget
        if isinstance(sys.stdout, FakeTTY):
            sys.stdout.set_log_widget(self.tools_log)

        def run_test() -> None:
            """Run test in thread."""
            self.status_var.set("Testing connection...")
            try:
                # Create Click context for GUI mode
                ctx = create_click_context()
                with ctx:
                    cli_app.manage_ping(
                        backend=BACKEND,
                        network_retry_count=NETWORK_ERROR_RETRY_COUNT,
                        use_system_ssl_ca=False,
                    )
                logger.info("Connection test successful!")
                self.status_var.set("Connection test successful")
                messagebox.showinfo("Success", "Connection to Evernote servers successful!")
            except Exception as e:
                logger.exception("Error testing connection")
                self.status_var.set(f"Error: {e}")
                messagebox.showerror("Error", f"Failed to connect:\n{e}")
            finally:
                root_logger.removeHandler(log_handler)
                if isinstance(sys.stdout, FakeTTY):
                    sys.stdout.set_log_widget(None)

        thread = threading.Thread(target=run_test, daemon=True)
        thread.start()


def main() -> None:
    """Main entry point for GUI application."""
    root = tk.Tk()
    app = EvernoteBackupGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

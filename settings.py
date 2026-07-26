from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from database import db
from utils import (
    BACKUP_DIR,
    human_datetime,
    open_path,
    show_error,
    show_info,
)


class SettingsPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, style="TFrame")
        self.app = app
        self.current_password_var = tk.StringVar()
        self.new_password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        self.show_password_var = tk.BooleanVar(value=False)
        self.theme_var = tk.StringVar(value=app.theme_name)
        self.auto_backup_var = tk.BooleanVar(value=(db.get_setting("auto_backup", "1") or "1") == "1")
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, style="Card.TFrame", padding=16)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        ttk.Label(header, text="Settings", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Change password, toggle the theme, and manage database backups.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        body = ttk.Frame(self, style="TFrame")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        security = ttk.Frame(body, style="Card.TFrame", padding=20)
        security.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        security.columnconfigure(1, weight=1)

        ttk.Label(security, text="Security", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            security,
            text="Update the logged-in admin password securely.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))

        self._password_field(security, 2, "Current Password", self.current_password_var)
        self._password_field(security, 3, "New Password", self.new_password_var)
        self._password_field(security, 4, "Confirm Password", self.confirm_password_var)

        ttk.Checkbutton(
            security,
            text="Show password",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 12))

        ttk.Button(security, text="Change Password", style="Primary.TButton", command=self.change_password).grid(
            row=6, column=0, columnspan=2, sticky="ew"
        )

        system = ttk.Frame(body, style="Card.TFrame", padding=20)
        system.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        system.columnconfigure(1, weight=1)

        ttk.Label(system, text="System", style="Header.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            system,
            text="Adjust the theme, back up the database, or restore from a saved copy.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))

        ttk.Label(system, text="Theme", style="CardTitle.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 4))
        theme_box = ttk.Combobox(system, values=["light", "dark"], textvariable=self.theme_var, state="readonly")
        theme_box.grid(row=2, column=1, sticky="ew", pady=(8, 4))
        theme_box.bind("<<ComboboxSelected>>", self._apply_theme_change)

        ttk.Checkbutton(
            system,
            text="Auto backup on login",
            variable=self.auto_backup_var,
            command=self._apply_auto_backup_change,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 2))

        ttk.Button(system, text="Backup Now", style="Success.TButton", command=self.backup_database).grid(
            row=4, column=0, columnspan=2, sticky="ew", pady=(18, 6)
        )
        ttk.Button(system, text="Restore Backup", style="Ghost.TButton", command=self.restore_database).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=6
        )
        ttk.Button(system, text="Open Backups Folder", style="Ghost.TButton", command=lambda: open_path(BACKUP_DIR)).grid(
            row=6, column=0, columnspan=2, sticky="ew", pady=6
        )
        ttk.Label(system, text=f"Last saved: {human_datetime()}", style="Muted.TLabel").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(18, 0)
        )

        footer = ttk.Frame(self, style="Card.TFrame", padding=12)
        footer.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel").pack(anchor="w")

    def _password_field(self, parent, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="CardTitle.TLabel").grid(row=row, column=0, sticky="w", pady=(10, 4))
        entry = ttk.Entry(parent, textvariable=variable, show="*")
        entry.grid(row=row, column=1, sticky="ew", pady=(10, 4))
        if row == 2:
            self.current_password_entry = entry
        elif row == 3:
            self.new_password_entry = entry
        else:
            self.confirm_password_entry = entry

    def _toggle_password_visibility(self) -> None:
        show_value = "" if self.show_password_var.get() else "*"
        self.current_password_entry.configure(show=show_value)
        self.new_password_entry.configure(show=show_value)
        self.confirm_password_entry.configure(show=show_value)

    def _apply_theme_change(self, _event=None) -> None:
        self.app.set_theme(self.theme_var.get())
        self.status_var.set(f"Theme switched to {self.theme_var.get()}.")

    def _apply_auto_backup_change(self) -> None:
        db.set_setting("auto_backup", "1" if self.auto_backup_var.get() else "0")
        self.status_var.set("Auto backup setting updated.")

    def apply_theme(self, palette) -> None:
        self.theme_var.set(self.app.theme_name)

    def change_password(self) -> None:
        current_password = self.current_password_var.get()
        new_password = self.new_password_var.get()
        confirm = self.confirm_password_var.get()

        if not current_password or not new_password or not confirm:
            show_error("Validation Error", "All password fields are required.", self)
            return
        if new_password != confirm:
            show_error("Validation Error", "New passwords do not match.", self)
            return
        if len(new_password) < 8:
            show_error("Validation Error", "Password must be at least 8 characters long.", self)
            return

        try:
            db.change_password(self.app.user["id"], current_password, new_password)
            self.current_password_var.set("")
            self.new_password_var.set("")
            self.confirm_password_var.set("")
            show_info("Success", "Password changed successfully.", self)
            self.status_var.set("Password updated successfully.")
        except Exception as exc:
            show_error("Change Password Error", str(exc), self)

    def backup_database(self) -> None:
        destination = filedialog.asksaveasfilename(
            parent=self,
            title="Save Backup",
            defaultextension=".db",
            initialdir=str(BACKUP_DIR),
            initialfile=f"students_backup_{datetime.now():%Y%m%d_%H%M%S}.db",
            filetypes=[("SQLite Backup", "*.db"), ("All Files", "*.*")],
        )
        if not destination:
            return
        try:
            path = db.backup_database(destination)
            show_info("Backup Complete", f"Backup saved to:\n{path}", self)
            self.status_var.set(f"Backup created: {path.name}")
            open_path(path.parent)
        except Exception as exc:
            show_error("Backup Error", str(exc), self)

    def restore_database(self) -> None:
        source = filedialog.askopenfilename(
            parent=self,
            title="Select Backup File",
            initialdir=str(BACKUP_DIR),
            filetypes=[("SQLite Backup", "*.db"), ("All Files", "*.*")],
        )
        if not source:
            return
        if not messagebox.askyesno(
            "Confirm Restore",
            "Restoring will replace the current database. Continue?",
            parent=self,
        ):
            return
        try:
            path = db.restore_database(source)
            show_info("Restore Complete", "Database restored successfully.", self)
            self.status_var.set("Database restored successfully.")
            self.app.refresh_active_pages()
            open_path(path.parent)
        except Exception as exc:
            show_error("Restore Error", str(exc), self)

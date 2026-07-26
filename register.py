from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from database import db
from utils import (
    APP_NAME,
    SECURITY_QUESTIONS,
    center_window,
    configure_ttk_style,
    show_error,
    show_info,
)


class RegisterWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, on_success=None) -> None:
        master = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
        super().__init__(master)
        self.parent = master
        self.on_success = on_success
        self.title(f"Create Admin - {APP_NAME}")
        self.resizable(False, False)
        self.configure(bg="#f4f7fb")
        center_window(self, 560, 650)
        self.transient(master)
        self.grab_set()

        self.style = ttk.Style(self)
        self.palette = configure_ttk_style(self.style, db.get_setting("theme", "light") or "light")

        self.full_name_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.confirm_var = tk.StringVar()
        self.answer_var = tk.StringVar()
        self.question_var = tk.StringVar(value=SECURITY_QUESTIONS[0])
        self.show_password_var = tk.BooleanVar(value=False)

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self, style="Card.TFrame", padding=24)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(container, text="Create new admin", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="Set up the first administrator or add another secure account.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 16))

        form = ttk.Frame(container, style="Card.TFrame")
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        self._field(form, 0, "Full Name", self.full_name_var)
        self._field(form, 1, "Username", self.username_var)
        self._password_field(form, 2, "Password", self.password_var)
        self._password_field(form, 3, "Confirm Password", self.confirm_var)

        ttk.Label(form, text="Security Question", style="CardTitle.TLabel").grid(
            row=4, column=0, sticky="w", padx=(0, 12), pady=(10, 4)
        )
        question_box = ttk.Combobox(
            form,
            values=SECURITY_QUESTIONS,
            textvariable=self.question_var,
            state="readonly",
        )
        question_box.grid(row=4, column=1, sticky="ew", pady=(10, 4))

        ttk.Label(form, text="Security Answer", style="CardTitle.TLabel").grid(
            row=5, column=0, sticky="w", padx=(0, 12), pady=(10, 4)
        )
        ttk.Entry(form, textvariable=self.answer_var).grid(row=5, column=1, sticky="ew", pady=(10, 4))

        hint = (
            "Tip: use a strong password and an answer you will remember exactly."
        )
        ttk.Label(form, text=hint, style="Muted.TLabel", wraplength=460).grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(10, 16)
        )

        self.show_toggle = ttk.Checkbutton(
            form,
            text="Show password",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
        )
        self.show_toggle.grid(row=7, column=0, columnspan=2, sticky="w", pady=(0, 16))

        actions = ttk.Frame(container, style="Card.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="Create Admin", style="Primary.TButton", command=self.create_admin).pack(
            side="left", expand=True, fill="x", padx=(0, 8)
        )
        ttk.Button(actions, text="Cancel", style="Ghost.TButton", command=self.destroy).pack(
            side="left", expand=True, fill="x", padx=(8, 0)
        )

    def _field(self, parent, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="CardTitle.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=(10, 4)
        )
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=(10, 4))

    def _password_field(self, parent, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="CardTitle.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=(10, 4)
        )
        entry = ttk.Entry(parent, textvariable=variable, show="*")
        entry.grid(row=row, column=1, sticky="ew", pady=(10, 4))
        if row == 2:
            self.password_entry = entry
        else:
            self.confirm_entry = entry

    def _toggle_password_visibility(self) -> None:
        show_value = "" if self.show_password_var.get() else "*"
        self.password_entry.configure(show=show_value)
        self.confirm_entry.configure(show=show_value)

    def create_admin(self) -> None:
        full_name = self.full_name_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get()
        confirm = self.confirm_var.get()
        answer = self.answer_var.get().strip()
        question = self.question_var.get().strip()

        if not full_name or not username or not password or not confirm or not answer or not question:
            show_error("Validation Error", "Please complete all fields.", self)
            return
        if password != confirm:
            show_error("Validation Error", "Passwords do not match.", self)
            return
        if len(password) < 8:
            show_error("Validation Error", "Password must be at least 8 characters long.", self)
            return

        try:
            db.create_admin(full_name, username, password, question, answer)
            show_info("Success", "Admin account created successfully.", self)
            if self.on_success:
                self.on_success(username)
            self.destroy()
        except Exception as exc:
            show_error("Registration Error", str(exc), self)


class ForgotPasswordWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc) -> None:
        master = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
        super().__init__(master)
        self.parent = master
        self.title(f"Forgot Password - {APP_NAME}")
        self.resizable(False, False)
        self.configure(bg="#f4f7fb")
        center_window(self, 560, 620)
        self.transient(master)
        self.grab_set()

        self.style = ttk.Style(self)
        self.palette = configure_ttk_style(self.style, db.get_setting("theme", "light") or "light")

        self.username_var = tk.StringVar()
        self.question_var = tk.StringVar(value="Load your security question")
        self.answer_var = tk.StringVar()
        self.new_password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        self.show_password_var = tk.BooleanVar(value=False)
        self.admin_record = None

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self, style="Card.TFrame", padding=24)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(container, text="Reset password", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="Verify your security answer and choose a new password.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(4, 16))

        form = ttk.Frame(container, style="Card.TFrame")
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        self._field(form, 0, "Username", self.username_var)

        ttk.Button(form, text="Load Question", style="Ghost.TButton", command=self.load_question).grid(
            row=1, column=1, sticky="e", pady=(8, 4)
        )

        ttk.Label(form, text="Security Question", style="CardTitle.TLabel").grid(
            row=2, column=0, sticky="nw", padx=(0, 12), pady=(10, 4)
        )
        ttk.Label(
            form,
            textvariable=self.question_var,
            style="Muted.TLabel",
            wraplength=360,
        ).grid(row=2, column=1, sticky="w", pady=(10, 4))

        self._field(form, 3, "Security Answer", self.answer_var)
        self._password_field(form, 4, "New Password", self.new_password_var)
        self._password_field(form, 5, "Confirm Password", self.confirm_password_var)

        self.show_toggle = ttk.Checkbutton(
            form,
            text="Show password",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
        )
        self.show_toggle.grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 16))

        actions = ttk.Frame(container, style="Card.TFrame")
        actions.pack(fill="x")
        ttk.Button(actions, text="Reset Password", style="Primary.TButton", command=self.reset_password).pack(
            side="left", expand=True, fill="x", padx=(0, 8)
        )
        ttk.Button(actions, text="Close", style="Ghost.TButton", command=self.destroy).pack(
            side="left", expand=True, fill="x", padx=(8, 0)
        )

    def _field(self, parent, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="CardTitle.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=(10, 4)
        )
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=(10, 4))

    def _password_field(self, parent, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label, style="CardTitle.TLabel").grid(
            row=row, column=0, sticky="w", padx=(0, 12), pady=(10, 4)
        )
        entry = ttk.Entry(parent, textvariable=variable, show="*")
        entry.grid(row=row, column=1, sticky="ew", pady=(10, 4))
        if row == 4:
            self.new_password_entry = entry
        else:
            self.confirm_password_entry = entry

    def _toggle_password_visibility(self) -> None:
        show_value = "" if self.show_password_var.get() else "*"
        self.new_password_entry.configure(show=show_value)
        self.confirm_password_entry.configure(show=show_value)

    def load_question(self) -> None:
        username = self.username_var.get().strip()
        if not username:
            show_error("Validation Error", "Enter your username first.", self)
            return

        record = db.get_admin_by_username(username)
        if not record:
            show_error("Not Found", "No admin account matches that username.", self)
            return

        self.admin_record = record
        self.question_var.set(record["security_question"])
        show_info("Loaded", "Security question loaded successfully.", self)

    def reset_password(self) -> None:
        if not self.admin_record:
            self.load_question()
            if not self.admin_record:
                return

        answer = self.answer_var.get().strip()
        new_password = self.new_password_var.get()
        confirm = self.confirm_password_var.get()

        if not answer or not new_password or not confirm:
            show_error("Validation Error", "Please fill all fields.", self)
            return
        if new_password != confirm:
            show_error("Validation Error", "Passwords do not match.", self)
            return
        if len(new_password) < 8:
            show_error("Validation Error", "Password must be at least 8 characters long.", self)
            return

        try:
            db.reset_password_by_security(self.admin_record["username"], answer, new_password)
            show_info("Success", "Password reset successfully.", self)
            self.destroy()
        except Exception as exc:
            show_error("Reset Error", str(exc), self)

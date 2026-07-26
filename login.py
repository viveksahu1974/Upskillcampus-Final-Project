from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from database import db
from register import ForgotPasswordWindow, RegisterWindow
from utils import (
    APP_NAME,
    LOGO_PATH,
    center_window,
    configure_ttk_style,
    ensure_placeholder_assets,
    load_image,
    set_window_icon,
    show_error,
    show_info,
)


class LoginPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent)
        self.app = app
        self.theme_name = app.theme_name
        self.palette = configure_ttk_style(ttk.Style(self), self.theme_name)
        self.configure(style="TFrame")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.remember_var = tk.BooleanVar(value=False)
        self.show_password_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="")

        self._build_ui()
        self._load_saved_username()

    def _build_ui(self) -> None:
        ensure_placeholder_assets()
        root = self.winfo_toplevel()
        set_window_icon(root)

        shell = ttk.Frame(self, style="TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=5)
        shell.columnconfigure(1, weight=4)
        shell.rowconfigure(0, weight=1)

        self._build_brand_panel(shell)
        self._build_login_panel(shell)

    def _build_brand_panel(self, parent: ttk.Frame) -> None:
        palette = self.palette
        brand = tk.Frame(parent, bg=palette["sidebar_bg"])
        brand.grid(row=0, column=0, sticky="nsew")
        brand.grid_propagate(False)

        style = ttk.Style(self)
        style.configure("Brand.TLabel", background=palette["sidebar_bg"], foreground=palette["sidebar_fg"], font=("Segoe UI", 11))
        style.configure("BrandTitle.TLabel", background=palette["sidebar_bg"], foreground="white", font=("Segoe UI Semibold", 28))
        style.configure("BrandBig.TLabel", background=palette["sidebar_bg"], foreground="white", font=("Segoe UI Semibold", 18))
        style.configure("BrandMuted.TLabel", background=palette["sidebar_bg"], foreground="#cbd5e1", font=("Segoe UI", 10))
        style.configure("Brand.TFrame", background=palette["sidebar_bg"])

        brand.columnconfigure(0, weight=1)
        brand.rowconfigure(0, weight=1)

        inner = ttk.Frame(brand, style="Brand.TFrame")
        inner.place(relx=0.5, rely=0.5, anchor="center")
        inner.configure(style="TFrame")

        logo = load_image(LOGO_PATH, (130, 130))
        if logo is not None:
            logo_label = ttk.Label(inner, image=logo, style="Brand.TLabel")
            logo_label.image = logo
            logo_label.pack(pady=(0, 18))

        ttk.Label(inner, text=APP_NAME, style="BrandTitle.TLabel", justify="center").pack(pady=(0, 8))
        ttk.Label(inner, text="Premium student operations suite", style="BrandBig.TLabel", justify="center").pack(
            pady=(0, 8)
        )
        ttk.Label(
            inner,
            text="Secure login, elegant dashboard, quick reporting, and a responsive student workflow in one desktop app.",
            style="BrandMuted.TLabel",
            justify="center",
            wraplength=380,
        ).pack(pady=(0, 18))

        features = [
            "Secure password hashing and recovery",
            "Beautiful dashboard with live stats",
            "Student CRUD, reports, charts, and backups",
        ]
        for item in features:
            ttk.Label(inner, text=f"\u25AA {item}", style="Brand.TLabel", justify="left", wraplength=380).pack(
                anchor="w", pady=4
            )

    def _build_login_panel(self, parent: ttk.Frame) -> None:
        palette = self.palette
        form_shell = ttk.Frame(parent, style="TFrame", padding=24)
        form_shell.grid(row=0, column=1, sticky="nsew")
        form_shell.columnconfigure(0, weight=1)
        form_shell.rowconfigure(0, weight=1)

        card = ttk.Frame(form_shell, style="Card.TFrame", padding=28)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.78)
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Welcome back", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            card,
            text="Log in to continue managing students and academic records.",
            style="Muted.TLabel",
            wraplength=420,
        ).grid(row=1, column=0, sticky="w", pady=(4, 18))

        form = ttk.Frame(card, style="Card.TFrame")
        form.grid(row=2, column=0, sticky="nsew")
        form.columnconfigure(0, weight=1)

        ttk.Label(form, text="Username", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.username_entry = ttk.Entry(form, textvariable=self.username_var)
        self.username_entry.grid(row=1, column=0, sticky="ew", pady=(6, 12))

        ttk.Label(form, text="Password", style="CardTitle.TLabel").grid(row=2, column=0, sticky="w")
        password_frame = ttk.Frame(form, style="Card.TFrame")
        password_frame.grid(row=3, column=0, sticky="ew", pady=(6, 12))
        password_frame.columnconfigure(0, weight=1)
        self.password_entry = ttk.Entry(password_frame, textvariable=self.password_var, show="*")
        self.password_entry.grid(row=0, column=0, sticky="ew")
        self.toggle_btn = ttk.Checkbutton(
            password_frame,
            text="Show",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
        )
        self.toggle_btn.grid(row=0, column=1, padx=(8, 0))

        options = ttk.Frame(form, style="Card.TFrame")
        options.grid(row=4, column=0, sticky="ew", pady=(0, 16))
        options.columnconfigure(0, weight=1)
        ttk.Checkbutton(options, text="Remember me", variable=self.remember_var).grid(row=0, column=0, sticky="w")
        ttk.Button(options, text="Forgot password?", style="Ghost.TButton", command=self.open_forgot_password).grid(
            row=0, column=1, sticky="e"
        )

        ttk.Button(form, text="Login", style="Primary.TButton", command=self.login).grid(
            row=5, column=0, sticky="ew", pady=(0, 10)
        )
        ttk.Button(form, text="Register New Admin", style="Ghost.TButton", command=self.open_register).grid(
            row=6, column=0, sticky="ew"
        )

        ttk.Separator(card).grid(row=3, column=0, sticky="ew", pady=18)
        ttk.Label(card, textvariable=self.status_var, style="Muted.TLabel", wraplength=420).grid(
            row=4, column=0, sticky="w"
        )

        self.username_entry.bind("<Return>", lambda _event: self.login())
        self.password_entry.bind("<Return>", lambda _event: self.login())
        self._sync_startup_message()

    def _sync_startup_message(self) -> None:
        if db.has_admins():
            self.status_var.set("Use your admin credentials to continue.")
        else:
            self.status_var.set("No admin account exists yet. Create the first admin to begin.")

    def _load_saved_username(self) -> None:
        saved_username = db.get_setting("remember_username", "") or ""
        if saved_username:
            self.username_var.set(saved_username)
            self.remember_var.set(True)
            self.password_entry.focus_set()
        else:
            self.username_entry.focus_set()

    def _toggle_password_visibility(self) -> None:
        self.password_entry.configure(show="" if self.show_password_var.get() else "*")

    def open_register(self) -> None:
        def _remember_username(username: str) -> None:
            self.username_var.set(username)
            self.remember_var.set(True)
            self.password_var.set("")
            self.password_entry.focus_set()
            self.status_var.set("Admin account created. You can log in now.")

        RegisterWindow(self, on_success=_remember_username)

    def open_forgot_password(self) -> None:
        ForgotPasswordWindow(self)

    def login(self) -> None:
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            show_error("Validation Error", "Enter both username and password.", self)
            return

        admin = db.authenticate_admin(username, password)
        if not admin:
            show_error("Login Failed", "Invalid username or password.", self)
            return

        if self.remember_var.get():
            db.set_setting("remember_username", username)
        else:
            db.delete_setting("remember_username")

        show_info("Welcome", f"Hello {admin['full_name']}! Login successful.", self)
        self.app.show_dashboard(admin)

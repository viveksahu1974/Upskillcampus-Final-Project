from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import tkinter as tk
from tkinter import messagebox, ttk

from database import db
from report import ReportsPage
from settings import SettingsPage
from students import StudentsPage
from utils import (
    APP_NAME,
    LOGO_PATH,
    configure_ttk_style,
    draw_vertical_gradient,
    human_datetime,
    load_image,
    maximize_window,
    open_path,
    show_error,
    show_info,
)


class DashboardPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app, user: Dict[str, object]) -> None:
        super().__init__(parent, style="TFrame")
        self.app = app
        self.user = user
        self.theme_name = app.theme_name
        self.palette = app.palette
        self.pages: Dict[str, ttk.Frame] = {}
        self.current_page_name: Optional[str] = None
        self.nav_buttons: Dict[str, ttk.Button] = {}

        self._configure_local_styles()
        self._build_ui()
        self._register_shortcuts()
        maximize_window(self.winfo_toplevel())
        self.switch_page("home")
        self._tick_clock()

    def _configure_local_styles(self) -> None:
        style = ttk.Style(self)
        style.configure("Sidebar.TFrame", background=self.palette["sidebar_bg"])
        style.configure("SidebarTitle.TLabel", background=self.palette["sidebar_bg"], foreground="white", font=("Segoe UI Semibold", 16))
        style.configure("SidebarSub.TLabel", background=self.palette["sidebar_bg"], foreground=self.palette["sidebar_fg"], font=("Segoe UI", 9))
        style.configure("SidebarInfo.TLabel", background=self.palette["sidebar_bg"], foreground=self.palette["sidebar_fg"], font=("Segoe UI", 10))
        style.configure("HeaderTitle.TLabel", background=self.palette["header_start"], foreground="white", font=("Segoe UI Semibold", 18))
        style.configure("HeaderSub.TLabel", background=self.palette["header_start"], foreground=self.palette["sidebar_fg"], font=("Segoe UI", 10))
        style.configure("HeaderRightTitle.TLabel", background=self.palette["header_end"], foreground="white", font=("Segoe UI Semibold", 14))
        style.configure("HeaderRightSub.TLabel", background=self.palette["header_end"], foreground=self.palette["sidebar_fg"], font=("Segoe UI", 9))
        style.configure("HeaderChip.TLabel", background=self.palette["header_end"], foreground="white", font=("Segoe UI Semibold", 10))

    def _build_ui(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(self, bg=self.palette["sidebar_bg"], width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)
        self.sidebar.columnconfigure(0, weight=1)

        self.sidebar_top = tk.Frame(self.sidebar, bg=self.palette["sidebar_bg"])
        self.sidebar_top.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 14))
        self.sidebar_top.columnconfigure(0, weight=1)
        logo = load_image(LOGO_PATH, (68, 68))
        if logo is not None:
            logo_label = ttk.Label(self.sidebar_top, image=logo, style="SidebarInfo.TLabel")
            logo_label.image = logo
            logo_label.grid(row=0, column=0, sticky="w")
        ttk.Label(self.sidebar_top, text=APP_NAME, style="SidebarTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(12, 0))
        ttk.Label(
            self.sidebar_top,
            text=f"Logged in as {self.user.get('full_name', '')}",
            style="SidebarSub.TLabel",
            wraplength=200,
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))

        self.nav_container = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        self.nav_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 10))
        self.sidebar.rowconfigure(1, weight=1)

        nav_items = [
            ("home", "Dashboard"),
            ("students", "Students"),
            ("reports", "Reports"),
            ("analytics", "Charts"),
            ("settings", "Settings"),
            ("about", "About"),
        ]
        for index, (key, label) in enumerate(nav_items):
            button = ttk.Button(self.nav_container, text=label, style="Sidebar.TButton", command=lambda item=key: self.switch_page(item))
            button.grid(row=index, column=0, sticky="ew", pady=5)
            self.nav_buttons[key] = button

        self.sidebar_footer = tk.Frame(self.sidebar, bg=self.palette["sidebar_bg"])
        self.sidebar_footer.grid(row=2, column=0, sticky="ew", padx=18, pady=18)
        ttk.Label(
            self.sidebar_footer,
            text=f"Session started {human_datetime(self.user.get('created_at'))}",
            style="SidebarInfo.TLabel",
            wraplength=200,
        ).pack(anchor="w", pady=(0, 12))
        ttk.Button(self.sidebar_footer, text="Toggle Theme", style="Ghost.TButton", command=self.app.toggle_theme).pack(fill="x", pady=4)
        ttk.Button(self.sidebar_footer, text="Logout", style="Danger.TButton", command=self.logout).pack(fill="x", pady=4)

        self.main = ttk.Frame(self, style="TFrame")
        self.main.grid(row=0, column=1, sticky="nsew")
        self.main.columnconfigure(0, weight=1)
        self.main.rowconfigure(1, weight=1)

        self.header_canvas = tk.Canvas(self.main, height=126, highlightthickness=0, bd=0)
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.bind("<Configure>", self._draw_header)

        self.header_left = tk.Frame(self.header_canvas, bg=self.palette["header_start"])
        self.header_right = tk.Frame(self.header_canvas, bg=self.palette["header_end"])
        self.header_left_id = self.header_canvas.create_window((18, 18), window=self.header_left, anchor="nw", width=500, height=92)
        self.header_right_id = self.header_canvas.create_window((18, 16), window=self.header_right, anchor="ne", width=320, height=94)

        self.page_title_var = tk.StringVar(value="Dashboard")
        self.page_subtitle_var = tk.StringVar(value="Overview of student records and quick actions.")
        self.clock_var = tk.StringVar(value=datetime.now().strftime("%d %b %Y, %I:%M:%S %p"))
        self.user_var = tk.StringVar(value=self.user.get("full_name", ""))

        self.header_left.columnconfigure(0, weight=1)
        ttk.Label(self.header_left, textvariable=self.page_title_var, style="HeaderTitle.TLabel").pack(anchor="w")
        ttk.Label(self.header_left, textvariable=self.page_subtitle_var, style="HeaderSub.TLabel").pack(anchor="w", pady=(4, 0))

        right_top = ttk.Frame(self.header_right, style="TFrame")
        right_top.pack(anchor="e", padx=16, pady=(12, 2))
        ttk.Label(right_top, textvariable=self.clock_var, style="HeaderChip.TLabel").pack(side="right", padx=(8, 0))
        ttk.Button(right_top, text="Theme", style="Ghost.TButton", command=self.app.toggle_theme).pack(side="right")

        ttk.Label(self.header_right, textvariable=self.user_var, style="HeaderRightTitle.TLabel").pack(anchor="e", padx=16)
        ttk.Label(self.header_right, text="Administrator", style="HeaderRightSub.TLabel").pack(anchor="e", padx=16, pady=(2, 0))

        self.page_container = ttk.Frame(self.main, style="TFrame")
        self.page_container.grid(row=1, column=0, sticky="nsew")
        self.page_container.columnconfigure(0, weight=1)
        self.page_container.rowconfigure(0, weight=1)

        self._set_nav_active("home")

    def _draw_header(self, _event=None) -> None:
        draw_vertical_gradient(self.header_canvas, self.palette["header_start"], self.palette["header_end"])
        width = max(1, self.header_canvas.winfo_width())
        self.header_canvas.coords(self.header_right_id, width - 18, 16)
        self.header_canvas.coords(self.header_left_id, 18, 18)

    def _register_shortcuts(self) -> None:
        root = self.winfo_toplevel()
        root.bind_all("<Control-1>", lambda _event: self.switch_page("home"))
        root.bind_all("<Control-2>", lambda _event: self.switch_page("students"))
        root.bind_all("<Control-3>", lambda _event: self.switch_page("reports"))
        root.bind_all("<Control-4>", lambda _event: self.switch_page("analytics"))
        root.bind_all("<Control-5>", lambda _event: self.switch_page("settings"))
        root.bind_all("<Control-6>", lambda _event: self.switch_page("about"))
        root.bind_all("<Control-n>", lambda _event: self._shortcut_new_student())
        root.bind_all("<Control-f>", lambda _event: self._shortcut_focus_search())
        root.bind_all("<Control-s>", lambda _event: self._shortcut_save_student())
        root.bind_all("<Control-l>", lambda _event: self.logout())
        root.bind_all("<F5>", lambda _event: self.refresh_all())

    def _unbind_shortcuts(self) -> None:
        root = self.winfo_toplevel()
        for sequence in [
            "<Control-1>",
            "<Control-2>",
            "<Control-3>",
            "<Control-4>",
            "<Control-5>",
            "<Control-6>",
            "<Control-n>",
            "<Control-f>",
            "<Control-s>",
            "<Control-l>",
            "<F5>",
        ]:
            try:
                root.unbind_all(sequence)
            except Exception:
                pass

    def _shortcut_new_student(self) -> None:
        page = self.switch_page("students")
        reset = getattr(page, "reset_form", None)
        if callable(reset):
            reset()

    def _shortcut_focus_search(self) -> None:
        if self.current_page_name == "students":
            page = self.pages.get("students")
            focus = getattr(page, "_focus_search", None) if page else None
            if callable(focus):
                focus()

    def _shortcut_save_student(self) -> None:
        if self.current_page_name == "students":
            page = self.pages.get("students")
            if page:
                if getattr(page, "selected_db_id", None):
                    update_student = getattr(page, "update_student", None)
                    if callable(update_student):
                        update_student()
                else:
                    add_student = getattr(page, "add_student", None)
                    if callable(add_student):
                        add_student()

    def _tick_clock(self) -> None:
        self.clock_var.set(datetime.now().strftime("%d %b %Y, %I:%M:%S %p"))
        self.after(1000, self._tick_clock)

    def _set_nav_active(self, key: str) -> None:
        for nav_key, button in self.nav_buttons.items():
            button.configure(style="SidebarActive.TButton" if nav_key == key else "Sidebar.TButton")

    def _page_factory(self, key: str) -> ttk.Frame:
        factories = {
            "home": lambda: HomePage(self.page_container, self.app),
            "students": lambda: StudentsPage(self.page_container, self.app),
            "reports": lambda: ReportsPage(self.page_container, self.app),
            "analytics": lambda: AnalyticsPage(self.page_container, self.app),
            "settings": lambda: SettingsPage(self.page_container, self.app),
            "about": lambda: AboutPage(self.page_container, self.app),
        }
        return factories[key]()

    def get_page(self, key: str) -> Optional[ttk.Frame]:
        return self.pages.get(key)

    def switch_page(self, key: str) -> ttk.Frame:
        if self.current_page_name and self.current_page_name in self.pages:
            self.pages[self.current_page_name].grid_remove()

        if key not in self.pages:
            self.pages[key] = self._page_factory(key)
            self.pages[key].grid(row=0, column=0, sticky="nsew")
        else:
            self.pages[key].grid()

        self.current_page_name = key
        titles = {
            "home": ("Dashboard", "Overview of student records and quick actions."),
            "students": ("Students", "Manage records, photos, validation, and pagination."),
            "reports": ("Reports", "Export data and generate PDF reports."),
            "analytics": ("Charts", "Department, gender, year, and status trends."),
            "settings": ("Settings", "Security, backup, restore, and theme controls."),
            "about": ("About", "Project summary and developer information."),
        }
        title, subtitle = titles.get(key, ("Dashboard", "Overview"))
        self.page_title_var.set(title)
        self.page_subtitle_var.set(subtitle)
        self._set_nav_active(key)

        page = self.pages[key]
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()
        return page

    def refresh_all(self) -> None:
        for page in self.pages.values():
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()

    def apply_theme(self, palette: Dict[str, str]) -> None:
        self.palette = palette
        style = ttk.Style(self)
        self._configure_local_styles()
        self.sidebar.configure(bg=palette["sidebar_bg"])
        self.sidebar_top.configure(bg=palette["sidebar_bg"])
        self.nav_container.configure(style="Sidebar.TFrame")
        self.sidebar_footer.configure(bg=palette["sidebar_bg"])
        self.header_left.configure(bg=palette["header_start"])
        self.header_right.configure(bg=palette["header_end"])
        for child in self.header_left.winfo_children():
            if isinstance(child, tk.Widget):
                try:
                    child.configure(background=palette["header_start"])
                except Exception:
                    pass
        for child in self.header_right.winfo_children():
            if isinstance(child, tk.Widget):
                try:
                    child.configure(background=palette["header_end"])
                except Exception:
                    pass
        self._draw_header()
        for page in self.pages.values():
            apply_theme = getattr(page, "apply_theme", None)
            if callable(apply_theme):
                apply_theme(palette)
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()

    def logout(self) -> None:
        if messagebox.askyesno("Logout", "Log out of the current session?", parent=self):
            self.app.show_login()

    def destroy(self) -> None:
        self._unbind_shortcuts()
        super().destroy()


class HomePage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, style="TFrame")
        self.app = app
        self.stat_vars = {
            "students": tk.StringVar(value="0"),
            "courses": tk.StringVar(value="0"),
            "male": tk.StringVar(value="0"),
            "female": tk.StringVar(value="0"),
        }
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        cards = ttk.Frame(self, style="TFrame", padding=(16, 16, 16, 8))
        cards.grid(row=0, column=0, sticky="ew")
        for column in range(4):
            cards.columnconfigure(column, weight=1)

        self.card_frames = []
        self.accent_bars = []
        definitions = [
            ("Total Students", "students", self.app.palette["primary"]),
            ("Total Courses", "courses", self.app.palette["accent"]),
            ("Male Students", "male", self.app.palette["success"]),
            ("Female Students", "female", self.app.palette["warning"]),
        ]
        for index, (label, key, color) in enumerate(definitions):
            frame = ttk.Frame(cards, style="Card.TFrame", padding=18)
            frame.grid(row=0, column=index, sticky="nsew", padx=8)
            accent = tk.Frame(frame, bg=color, height=4)
            accent.pack(fill="x", pady=(0, 12))
            ttk.Label(frame, text=label, style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(frame, textvariable=self.stat_vars[key], style="CardValue.TLabel").pack(anchor="w", pady=(8, 2))
            ttk.Label(frame, text="Live metric", style="CardSub.TLabel").pack(anchor="w")
            self.card_frames.append((frame, color))
            self.accent_bars.append(accent)

        body = ttk.Frame(self, style="TFrame", padding=(16, 0, 16, 16))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=5)
        body.columnconfigure(1, weight=3)
        body.rowconfigure(0, weight=1)

        recent = ttk.Frame(body, style="Card.TFrame", padding=16)
        recent.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        recent.columnconfigure(0, weight=1)
        recent.rowconfigure(1, weight=1)
        ttk.Label(recent, text="Recently Added Students", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        self.recent_tree = ttk.Treeview(
            recent,
            columns=("student_id", "name", "course", "status"),
            show="headings",
            height=10,
        )
        for column, title, width in [
            ("student_id", "Student ID", 130),
            ("name", "Name", 180),
            ("course", "Course", 130),
            ("status", "Status", 110),
        ]:
            self.recent_tree.heading(column, text=title)
            self.recent_tree.column(column, width=width, anchor="w")
        self.recent_tree.grid(row=1, column=0, sticky="nsew", pady=(12, 0))

        quick = ttk.Frame(body, style="Card.TFrame", padding=16)
        quick.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        quick.columnconfigure(0, weight=1)
        ttk.Label(quick, text="Quick Actions", style="Header.TLabel").pack(anchor="w")
        actions = [
            ("Add Student", self._open_student_form),
            ("Open Reports", lambda: self.app.dashboard_page.switch_page("reports")),
            ("View Charts", lambda: self.app.dashboard_page.switch_page("analytics")),
            ("Database Tools", lambda: self.app.dashboard_page.switch_page("settings")),
            ("Toggle Theme", self.app.toggle_theme),
        ]
        for label, callback in actions:
            ttk.Button(quick, text=label, style="Ghost.TButton", command=callback).pack(fill="x", pady=6)

    def _open_student_form(self) -> None:
        page = self.app.dashboard_page.switch_page("students")
        reset = getattr(page, "reset_form", None)
        if callable(reset):
            reset()

    def refresh(self) -> None:
        self.stat_vars["students"].set(str(db.total_students()))
        self.stat_vars["courses"].set(str(db.count_courses()))
        self.stat_vars["male"].set(str(db.total_male_students()))
        self.stat_vars["female"].set(str(db.total_female_students()))

        for row in self.recent_tree.get_children():
            self.recent_tree.delete(row)
        for student in db.recent_students(8):
            self.recent_tree.insert(
                "",
                "end",
                values=(
                    student.get("student_id", ""),
                    student.get("full_name", ""),
                    student.get("course", ""),
                    student.get("status", ""),
                ),
            )

    def apply_theme(self, palette: Dict[str, str]) -> None:
        accents = [palette["primary"], palette["accent"], palette["success"], palette["warning"]]
        for bar, color in zip(self.accent_bars, accents):
            try:
                bar.configure(bg=color)
            except Exception:
                pass


class AnalyticsPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, style="TFrame")
        self.app = app
        self.figure = None
        self.canvas = None
        self._build_ui()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.container = ttk.Frame(self, style="Card.TFrame", padding=16)
        self.container.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        self.container.columnconfigure(0, weight=1)
        self.container.rowconfigure(1, weight=1)

        ttk.Label(self.container, text="Analytics", style="Header.TLabel").grid(row=0, column=0, sticky="w")

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure

            self.FigureCanvasTkAgg = FigureCanvasTkAgg
            self.Figure = Figure
            self.figure = Figure(figsize=(12, 7), dpi=100)
            self.figure.patch.set_facecolor(self.app.palette["surface"])
            self.canvas = FigureCanvasTkAgg(self.figure, master=self.container)
            self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        except Exception:
            ttk.Label(
                self.container,
                text="Matplotlib is not available. Install it to view charts.",
                style="Muted.TLabel",
            ).grid(row=1, column=0, sticky="nsew", pady=(18, 0))

    def refresh(self) -> None:
        if not self.figure or not self.canvas:
            return
        self.figure.clear()
        self.figure.patch.set_facecolor(self.app.palette["surface"])

        ax1 = self.figure.add_subplot(221)
        ax2 = self.figure.add_subplot(222)
        ax3 = self.figure.add_subplot(223)
        ax4 = self.figure.add_subplot(224)

        departments = db.count_by_department()
        genders = db.count_by_gender()
        years = db.count_by_admission_year()
        statuses = db.count_by_status()

        if departments:
            labels = [item["label"] for item in departments][:8]
            values = [item["total"] for item in departments][:8]
            ax1.barh(labels, values, color=self.app.palette["primary"])
            ax1.set_title("Students by Department")
        else:
            ax1.text(0.5, 0.5, "No data", ha="center", va="center")

        if genders:
            labels = [item["label"] for item in genders]
            values = [item["total"] for item in genders]
            ax2.pie(values, labels=labels, autopct="%1.0f%%", colors=[self.app.palette["accent"], self.app.palette["warning"], self.app.palette["success"]])
            ax2.set_title("Student Gender Split")
        else:
            ax2.text(0.5, 0.5, "No data", ha="center", va="center")

        if years:
            labels = [item["label"] for item in years]
            values = [item["total"] for item in years]
            ax3.bar(labels, values, color=self.app.palette["success"])
            ax3.set_title("Admissions by Year")
        else:
            ax3.text(0.5, 0.5, "No data", ha="center", va="center")

        if statuses:
            labels = [item["label"] for item in statuses]
            values = [item["total"] for item in statuses]
            ax4.pie(values, labels=labels, autopct="%1.0f%%", colors=[self.app.palette["primary"], self.app.palette["warning"], self.app.palette["accent"], self.app.palette["danger"]])
            ax4.set_title("Status Mix")
        else:
            ax4.text(0.5, 0.5, "No data", ha="center", va="center")

        for axis in [ax1, ax2, ax3, ax4]:
            axis.tick_params(labelsize=8)

        self.figure.tight_layout()
        self.canvas.draw_idle()


class AboutPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, style="TFrame")
        self.app = app
        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self, style="Card.TFrame", padding=24)
        container.pack(fill="both", expand=True, padx=16, pady=16)
        ttk.Label(container, text="About This Project", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="A premium Tkinter + SQLite student management system designed for demos, internships, and portfolio submissions.",
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(6, 14))

        features = [
            "Authentication with password hashing and security recovery",
            "Student CRUD with photo support and webcam capture",
            "Search, pagination, sorting, and validation",
            "Exports to CSV, Excel, and PDF",
            "Charts, backups, restore, theme switching, and keyboard shortcuts",
        ]
        for feature in features:
            ttk.Label(container, text=f"\u25AA {feature}", style="CardTitle.TLabel").pack(anchor="w", pady=3)

        ttk.Separator(container).pack(fill="x", pady=16)
        ttk.Label(container, text=f"Version: 1.0", style="Header.TLabel").pack(anchor="w")
        ttk.Label(container, text=f"Built with Python, Tkinter, SQLite, Pillow, pandas, matplotlib, OpenCV, openpyxl, and reportlab.", style="Muted.TLabel", wraplength=760).pack(anchor="w", pady=(4, 0))

    def refresh(self) -> None:
        return

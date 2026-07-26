from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk

from dashboard import DashboardPage
from database import db
from login import LoginPage
from utils import APP_NAME, LOGO_PATH, LoadingOverlay, THEMES, center_window, configure_ttk_style, ensure_placeholder_assets, load_image, maximize_window, set_window_icon


class SplashScreen(tk.Toplevel):
    def __init__(self, master: tk.Misc, theme_name: str) -> None:
        super().__init__(master)
        self.theme_name = theme_name
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        palette = THEMES.get(theme_name, THEMES["light"])
        self.configure(bg=palette["sidebar_bg"])
        self.geometry("520x280")
        center_window(self, 520, 280)

        container = ttk.Frame(self, style="Card.TFrame", padding=24)
        container.pack(fill="both", expand=True)
        logo = load_image(LOGO_PATH, (84, 84))
        if logo is not None:
            logo_label = ttk.Label(container, image=logo, style="Card.TLabel")
            logo_label.image = logo
            logo_label.pack(anchor="center", pady=(0, 8))
        ttk.Label(container, text=APP_NAME, style="Title.TLabel").pack(anchor="center", pady=(14, 6))
        ttk.Label(
            container,
            text="Loading your premium desktop workspace...",
            style="Muted.TLabel",
        ).pack(anchor="center")
        self.progress = ttk.Progressbar(container, mode="indeterminate", length=360)
        self.progress.pack(pady=(28, 8))
        self.progress.start(12)
        ttk.Label(container, text="Secure authentication, analytics, reports, and backups.", style="CardTitle.TLabel").pack(
            anchor="center", pady=(6, 0)
        )


class StudentManagementApp:
    def __init__(self) -> None:
        ensure_placeholder_assets()
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.minsize(1180, 760)
        self.style = ttk.Style(self.root)
        self.theme_name = db.get_setting("theme", "light") or "light"
        self.palette = configure_ttk_style(self.style, self.theme_name)
        self.current_screen = None
        self.dashboard_page: DashboardPage | None = None
        self.user = None
        set_window_icon(self.root)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.loading_overlay = LoadingOverlay(self.root, "Preparing application...")

    def run(self) -> None:
        self.root.withdraw()
        splash = SplashScreen(self.root, self.theme_name)
        self.root.after(1400, lambda: self._finish_startup(splash))
        self.root.mainloop()

    def _finish_startup(self, splash: SplashScreen) -> None:
        try:
            splash.progress.stop()
        except Exception:
            pass
        splash.destroy()
        self.root.deiconify()
        self.show_login()

    def clear_screen(self) -> None:
        if self.current_screen is not None:
            try:
                self.current_screen.destroy()
            except Exception:
                pass
            self.current_screen = None

    def show_login(self) -> None:
        self.clear_screen()
        self.dashboard_page = None
        self.user = None
        self.root.geometry("1220x760")
        self.root.minsize(1180, 760)
        try:
            self.root.state("normal")
        except Exception:
            pass
        center_window(self.root, 1220, 760)
        self.current_screen = LoginPage(self.root, self)
        self.current_screen.pack(fill="both", expand=True)

    def show_dashboard(self, user) -> None:
        self.clear_screen()
        self.user = user
        self._run_auto_backup()
        self.current_screen = DashboardPage(self.root, self, user)
        self.dashboard_page = self.current_screen
        self.current_screen.pack(fill="both", expand=True)
        maximize_window(self.root)

    def _run_auto_backup(self) -> None:
        if (db.get_setting("auto_backup", "1") or "1") != "1":
            return
        today_stamp = datetime.now().strftime("%Y-%m-%d")
        if db.get_setting("last_auto_backup", "") == today_stamp:
            return
        try:
            self.show_loading("Creating automatic backup...")
            backup_path = db.backup_database()
            db.set_setting("last_auto_backup", today_stamp)
            db.set_setting("last_backup_path", str(backup_path))
        except Exception:
            pass
        finally:
            self.hide_loading()

    def switch_page(self, page_name: str):
        if self.dashboard_page is not None:
            return self.dashboard_page.switch_page(page_name)
        return None

    def refresh_active_pages(self) -> None:
        if self.dashboard_page is not None:
            self.dashboard_page.refresh_all()

    def set_theme(self, theme_name: str) -> None:
        if theme_name not in ("light", "dark"):
            theme_name = "light"
        self.theme_name = theme_name
        db.set_setting("theme", theme_name)
        self.palette = configure_ttk_style(self.style, theme_name)
        if self.dashboard_page is not None:
            self.dashboard_page.apply_theme(self.palette)
        elif isinstance(self.current_screen, LoginPage):
            self.show_login()

    def toggle_theme(self) -> None:
        self.set_theme("dark" if self.theme_name == "light" else "light")

    def show_loading(self, text: str) -> None:
        self.loading_overlay.show(text)

    def hide_loading(self) -> None:
        self.loading_overlay.hide()

    def _on_close(self) -> None:
        self.root.destroy()


def main() -> None:
    app = StudentManagementApp()
    app.run()


if __name__ == "__main__":
    main()

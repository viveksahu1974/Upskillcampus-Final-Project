from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except Exception:  # pragma: no cover - optional dependency fallback
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageTk = None


APP_NAME = "Student Management System"
PROJECT_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_DIR = ASSETS_DIR / "icons"
IMAGE_DIR = ASSETS_DIR / "images"
STUDENT_PHOTO_DIR = IMAGE_DIR / "students"
DATABASE_DIR = PROJECT_ROOT / "database"
EXPORT_DIR = PROJECT_ROOT / "exports"
REPORT_DIR = PROJECT_ROOT / "reports"
BACKUP_DIR = DATABASE_DIR / "backups"
DB_PATH = DATABASE_DIR / "students.db"
LOGO_PATH = ASSETS_DIR / "logo.png"

FONT_FAMILY = "Segoe UI"
FONT_FAMILY_BOLD = "Segoe UI Semibold"

SECURITY_QUESTIONS = [
    "What is your favorite color?",
    "What city were you born in?",
    "What is your first school name?",
    "What is your pet's name?",
    "What is your mother's maiden name?",
]

THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#f4f7fb",
        "surface": "#ffffff",
        "surface_alt": "#eef3fb",
        "text": "#172033",
        "muted": "#667085",
        "primary": "#1d4ed8",
        "primary_hover": "#1742b0",
        "accent": "#0ea5e9",
        "success": "#16a34a",
        "danger": "#dc2626",
        "warning": "#d97706",
        "border": "#d7e1ee",
        "input": "#ffffff",
        "selected": "#dbeafe",
        "sidebar_bg": "#0f172a",
        "sidebar_fg": "#e2e8f0",
        "sidebar_active": "#1e293b",
        "header_start": "#2563eb",
        "header_end": "#0f766e",
    },
    "dark": {
        "bg": "#0f172a",
        "surface": "#111827",
        "surface_alt": "#1f2937",
        "text": "#e5eefc",
        "muted": "#9ca3af",
        "primary": "#38bdf8",
        "primary_hover": "#0ea5e9",
        "accent": "#a78bfa",
        "success": "#22c55e",
        "danger": "#f87171",
        "warning": "#f59e0b",
        "border": "#334155",
        "input": "#0b1220",
        "selected": "#1d4ed8",
        "sidebar_bg": "#020617",
        "sidebar_fg": "#e2e8f0",
        "sidebar_active": "#1e293b",
        "header_start": "#1d4ed8",
        "header_end": "#7c3aed",
    },
}


def ensure_directories() -> None:
    for path in [
        ASSETS_DIR,
        ICON_DIR,
        IMAGE_DIR,
        STUDENT_PHOTO_DIR,
        DATABASE_DIR,
        EXPORT_DIR,
        REPORT_DIR,
        BACKUP_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def ensure_placeholder_assets() -> None:
    ensure_directories()
    if LOGO_PATH.exists() or Image is None:
        return

    size = 512
    image = Image.new("RGBA", (size, size), "#0f172a")
    draw = ImageDraw.Draw(image)

    top = _hex_to_rgb("#2563eb")
    bottom = _hex_to_rgb("#0f766e")
    for y in range(size):
        ratio = y / max(1, size - 1)
        color = _interpolate_rgb(top, bottom, ratio)
        draw.line((0, y, size, y), fill=color)

    draw.ellipse((48, 48, 464, 464), fill=(255, 255, 255, 24))
    draw.ellipse((84, 84, 428, 428), fill=(15, 23, 42, 220))

    try:
        title_font = _load_font(172, bold=True)
        subtitle_font = _load_font(34, bold=False)
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    draw.text((256, 206), "SMS", font=title_font, fill="white", anchor="mm")
    draw.text((256, 330), "Student Suite", font=subtitle_font, fill="#cbd5e1", anchor="mm")
    image.save(LOGO_PATH)


def _load_font(size: int, bold: bool = False):
    if ImageFont is None:
        raise RuntimeError("Pillow is not available")

    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            if Path(candidate).exists():
                return ImageFont.truetype(candidate, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def load_image(path: Path | str, size: Optional[Tuple[int, int]] = None):
    if Image is None or ImageTk is None:
        return None

    image_path = Path(path)
    if not image_path.exists():
        return None
    try:
        image = Image.open(image_path).convert("RGBA")
        if size:
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", None)
            if resample is None:
                resample = getattr(Image, "LANCZOS", 1)
            image = image.resize(size, resample)
        return ImageTk.PhotoImage(image)
    except Exception:
        return None


def create_placeholder_avatar(path: Path, label: str = "SMS") -> None:
    if Image is None:
        return
    canvas = Image.new("RGBA", (420, 420), "#dbeafe")
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((30, 30, 390, 390), fill="#1d4ed8")
    draw.ellipse((70, 70, 350, 350), fill="#0f172a")
    try:
        font = _load_font(96, bold=True)
    except Exception:
        font = ImageFont.load_default()
    draw.text((210, 190), label, fill="white", font=font, anchor="mm")
    canvas.save(path)


def interpolate_color(start: str, end: str, ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    start_rgb = _hex_to_rgb(start)
    end_rgb = _hex_to_rgb(end)
    blended = _interpolate_rgb(start_rgb, end_rgb, ratio)
    return _rgb_to_hex(blended)


def draw_vertical_gradient(canvas: tk.Canvas, start_color: str, end_color: str) -> None:
    canvas.delete("gradient")
    width = max(1, canvas.winfo_width())
    height = max(1, canvas.winfo_height())
    steps = min(height, 180)
    for index in range(steps):
        ratio = index / max(1, steps - 1)
        color = interpolate_color(start_color, end_color, ratio)
        y1 = int(index * height / steps)
        y2 = int((index + 1) * height / steps)
        canvas.create_rectangle(0, y1, width, y2, outline=color, fill=color, tags=("gradient",))


def configure_ttk_style(style: ttk.Style, theme_name: str = "light") -> Dict[str, str]:
    palette = THEMES.get(theme_name, THEMES["light"])
    style.theme_use("clam")

    default_font = (FONT_FAMILY, 10)
    bold_font = (FONT_FAMILY_BOLD, 10)
    title_font = (FONT_FAMILY_BOLD, 18)
    header_font = (FONT_FAMILY_BOLD, 13)

    style.configure(
        ".",
        background=palette["bg"],
        foreground=palette["text"],
        font=default_font,
    )
    style.configure("TFrame", background=palette["bg"])
    style.configure("TLabel", background=palette["bg"], foreground=palette["text"], font=default_font)
    style.configure("TButton", font=default_font, padding=(12, 8), relief="flat")
    style.map("TButton", relief=[("pressed", "sunken"), ("active", "flat")])

    style.configure("TCheckbutton", background=palette["bg"], foreground=palette["text"], font=default_font)
    style.configure("TRadiobutton", background=palette["bg"], foreground=palette["text"], font=default_font)
    style.configure(
        "TEntry",
        fieldbackground=palette["input"],
        foreground=palette["text"],
        padding=7,
    )
    style.configure(
        "TCombobox",
        fieldbackground=palette["input"],
        background=palette["input"],
        foreground=palette["text"],
        padding=7,
    )
    style.map("TCombobox", fieldbackground=[("readonly", palette["input"])])

    style.configure("Card.TFrame", background=palette["surface"], relief="flat", borderwidth=0)
    style.configure("Card.TLabel", background=palette["surface"], foreground=palette["text"], font=default_font)
    style.configure("Surface.TFrame", background=palette["surface"])
    style.configure("Muted.TLabel", background=palette["surface"], foreground=palette["muted"], font=default_font)
    style.configure("Title.TLabel", background=palette["surface"], foreground=palette["text"], font=title_font)
    style.configure("Header.TLabel", background=palette["surface"], foreground=palette["text"], font=header_font)
    style.configure("Section.TLabelframe", background=palette["bg"], foreground=palette["text"], padding=10)
    style.configure("Section.TLabelframe.Label", background=palette["bg"], foreground=palette["text"], font=bold_font)

    style.configure(
        "Primary.TButton",
        background=palette["primary"],
        foreground="white",
        font=bold_font,
        padding=(14, 9),
    )
    style.map(
        "Primary.TButton",
        background=[("active", palette["primary_hover"]), ("disabled", palette["border"])],
        foreground=[("disabled", palette["muted"])],
    )

    style.configure(
        "Success.TButton",
        background=palette["success"],
        foreground="white",
        font=bold_font,
        padding=(14, 9),
    )
    style.map("Success.TButton", background=[("active", palette["success"])])

    style.configure(
        "Danger.TButton",
        background=palette["danger"],
        foreground="white",
        font=bold_font,
        padding=(14, 9),
    )
    style.map("Danger.TButton", background=[("active", palette["danger"])])

    style.configure(
        "Ghost.TButton",
        background=palette["surface"],
        foreground=palette["primary"],
        font=bold_font,
        padding=(12, 8),
        bordercolor=palette["border"],
    )
    style.map("Ghost.TButton", background=[("active", palette["surface_alt"])])

    style.configure(
        "Sidebar.TButton",
        background=palette["sidebar_bg"],
        foreground=palette["sidebar_fg"],
        font=(FONT_FAMILY_BOLD, 10),
        padding=(14, 11),
        anchor="w",
        relief="flat",
    )
    style.configure(
        "SidebarActive.TButton",
        background=palette["sidebar_active"],
        foreground="white",
        font=(FONT_FAMILY_BOLD, 10),
        padding=(14, 11),
        anchor="w",
        relief="flat",
    )
    style.map(
        "Sidebar.TButton",
        background=[("active", palette["sidebar_active"])],
        foreground=[("disabled", palette["muted"])],
    )
    style.map("SidebarActive.TButton", background=[("active", palette["sidebar_active"])])

    style.configure(
        "CardTitle.TLabel",
        background=palette["surface"],
        foreground=palette["muted"],
        font=(FONT_FAMILY, 10),
    )
    style.configure(
        "CardValue.TLabel",
        background=palette["surface"],
        foreground=palette["text"],
        font=(FONT_FAMILY_BOLD, 22),
    )
    style.configure(
        "CardSub.TLabel",
        background=palette["surface"],
        foreground=palette["muted"],
        font=(FONT_FAMILY, 9),
    )

    style.configure(
        "Treeview",
        background=palette["surface"],
        fieldbackground=palette["surface"],
        foreground=palette["text"],
        bordercolor=palette["border"],
        rowheight=29,
        font=default_font,
    )
    style.configure(
        "Treeview.Heading",
        background=palette["surface_alt"],
        foreground=palette["text"],
        font=bold_font,
        padding=8,
    )
    style.map(
        "Treeview",
        background=[("selected", palette["selected"])],
        foreground=[("selected", palette["text"])],
    )

    style.configure("TLabelframe", background=palette["bg"], foreground=palette["text"])
    style.configure("TLabelframe.Label", background=palette["bg"], foreground=palette["text"], font=bold_font)
    return palette


def center_window(window: tk.Tk | tk.Toplevel, width: int, height: int) -> None:
    window.update_idletasks()
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max(0, int((screen_width - width) / 2))
    y = max(0, int((screen_height - height) / 2))
    window.geometry(f"{width}x{height}+{x}+{y}")


def maximize_window(window: tk.Tk | tk.Toplevel) -> None:
    try:
        window.state("zoomed")
    except Exception:
        window.geometry(f"{window.winfo_screenwidth()}x{window.winfo_screenheight()}+0+0")


def set_window_icon(window: tk.Misc) -> None:
    if ImageTk is None:
        return
    try:
        icon_image = load_image(LOGO_PATH, (32, 32))
        if icon_image is not None and hasattr(window, "iconphoto"):
            window.iconphoto(True, icon_image)
            setattr(window, "_icon_image", icon_image)
    except Exception:
        pass


def open_path(path: Path | str) -> None:
    target = str(path)
    if sys.platform.startswith("win"):
        os.startfile(target)  # type: ignore[attr-defined]
        return
    if sys.platform == "darwin":
        subprocess.Popen(["open", target])
        return
    subprocess.Popen(["xdg-open", target])


def safe_copy(source: Path | str, destination: Path | str) -> Path:
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination_path)
    return destination_path


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def current_year() -> str:
    return datetime.now().strftime("%Y")


def human_datetime(value: Optional[str] = None) -> str:
    if value:
        try:
            return datetime.fromisoformat(value).strftime("%d %b %Y, %I:%M %p")
        except Exception:
            pass
    return datetime.now().strftime("%d %b %Y, %I:%M %p")


def normalize_date(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    raise ValueError("Date must be in YYYY-MM-DD format.")


def is_valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value.strip()))


def is_valid_phone(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return 10 <= len(digits) <= 15


def is_valid_aadhaar(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    return len(digits) == 12


def clean_phone(value: str) -> str:
    return re.sub(r"\s+", "", value.strip())


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    )
    return f"{salt}${base64.b64encode(derived).decode('utf-8')}"


def verify_password(password: str, stored_value: str) -> bool:
    try:
        salt, hashed_value = stored_value.split("$", 1)
    except ValueError:
        return False
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    )
    return hmac.compare_digest(base64.b64encode(derived).decode("utf-8"), hashed_value)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def validate_student_data(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    required_fields = [
        ("full_name", "Full Name"),
        ("roll_number", "Roll Number"),
        ("registration_number", "Registration Number"),
        ("father_name", "Father's Name"),
        ("mother_name", "Mother's Name"),
        ("gender", "Gender"),
        ("dob", "Date of Birth"),
        ("phone", "Phone Number"),
        ("email", "Email"),
        ("address", "Address"),
        ("course", "Course"),
        ("year", "Year"),
        ("semester", "Semester"),
        ("department", "Department"),
        ("admission_date", "Admission Date"),
        ("status", "Student Status"),
    ]

    for key, label in required_fields:
        value = str(data.get(key, "")).strip()
        if not value:
            errors.append(f"{label} is required.")

    email = str(data.get("email", "")).strip()
    if email and not is_valid_email(email):
        errors.append("Enter a valid email address.")

    phone = str(data.get("phone", "")).strip()
    if phone and not is_valid_phone(phone):
        errors.append("Enter a valid phone number.")

    aadhaar = str(data.get("aadhaar_number", "")).strip()
    if aadhaar and not is_valid_aadhaar(aadhaar):
        errors.append("Aadhaar number must contain exactly 12 digits.")

    roll_number = str(data.get("roll_number", "")).strip()
    if roll_number and len(roll_number) < 2:
        errors.append("Roll Number is too short.")

    admission_date = str(data.get("admission_date", "")).strip()
    if admission_date:
        try:
            normalize_date(admission_date)
        except ValueError:
            errors.append("Admission Date must be a valid date.")

    dob = str(data.get("dob", "")).strip()
    if dob:
        try:
            normalize_date(dob)
        except ValueError:
            errors.append("Date of Birth must be a valid date.")

    return errors


def normalize_student_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(data)
    for key in [
        "full_name",
        "roll_number",
        "registration_number",
        "father_name",
        "mother_name",
        "gender",
        "email",
        "course",
        "year",
        "semester",
        "department",
        "blood_group",
        "aadhaar_number",
        "status",
        "photo_path",
    ]:
        if key in normalized and normalized[key] is not None:
            normalized[key] = normalize_text(str(normalized[key]))

    if "phone" in normalized:
        normalized["phone"] = clean_phone(str(normalized["phone"]))

    if "address" in normalized and normalized["address"] is not None:
        normalized["address"] = str(normalized["address"]).strip()

    if "dob" in normalized:
        normalized["dob"] = normalize_date(str(normalized["dob"]).strip()) if str(normalized["dob"]).strip() else ""
    if "admission_date" in normalized:
        normalized["admission_date"] = (
            normalize_date(str(normalized["admission_date"]).strip()) if str(normalized["admission_date"]).strip() else ""
        )
    return normalized


def student_photo_filename(student_id: str, source_path: Path | str) -> Path:
    source = Path(source_path)
    suffix = source.suffix.lower() or ".jpg"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return STUDENT_PHOTO_DIR / f"{student_id}_{stamp}{suffix}"


def copy_student_photo(student_id: str, source_path: Path | str) -> Path:
    destination = student_photo_filename(student_id, source_path)
    return safe_copy(source_path, destination)


def delete_file_if_exists(path: Optional[Path | str]) -> None:
    if not path:
        return
    try:
        file_path = Path(path)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        pass


def create_scrollable_frame(parent: tk.Misc, background: Optional[str] = None):
    container = ttk.Frame(parent)
    canvas = tk.Canvas(container, highlightthickness=0, bd=0, bg=background)
    scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable = ttk.Frame(canvas)

    scrollable.bind(
        "<Configure>",
        lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas_window = canvas.create_window((0, 0), window=scrollable, anchor="nw")

    def _resize(event):
        canvas.itemconfig(canvas_window, width=event.width)

    canvas.bind("<Configure>", _resize)
    canvas.configure(yscrollcommand=scrollbar.set)
    container.columnconfigure(0, weight=1)
    container.rowconfigure(0, weight=1)
    canvas.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    return container, canvas, scrollable


def show_info(title: str, message: str, parent: Optional[tk.Misc] = None) -> None:
    messagebox.showinfo(title, message, parent=parent)


def show_warning(title: str, message: str, parent: Optional[tk.Misc] = None) -> None:
    messagebox.showwarning(title, message, parent=parent)


def show_error(title: str, message: str, parent: Optional[tk.Misc] = None) -> None:
    messagebox.showerror(title, message, parent=parent)


def ask_confirm(title: str, message: str, parent: Optional[tk.Misc] = None) -> bool:
    return messagebox.askyesno(title, message, parent=parent)


def open_file_dialog(**kwargs: Any) -> str:
    return filedialog.askopenfilename(**kwargs)


def save_file_dialog(**kwargs: Any) -> str:
    return filedialog.asksaveasfilename(**kwargs)


class LoadingOverlay:
    def __init__(self, master: tk.Misc, text: str = "Please wait...") -> None:
        self.master = master
        self.text = text
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.transient(master)
        self.window.configure(bg="#000000")

        self.container = ttk.Frame(self.window, style="Card.TFrame", padding=24)
        self.container.pack(fill="both", expand=True)
        self.label = ttk.Label(self.container, text=text, style="Header.TLabel")
        self.label.pack(pady=(8, 12))
        self.progress = ttk.Progressbar(self.container, mode="indeterminate", length=280)
        self.progress.pack(fill="x", pady=(0, 8))

    def show(self, text: Optional[str] = None) -> None:
        if text:
            self.text = text
            self.label.configure(text=text)
        self.window.update_idletasks()
        width, height = 360, 140
        screen_x = self.master.winfo_rootx()
        screen_y = self.master.winfo_rooty()
        screen_w = max(1, self.master.winfo_width())
        screen_h = max(1, self.master.winfo_height())
        x = screen_x + int((screen_w - width) / 2)
        y = screen_y + int((screen_h - height) / 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.deiconify()
        self.progress.start(12)
        self.window.lift()
        self.window.grab_set()

    def hide(self) -> None:
        try:
            self.progress.stop()
            self.window.grab_release()
            self.window.withdraw()
        except Exception:
            pass


def _hex_to_rgb(value: str) -> Tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(value: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*value)


def _interpolate_rgb(start: Tuple[int, int, int], end: Tuple[int, int, int], ratio: float) -> Tuple[int, int, int]:
    return tuple(
        int(round(start[index] + (end[index] - start[index]) * ratio))
        for index in range(3)
    )


ensure_directories()

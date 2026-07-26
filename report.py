from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import tkinter as tk
from tkinter import filedialog, ttk

from database import db
from utils import (
    APP_NAME,
    EXPORT_DIR,
    REPORT_DIR,
    current_year,
    human_datetime,
    open_path,
    show_error,
    show_info,
)

STUDENT_COLUMNS = [
    "student_id",
    "full_name",
    "roll_number",
    "registration_number",
    "father_name",
    "mother_name",
    "gender",
    "dob",
    "phone",
    "email",
    "address",
    "course",
    "year",
    "semester",
    "department",
    "blood_group",
    "aadhaar_number",
    "admission_date",
    "status",
    "photo_path",
    "created_at",
    "updated_at",
]


def _ensure_pandas():
    try:
        import pandas as pd

        return pd
    except Exception as exc:  # pragma: no cover - optional dependency fallback
        raise RuntimeError("pandas is required for export features.") from exc


def _ensure_reportlab():
    try:
        from reportlab.lib import colors
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4, landscape, portrait
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.pdfgen import canvas as pdfcanvas
        from reportlab.platypus import Image as RLImage
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from reportlab.graphics import renderPDF
        from reportlab.graphics.barcode import qr
        from reportlab.graphics.shapes import Drawing

        return {
            "colors": colors,
            "HexColor": HexColor,
            "A4": A4,
            "landscape": landscape,
            "portrait": portrait,
            "ParagraphStyle": ParagraphStyle,
            "getSampleStyleSheet": getSampleStyleSheet,
            "inch": inch,
            "pdfcanvas": pdfcanvas,
            "RLImage": RLImage,
            "Paragraph": Paragraph,
            "SimpleDocTemplate": SimpleDocTemplate,
            "Spacer": Spacer,
            "Table": Table,
            "TableStyle": TableStyle,
            "renderPDF": renderPDF,
            "qr": qr,
            "Drawing": Drawing,
        }
    except Exception as exc:  # pragma: no cover - optional dependency fallback
        raise RuntimeError("reportlab is required for PDF features.") from exc


def export_students_to_csv(students: List[Dict[str, object]], output_path: Optional[Path | str] = None) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path) if output_path else EXPORT_DIR / f"students_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with path.open("w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=STUDENT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in students:
            writer.writerow(row)
    return path


def export_students_to_excel(students: List[Dict[str, object]], output_path: Optional[Path | str] = None) -> Path:
    pd = _ensure_pandas()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path) if output_path else EXPORT_DIR / f"students_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
    frame = pd.DataFrame(students, columns=STUDENT_COLUMNS)
    frame.to_excel(path, index=False)
    return path


def generate_student_list_pdf(students: List[Dict[str, object]], output_path: Optional[Path | str] = None) -> Path:
    libs = _ensure_reportlab()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path) if output_path else REPORT_DIR / f"student_list_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    doc = libs["SimpleDocTemplate"](str(path), pagesize=libs["landscape"](libs["A4"]), rightMargin=18, leftMargin=18, topMargin=18, bottomMargin=18)
    styles = libs["getSampleStyleSheet"]()
    story = []

    title_style = libs["ParagraphStyle"](
        "TitleStyle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=libs["HexColor"]("#1d4ed8"),
        spaceAfter=8,
    )
    subtitle_style = libs["ParagraphStyle"](
        "SubtitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=libs["HexColor"]("#475569"),
        spaceAfter=12,
    )

    story.append(libs["Paragraph"](APP_NAME, title_style))
    story.append(libs["Paragraph"]("Student List Report", styles["Heading2"]))
    story.append(libs["Paragraph"](f"Generated on {human_datetime()}", subtitle_style))

    data = [
        ["Student ID", "Name", "Roll No", "Course", "Department", "Phone", "Status"],
    ]
    for student in students:
        data.append(
            [
                student.get("student_id", ""),
                student.get("full_name", ""),
                student.get("roll_number", ""),
                student.get("course", ""),
                student.get("department", ""),
                student.get("phone", ""),
                student.get("status", ""),
            ]
        )

    table = libs["Table"](data, repeatRows=1)
    table.setStyle(
        libs["TableStyle"](
            [
                ("BACKGROUND", (0, 0), (-1, 0), libs["HexColor"]("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), libs["colors"].white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, libs["colors"].HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [libs["colors"].white, libs["HexColor"]("#f8fbff")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return path


def _add_qr_code(libs, canvas_obj, text: str, x: int, y: int, size: int = 90) -> None:
    qr_code = libs["qr"].QrCodeWidget(text)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = libs["Drawing"](size, size, transform=[size / width, 0, 0, size / height, 0, 0])
    drawing.add(qr_code)
    libs["renderPDF"].draw(drawing, canvas_obj, x, y)


def generate_student_report_pdf(student: Dict[str, object], output_path: Optional[Path | str] = None) -> Path:
    libs = _ensure_reportlab()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    student_id = str(student.get("student_id", "student"))
    path = Path(output_path) if output_path else REPORT_DIR / f"report_card_{student_id}_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    page_width, page_height = libs["A4"]
    canvas_obj = libs["pdfcanvas"](str(path), pagesize=libs["portrait"](libs["A4"]))

    primary = libs["HexColor"]("#1d4ed8")
    secondary = libs["HexColor"]("#0f766e")
    muted = libs["HexColor"]("#475569")

    canvas_obj.setFillColor(primary)
    canvas_obj.rect(0, page_height - 120, page_width, 120, fill=1, stroke=0)
    canvas_obj.setFillColor(libs["colors"].white)
    canvas_obj.setFont("Helvetica-Bold", 22)
    canvas_obj.drawString(40, page_height - 62, APP_NAME)
    canvas_obj.setFont("Helvetica", 10)
    canvas_obj.drawString(40, page_height - 80, "Official student report card")

    canvas_obj.setFillColor(secondary)
    canvas_obj.roundRect(38, 36, page_width - 76, page_height - 176, 18, fill=0, stroke=1)

    photo_path = str(student.get("photo_path", "") or "")
    if photo_path:
        try:
            canvas_obj.drawImage(photo_path, 48, page_height - 290, width=100, height=120, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    canvas_obj.setFillColor(muted)
    canvas_obj.setFont("Helvetica-Bold", 14)
    canvas_obj.drawString(170, page_height - 190, f"Student ID: {student.get('student_id', '')}")
    canvas_obj.drawString(170, page_height - 210, f"Name: {student.get('full_name', '')}")
    canvas_obj.drawString(170, page_height - 230, f"Course: {student.get('course', '')}")
    canvas_obj.drawString(170, page_height - 250, f"Department: {student.get('department', '')}")

    details = [
        ("Roll Number", "roll_number"),
        ("Registration Number", "registration_number"),
        ("Father's Name", "father_name"),
        ("Mother's Name", "mother_name"),
        ("Gender", "gender"),
        ("Date of Birth", "dob"),
        ("Phone", "phone"),
        ("Email", "email"),
        ("Year", "year"),
        ("Semester", "semester"),
        ("Blood Group", "blood_group"),
        ("Aadhaar Number", "aadhaar_number"),
        ("Admission Date", "admission_date"),
        ("Status", "status"),
    ]

    start_y = page_height - 300
    canvas_obj.setFont("Helvetica", 11)
    for index, (label, key) in enumerate(details):
        row_y = start_y - (index * 20)
        canvas_obj.setFillColor(muted)
        canvas_obj.drawString(50, row_y, f"{label}:")
        canvas_obj.setFillColor(libs["colors"].black)
        canvas_obj.drawString(180, row_y, str(student.get(key, "")))

    qr_text = f"StudentID={student.get('student_id', '')};Name={student.get('full_name', '')};Roll={student.get('roll_number', '')}"
    _add_qr_code(libs, canvas_obj, qr_text, page_width - 150, 70, size=90)
    canvas_obj.setFillColor(muted)
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.drawString(46, 52, f"Generated on {human_datetime()}")
    canvas_obj.showPage()
    canvas_obj.save()
    return path


def generate_student_id_card_pdf(student: Dict[str, object], output_path: Optional[Path | str] = None) -> Path:
    libs = _ensure_reportlab()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    student_id = str(student.get("student_id", "student"))
    path = Path(output_path) if output_path else REPORT_DIR / f"id_card_{student_id}_{datetime.now():%Y%m%d_%H%M%S}.pdf"

    page_width = 360
    page_height = 220
    canvas_obj = libs["pdfcanvas"](str(path), pagesize=(page_width, page_height))
    primary = libs["HexColor"]("#1d4ed8")
    secondary = libs["HexColor"]("#0f172a")
    accent = libs["HexColor"]("#0f766e")

    canvas_obj.setFillColor(primary)
    canvas_obj.rect(0, 0, page_width, page_height, fill=1, stroke=0)
    canvas_obj.setFillColor(secondary)
    canvas_obj.roundRect(10, 10, page_width - 20, page_height - 20, 18, fill=1, stroke=0)

    canvas_obj.setFillColor(libs["colors"].white)
    canvas_obj.setFont("Helvetica-Bold", 18)
    canvas_obj.drawString(24, page_height - 38, APP_NAME)
    canvas_obj.setFont("Helvetica", 9)
    canvas_obj.drawString(24, page_height - 52, "Student Identity Card")

    photo_path = str(student.get("photo_path", "") or "")
    if photo_path:
        try:
            canvas_obj.drawImage(photo_path, 24, 86, width=68, height=84, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    canvas_obj.setFillColor(libs["colors"].white)
    canvas_obj.setFont("Helvetica-Bold", 12)
    canvas_obj.drawString(104, 144, str(student.get("full_name", "")))
    canvas_obj.setFont("Helvetica", 9)
    canvas_obj.drawString(104, 126, f"Student ID: {student.get('student_id', '')}")
    canvas_obj.drawString(104, 112, f"Roll Number: {student.get('roll_number', '')}")
    canvas_obj.drawString(104, 98, f"Course: {student.get('course', '')}")
    canvas_obj.drawString(104, 84, f"Department: {student.get('department', '')}")

    qr_text = f"{student.get('student_id', '')}|{student.get('full_name', '')}|{student.get('roll_number', '')}"
    _add_qr_code(libs, canvas_obj, qr_text, 258, 48, size=70)
    canvas_obj.setFillColor(accent)
    canvas_obj.setFont("Helvetica-Bold", 8)
    canvas_obj.drawString(24, 28, f"Issued: {current_year()}")
    canvas_obj.save()
    return path


class ReportsPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, style="TFrame")
        self.app = app
        self.selected_student: Optional[Dict[str, object]] = None
        self.keyword_var = tk.StringVar()
        self.search_field_var = tk.StringVar(value="all")
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, style="Card.TFrame", padding=16)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        header.columnconfigure(1, weight=1)

        ttk.Label(header, text="Reports and exports", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Export data, print student lists, and generate printable PDF report cards.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        search = ttk.Frame(self, style="Card.TFrame", padding=12)
        search.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        search.columnconfigure(1, weight=1)

        ttk.Label(search, text="Search", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Combobox(
            search,
            textvariable=self.search_field_var,
            values=["all", "name", "roll_number", "registration_number", "phone", "course", "department"],
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky="w", padx=(0, 10))
        ttk.Entry(search, textvariable=self.keyword_var).grid(row=0, column=2, sticky="ew", padx=(0, 10))
        ttk.Button(search, text="Find", style="Primary.TButton", command=self.refresh).grid(row=0, column=3, padx=(0, 8))
        ttk.Button(search, text="Reset", style="Ghost.TButton", command=self.reset_search).grid(row=0, column=4, padx=(0, 8))
        ttk.Button(search, text="Refresh", style="Ghost.TButton", command=self.refresh).grid(row=0, column=5)

        actions = ttk.Frame(self, style="Card.TFrame", padding=12)
        actions.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        actions.columnconfigure(0, weight=1)
        actions.rowconfigure(1, weight=1)

        buttons = ttk.Frame(actions, style="Card.TFrame")
        buttons.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for index in range(5):
            buttons.columnconfigure(index, weight=1)

        ttk.Button(buttons, text="Export CSV", style="Success.TButton", command=self.export_csv).grid(row=0, column=0, sticky="ew", padx=4)
        ttk.Button(buttons, text="Export Excel", style="Primary.TButton", command=self.export_excel).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(buttons, text="Student PDF", style="Ghost.TButton", command=self.generate_report_pdf).grid(row=0, column=2, sticky="ew", padx=4)
        ttk.Button(buttons, text="ID Card PDF", style="Ghost.TButton", command=self.generate_id_card_pdf).grid(row=0, column=3, sticky="ew", padx=4)
        ttk.Button(buttons, text="Print List", style="Danger.TButton", command=self.print_student_list).grid(row=0, column=4, sticky="ew", padx=4)

        table_frame = ttk.Frame(actions, style="Card.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("student_id", "full_name", "roll_number", "registration_number", "course", "department", "phone", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "student_id": "Student ID",
            "full_name": "Name",
            "roll_number": "Roll No",
            "registration_number": "Reg No",
            "course": "Course",
            "department": "Department",
            "phone": "Phone",
            "status": "Status",
        }
        widths = {"student_id": 130, "full_name": 180, "roll_number": 110, "registration_number": 120, "course": 120, "department": 140, "phone": 120, "status": 100}
        for column in columns:
            self.tree.heading(column, text=headings[column], command=lambda column_name=column: self._sort(column_name))
            self.tree.column(column, width=widths[column], anchor="w")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self.generate_report_pdf)

        footer = ttk.Frame(actions, style="Card.TFrame")
        footer.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(1, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(footer, text="Open Reports Folder", style="Ghost.TButton", command=lambda: open_path(REPORT_DIR)).grid(
            row=0, column=2, sticky="e"
        )

        self.sort_column = "created_at"
        self.sort_desc = True

    def _sort(self, column_name: str) -> None:
        mapping = {
            "student_id": "student_id",
            "full_name": "full_name",
            "roll_number": "roll_number",
            "registration_number": "registration_number",
            "course": "course",
            "department": "department",
            "phone": "phone",
            "status": "status",
        }
        field = mapping.get(column_name, "created_at")
        if self.sort_column == field:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_column = field
            self.sort_desc = False
        self.refresh()

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            self.selected_student = None
            return
        item = self.tree.item(selection[0], "values")
        student_id = item[0]
        self.selected_student = db.get_student_by_student_id(student_id)

    def reset_search(self) -> None:
        self.keyword_var.set("")
        self.search_field_var.set("all")
        self.refresh()

    def refresh(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        try:
            students = db.fetch_students(
                keyword=self.keyword_var.get(),
                field=self.search_field_var.get(),
                sort_field=self.sort_column,
                sort_desc=self.sort_desc,
            )
            for student in students:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        student.get("student_id", ""),
                        student.get("full_name", ""),
                        student.get("roll_number", ""),
                        student.get("registration_number", ""),
                        student.get("course", ""),
                        student.get("department", ""),
                        student.get("phone", ""),
                        student.get("status", ""),
                    ),
                )
            self.status_var.set(f"{len(students)} records loaded.")
        except Exception as exc:
            self.status_var.set("Unable to load reports.")
            show_error("Report Error", str(exc), self)

    def _selected_student_or_prompt(self) -> Optional[Dict[str, object]]:
        if self.selected_student:
            return self.selected_student
        selection = self.tree.selection()
        if not selection:
            show_error("Selection Required", "Select a student from the table first.", self)
            return None
        item = self.tree.item(selection[0], "values")
        self.selected_student = db.get_student_by_student_id(item[0])
        return self.selected_student

    def export_csv(self) -> None:
        try:
            students = db.fetch_students(
                keyword=self.keyword_var.get(),
                field=self.search_field_var.get(),
                sort_field=self.sort_column,
                sort_desc=self.sort_desc,
            )
            path = export_students_to_csv(students)
            show_info("Export Complete", f"CSV file saved to:\n{path}", self)
            self.status_var.set(f"Exported CSV to {path.name}")
        except Exception as exc:
            show_error("Export Error", str(exc), self)

    def export_excel(self) -> None:
        try:
            students = db.fetch_students(
                keyword=self.keyword_var.get(),
                field=self.search_field_var.get(),
                sort_field=self.sort_column,
                sort_desc=self.sort_desc,
            )
            path = export_students_to_excel(students)
            show_info("Export Complete", f"Excel file saved to:\n{path}", self)
            self.status_var.set(f"Exported Excel to {path.name}")
        except Exception as exc:
            show_error("Export Error", str(exc), self)

    def generate_report_pdf(self, _event=None) -> None:
        student = self._selected_student_or_prompt()
        if not student:
            return
        try:
            path = generate_student_report_pdf(student)
            show_info("Report Generated", f"PDF report created:\n{path}", self)
            self.status_var.set(f"Report generated for {student.get('full_name', '')}")
            open_path(path)
        except Exception as exc:
            show_error("PDF Error", str(exc), self)

    def generate_id_card_pdf(self) -> None:
        student = self._selected_student_or_prompt()
        if not student:
            return
        try:
            path = generate_student_id_card_pdf(student)
            show_info("ID Card Generated", f"ID card created:\n{path}", self)
            self.status_var.set(f"ID card generated for {student.get('full_name', '')}")
            open_path(path)
        except Exception as exc:
            show_error("ID Card Error", str(exc), self)

    def print_student_list(self) -> None:
        try:
            students = db.fetch_students(
                keyword=self.keyword_var.get(),
                field=self.search_field_var.get(),
                sort_field=self.sort_column,
                sort_desc=self.sort_desc,
            )
            path = generate_student_list_pdf(students)
            show_info("Print Ready", f"Printable PDF created:\n{path}", self)
            self.status_var.set(f"Printable list created with {len(students)} rows")
            open_path(path)
        except Exception as exc:
            show_error("Print Error", str(exc), self)

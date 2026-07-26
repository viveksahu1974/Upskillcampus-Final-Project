from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from database import db
from report import generate_student_id_card_pdf
from utils import (
    APP_NAME,
    IMAGE_DIR,
    STUDENT_PHOTO_DIR,
    create_placeholder_avatar,
    copy_student_photo,
    delete_file_if_exists,
    ensure_directories,
    load_image,
    normalize_student_payload,
    normalize_text,
    show_error,
    show_info,
    validate_student_data,
)


class StudentsPage(ttk.Frame):
    def __init__(self, parent: tk.Misc, app) -> None:
        super().__init__(parent, style="TFrame")
        self.app = app
        self.selected_db_id: Optional[int] = None
        self.current_student: Optional[Dict[str, object]] = None
        self.pending_photo_path: Optional[str] = None
        self.current_photo_path: Optional[str] = None
        self.sort_column = "created_at"
        self.sort_desc = True
        self.current_page = 0
        self.page_size_var = tk.IntVar(value=10)
        self.search_field_var = tk.StringVar(value="all")
        self.search_text_var = tk.StringVar()
        self.student_id_var = tk.StringVar(value=db.preview_student_id())
        self.full_name_var = tk.StringVar()
        self.roll_number_var = tk.StringVar()
        self.registration_number_var = tk.StringVar()
        self.father_name_var = tk.StringVar()
        self.mother_name_var = tk.StringVar()
        self.gender_var = tk.StringVar(value="Male")
        self.dob_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.course_var = tk.StringVar()
        self.year_var = tk.StringVar(value="1st Year")
        self.semester_var = tk.StringVar(value="1")
        self.department_var = tk.StringVar()
        self.blood_group_var = tk.StringVar()
        self.aadhaar_var = tk.StringVar()
        self.admission_date_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Active")
        self.message_var = tk.StringVar(value="Ready")
        self.total_count_var = tk.StringVar(value="0 records")

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, style="Card.TFrame", padding=16)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 10))
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Student Management", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Add, update, search, and organize student records from one modern workspace.",
            style="Muted.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Label(header, textvariable=self.total_count_var, style="Muted.TLabel").grid(row=0, column=2, sticky="e")

        toolbar = ttk.Frame(self, style="Card.TFrame", padding=12)
        toolbar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        for index in range(8):
            toolbar.columnconfigure(index, weight=1 if index in (2, 3) else 0)

        ttk.Label(toolbar, text="Search", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Combobox(
            toolbar,
            textvariable=self.search_field_var,
            state="readonly",
            values=["all", "name", "student_id", "roll_number", "registration_number", "phone", "course", "department"],
            width=18,
        ).grid(row=0, column=1, sticky="w", padx=(0, 8))
        self.search_text_entry = ttk.Entry(toolbar, textvariable=self.search_text_var)
        self.search_text_entry.grid(row=0, column=2, sticky="ew", padx=(0, 8))
        self.search_text_entry.bind("<Return>", lambda _event: self.search_students())
        ttk.Button(toolbar, text="Find", style="Primary.TButton", command=self.search_students).grid(row=0, column=3, sticky="ew", padx=(0, 6))
        ttk.Button(toolbar, text="View All", style="Ghost.TButton", command=self.view_all_students).grid(
            row=0, column=4, sticky="ew", padx=(0, 6)
        )
        ttk.Button(toolbar, text="Reset Form", style="Ghost.TButton", command=self.reset_form).grid(row=0, column=5, sticky="ew", padx=(0, 6))
        ttk.Button(toolbar, text="Reload", style="Ghost.TButton", command=self.refresh).grid(row=0, column=6, sticky="ew", padx=(0, 6))
        ttk.Button(toolbar, text="Reports", style="Success.TButton", command=lambda: self.app.switch_page("reports")).grid(
            row=0, column=7, sticky="ew"
        )

        body = ttk.Frame(self, style="TFrame")
        body.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        body.columnconfigure(0, weight=4)
        body.columnconfigure(1, weight=6)
        body.rowconfigure(0, weight=1)

        form_card = ttk.Frame(body, style="Card.TFrame", padding=16)
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        form_card.columnconfigure(0, weight=1)
        form_card.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(form_card)
        notebook.grid(row=0, column=0, sticky="nsew")
        self._build_identity_tab(notebook)
        self._build_academic_tab(notebook)
        self._build_contact_tab(notebook)
        self._build_photo_tab(notebook)

        actions = ttk.Frame(form_card, style="Card.TFrame")
        actions.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        for index in range(5):
            actions.columnconfigure(index, weight=1)

        ttk.Button(actions, text="Add Student", style="Primary.TButton", command=self.add_student).grid(
            row=0, column=0, sticky="ew", padx=4
        )
        ttk.Button(actions, text="Update Student", style="Success.TButton", command=self.update_student).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ttk.Button(actions, text="Delete Student", style="Danger.TButton", command=self.delete_student).grid(
            row=0, column=2, sticky="ew", padx=4
        )
        ttk.Button(actions, text="Generate ID Card", style="Ghost.TButton", command=self.generate_id_card).grid(
            row=0, column=3, sticky="ew", padx=4
        )
        ttk.Button(actions, text="Clear", style="Ghost.TButton", command=self.reset_form).grid(row=0, column=4, sticky="ew", padx=4)

        table_card = ttk.Frame(body, style="Card.TFrame", padding=16)
        table_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        table_card.columnconfigure(0, weight=1)
        table_card.rowconfigure(1, weight=1)

        table_header = ttk.Frame(table_card, style="Card.TFrame")
        table_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        table_header.columnconfigure(1, weight=1)
        ttk.Label(table_header, text="All Students", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(table_header, textvariable=self.message_var, style="Muted.TLabel").grid(row=0, column=1, sticky="e")

        columns = (
            "student_id",
            "full_name",
            "roll_number",
            "registration_number",
            "course",
            "department",
            "gender",
            "phone",
            "status",
            "admission_date",
        )
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")
        headings = {
            "student_id": "Student ID",
            "full_name": "Name",
            "roll_number": "Roll No",
            "registration_number": "Reg No",
            "course": "Course",
            "department": "Department",
            "gender": "Gender",
            "phone": "Phone",
            "status": "Status",
            "admission_date": "Admission",
        }
        widths = {
            "student_id": 120,
            "full_name": 160,
            "roll_number": 100,
            "registration_number": 110,
            "course": 120,
            "department": 130,
            "gender": 90,
            "phone": 110,
            "status": 90,
            "admission_date": 100,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column], command=lambda col=column: self._sort_by(col))
            self.tree.column(column, width=widths[column], anchor="w")

        y_scroll = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        y_scroll.grid(row=1, column=1, sticky="ns")
        x_scroll.grid(row=2, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", lambda _event: self.generate_id_card())

        paging = ttk.Frame(table_card, style="Card.TFrame")
        paging.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        paging.columnconfigure(1, weight=1)
        ttk.Button(paging, text="Prev", style="Ghost.TButton", command=self.prev_page).grid(row=0, column=0, padx=(0, 6))
        ttk.Label(paging, textvariable=self.total_count_var, style="Muted.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(paging, text="Page size", style="CardTitle.TLabel").grid(row=0, column=2, padx=(0, 6))
        page_size_box = ttk.Combobox(
            paging,
            textvariable=self.page_size_var,
            values=[10, 25, 50, 100],
            width=6,
            state="readonly",
        )
        page_size_box.grid(row=0, column=3, padx=(0, 6))
        page_size_box.bind("<<ComboboxSelected>>", lambda _event: self._change_page_size())
        ttk.Button(paging, text="Next", style="Ghost.TButton", command=self.next_page).grid(row=0, column=4, padx=(0, 6))
        ttk.Label(paging, textvariable=self.message_var, style="Muted.TLabel").grid(row=0, column=5, sticky="e")

        self._populate_placeholder_photo()

    def _focus_search(self) -> None:
        self.search_text_entry.focus_set()

    def _build_identity_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, style="Card.TFrame", padding=12)
        notebook.add(tab, text="Identity")
        tab.columnconfigure(1, weight=1)

        self._field(tab, 0, "Student ID", self.student_id_var, readonly=True)
        self._field(tab, 1, "Full Name", self.full_name_var)
        self._field(tab, 2, "Roll Number", self.roll_number_var)
        self._field(tab, 3, "Registration No.", self.registration_number_var)
        self._field(tab, 4, "Father's Name", self.father_name_var)
        self._field(tab, 5, "Mother's Name", self.mother_name_var)

        ttk.Label(tab, text="Gender", style="CardTitle.TLabel").grid(row=6, column=0, sticky="w", pady=(8, 4))
        ttk.Combobox(tab, textvariable=self.gender_var, values=["Male", "Female", "Other", "Prefer not to say"], state="readonly").grid(
            row=6, column=1, sticky="ew", pady=(8, 4)
        )
        self._field(tab, 7, "Date of Birth", self.dob_var)
        ttk.Label(tab, text="Blood Group", style="CardTitle.TLabel").grid(row=8, column=0, sticky="w", pady=(8, 4))
        ttk.Combobox(
            tab,
            textvariable=self.blood_group_var,
            values=["", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"],
            state="readonly",
        ).grid(row=8, column=1, sticky="ew", pady=(8, 4))

    def _build_academic_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, style="Card.TFrame", padding=12)
        notebook.add(tab, text="Academic")
        tab.columnconfigure(1, weight=1)

        self._field(tab, 0, "Course", self.course_var)
        ttk.Label(tab, text="Year", style="CardTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(8, 4))
        ttk.Combobox(
            tab,
            textvariable=self.year_var,
            values=["1st Year", "2nd Year", "3rd Year", "4th Year"],
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", pady=(8, 4))
        ttk.Label(tab, text="Semester", style="CardTitle.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 4))
        ttk.Combobox(tab, textvariable=self.semester_var, values=["1", "2", "3", "4", "5", "6", "7", "8"], state="readonly").grid(
            row=2, column=1, sticky="ew", pady=(8, 4)
        )
        self._field(tab, 3, "Department", self.department_var)
        ttk.Label(tab, text="Admission Date", style="CardTitle.TLabel").grid(row=4, column=0, sticky="w", pady=(8, 4))
        ttk.Entry(tab, textvariable=self.admission_date_var).grid(row=4, column=1, sticky="ew", pady=(8, 4))
        ttk.Label(tab, text="Student Status", style="CardTitle.TLabel").grid(row=5, column=0, sticky="w", pady=(8, 4))
        ttk.Combobox(
            tab,
            textvariable=self.status_var,
            values=["Active", "Inactive", "Graduated", "Transferred"],
            state="readonly",
        ).grid(row=5, column=1, sticky="ew", pady=(8, 4))

    def _build_contact_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, style="Card.TFrame", padding=12)
        notebook.add(tab, text="Contact")
        tab.columnconfigure(1, weight=1)

        self._field(tab, 0, "Phone Number", self.phone_var)
        self._field(tab, 1, "Email", self.email_var)
        self._field(tab, 2, "Aadhaar Number", self.aadhaar_var)
        ttk.Label(tab, text="Address", style="CardTitle.TLabel").grid(row=3, column=0, sticky="nw", pady=(8, 4))
        self.address_text = tk.Text(tab, height=5, wrap="word", relief="flat", borderwidth=1)
        self.address_text.grid(row=3, column=1, sticky="nsew", pady=(8, 4))
        tab.rowconfigure(3, weight=1)

    def _build_photo_tab(self, notebook: ttk.Notebook) -> None:
        tab = ttk.Frame(notebook, style="Card.TFrame", padding=12)
        notebook.add(tab, text="Photo")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        self.photo_preview_container = ttk.Frame(tab, style="Card.TFrame", padding=12)
        self.photo_preview_container.grid(row=0, column=0, sticky="ew")
        self.photo_label = ttk.Label(self.photo_preview_container, style="Card.TLabel")
        self.photo_label.pack(pady=(0, 8))
        ttk.Label(self.photo_preview_container, text="Preview", style="CardTitle.TLabel").pack()

        controls = ttk.Frame(tab, style="Card.TFrame")
        controls.grid(row=1, column=0, sticky="nsew", pady=(16, 0))
        controls.columnconfigure(0, weight=1)
        ttk.Button(controls, text="Upload Photo", style="Primary.TButton", command=self.upload_photo).pack(fill="x", pady=6)
        ttk.Button(controls, text="Capture Photo", style="Ghost.TButton", command=self.capture_photo).pack(fill="x", pady=6)
        ttk.Button(controls, text="Delete Photo", style="Danger.TButton", command=self.delete_photo).pack(fill="x", pady=6)
        ttk.Button(controls, text="Generate ID Card", style="Success.TButton", command=self.generate_id_card).pack(fill="x", pady=6)

    def _field(self, parent, row: int, label: str, variable: tk.StringVar, readonly: bool = False) -> None:
        ttk.Label(parent, text=label, style="CardTitle.TLabel").grid(row=row, column=0, sticky="w", pady=(8, 4))
        entry = ttk.Entry(parent, textvariable=variable, state="readonly" if readonly else "normal")
        entry.grid(row=row, column=1, sticky="ew", pady=(8, 4))
        if label == "Student ID":
            self.student_id_entry = entry
        elif label == "Full Name":
            self.full_name_entry = entry
        elif label == "Roll Number":
            self.roll_number_entry = entry
        elif label == "Registration No.":
            self.registration_number_entry = entry
        elif label == "Father's Name":
            self.father_name_entry = entry
        elif label == "Mother's Name":
            self.mother_name_entry = entry
        elif label == "Course":
            self.course_entry = entry
        elif label == "Phone Number":
            self.phone_entry = entry
        elif label == "Email":
            self.email_entry = entry
        elif label == "Aadhaar Number":
            self.aadhaar_entry = entry

    def _populate_placeholder_photo(self) -> None:
        ensure_directories()
        placeholder = IMAGE_DIR / "avatar_placeholder.png"
        if not placeholder.exists():
            create_placeholder_avatar(placeholder, "SMS")
        self._set_photo_preview(str(placeholder), placeholder_text="No Photo")

    def _set_photo_preview(self, path: Optional[str], placeholder_text: str = "No Photo") -> None:
        if path and Path(path).exists():
            image = load_image(path, (180, 180))
            if image is not None:
                self.photo_label.configure(image=image, text="")
                self.photo_label.image = image
                return
        self.photo_label.configure(text=placeholder_text, image="")
        self.photo_label.image = None

    def apply_theme(self, palette: Dict[str, str]) -> None:
        try:
            self.address_text.configure(bg=palette["input"], fg=palette["text"], insertbackground=palette["text"])
        except Exception:
            pass

    def _build_student_payload(self) -> Dict[str, object]:
        return {
            "full_name": self.full_name_var.get(),
            "roll_number": self.roll_number_var.get(),
            "registration_number": self.registration_number_var.get(),
            "father_name": self.father_name_var.get(),
            "mother_name": self.mother_name_var.get(),
            "gender": self.gender_var.get(),
            "dob": self.dob_var.get(),
            "phone": self.phone_var.get(),
            "email": self.email_var.get(),
            "address": self.address_text.get("1.0", "end").strip(),
            "course": self.course_var.get(),
            "year": self.year_var.get(),
            "semester": self.semester_var.get(),
            "department": self.department_var.get(),
            "blood_group": self.blood_group_var.get(),
            "aadhaar_number": self.aadhaar_var.get(),
            "admission_date": self.admission_date_var.get(),
            "status": self.status_var.get(),
            "photo_path": self.current_photo_path or self.pending_photo_path or "",
        }

    def _validate_payload(self, payload: Dict[str, object]) -> Optional[Dict[str, object]]:
        errors = validate_student_data(payload)
        if errors:
            show_error("Validation Error", "\n".join(errors), self)
            return None
        return normalize_student_payload(payload)

    def add_student(self) -> None:
        payload = self._build_student_payload()
        normalized = self._validate_payload(payload)
        if not normalized:
            return

        try:
            student = db.add_student(normalized)
            if self.pending_photo_path:
                copied_path = copy_student_photo(student["student_id"], self.pending_photo_path)
                student = db.update_student(student["id"], {**student, "photo_path": str(copied_path)})
            self.pending_photo_path = None
            show_info("Success", "Student added successfully.", self)
            self.reset_form()
            self.app.refresh_active_pages()
            self.message_var.set(f"Student {student['student_id']} added successfully.")
        except Exception as exc:
            show_error("Add Student Error", str(exc), self)

    def update_student(self) -> None:
        if not self.selected_db_id:
            show_error("Selection Required", "Select a student record first.", self)
            return
        payload = self._build_student_payload()
        normalized = self._validate_payload(payload)
        if not normalized:
            return
        try:
            student = db.update_student(self.selected_db_id, normalized)
            if self.pending_photo_path:
                if student.get("photo_path"):
                    delete_file_if_exists(student.get("photo_path"))
                copied_path = copy_student_photo(student["student_id"], self.pending_photo_path)
                student = db.update_student(student["id"], {**student, "photo_path": str(copied_path)})
            self.current_student = student
            self.current_photo_path = student.get("photo_path") or None
            self.pending_photo_path = None
            show_info("Success", "Student updated successfully.", self)
            self.app.refresh_active_pages()
            self.message_var.set(f"Student {student['student_id']} updated successfully.")
        except Exception as exc:
            show_error("Update Error", str(exc), self)

    def delete_student(self) -> None:
        if not self.selected_db_id:
            show_error("Selection Required", "Select a student record first.", self)
            return
        student = self.current_student or db.get_student_by_id(self.selected_db_id)
        if not student:
            show_error("Not Found", "Selected student could not be found.", self)
            return
        if not messagebox.askyesno("Confirm Delete", "Delete this student record permanently?", parent=self):
            return
        try:
            delete_file_if_exists(student.get("photo_path"))
            db.delete_student(self.selected_db_id)
            show_info("Deleted", "Student deleted successfully.", self)
            self.reset_form()
            self.app.refresh_active_pages()
            self.message_var.set("Student deleted.")
        except Exception as exc:
            show_error("Delete Error", str(exc), self)

    def generate_id_card(self) -> None:
        student: Optional[Dict[str, object]] = self.current_student
        if not student and self.selected_db_id:
            student = db.get_student_by_id(self.selected_db_id)
        if not student:
            show_error("Selection Required", "Save or select a student first.", self)
            return
        try:
            path = generate_student_id_card_pdf(student)
            show_info("ID Card Generated", f"ID card saved to:\n{path}", self)
        except Exception as exc:
            show_error("ID Card Error", str(exc), self)

    def search_students(self) -> None:
        self.current_page = 0
        self.refresh()

    def view_all_students(self) -> None:
        self.search_text_var.set("")
        self.search_field_var.set("all")
        self.current_page = 0
        self.refresh()

    def reset_form(self, keep_preview: bool = False) -> None:
        self.selected_db_id = None
        self.current_student = None
        self.pending_photo_path = None
        self.current_photo_path = None
        self.student_id_var.set(db.preview_student_id())
        self.full_name_var.set("")
        self.roll_number_var.set("")
        self.registration_number_var.set("")
        self.father_name_var.set("")
        self.mother_name_var.set("")
        self.gender_var.set("Male")
        self.dob_var.set("")
        self.phone_var.set("")
        self.email_var.set("")
        self.course_var.set("")
        self.year_var.set("1st Year")
        self.semester_var.set("1")
        self.department_var.set("")
        self.blood_group_var.set("")
        self.aadhaar_var.set("")
        self.admission_date_var.set("")
        self.status_var.set("Active")
        self.address_text.delete("1.0", "end")
        if not keep_preview:
            self._populate_placeholder_photo()
        self.message_var.set("Form reset.")

    def upload_photo(self) -> None:
        photo = filedialog.askopenfilename(
            parent=self,
            title="Select Student Photo",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All Files", "*.*")],
        )
        if not photo:
            return
        self.pending_photo_path = photo
        self.current_photo_path = photo
        self._set_photo_preview(photo)
        self.message_var.set("Photo selected.")

    def capture_photo(self) -> None:
        try:
            import cv2
        except Exception:
            show_error("Webcam Unavailable", "OpenCV is not installed, so webcam capture is unavailable.", self)
            return

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            show_error("Webcam Error", "Unable to open the webcam.", self)
            return

        captured_path = Path(tempfile.gettempdir()) / "sms_captured_photo.png"
        try:
            while True:
                success, frame = camera.read()
                if not success:
                    raise RuntimeError("Unable to capture a webcam frame.")
                cv2.imshow("Capture Photo - Press C to Save / Q to Cancel", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("c"), ord("C")):
                    cv2.imwrite(str(captured_path), frame)
                    self.pending_photo_path = str(captured_path)
                    self.current_photo_path = str(captured_path)
                    self._set_photo_preview(str(captured_path))
                    self.message_var.set("Photo captured from webcam.")
                    break
                if key in (ord("q"), ord("Q"), 27):
                    break
        finally:
            camera.release()
            cv2.destroyAllWindows()

    def delete_photo(self) -> None:
        if self.current_student and self.current_student.get("photo_path"):
            if not messagebox.askyesno("Delete Photo", "Remove the saved photo from this student?", parent=self):
                return
            try:
                delete_file_if_exists(self.current_student.get("photo_path"))
                student = db.update_student(self.current_student["id"], {**self.current_student, "photo_path": ""})
                self.current_student = student
                self.current_photo_path = None
                self.pending_photo_path = None
                self._populate_placeholder_photo()
                self.message_var.set("Photo deleted.")
                show_info("Deleted", "Student photo removed successfully.", self)
            except Exception as exc:
                show_error("Delete Photo Error", str(exc), self)
        else:
            self.pending_photo_path = None
            self.current_photo_path = None
            self._populate_placeholder_photo()
            self.message_var.set("Photo cleared.")

    def _sort_by(self, column: str) -> None:
        mapping = {
            "student_id": "student_id",
            "full_name": "full_name",
            "roll_number": "roll_number",
            "registration_number": "registration_number",
            "course": "course",
            "department": "department",
            "gender": "gender",
            "phone": "phone",
            "status": "status",
            "admission_date": "admission_date",
        }
        field = mapping.get(column, "created_at")
        if self.sort_column == field:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_column = field
            self.sort_desc = False
        self.refresh()

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        student_id = values[0]
        student = db.get_student_by_student_id(student_id)
        if not student:
            return
        self._load_student(student)

    def _load_student(self, student: Dict[str, object]) -> None:
        self.selected_db_id = int(student["id"])
        self.current_student = student
        self.student_id_var.set(str(student.get("student_id", "")))
        self.full_name_var.set(str(student.get("full_name", "")))
        self.roll_number_var.set(str(student.get("roll_number", "")))
        self.registration_number_var.set(str(student.get("registration_number", "")))
        self.father_name_var.set(str(student.get("father_name", "")))
        self.mother_name_var.set(str(student.get("mother_name", "")))
        self.gender_var.set(str(student.get("gender", "Male")))
        self.dob_var.set(str(student.get("dob", "")))
        self.phone_var.set(str(student.get("phone", "")))
        self.email_var.set(str(student.get("email", "")))
        self.course_var.set(str(student.get("course", "")))
        self.year_var.set(str(student.get("year", "1st Year")))
        self.semester_var.set(str(student.get("semester", "1")))
        self.department_var.set(str(student.get("department", "")))
        self.blood_group_var.set(str(student.get("blood_group", "")))
        self.aadhaar_var.set(str(student.get("aadhaar_number", "")))
        self.admission_date_var.set(str(student.get("admission_date", "")))
        self.status_var.set(str(student.get("status", "Active")))
        self.address_text.delete("1.0", "end")
        self.address_text.insert("1.0", str(student.get("address", "")))
        self.current_photo_path = str(student.get("photo_path", "") or "") or None
        self.pending_photo_path = None
        self._set_photo_preview(self.current_photo_path)
        self.message_var.set(f"Selected {student.get('student_id', '')}.")

    def refresh(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        limit = int(self.page_size_var.get() or 10)
        offset = self.current_page * limit
        keyword = self.search_text_var.get().strip()
        field = self.search_field_var.get().strip()

        try:
            total = db.count_students(keyword=keyword, field=field)
            students = db.fetch_students(
                keyword=keyword,
                field=field,
                sort_field=self.sort_column,
                sort_desc=self.sort_desc,
                limit=limit,
                offset=offset,
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
                        student.get("gender", ""),
                        student.get("phone", ""),
                        student.get("status", ""),
                        student.get("admission_date", ""),
                    ),
                )
            total_pages = max(1, (total + limit - 1) // limit)
            self.total_count_var.set(f"{total} records | Page {self.current_page + 1} of {total_pages}")
            self.message_var.set("Records loaded successfully.")
        except Exception as exc:
            show_error("Load Error", str(exc), self)

    def next_page(self) -> None:
        limit = int(self.page_size_var.get() or 10)
        total = db.count_students(keyword=self.search_text_var.get().strip(), field=self.search_field_var.get().strip())
        if (self.current_page + 1) * limit >= total:
            return
        self.current_page += 1
        self.refresh()

    def prev_page(self) -> None:
        if self.current_page <= 0:
            return
        self.current_page -= 1
        self.refresh()

    def _change_page_size(self) -> None:
        self.current_page = 0
        self.refresh()

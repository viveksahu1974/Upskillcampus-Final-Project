from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from utils import (
    BACKUP_DIR,
    DB_PATH,
    current_year,
    ensure_directories,
    hash_password,
    normalize_student_payload,
    now_iso,
    safe_copy,
    verify_password,
)


class DatabaseManager:
    def __init__(self, db_path: Path | str = DB_PATH) -> None:
        ensure_directories()
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _ensure_schema(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    security_question TEXT NOT NULL,
                    security_answer_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT
                );

                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT UNIQUE,
                    full_name TEXT NOT NULL,
                    roll_number TEXT NOT NULL UNIQUE,
                    registration_number TEXT NOT NULL UNIQUE,
                    father_name TEXT NOT NULL,
                    mother_name TEXT NOT NULL,
                    gender TEXT NOT NULL,
                    dob TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT NOT NULL,
                    address TEXT NOT NULL,
                    course TEXT NOT NULL,
                    year TEXT NOT NULL,
                    semester TEXT NOT NULL,
                    department TEXT NOT NULL,
                    blood_group TEXT,
                    aadhaar_number TEXT,
                    admission_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    photo_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_students_roll ON students(roll_number);
                CREATE INDEX IF NOT EXISTS idx_students_reg ON students(registration_number);
                CREATE INDEX IF NOT EXISTS idx_students_course ON students(course);
                CREATE INDEX IF NOT EXISTS idx_students_department ON students(department);
                """
            )

    @staticmethod
    def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        return dict(row)

    def admin_count(self) -> int:
        with self.connection() as connection:
            cursor = connection.execute("SELECT COUNT(*) FROM admins")
            return int(cursor.fetchone()[0])

    def has_admins(self) -> bool:
        return self.admin_count() > 0

    def get_admin_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT * FROM admins WHERE username = ?",
                (username.strip(),),
            )
            return self._row_to_dict(cursor.fetchone())

    def get_admin_by_id(self, admin_id: int) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT * FROM admins WHERE id = ?",
                (admin_id,),
            )
            return self._row_to_dict(cursor.fetchone())

    def create_admin(
        self,
        full_name: str,
        username: str,
        password: str,
        security_question: str,
        security_answer: str,
    ) -> int:
        full_name = full_name.strip()
        username = username.strip().lower()
        if not full_name or not username or not password:
            raise ValueError("Admin profile is incomplete.")
        if self.get_admin_by_username(username):
            raise ValueError("Username already exists.")

        with self.connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO admins (
                    full_name, username, password_hash, security_question,
                    security_answer_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    full_name,
                    username,
                    hash_password(password),
                    security_question.strip(),
                    hash_password(security_answer.lower().strip()),
                    now_iso(),
                ),
            )
            return int(cursor.lastrowid)

    def authenticate_admin(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        admin = self.get_admin_by_username(username)
        if not admin or not verify_password(password, admin["password_hash"]):
            return None
        self.update_last_login(int(admin["id"]))
        return self.get_admin_by_id(int(admin["id"]))

    def update_last_login(self, admin_id: int) -> None:
        with self.connection() as connection:
            connection.execute(
                "UPDATE admins SET last_login = ? WHERE id = ?",
                (now_iso(), admin_id),
            )

    def change_password(self, admin_id: int, current_password: str, new_password: str) -> None:
        admin = self.get_admin_by_id(admin_id)
        if not admin:
            raise ValueError("Admin account not found.")
        if not verify_password(current_password, admin["password_hash"]):
            raise ValueError("Current password is incorrect.")

        with self.connection() as connection:
            connection.execute(
                "UPDATE admins SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), admin_id),
            )

    def reset_password_by_security(
        self,
        username: str,
        security_answer: str,
        new_password: str,
    ) -> None:
        admin = self.get_admin_by_username(username)
        if not admin:
            raise ValueError("Username not found.")

        answer = security_answer.lower().strip()
        if not verify_password(answer, admin["security_answer_hash"]):
            raise ValueError("Security answer does not match.")

        with self.connection() as connection:
            connection.execute(
                "UPDATE admins SET password_hash = ? WHERE id = ?",
                (hash_password(new_password), admin["id"]),
            )

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self.connection() as connection:
            cursor = connection.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                INSERT INTO app_settings(key, value)
                VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )

    def delete_setting(self, key: str) -> None:
        with self.connection() as connection:
            connection.execute("DELETE FROM app_settings WHERE key = ?", (key,))

    def preview_student_id(self) -> str:
        with self.connection() as connection:
            cursor = connection.execute("SELECT seq FROM sqlite_sequence WHERE name = ?", ("students",))
            row = cursor.fetchone()
            if row and row[0] is not None:
                next_id = int(row[0]) + 1
            else:
                cursor = connection.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM students")
                next_id = int(cursor.fetchone()[0])
        return self._build_student_id(next_id)

    def _build_student_id(self, row_id: int) -> str:
        stamp = datetime.now().strftime("%Y%m%d")
        return f"STD{stamp}{row_id:05d}"

    def _student_exists(
        self,
        field: str,
        value: str,
        exclude_id: Optional[int] = None,
    ) -> bool:
        sql = f"SELECT 1 FROM students WHERE {field} = ?"
        params: List[Any] = [value]
        if exclude_id is not None:
            sql += " AND id != ?"
            params.append(exclude_id)
        with self.connection() as connection:
            cursor = connection.execute(sql, params)
            return cursor.fetchone() is not None

    def student_exists_by_roll(self, roll_number: str, exclude_id: Optional[int] = None) -> bool:
        return self._student_exists("roll_number", roll_number.strip(), exclude_id=exclude_id)

    def student_exists_by_registration(self, registration_number: str, exclude_id: Optional[int] = None) -> bool:
        return self._student_exists("registration_number", registration_number.strip(), exclude_id=exclude_id)

    def student_exists_by_phone(self, phone: str, exclude_id: Optional[int] = None) -> bool:
        return self._student_exists("phone", phone.strip(), exclude_id=exclude_id)

    def student_exists_by_aadhaar(self, aadhaar_number: str, exclude_id: Optional[int] = None) -> bool:
        return self._student_exists("aadhaar_number", aadhaar_number.strip(), exclude_id=exclude_id)

    def _assert_unique_student_fields(self, data: Dict[str, Any], exclude_id: Optional[int] = None) -> None:
        checks = [
            ("roll_number", "Roll Number"),
            ("registration_number", "Registration Number"),
            ("aadhaar_number", "Aadhaar Number"),
        ]
        for field, label in checks:
            value = str(data.get(field, "")).strip()
            if value and self._student_exists(field, value, exclude_id=exclude_id):
                raise ValueError(f"{label} already exists.")

    def add_student(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = normalize_student_payload(data)
        self._assert_unique_student_fields(payload)
        payload.setdefault("blood_group", "")
        payload.setdefault("aadhaar_number", "")
        payload.setdefault("photo_path", "")

        columns = [
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
        values = [
            None,
            payload["full_name"],
            payload["roll_number"],
            payload["registration_number"],
            payload["father_name"],
            payload["mother_name"],
            payload["gender"],
            payload["dob"],
            payload["phone"],
            payload["email"],
            payload["address"],
            payload["course"],
            payload["year"],
            payload["semester"],
            payload["department"],
            payload.get("blood_group", ""),
            payload.get("aadhaar_number", ""),
            payload["admission_date"],
            payload["status"],
            payload.get("photo_path", ""),
            now_iso(),
            now_iso(),
        ]

        with self.connection() as connection:
            cursor = connection.execute(
                f"INSERT INTO students ({', '.join(columns)}) VALUES ({', '.join(['?'] * len(columns))})",
                values,
            )
            row_id = int(cursor.lastrowid)
            student_id = self._build_student_id(row_id)
            connection.execute(
                "UPDATE students SET student_id = ? WHERE id = ?",
                (student_id, row_id),
            )
        return self.get_student_by_id(row_id)  # type: ignore[return-value]

    def update_student(self, student_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        existing = self.get_student_by_id(student_id)
        if not existing:
            raise ValueError("Student not found.")

        payload = normalize_student_payload(data)
        self._assert_unique_student_fields(payload, exclude_id=student_id)
        payload.setdefault("blood_group", "")
        payload.setdefault("aadhaar_number", "")
        payload.setdefault("photo_path", "")

        with self.connection() as connection:
            connection.execute(
                """
                UPDATE students
                SET
                    full_name = ?,
                    roll_number = ?,
                    registration_number = ?,
                    father_name = ?,
                    mother_name = ?,
                    gender = ?,
                    dob = ?,
                    phone = ?,
                    email = ?,
                    address = ?,
                    course = ?,
                    year = ?,
                    semester = ?,
                    department = ?,
                    blood_group = ?,
                    aadhaar_number = ?,
                    admission_date = ?,
                    status = ?,
                    photo_path = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    payload["full_name"],
                    payload["roll_number"],
                    payload["registration_number"],
                    payload["father_name"],
                    payload["mother_name"],
                    payload["gender"],
                    payload["dob"],
                    payload["phone"],
                    payload["email"],
                    payload["address"],
                    payload["course"],
                    payload["year"],
                    payload["semester"],
                    payload["department"],
                    payload.get("blood_group", ""),
                    payload.get("aadhaar_number", ""),
                    payload["admission_date"],
                    payload["status"],
                    payload.get("photo_path", ""),
                    now_iso(),
                    student_id,
                ),
            )
        return self.get_student_by_id(student_id)  # type: ignore[return-value]

    def delete_student(self, student_id: int) -> None:
        student = self.get_student_by_id(student_id)
        if not student:
            raise ValueError("Student not found.")
        with self.connection() as connection:
            connection.execute("DELETE FROM students WHERE id = ?", (student_id,))

    def get_student_by_id(self, student_id: int) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            return self._row_to_dict(cursor.fetchone())

    def get_student_by_student_id(self, student_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
            return self._row_to_dict(cursor.fetchone())

    def get_student_by_roll(self, roll_number: str) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute("SELECT * FROM students WHERE roll_number = ?", (roll_number.strip(),))
            return self._row_to_dict(cursor.fetchone())

    def get_student_by_registration(self, registration_number: str) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT * FROM students WHERE registration_number = ?",
                (registration_number.strip(),),
            )
            return self._row_to_dict(cursor.fetchone())

    def get_student_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute("SELECT * FROM students WHERE phone = ?", (phone.strip(),))
            return self._row_to_dict(cursor.fetchone())

    def _build_search_clause(
        self,
        keyword: str = "",
        field: str = "all",
        filters: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []

        keyword = keyword.strip()
        filters = filters or {}

        if keyword:
            like_value = f"%{keyword}%"
            field_map = {
                "all": [
                    "student_id",
                    "full_name",
                    "roll_number",
                    "registration_number",
                    "phone",
                    "course",
                    "department",
                ],
                "student_id": ["student_id"],
                "name": ["full_name"],
                "roll_number": ["roll_number"],
                "registration_number": ["registration_number"],
                "phone": ["phone"],
                "course": ["course"],
                "department": ["department"],
            }
            columns = field_map.get(field, field_map["all"])
            if len(columns) == 1:
                clauses.append(f"{columns[0]} LIKE ?")
                params.append(like_value)
            else:
                clauses.append("(" + " OR ".join([f"{column} LIKE ?" for column in columns]) + ")")
                params.extend([like_value] * len(columns))

        for key, value in filters.items():
            if value and value != "All":
                clauses.append(f"{key} = ?")
                params.append(value.strip())

        clause = ""
        if clauses:
            clause = " WHERE " + " AND ".join(clauses)
        return clause, params

    def _sanitize_sort_field(self, sort_field: str) -> str:
        allowed = {
            "id",
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
            "created_at",
            "updated_at",
        }
        return sort_field if sort_field in allowed else "created_at"

    def fetch_students(
        self,
        keyword: str = "",
        field: str = "all",
        filters: Optional[Dict[str, str]] = None,
        sort_field: str = "created_at",
        sort_desc: bool = True,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        clause, params = self._build_search_clause(keyword, field, filters)
        order_by = self._sanitize_sort_field(sort_field)
        direction = "DESC" if sort_desc else "ASC"
        sql = f"SELECT * FROM students{clause} ORDER BY {order_by} {direction}, id {direction}"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([int(limit), int(offset)])
        with self.connection() as connection:
            cursor = connection.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def count_students(
        self,
        keyword: str = "",
        field: str = "all",
        filters: Optional[Dict[str, str]] = None,
    ) -> int:
        clause, params = self._build_search_clause(keyword, field, filters)
        with self.connection() as connection:
            cursor = connection.execute(f"SELECT COUNT(*) FROM students{clause}", params)
            return int(cursor.fetchone()[0])

    def all_students(self) -> List[Dict[str, Any]]:
        return self.fetch_students(sort_field="created_at", sort_desc=True)

    def recent_students(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT * FROM students ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def count_courses(self) -> int:
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT COUNT(DISTINCT course) FROM students WHERE TRIM(COALESCE(course, '')) <> ''"
            )
            return int(cursor.fetchone()[0])

    def count_gender(self, gender: str) -> int:
        with self.connection() as connection:
            cursor = connection.execute(
                "SELECT COUNT(*) FROM students WHERE LOWER(gender) = LOWER(?)",
                (gender,),
            )
            return int(cursor.fetchone()[0])

    def count_by_status(self) -> List[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT status AS label, COUNT(*) AS total
                FROM students
                WHERE TRIM(COALESCE(status, '')) <> ''
                GROUP BY status
                ORDER BY total DESC, label ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def count_by_department(self) -> List[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT department AS label, COUNT(*) AS total
                FROM students
                WHERE TRIM(COALESCE(department, '')) <> ''
                GROUP BY department
                ORDER BY total DESC, label ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def count_by_gender(self) -> List[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT gender AS label, COUNT(*) AS total
                FROM students
                WHERE TRIM(COALESCE(gender, '')) <> ''
                GROUP BY gender
                ORDER BY total DESC, label ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def count_by_admission_year(self) -> List[Dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT SUBSTR(admission_date, 1, 4) AS label, COUNT(*) AS total
                FROM students
                WHERE TRIM(COALESCE(admission_date, '')) <> ''
                GROUP BY SUBSTR(admission_date, 1, 4)
                ORDER BY label ASC
                """
            )
            return [dict(row) for row in cursor.fetchall()]

    def distinct_courses(self) -> List[str]:
        with self.connection() as connection:
            cursor = connection.execute(
                """
                SELECT DISTINCT course
                FROM students
                WHERE TRIM(COALESCE(course, '')) <> ''
                ORDER BY course ASC
                """
            )
            return [row[0] for row in cursor.fetchall()]

    def total_students(self) -> int:
        return self.count_students()

    def total_male_students(self) -> int:
        return self.count_gender("Male")

    def total_female_students(self) -> int:
        return self.count_gender("Female")

    def backup_database(self, destination: Optional[Path | str] = None) -> Path:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if destination is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            destination = BACKUP_DIR / f"students_backup_{stamp}.db"
        destination_path = Path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.db_path, destination_path)
        return destination_path

    def restore_database(self, source: Path | str) -> Path:
        source_path = Path(source)
        if not source_path.exists():
            raise FileNotFoundError("Backup file not found.")
        shutil.copy2(source_path, self.db_path)
        self._ensure_schema()
        return self.db_path

    def reset_database(self) -> None:
        if self.db_path.exists():
            self.db_path.unlink()
        self._ensure_schema()


db = DatabaseManager()

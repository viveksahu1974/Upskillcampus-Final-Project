# Student Management System

## Browser-only portfolio preview

**[▶ Try the interactive Student Management dashboard preview](https://viveksahu1974.github.io/portfolio/student-manager-demo/)** — a static web recreation showing synthetic student records, filtering, sample add/delete and CSV export. **This is not the actual Tkinter + SQLite desktop application**: there is no database, login, webcam or persisted records. For the full program, use `python main.py` as documented below.

A premium desktop Student Management System built with Python, Tkinter, and SQLite.

## Features

- Secure admin authentication with hashed passwords
- Register new admin and forgot-password recovery using security questions
- Remember me, show/hide password, and responsive login screen
- Modern dashboard with live statistics, recent students, and quick actions
- Full student CRUD with search, filtering, sorting, and pagination
- Photo upload, webcam capture, preview, update, and delete
- CSV, Excel, and PDF exports
- Student report card PDF and QR-backed ID card PDF
- Charts for department, gender, admission year, and status
- Theme switching, backups, restores, and password change
- Keyboard shortcuts and splash screen

## Project Structure

```text
student_management_system/
├── main.py
├── login.py
├── register.py
├── dashboard.py
├── students.py
├── database.py
├── report.py
├── settings.py
├── utils.py
├── assets/
├── database/
├── exports/
├── reports/
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10+
- Tkinter
- SQLite
- Pillow
- pandas
- openpyxl
- matplotlib
- opencv-python
- reportlab

## Run

```bash
pip install -r requirements.txt
python main.py
```

On Windows, you can also run:

```bash
py -3 main.py
```

## Notes

- The app creates the SQLite database and folders automatically on first launch.
- If no admin account exists yet, use `Register New Admin` from the login screen.
- Webcam capture requires OpenCV and a working camera device.

## License

Use this project freely for learning, portfolios, internship submissions, and demonstrations.

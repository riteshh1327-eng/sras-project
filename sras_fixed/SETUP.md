# SRAS — Student Result Analysis System
## Setup & Installation Guide

---

## Architecture

```
Student (permanent identity — name, email, DOB, gender)
    └── Enrollment (student + class + roll_id + academic_year)
             └── SemesterSubject (subject + semester + credits + components)
                      └── EnhancedResult (5-component marks: IA1, IA2, TW, Oral, SEM)
                               └── SemesterSummary (cached SGPA/CGPA per semester)
```

---

## Prerequisites

- Python 3.10+
- pip

---

## Quick Start

### 1. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate.bat       # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` contains:
```
Django>=4.2,<5.0
openpyxl>=3.1.0
```

### 3. Apply migrations

```bash
python manage.py migrate
```

This runs all 4 migrations in order:
- `0001_initial` — Student, StudentClass, Subject, Result, Notice
- `0002_teacher_result_computed` — Teacher, computed fields on Result
- `0003_result_engine` — GradeScale, SemesterSubject, EnhancedResult, SemesterSummary
- `0004_enrollment_and_refactor` — Enrollment bridge model, data migration, index fixes

### 4. Seed grade scale (optional — already seeded in migration 0003)

```bash
python manage.py seed_engine
```

### 5. Create a teacher account

```bash
python manage.py shell
```

```python
from core.models import Teacher
t = Teacher(name='Admin Teacher', email='teacher@sras.com')
t.set_password('admin123')
t.save()
exit()
```

### 6. Run development server

```bash
python manage.py runserver
```

Open: **http://127.0.0.1:8000**

---

## Accounts

| Role    | Email               | Password   | Notes                           |
|---------|---------------------|------------|---------------------------------|
| Teacher | teacher@sras.com    | admin123   | Created manually above          |
| Student | student@example.com | DDMMYYYY   | Date of Birth as password       |
| Student | student@example.com | SE001      | Legacy fallback: roll_id        |

---

## Workflow (Teacher)

1. **Create a Class** → `/classes/create/`  
   e.g., SE-A, Academic Year: 2024-25

2. **Add Subjects** → `/subjects/create/`  
   e.g., Data Structures, Networks

3. **Add Subject Combinations** → `/combinations/create/`  
   Link subjects to a class

4. **Add Students** (one of three ways):
   - Manual: `/students/add/` → then **Enroll** at `/engine/enrollments/add/`
   - Excel Upload: `/students/upload/` (creates Student + Enrollment together)
   - Django Admin: `/admin/`

5. **Create Semester Subjects** → `/engine/subjects/`  
   Configure credits, IA/TW/Oral/SEM components and max marks

6. **Enter Marks** → `/results/engine/bulk/`  
   Select Year → Class → Semester → Subject → Component → Enter marks row by row  
   Excel-style Enter key navigation supported

7. **View Results** → `/results/engine/class/`

8. **View Analytics** → `/analytics/teacher/`

---

## Workflow (Student)

1. Login with email + Date of Birth (DDMMYYYY format)  
   e.g., DOB = 15 Aug 2004 → password = `15082004`

2. View results at `/student/results/explore/`

3. Download marksheet at `/student/marksheet/<semester>/<year>/`

---

## Phase-Aware Grading

Marks entry supports progressive phases:

| Phase   | Condition                    | Status            |
|---------|------------------------------|-------------------|
| Phase 0 | No marks entered             | `Pending`         |
| Phase 1 | Only IA1 entered             | `Phase1 Pass/Fail`|
| Phase 2 | IA1 + IA2, no SEM            | `Phase2 Pass/Fail`|
| Final   | SEM entered (or no-SEM subj) | `Pass / Fail / Absent` |

---

## Grade Scale (University of Mumbai)

| Grade | Min % | Max % | Points | Pass? |
|-------|-------|-------|--------|-------|
| O     | 75    | 100   | 10.0   | Yes   |
| A+    | 65    | 74    | 9.0    | Yes   |
| A     | 55    | 64    | 8.0    | Yes   |
| B+    | 50    | 54    | 7.0    | Yes   |
| B     | 45    | 49    | 6.0    | Yes   |
| C     | 40    | 44    | 5.0    | Yes   |
| F     | 0     | 39    | 0.0    | No    |

---

## Excel Upload Format

Columns (row 1 = optional header):

| Column | Name    | Required | Notes                        |
|--------|---------|----------|------------------------------|
| A      | Name    | ✓        | Student full name            |
| B      | RollID  | ✓        | e.g., SE001                  |
| C      | Email   |          | Used for dedup/login         |
| D      | Gender  | ✓        | Male / Female / Other        |
| E      | DOB     |          | YYYY-MM-DD or DD-MM-YYYY     |

Download sample: `/students/download-sample/`

---

## Key URL Reference

| URL                              | Description                   |
|----------------------------------|-------------------------------|
| `/`                              | Public home                   |
| `/login/`                        | Login (teacher + student)     |
| `/dashboard/`                    | Teacher dashboard             |
| `/engine/enrollments/`           | Manage enrollments            |
| `/engine/subjects/`              | Manage semester subjects      |
| `/results/engine/bulk/`          | Bulk mark entry               |
| `/results/engine/class/`         | Class result overview         |
| `/analytics/teacher/`            | Teacher analytics + charts    |
| `/student/dashboard/`            | Student portal                |
| `/student/results/explore/`      | Student result explorer       |
| `/admin/`                        | Django admin                  |

---

## Bugs Fixed in This Release

1. **Migration crash** — `student__roll_id` ordering removed before field was dropped.  
   Fix: `AlterModelOptions` now runs **before** `RemoveField` for both `EnhancedResult` and `SemesterSummary`.

2. **SQLite index crash** — indexes referencing `student` FK were not removed before `RemoveField`.  
   Fix: `RemoveIndex(core_enh_stu_ss_idx)` and `RemoveIndex(core_sem_sum_idx)` added **before** respective `RemoveField` operations.

3. **Result ordering** — `Result.Meta.ordering` in migration state referenced `student__roll_id` after it was removed from `Student`.  
   Fix: `AlterModelOptions` on `result` added at end of migration 0004.

4. **StudentForm field** — form used `dob` but model field is `date_of_birth`.  
   Status: Already correct — `forms.py` uses `date_of_birth` correctly.

5. **Views using Result.objects** — student portal `dashboard`, `results`, `performance`, `export_csv` all used legacy `Result`.  
   Fix: Rewritten to use `EnhancedResult` via `Enrollment`.

6. **CSV export** — `student.roll_id` and `student.student_class` accessed directly.  
   Fix: Now uses `enrollment.roll_id` and `enrollment.student_class`.

7. **Dashboard template** — `recent_students` iterated `Student` objects using `.roll_id` shim.  
   Fix: View now passes `Enrollment` objects; template uses `enr.roll_id` and `enr.student_class`.

8. **Marksheet template** — used `student.roll_id` and `student.student_class` shims.  
   Fix: Now uses `enrollment.roll_id` and `enrollment.student_class` from context.

9. **Authentication** — `services.authenticate_student()` handles DOB (DDMMYYYY) primary + roll_id fallback. Unchanged and correct.

10. **Excel import** — creates `Student` + `Enrollment` separately. Duplicate prevention via `get_or_create`. Unchanged and correct.

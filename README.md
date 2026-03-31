<<<<<<< HEAD
# SRAS — Student Result Analysis System

A modern, production-ready Django web platform for teachers to manage students,
subjects, classes, results, and notices.

---

## 📋 Features

- **Class Management** — Create/edit/delete classes (FE/SE/TE/BE, sections, academic year)
- **Subject Management** — Full CRUD for subjects with optional codes
- **Subject Combinations** — Assign subjects to specific classes
- **Student Management** — Add, edit, delete students with class assignment
- **Excel Bulk Upload** — Import hundreds of students from `.xlsx` files via openpyxl
- **Result Entry** — Enter IA-1, IA-2, Semester marks per student per subject
- **Result Filtering** — Filter by class, subject, student name, roll ID; sort by marks; filter by fail status
- **Notice Board** — Post/manage announcements; public notice board page
- **Modern Dashboard** — Stats, quick actions, recent activity
- **Responsive Sidebar UI** — Collapsible sidebar, Inter-style typography, blue accent theme

---

## 🚀 Quick Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run migrations

```bash
python manage.py migrate
```

### 3. Create a superuser (admin/teacher account)

```bash
python manage.py createsuperuser
```

### 4. Run the development server

```bash
python manage.py runserver
```

### 5. Visit the site

- **Public Homepage**: http://127.0.0.1:8000/
- **Teacher Login**: http://127.0.0.1:8000/login/
- **Dashboard**: http://127.0.0.1:8000/dashboard/
- **Django Admin**: http://127.0.0.1:8000/admin/

---

## 📁 Project Structure

```
sras/
├── manage.py
├── requirements.txt
├── db.sqlite3              (auto-created after migrate)
├── sras/
│   ├── settings.py         # Django config (SQLite dev / PostgreSQL prod)
│   ├── urls.py             # Root URL config
│   └── wsgi.py
├── core/
│   ├── models.py           # All database models
│   ├── views.py            # All views (class, subject, student, result, notice)
│   ├── urls.py             # App URL patterns
│   ├── forms.py            # All Django forms
│   ├── admin.py            # Django admin registration
│   ├── excel_utils.py      # openpyxl Excel import/export logic
│   ├── migrations/
│   │   └── 0001_initial.py
│   └── templates/core/
│       ├── base.html           # Sidebar layout base template
│       ├── home.html           # Public landing page
│       ├── login.html          # Teacher login
│       ├── dashboard.html      # Admin dashboard
│       ├── class_list.html     # Manage classes
│       ├── class_form.html     # Create/edit class
│       ├── subject_list.html   # Manage subjects
│       ├── subject_form.html   # Create/edit subject
│       ├── combination_list.html
│       ├── combination_form.html
│       ├── student_list.html   # Manage students
│       ├── student_form.html   # Add/edit student
│       ├── student_detail.html # Student profile + results
│       ├── student_upload.html # Excel upload form
│       ├── result_add.html     # Step 1: select class/subject
│       ├── result_enter.html   # Step 2: enter marks
│       ├── result_list.html    # Filter/view all results
│       ├── notice_list.html    # Manage notices
│       ├── notice_form.html    # Add/edit notice
│       ├── public_notices.html # Public notice board
│       └── confirm_delete.html # Generic delete confirmation
└── static/
    ├── css/
    │   ├── main.css    # Full design system (dashboard + app)
    │   └── public.css  # Public homepage styles
    └── js/
        └── main.js     # Sidebar toggle, mark validation, UX
```

---

## 📊 Database Models

| Model | Key Fields |
|-------|------------|
| `StudentClass` | class_year, section, academic_year |
| `Subject` | name, code, description |
| `SubjectCombination` | student_class (FK), subject (FK) |
| `Student` | name, roll_id, email, gender, dob, student_class (FK) |
| `Result` | student (FK), subject (FK), ia1_marks, ia2_marks, sem_marks |
| `Notice` | title, content, is_active |

---

## 📤 Excel Upload Format

Download the sample from `/students/download-sample/`

| Column | Example |
|--------|---------|
| Name | Rahul Patil |
| RollID | SE001 |
| Email | rahul@gmail.com |
| Gender | Male / Female / Other |
| DOB | 2004-05-21 |

---

## 🎯 Result Grading

| Grade | Range |
|-------|-------|
| O (Outstanding) | ≥ 75% |
| A+ (Excellent) | ≥ 65% |
| A (Very Good) | ≥ 55% |
| B+ (Good) | ≥ 45% |
| B (Average) | ≥ 40% |
| F (Fail) | < 40% |

**Fail conditions**: IA-1 < 8, IA-2 < 8, SEM < 24

---

## 🗄️ PostgreSQL (Production)

Update `DATABASES` in `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'sras_db',
        'USER': 'sras_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Install: `pip install psycopg2-binary`

---

## 🔮 Future Features (Architecture Ready)

- [ ] Automatic result calculation & GPA
- [ ] Student ranking per class
- [ ] Export results to PDF
- [ ] Student login portal
- [ ] Graph-based analytics (Chart.js)
- [ ] Email notifications for notices
- [ ] Multi-teacher role support
- [ ] Mobile app API (Django REST Framework)
=======
# sras-project
>>>>>>> f7cc81420797db66c7eafe01b1820a37e2a3ae27

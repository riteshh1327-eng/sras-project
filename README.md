# 🎓 SRAS — Student Result Analysis System

A modern, production-ready Django web platform for teachers to manage students, subjects, classes, results, and notices.

---

## 📋 Features

- **Class Management** — Create/edit/delete classes (FE/SE/TE/BE, sections, academic year)
- **Subject Management** — Full CRUD for subjects with optional codes
- **Subject Combinations** — Assign subjects to specific classes
- **Student Management** — Add, edit, delete students with class assignment
- **Excel Bulk Upload** — Import hundreds of students from `.xlsx` files via openpyxl
- **Result Entry** — Enter IA-1, IA-2, Semester marks per student per subject
- **Result Filtering** — Filter by class, subject, student name, roll ID
- **Notice Board** — Post/manage announcements with public notice board
- **Modern Dashboard** — Stats, quick actions, recent activity
- **Responsive Sidebar UI** — Clean academic dashboard UI

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

### 3. Create superuser

```bash
python manage.py createsuperuser
```

### 4. Run server

```bash
python manage.py runserver
```

### 5. Visit

- Homepage → http://127.0.0.1:8000/
- Login → http://127.0.0.1:8000/login/
- Dashboard → http://127.0.0.1:8000/dashboard/
- Admin → http://127.0.0.1:8000/admin/

---

## 📁 Project Structure

```
sras/
├── manage.py
├── requirements.txt
├── sras/
├── core/
└── static/
```

---

## 📊 Database Models

| Model | Description |
|-------|-------------|
| StudentClass | Class & academic year |
| Subject | Subject information |
| SubjectCombination | Class subject mapping |
| Student | Student details |
| Result | Marks & grades |
| Notice | Announcements |

---

## 📤 Excel Upload Format

| Column | Example |
|--------|---------|
| Name | Rahul Patil |
| RollID | SE001 |
| Email | rahul@gmail.com |
| Gender | Male |
| DOB | 2004-05-21 |

---

## 🎯 Result Grading

| Grade | Range |
|-------|-------|
| O | ≥ 75% |
| A+ | ≥ 65% |
| A | ≥ 55% |
| B+ | ≥ 45% |
| B | ≥ 40% |
| F | < 40% |

Fail Conditions:
- IA-1 < 8
- IA-2 < 8
- SEM < 24

---

## 🔮 Future Features

- Automatic GPA Calculation  
- Student Ranking  
- PDF Export  
- Student Login Portal  
- Analytics Dashboard  
- Email Notifications  
- Multi-Teacher Support  
- REST API Support  

---

## 👨‍💻 Built With

- Django  
- SQLite (Development)  
- PostgreSQL (Production)  
- HTML / CSS / JavaScript  

---

## 📌 Author

**Ritesh Mohanty**  
Student Result Analysis System (SRAS)
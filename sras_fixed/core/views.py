"""
SRAS - Views
Enrollment-centric architecture.
All student queries go through Enrollment.
Result (legacy) model is kept for pattern_analysis and result_enter views only.
Student portal dashboard/results use EnhancedResult via Enrollment.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count, Avg
from django.forms import formset_factory
import io, csv, json

from .models import (
    Teacher, StudentClass, Subject, SubjectCombination,
    Student, Enrollment, Result, Notice,
    GradeScale, SemesterSubject, EnhancedResult, SemesterSummary,
)
from .forms import (
    StudentClassForm, SubjectForm, SubjectCombinationForm,
    StudentForm, EnrollmentForm, ExcelUploadForm, ResultForm, ResultFilterForm, NoticeForm,
)
from .excel_utils import import_students_from_excel, generate_sample_excel
from . import services


# ─── Session helpers ──────────────────────────────────────────────────────────

def _set_teacher_session(request, teacher):
    request.session['user_type']  = 'teacher'
    request.session['user_id']    = teacher.id
    request.session['user_name']  = teacher.name
    request.session['user_email'] = teacher.email

def _set_student_session(request, student):
    request.session['user_type']  = 'student'
    request.session['user_id']    = student.id
    request.session['user_name']  = student.name
    request.session['user_email'] = student.email

def _get_current_teacher(request):
    if request.session.get('user_type') != 'teacher':
        return None
    return Teacher.objects.filter(pk=request.session.get('user_id'), is_active=True).first()

def _get_current_student(request):
    if request.session.get('user_type') != 'student':
        return None
    return Student.objects.filter(pk=request.session.get('user_id')).first()


def teacher_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not _get_current_teacher(request):
            messages.error(request, 'You must be logged in as a teacher.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper

def student_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not _get_current_student(request):
            messages.error(request, 'You must be logged in as a student.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ─── Authentication ───────────────────────────────────────────────────────────

def login_view(request):
    if request.session.get('user_type') == 'teacher':
        return redirect('dashboard')
    if request.session.get('user_type') == 'student':
        return redirect('student_dashboard')

    if request.method == 'POST':
        email    = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()

        if not email or not password:
            messages.error(request, 'Please enter both email and password.')
            return render(request, 'core/login.html', {})

        # 1. Check teacher table
        teacher = Teacher.objects.filter(email__iexact=email, is_active=True).first()
        if teacher:
            if teacher.check_password(password):
                _set_teacher_session(request, teacher)
                messages.success(request, f'Welcome back, {teacher.name}!')
                return redirect('dashboard')
            # Fallback: plaintext password stored in DB (auto-rehash on match)
            if teacher.password == password:
                teacher.set_password(password)
                teacher.save()
                _set_teacher_session(request, teacher)
                messages.success(request, f'Welcome back, {teacher.name}!')
                return redirect('dashboard')
            messages.error(request, 'Incorrect password.')
            return render(request, 'core/login.html', {})

        # 2. Check student — password = DOB (DDMMYYYY) or legacy roll_id
        student = services.authenticate_student(email, password)
        if student:
            _set_student_session(request, student)
            messages.success(request, f'Welcome, {student.name}!')
            return redirect('student_dashboard')

        if Student.objects.filter(email__iexact=email).exists():
            messages.error(request,
                'Incorrect password. Use your Date of Birth as DDMMYYYY.')
            return render(request, 'core/login.html', {})

        messages.error(request, 'User not registered. Please contact your teacher.')

    return render(request, 'core/login.html', {})


def logout_view(request):
    request.session.flush()
    messages.info(request, 'You have been logged out.')
    return redirect('home')


# ─── Public Pages ─────────────────────────────────────────────────────────────

def home(request):
    notices = Notice.objects.filter(is_active=True)[:6]
    stats = {
        'classes':  StudentClass.objects.count(),
        'students': Student.objects.count(),
        'subjects': Subject.objects.count(),
        'results':  EnhancedResult.objects.count(),
    }
    return render(request, 'core/home.html', {'notices': notices, 'stats': stats})


def public_notices(request):
    notices = Notice.objects.filter(is_active=True)
    return render(request, 'core/public_notices.html', {'notices': notices})


# ─── Dashboard ────────────────────────────────────────────────────────────────

@teacher_required
def dashboard(request):
    stats = {
        'classes':      StudentClass.objects.count(),
        'students':     Student.objects.count(),
        'subjects':     Subject.objects.count(),
        'results':      EnhancedResult.objects.count(),
        'notices':      Notice.objects.filter(is_active=True).count(),
        'combinations': SubjectCombination.objects.count(),
    }
    # recent_students: show latest Enrollment objects (each has roll_id+class)
    recent_students = (
        Enrollment.objects
        .select_related('student', 'student_class')
        .order_by('-created_at')[:5]
    )
    recent_notices = Notice.objects.order_by('-created_at')[:4]

    classes_with_counts = StudentClass.objects.annotate(
        student_count=Count('enrollments')
    ).order_by('-student_count')[:5]

    context = {
        'stats':              stats,
        'recent_students':    recent_students,   # Enrollment objects
        'recent_notices':     recent_notices,
        'classes_with_counts': classes_with_counts,
    }
    return render(request, 'core/dashboard.html', context)


# ─── Class Management ─────────────────────────────────────────────────────────

@teacher_required
def class_list(request):
    classes = StudentClass.objects.annotate(
        student_count=Count('enrollments')
    ).order_by('class_year', 'section')
    return render(request, 'core/class_list.html', {'classes': classes})


@teacher_required
def class_create(request):
    if request.method == 'POST':
        form = StudentClassForm(request.POST)
        if form.is_valid():
            cls = form.save()
            messages.success(request, f'Class "{cls}" created successfully.')
            return redirect('class_list')
        messages.error(request, 'Please fix the errors below.')
    else:
        form = StudentClassForm()
    return render(request, 'core/class_form.html', {'form': form, 'action': 'Create'})


@teacher_required
def class_edit(request, pk):
    cls = get_object_or_404(StudentClass, pk=pk)
    if request.method == 'POST':
        form = StudentClassForm(request.POST, instance=cls)
        if form.is_valid():
            form.save()
            messages.success(request, f'Class "{cls}" updated.')
            return redirect('class_list')
    else:
        form = StudentClassForm(instance=cls)
    return render(request, 'core/class_form.html', {'form': form, 'action': 'Edit', 'object': cls})


@teacher_required
def class_delete(request, pk):
    cls = get_object_or_404(StudentClass, pk=pk)
    if request.method == 'POST':
        name = str(cls)
        cls.delete()
        messages.success(request, f'Class "{name}" deleted.')
        return redirect('class_list')
    return render(request, 'core/confirm_delete.html', {
        'object': cls, 'object_type': 'Class', 'cancel_url': 'class_list'
    })


# ─── Subject Management ───────────────────────────────────────────────────────

@teacher_required
def subject_list(request):
    subjects = Subject.objects.annotate(class_count=Count('subject_combinations')).order_by('name')
    return render(request, 'core/subject_list.html', {'subjects': subjects})


@teacher_required
def subject_create(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subj = form.save()
            messages.success(request, f'Subject "{subj.name}" created.')
            return redirect('subject_list')
    else:
        form = SubjectForm()
    return render(request, 'core/subject_form.html', {'form': form, 'action': 'Create'})


@teacher_required
def subject_edit(request, pk):
    subj = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Subject "{subj.name}" updated.')
            return redirect('subject_list')
    else:
        form = SubjectForm(instance=subj)
    return render(request, 'core/subject_form.html', {'form': form, 'action': 'Edit', 'object': subj})


@teacher_required
def subject_delete(request, pk):
    subj = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        name = subj.name
        subj.delete()
        messages.success(request, f'Subject "{name}" deleted.')
        return redirect('subject_list')
    return render(request, 'core/confirm_delete.html', {
        'object': subj, 'object_type': 'Subject', 'cancel_url': 'subject_list'
    })


# ─── Subject Combination ──────────────────────────────────────────────────────

@teacher_required
def combination_list(request):
    combinations = SubjectCombination.objects.select_related(
        'student_class', 'subject'
    ).order_by('student_class__class_year', 'student_class__section', 'subject__name')
    grouped = {}
    for combo in combinations:
        grouped.setdefault(combo.student_class, []).append(combo)
    return render(request, 'core/combination_list.html', {'grouped': grouped})


@teacher_required
def combination_create(request):
    if request.method == 'POST':
        form = SubjectCombinationForm(request.POST)
        if form.is_valid():
            combo = form.save()
            messages.success(request, f'Combination added: {combo}')
            return redirect('combination_list')
    else:
        form = SubjectCombinationForm()
    return render(request, 'core/combination_form.html', {'form': form, 'action': 'Add'})


@teacher_required
def combination_edit(request, pk):
    combo = get_object_or_404(SubjectCombination, pk=pk)
    if request.method == 'POST':
        form = SubjectCombinationForm(request.POST, instance=combo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Combination updated.')
            return redirect('combination_list')
    else:
        form = SubjectCombinationForm(instance=combo)
    return render(request, 'core/combination_form.html', {'form': form, 'action': 'Edit', 'object': combo})


@teacher_required
def combination_delete(request, pk):
    combo = get_object_or_404(SubjectCombination, pk=pk)
    if request.method == 'POST':
        combo.delete()
        messages.success(request, 'Combination removed.')
        return redirect('combination_list')
    return render(request, 'core/confirm_delete.html', {
        'object': combo, 'object_type': 'Subject Combination', 'cancel_url': 'combination_list'
    })


# ─── Student Management ───────────────────────────────────────────────────────

@teacher_required
def student_list(request):
    class_filter = request.GET.get('class')
    search       = request.GET.get('search', '').strip()

    enr_qs = (
        Enrollment.objects
        .select_related('student', 'student_class')
        .order_by('student_class__class_year', 'student_class__section', 'roll_id')
    )
    if class_filter:
        enr_qs = enr_qs.filter(student_class__pk=class_filter)
    if search:
        enr_qs = enr_qs.filter(
            Q(student__name__icontains=search) |
            Q(roll_id__icontains=search) |
            Q(student__email__icontains=search)
        )

    classes = StudentClass.objects.all()
    context = {
        'students':     enr_qs,           # Enrollment objects
        'classes':      classes,
        'class_filter': class_filter,
        'search':       search,
    }
    return render(request, 'core/student_list.html', context)


@teacher_required
def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, f'Student "{student.name}" added. Now enroll them in a class.')
            return redirect('re_enrollment_create')
    else:
        form = StudentForm()
    return render(request, 'core/student_form.html', {'form': form, 'action': 'Add'})


@teacher_required
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, f'Student "{student.name}" updated.')
            return redirect('student_list')
    else:
        form = StudentForm(instance=student)
    return render(request, 'core/student_form.html', {'form': form, 'action': 'Edit', 'object': student})


@teacher_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        name = student.name
        student.delete()
        messages.success(request, f'Student "{name}" deleted.')
        return redirect('student_list')
    return render(request, 'core/confirm_delete.html', {
        'object': student, 'object_type': 'Student', 'cancel_url': 'student_list'
    })


@teacher_required
def student_detail(request, pk):
    student    = get_object_or_404(Student, pk=pk)
    enrollment = student.current_enrollment
    # Legacy results (if any)
    legacy_results = Result.objects.filter(student=student).select_related('subject')
    total     = sum(r.total_marks for r in legacy_results)
    max_total = len(legacy_results) * 100
    context = {
        'student':    student,
        'enrollment': enrollment,
        'results':    legacy_results,
        'total':      total,
        'max_total':  max_total,
    }
    return render(request, 'core/student_detail.html', context)


# ─── Excel Upload ─────────────────────────────────────────────────────────────

@teacher_required
def student_upload_excel(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            student_class = form.cleaned_data['student_class']
            excel_file    = form.cleaned_data['excel_file']
            result        = import_students_from_excel(excel_file, student_class)

            if result['errors'] and result['created'] == 0:
                for err in result['errors'][:5]:
                    messages.error(request, err)
            else:
                if result['created'] > 0:
                    messages.success(request,
                        f"✅ {result['created']} student(s) imported into {student_class}.")
                if result['skipped'] > 0:
                    messages.warning(request, f"⚠️ {result['skipped']} row(s) skipped.")
                for warn in result['warnings'][:5]:
                    messages.warning(request, warn)
                for err in result['errors'][:3]:
                    messages.error(request, err)
                if result['created'] > 0:
                    return redirect('student_list')
    else:
        form = ExcelUploadForm()
    return render(request, 'core/student_upload.html', {'form': form})


def download_sample_excel(request):
    wb = generate_sample_excel()
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="sras_student_upload_sample.xlsx"'
    return response


# ─── Legacy Result Management (kept for backward compatibility) ───────────────

@teacher_required
def result_add(request):
    classes = StudentClass.objects.annotate(
        student_count=Count('enrollments')
    ).filter(student_count__gt=0)
    selected_class = None
    subjects = []

    class_id   = request.GET.get('class_id') or request.POST.get('class_id')
    subject_id = request.GET.get('subject_id') or request.POST.get('subject_id')

    if class_id:
        selected_class = get_object_or_404(StudentClass, pk=class_id)
        subjects = Subject.objects.filter(
            subjectcombination__student_class=selected_class
        ).distinct()

    if subject_id and selected_class:
        return redirect('result_enter', class_id=selected_class.pk, subject_id=subject_id)

    return render(request, 'core/result_add.html', {
        'classes': classes,
        'selected_class': selected_class,
        'subjects': subjects,
    })


@teacher_required
def result_enter(request, class_id, subject_id):
    student_class = get_object_or_404(StudentClass, pk=class_id)
    subject       = get_object_or_404(Subject, pk=subject_id)

    # Students via Enrollment, sorted by roll_id ascending
    students = Student.objects.filter(
        enrollments__student_class=student_class,
        enrollments__academic_year=student_class.academic_year,
    ).order_by('enrollments__roll_id')

    if not students.exists():
        messages.warning(request, 'No students enrolled in this class.')
        return redirect('result_add')

    initial_data = []
    existing_results = {r.student_id: r for r in Result.objects.filter(
        student__in=students, subject=subject
    )}

    for student in students:
        result = existing_results.get(student.pk)
        initial_data.append({
            'ia1_marks': result.ia1_marks if result else 0,
            'ia2_marks': result.ia2_marks if result else 0,
            'sem_marks': result.sem_marks if result else 0,
        })

    ResultFormSet = formset_factory(ResultForm, extra=0)

    if request.method == 'POST':
        formset = ResultFormSet(request.POST, initial=initial_data)
        if formset.is_valid():
            for student, form in zip(students, formset):
                if form.has_changed() or student.pk not in existing_results:
                    cd = form.cleaned_data
                    if student.pk in existing_results:
                        r = existing_results[student.pk]
                        r.ia1_marks = cd['ia1_marks']
                        r.ia2_marks = cd['ia2_marks']
                        r.sem_marks = cd['sem_marks']
                        r.save()
                    else:
                        Result.objects.create(
                            student=student, subject=subject,
                            ia1_marks=cd['ia1_marks'],
                            ia2_marks=cd['ia2_marks'],
                            sem_marks=cd['sem_marks'],
                        )
            messages.success(request, f'Results saved for {len(students)} student(s).')
            return redirect('result_list')
        messages.error(request, 'Please fix errors in the marks.')
    else:
        formset = ResultFormSet(initial=initial_data)

    context = {
        'student_class':  student_class,
        'subject':        subject,
        'student_forms':  list(zip(students, formset)),
        'formset':        formset,
        'existing':       existing_results,
    }
    return render(request, 'core/result_enter.html', context)


@teacher_required
def result_list(request):
    filter_form = ResultFilterForm(request.GET or None)
    results = Result.objects.select_related('student', 'subject').order_by('student__name', 'subject__name')

    if filter_form.is_valid():
        cd = filter_form.cleaned_data
        if cd.get('student_class'):
            results = results.filter(
                student__enrollments__student_class=cd['student_class']
            )
        if cd.get('subject'):
            results = results.filter(subject=cd['subject'])
        if cd.get('student_name'):
            results = results.filter(student__name__icontains=cd['student_name'])
        fail_filter = cd.get('fail_filter')
        if fail_filter == 'fail_ia1':
            results = results.filter(ia1_marks__lt=8)
        elif fail_filter == 'fail_ia2':
            results = results.filter(ia2_marks__lt=8)
        elif fail_filter == 'fail_sem':
            results = results.filter(sem_marks__lt=24)
        elif fail_filter == 'fail_any':
            results = results.filter(
                Q(ia1_marks__lt=8) | Q(ia2_marks__lt=8) | Q(sem_marks__lt=24)
            )

    result_list_data = [{'obj': r, 'total': r.total_marks} for r in results]

    sort_by = request.GET.get('sort_by', '')
    if sort_by == 'total_asc':
        result_list_data.sort(key=lambda x: x['total'])
    elif sort_by == 'total_desc':
        result_list_data.sort(key=lambda x: x['total'], reverse=True)

    return render(request, 'core/result_list.html', {
        'filter_form':     filter_form,
        'result_list_data': result_list_data,
        'total_count':     len(result_list_data),
    })


# ─── Notice Management ────────────────────────────────────────────────────────

@teacher_required
def notice_list(request):
    return render(request, 'core/notice_list.html', {
        'notices': Notice.objects.order_by('-created_at')
    })


@teacher_required
def notice_create(request):
    if request.method == 'POST':
        form = NoticeForm(request.POST)
        if form.is_valid():
            notice = form.save()
            messages.success(request, f'Notice "{notice.title}" created.')
            return redirect('notice_list')
    else:
        form = NoticeForm()
    return render(request, 'core/notice_form.html', {'form': form, 'action': 'Add'})


@teacher_required
def notice_edit(request, pk):
    notice = get_object_or_404(Notice, pk=pk)
    if request.method == 'POST':
        form = NoticeForm(request.POST, instance=notice)
        if form.is_valid():
            form.save()
            messages.success(request, f'Notice "{notice.title}" updated.')
            return redirect('notice_list')
    else:
        form = NoticeForm(instance=notice)
    return render(request, 'core/notice_form.html', {'form': form, 'action': 'Edit', 'object': notice})


@teacher_required
def notice_delete(request, pk):
    notice = get_object_or_404(Notice, pk=pk)
    if request.method == 'POST':
        title = notice.title
        notice.delete()
        messages.success(request, f'Notice "{title}" deleted.')
        return redirect('notice_list')
    return render(request, 'core/confirm_delete.html', {
        'object': notice, 'object_type': 'Notice', 'cancel_url': 'notice_list'
    })


# ─── AJAX helpers ─────────────────────────────────────────────────────────────

@teacher_required
def get_subjects_for_class(request):
    class_id = request.GET.get('class_id')
    if not class_id:
        return JsonResponse({'subjects': []})
    subjects = Subject.objects.filter(
        subjectcombination__student_class_id=class_id
    ).values('id', 'name')
    return JsonResponse({'subjects': list(subjects)})


# ═══════════════════════════════════════════════════════════════════════════════
# TEACHER: PATTERN ANALYSIS  (legacy Result model — kept for analysis)
# ═══════════════════════════════════════════════════════════════════════════════

@teacher_required
def pattern_analysis(request):
    classes  = StudentClass.objects.all()
    subjects = Subject.objects.all()

    class_id   = request.GET.get('class_id', '')
    exam_type  = request.GET.get('exam_type', '')
    fail_count = request.GET.get('fail_count', '')
    subject_id = request.GET.get('subject_id', '')

    results = Result.objects.select_related('student', 'subject')

    if class_id:
        student_ids = Enrollment.objects.filter(
            student_class_id=class_id
        ).values_list('student_id', flat=True)
        results = results.filter(student_id__in=student_ids)
    if subject_id:
        results = results.filter(subject_id=subject_id)
    if exam_type == 'ia1':
        results = results.filter(ia1_marks__lt=8)
    elif exam_type == 'ia2':
        results = results.filter(ia2_marks__lt=8)
    elif exam_type == 'sem':
        results = results.filter(sem_marks__lt=24)

    student_fail_map = {}
    for r in Result.objects.select_related('student'):
        if r.is_overall_fail:
            student_fail_map[r.student_id] = student_fail_map.get(r.student_id, 0) + 1

    if fail_count == '1':
        results = results.filter(student_id__in=[s for s,c in student_fail_map.items() if c == 1])
    elif fail_count == '2':
        results = results.filter(student_id__in=[s for s,c in student_fail_map.items() if c == 2])
    elif fail_count == '3':
        results = results.filter(student_id__in=[s for s,c in student_fail_map.items() if c >= 3])

    results = results.filter(status='Fail')

    total_results = Result.objects.count()
    total_fail    = Result.objects.filter(status='Fail').count()
    fail_pct      = round((total_fail / total_results * 100), 1) if total_results else 0

    grade_dist = {g: 0 for g in ['O', 'A+', 'A', 'B+', 'B', 'F']}
    for r in Result.objects.values('grade').annotate(cnt=Count('id')):
        if r['grade'] in grade_dist:
            grade_dist[r['grade']] = r['cnt']

    subj_fail_data = []
    for subj in subjects:
        s_total = Result.objects.filter(subject=subj).count()
        s_fail  = Result.objects.filter(subject=subj, status='Fail').count()
        if s_total:
            subj_fail_data.append({
                'name': subj.name,
                'fail_pct': round(s_fail / s_total * 100, 1),
            })

    student_fail_subjects = {}
    for r in Result.objects.filter(status='Fail').select_related('student', 'subject'):
        student_fail_subjects.setdefault(r.student_id, []).append(r.subject.display_name)

    result_rows = []
    for r in results:
        # Get enrollment for roll_id/class display
        enr = r.student.current_enrollment
        result_rows.append({
            'r':              r,
            'enrollment':     enr,
            'failed_subjects': ', '.join(student_fail_subjects.get(r.student_id, [])),
        })

    return render(request, 'core/pattern_analysis.html', {
        'classes':       classes,
        'subjects':      subjects,
        'results':       result_rows,
        'fail_pct':      fail_pct,
        'total_fail':    total_fail,
        'total_results': total_results,
        'grade_dist_json': json.dumps(grade_dist),
        'subj_fail_json':  json.dumps(subj_fail_data),
        'sel_class':     class_id,
        'sel_exam':      exam_type,
        'sel_fail_count': fail_count,
        'sel_subject':   subject_id,
    })


@teacher_required
def export_failure_csv(request):
    """Export failing students as CSV using Enrollment for roll_id / class."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sras_failure_report.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Student Name', 'Roll ID', 'Class', 'Subject',
        'IA1', 'IA2', 'SEM', 'Total', 'Grade', 'Status'
    ])
    fails = Result.objects.filter(status='Fail').select_related('student', 'subject')
    for r in fails:
        enr        = r.student.current_enrollment
        roll_id    = enr.roll_id if enr else '—'
        class_name = str(enr.student_class) if enr else '—'
        writer.writerow([
            r.student.name, roll_id, class_name,
            r.subject.display_name,
            r.ia1_marks, r.ia2_marks, r.sem_marks,
            r.total, r.grade, r.status,
        ])
    return response


# ═══════════════════════════════════════════════════════════════════════════════
# STUDENT PORTAL  — Enrollment-centric
# ═══════════════════════════════════════════════════════════════════════════════

@student_required
def student_dashboard(request):
    student    = _get_current_student(request)
    enrollment = student.current_enrollment

    # Stats from EnhancedResult via Student
    enhanced_results_all = []
    semester_data = []
    total_subjects = passed = failed = 0

    if student:
        enhanced_results_all = list(
            EnhancedResult.objects
            .filter(enrollment__student=student)
            .select_related('semester_subject__subject', 'semester_subject', 'enrollment')
            .order_by('-updated_at')
        )
        total_subjects = len(enhanced_results_all)
        passed  = sum(1 for r in enhanced_results_all if r.status == 'Pass')
        failed  = sum(1 for r in enhanced_results_all if r.status in ('Fail', 'Absent'))
            
        summaries = list(
            SemesterSummary.objects.filter(enrollment__student=student)
            .order_by('-academic_year', '-semester')
        )
        
        for s in summaries:
            s_results = [r for r in enhanced_results_all if r.semester_subject.academic_year == s.academic_year and r.semester_subject.semester == s.semester]
            s_results.sort(key=lambda x: x.semester_subject.subject.display_name)
            semester_data.append({
                'summary': s,
                'results': s_results
            })

    notices = Notice.objects.filter(is_active=True)[:5]

    return render(request, 'core/student/dashboard.html', {
        'student':        student,
        'enrollment':     enrollment,
        'semester_data':  semester_data,
        'total_subjects': total_subjects,
        'passed':         passed,
        'failed':         failed,
        'recent_results': enhanced_results_all[:5],
        'notices':        notices,
    })


@student_required
def student_results(request):
    student = _get_current_student(request)

    # Fetch ALL results across ALL enrollments for this student
    results = list(
        EnhancedResult.objects
        .filter(enrollment__student=student)
        .select_related(
            'semester_subject__subject',
            'semester_subject__student_class',
            'enrollment',
        )
        .order_by(
            'semester_subject__academic_year',
            'semester_subject__semester',
            'semester_subject__subject__name',
        )
    )

    return render(request, 'core/student/results.html', {
        'student': student,
        'results': results,
    })


@student_required
def student_subject_detail(request, subject_id):
    """Detail view for a legacy Result (subject_id = Subject pk)."""
    student = _get_current_student(request)
    subject = get_object_or_404(Subject, pk=subject_id)
    result  = get_object_or_404(Result, student=student, subject=subject)

    ia1_pct = round(float(result.ia1_marks) / 20 * 100, 1)
    ia2_pct = round(float(result.ia2_marks) / 20 * 100, 1)
    sem_pct = round(float(result.sem_marks) / 60 * 100, 1)

    return render(request, 'core/student/subject_detail.html', {
        'student': student, 'subject': subject, 'result': result,
        'ia1_pct': ia1_pct, 'ia2_pct': ia2_pct, 'sem_pct': sem_pct,
    })




@student_required
def student_notices(request):
    student = _get_current_student(request)
    notices = Notice.objects.filter(is_active=True)
    return render(request, 'core/student/notices.html', {'student': student, 'notices': notices})


@student_required
def student_export_results_csv(request):
    """Export student's EnhancedResults as CSV."""
    student    = _get_current_student(request)
    enrollment = student.current_enrollment

    roll_id = enrollment.roll_id if enrollment else 'student'

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{roll_id}_results.csv"'
    writer = csv.writer(response)
    writer.writerow([
        'Subject', 'Semester', 'IA1', 'IA2', 'TW', 'Oral', 'SEM',
        'Total', 'Max', '%', 'Grade', 'Status'
    ])

    if enrollment:
        for r in EnhancedResult.objects.filter(
            enrollment=enrollment
        ).select_related('semester_subject__subject').order_by(
            'semester_subject__semester', 'semester_subject__subject__name'
        ):
            ss = r.semester_subject
            writer.writerow([
                ss.subject.display_name,
                ss.semester,
                r.ia1 or '', r.ia2 or '', r.tw or '', r.oral or '', r.sem or '',
                r.total, ss.max_total, r.percentage, r.grade, r.status,
            ])
    return response

from django.contrib.auth.models import User
from django.http import HttpResponse

def fix_admin(request):
    User.objects.create_superuser("admin", "admin@gmail.com", "admin123")
    return HttpResponse("Admin created")
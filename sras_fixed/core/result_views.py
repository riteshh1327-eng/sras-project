"""
SRAS — Result Engine Views (Enrollment-centric edition)
=======================================================
All queries go through Enrollment.
All business logic delegated to services.py.
Views only orchestrate queries and render templates.

Query pattern enforced throughout:
  Enrollment → SemesterSubject → EnhancedResult → SemesterSummary
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
import json

from .result_models import SemesterSubject, EnhancedResult, SemesterSummary
from .models import Student, StudentClass, Enrollment, Subject
from . import services


# ── Session helpers & decorators ──────────────────────────────────────────────

def _get_current_teacher(request):
    from .models import Teacher
    if request.session.get('user_type') != 'teacher':
        return None
    return Teacher.objects.filter(
        pk=request.session.get('user_id'), is_active=True
    ).first()


def _get_current_student(request):
    """Return the Student from session, or None."""
    if request.session.get('user_type') != 'student':
        return None
    return Student.objects.filter(pk=request.session.get('user_id')).first()


def _get_current_enrollment(request):
    """Return the Student's current Enrollment, or None."""
    student = _get_current_student(request)
    if not student:
        return None
    return student.current_enrollment


def teacher_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not _get_current_teacher(request):
            messages.error(request, 'Login as a teacher to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def student_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not _get_current_student(request):
            messages.error(request, 'Login as a student to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ═══════════════════════════════════════════════════════════════════════════════
# TEACHER — ENROLLMENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@teacher_required
def enrollment_list(request):
    """List enrollments for a class+year, sorted by roll_id ascending."""
    classes = StudentClass.objects.all().order_by('class_year', 'section', 'academic_year')

    sel_cls  = request.GET.get('class_id', '')
    sel_year = request.GET.get('year', '')

    enrollments  = Enrollment.objects.none()
    academic_years = []

    if sel_cls:
        academic_years = (
            Enrollment.objects
            .filter(student_class_id=sel_cls)
            .values_list('academic_year', flat=True)
            .distinct()
            .order_by('-academic_year')
        )

    if sel_cls and sel_year:
        enrollments = (
            Enrollment.objects
            .filter(student_class_id=sel_cls, academic_year=sel_year)
            .select_related('student', 'student_class')
            .order_by('roll_id')          # roll_id ascending — always
        )

    return render(request, 'core/result_engine/enrollment_list.html', {
        'classes':       classes,
        'enrollments':   enrollments,
        'academic_years':academic_years,
        'sel_cls':       sel_cls,
        'sel_year':      sel_year,
    })


@teacher_required
def enrollment_create(request):
    """Enroll a student in a class for an academic year."""
    classes  = StudentClass.objects.all()
    students = Student.objects.all().order_by('name')

    if request.method == 'POST':
        p = request.POST
        try:
            Enrollment.objects.create(
                student_id    = p['student'],
                student_class_id = p['student_class'],
                academic_year = p['academic_year'].strip(),
                roll_id       = p['roll_id'].strip(),
            )
            messages.success(request, 'Student enrolled successfully.')
            return redirect('re_enrollment_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'core/result_engine/enrollment_form.html', {
        'classes': classes, 'students': students, 'action': 'Enroll',
    })


@teacher_required
def enrollment_delete(request, pk):
    enr = get_object_or_404(Enrollment, pk=pk)
    if request.method == 'POST':
        name = enr.student.name
        enr.delete()
        messages.success(request, f'Enrollment for {name} removed.')
        return redirect('re_enrollment_list')
    return render(request, 'core/confirm_delete.html', {
        'object': enr, 'object_type': 'Enrollment',
        'cancel_url': 're_enrollment_list',
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TEACHER — SEMESTER SUBJECT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@teacher_required
def semester_subject_list(request):
    """List all semester subjects, grouped by class+semester+year."""
    items = SemesterSubject.objects.select_related(
        'student_class', 'subject'
    ).order_by('academic_year', 'semester', 'student_class', 'subject__name')

    grouped = {}
    for ss in items:
        key = f"{ss.academic_year} | Sem {ss.semester} | {ss.student_class}"
        grouped.setdefault(key, []).append(ss)

    return render(request, 'core/result_engine/semester_subject_list.html',
                  {'grouped': grouped})


@teacher_required
def semester_subject_create(request):
    """Create a SemesterSubject mapping."""
    classes  = StudentClass.objects.all()
    subjects = Subject.objects.all()

    if request.method == 'POST':
        p = request.POST
        try:
            ss = SemesterSubject.objects.create(
                student_class_id = p['student_class'],
                subject_id       = p['subject'],
                semester         = p['semester'],
                academic_year    = p.get('academic_year', '').strip(),
                credits          = int(p.get('credits', 4)),
                has_ia           = 'has_ia'   in p,
                has_tw           = 'has_tw'   in p,
                has_oral         = 'has_oral' in p,
                has_sem          = 'has_sem'  in p,
                max_ia1          = int(p.get('max_ia1', 20)),
                max_ia2          = int(p.get('max_ia2', 20)),
                max_tw           = int(p.get('max_tw', 25)),
                max_oral         = int(p.get('max_oral', 25)),
                max_sem          = int(p.get('max_sem', 60)),
                min_ia1          = int(p.get('min_ia1', 8)),
                min_ia2          = int(p.get('min_ia2', 8)),
                min_tw           = int(p.get('min_tw', 10)),
                min_oral         = int(p.get('min_oral', 10)),
                min_sem          = int(p.get('min_sem', 24)),
            )
            messages.success(request, f'Semester subject created: {ss}')
            return redirect('re_semester_subject_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'core/result_engine/semester_subject_form.html', {
        'classes': classes, 'subjects': subjects,
        'semester_choices': [(str(i), f'Semester {i}') for i in range(1, 9)],
        'action': 'Create',
    })


@teacher_required
def semester_subject_edit(request, pk):
    """Edit an existing SemesterSubject mapping."""
    ss = get_object_or_404(SemesterSubject, pk=pk)
    classes  = StudentClass.objects.all()
    subjects = Subject.objects.all()

    if request.method == 'POST':
        p = request.POST
        try:
            ss.student_class_id = p['student_class']
            ss.subject_id       = p['subject']
            ss.semester         = p['semester']
            ss.academic_year    = p.get('academic_year', '').strip()
            ss.credits          = int(p.get('credits', 4))
            ss.has_ia           = 'has_ia'   in p
            ss.has_tw           = 'has_tw'   in p
            ss.has_oral         = 'has_oral' in p
            ss.has_sem          = 'has_sem'  in p
            ss.max_ia1          = int(p.get('max_ia1', 20))
            ss.max_ia2          = int(p.get('max_ia2', 20))
            ss.max_tw           = int(p.get('max_tw', 25))
            ss.max_oral         = int(p.get('max_oral', 25))
            ss.max_sem          = int(p.get('max_sem', 60))
            ss.min_ia1          = int(p.get('min_ia1', 8))
            ss.min_ia2          = int(p.get('min_ia2', 8))
            ss.min_tw           = int(p.get('min_tw', 10))
            ss.min_oral         = int(p.get('min_oral', 10))
            ss.min_sem          = int(p.get('min_sem', 24))
            ss.save()
            messages.success(request, f'Semester subject updated: {ss}')
            return redirect('re_semester_subject_list')
        except Exception as e:
            messages.error(request, f'Error: {e}')

    return render(request, 'core/result_engine/semester_subject_form.html', {
        'ss': ss, 'classes': classes, 'subjects': subjects,
        'semester_choices': [(str(i), f'Semester {i}') for i in range(1, 9)],
        'action': 'Edit',
    })


@teacher_required
def semester_subject_delete(request, pk):
    ss = get_object_or_404(SemesterSubject, pk=pk)
    if request.method == 'POST':
        ss.delete()
        messages.success(request, 'Semester subject deleted.')
        return redirect('re_semester_subject_list')
    return render(request, 'core/confirm_delete.html', {
        'object': ss, 'object_type': 'Semester Subject',
        'cancel_url': 're_semester_subject_list',
    })


# ═══════════════════════════════════════════════════════════════════════════════
# TEACHER — BULK RESULT ENTRY  (Enrollment-centric)
# ═══════════════════════════════════════════════════════════════════════════════

@teacher_required
def bulk_result_entry(request):
    """
    Step 1+2: year → class → semester → subject → component selector.
    Step 3: marks entry table (one row per Enrollment, sorted by roll_id).
    """
    academic_years = (
        SemesterSubject.objects
        .values_list('academic_year', flat=True)
        .distinct()
        .order_by('-academic_year')
    )
    classes  = StudentClass.objects.all()
    sem_list = [(str(i), f'Semester {i}') for i in range(1, 9)]

    sel_year = request.GET.get('year', '')
    sel_cls  = request.GET.get('class_id', '')
    sel_sem  = request.GET.get('sem', '')
    sel_ss   = request.GET.get('ss_id', '')
    sel_comp = request.GET.get('component', '')   # ia1|ia2|tw|oral|sem

    semester_subjects = SemesterSubject.objects.none()
    if sel_year and sel_cls and sel_sem:
        semester_subjects = SemesterSubject.objects.filter(
            academic_year=sel_year,
            student_class_id=sel_cls,
            semester=sel_sem,
        ).select_related('subject')

    context = {
        'academic_years':   academic_years,
        'classes':          classes,
        'sem_list':         sem_list,
        'semester_subjects':semester_subjects,
        'sel_year': sel_year,
        'sel_cls':  sel_cls,
        'sel_sem':  sel_sem,
        'sel_ss':   sel_ss,
        'sel_comp': sel_comp,
    }

    # Step 3: show entry table
    if sel_ss and sel_comp:
        ss = get_object_or_404(SemesterSubject, pk=sel_ss)

        # All enrollments for this class+year — sorted roll_id ascending
        enrollments = (
            Enrollment.objects
            .filter(
                student_class=ss.student_class,
                academic_year=ss.academic_year,
            )
            .select_related('student')
            .order_by('roll_id')           # ← standardised ascending sort
        )

        # Load existing EnhancedResults keyed by enrollment_id
        existing = {
            er.enrollment_id: er
            for er in EnhancedResult.objects.filter(semester_subject=ss)
        }

        rows = []
        for enr in enrollments:
            er = existing.get(enr.id)
            rows.append({
                'enrollment': enr,
                'er':         er,
                'current':    getattr(er, sel_comp, None) if er else None,
            })

        context.update({'ss': ss, 'rows': rows})
        return render(request, 'core/result_engine/bulk_entry.html', context)

    return render(request, 'core/result_engine/bulk_entry_select.html', context)


@teacher_required
@teacher_required
def bulk_result_save(request):

    if request.method != 'POST':
        return redirect('re_bulk_entry')

    print("DEBUG POST DATA:", request.POST)

    ss_id = request.POST.get('ss_id')
    comp  = request.POST.get('component')  # ← IMPORTANT

    ss = get_object_or_404(SemesterSubject, pk=ss_id)

    enrollments = (
        Enrollment.objects
        .filter(
            student_class=ss.student_class,
            academic_year=ss.academic_year,
        )
        .order_by('roll_id')
    )

    enrollment_marks = []

    for enr in enrollments:
        absent = f'absent_{enr.id}' in request.POST
        val = request.POST.get(f'marks_{enr.id}')

        try:
            val = float(val) if val else None
        except:
            val = None

        entry = {
            'enrollment_id': enr.id,
            'is_absent': absent,
        }

        # 🔥 KEY FIX: assign dynamically
        if comp:
            entry[comp] = val

        enrollment_marks.append(entry)

    result = services.compute_bulk(ss, enrollment_marks)

    for enr in enrollments:
        services.compute_semester_summary(
            enr, ss.semester, ss.academic_year
        )

    messages.success(
        request,
        f"Saved: {result['created']} new, {result['updated']} updated"
    )

    return redirect(
        f"/results/engine/bulk/?year={ss.academic_year}"
        f"&class_id={ss.student_class_id}"
        f"&sem={ss.semester}"
        f"&ss_id={ss.pk}"
        f"&component={comp}"
    )
# ═══════════════════════════════════════════════════════════════════════════════
# TEACHER — CLASS RESULT OVERVIEW  (no topper/rank)
# ═══════════════════════════════════════════════════════════════════════════════

@teacher_required
def enhanced_result_list(request):
    """
    Class-level result table with per-subject component breakdown.
    Supports search by name/roll and filtering by pass/fail/component.
    """
    from django.db.models import Q

    academic_years = (
        SemesterSubject.objects
        .values_list('academic_year', flat=True)
        .distinct()
        .order_by('-academic_year')
    )
    classes  = StudentClass.objects.all()
    sem_list = [(str(i), f'Semester {i}') for i in range(1, 9)]

    sel_year   = request.GET.get('year', '')
    sel_cls    = request.GET.get('class_id', '')
    sel_sem    = request.GET.get('sem', '')
    search_q   = request.GET.get('q', '').strip()
    filter_by  = request.GET.get('filter', '')       # pass | fail
    comp_fail  = request.GET.get('comp_fail', '')     # ia1 | ia2 | sem | tw | oral

    summaries = []
    analytics = {}
    er_by_enrollment = {}

    if sel_year and sel_cls and sel_sem:
        sc = get_object_or_404(StudentClass, pk=sel_cls)

        # ── 1. Fetch all SemesterSummary rows ────────────────────────────────
        sum_qs = (
            SemesterSummary.objects
            .filter(
                enrollment__student_class=sc,
                enrollment__academic_year=sel_year,
                semester=sel_sem,
                academic_year=sel_year,
            )
            .select_related('enrollment__student', 'enrollment')
            .order_by('enrollment__roll_id')
        )

        # Apply name/roll search
        if search_q:
            sum_qs = sum_qs.filter(
                Q(enrollment__student__name__icontains=search_q) |
                Q(enrollment__roll_id__icontains=search_q)
            )

        summaries = list(sum_qs)

        # ── 2. Fetch all EnhancedResult rows for component details ───────────
        all_er = (
            EnhancedResult.objects
            .filter(
                enrollment__student_class=sc,
                enrollment__academic_year=sel_year,
                semester_subject__semester=sel_sem,
                semester_subject__academic_year=sel_year,
            )
            .select_related('semester_subject__subject', 'semester_subject', 'enrollment')
            .order_by('semester_subject__subject__name')
        )
        for er in all_er:
            er_by_enrollment.setdefault(er.enrollment_id, []).append(er)

        # Attach er_list to each summary
        for s in summaries:
            s.er_list = er_by_enrollment.get(s.enrollment_id, [])

        # ── 3. Post-fetch filters ────────────────────────────────────────────
        if filter_by == 'pass':
            summaries = [s for s in summaries if s.result == 'Pass']
        elif filter_by == 'fail':
            summaries = [s for s in summaries if s.result != 'Pass']

        if comp_fail:
            # Keep only students who failed in the selected component
            def _has_comp_fail(s, comp):
                for er in s.er_list:
                    if comp == 'ia1' and er.semester_subject.has_ia and er.is_fail_ia:
                        return True
                    if comp == 'ia2' and er.semester_subject.has_ia and er.is_fail_ia:
                        return True
                    if comp == 'sem' and er.is_fail_sem:
                        return True
                    if comp == 'tw' and er.is_fail_tw:
                        return True
                    if comp == 'oral' and er.is_fail_oral:
                        return True
                return False
            summaries = [s for s in summaries if _has_comp_fail(s, comp_fail)]

        analytics = services.get_class_analytics(sc, sel_sem, sel_year)

    return render(request, 'core/result_engine/enhanced_result_list.html', {
        'academic_years':   academic_years,
        'classes':          classes,
        'sem_list':         sem_list,
        'sel_year':         sel_year,
        'sel_cls':          sel_cls,
        'sel_sem':          sel_sem,
        'summaries':        summaries,
        'analytics':        analytics,
        'search_q':         search_q,
        'filter_by':        filter_by,
        'comp_fail':        comp_fail,
    })




# ═══════════════════════════════════════════════════════════════════════════════
# STUDENT — ENHANCED RESULT EXPLORER  (Enrollment-centric)
# ═══════════════════════════════════════════════════════════════════════════════

@student_required
def student_result_explorer(request):
    """
    Student picks a semester → sees their EnhancedResults across ALL enrollments.

    A student may have multiple enrollments (different academic years / classes).
    We must query ALL of them, not just the "current" one.

    Query chain:  student → all Enrollments → EnhancedResult
    """
    student = _get_current_student(request)

    # Collect ALL enrollments for this student
    all_enrollments = list(
        Enrollment.objects
        .filter(student=student)
        .select_related('student_class')
        .order_by('academic_year')
    )

    if not all_enrollments:
        messages.warning(request, 'You have no enrollments. Contact your teacher.')
        return redirect('student_dashboard')

    # Gather all (semester, academic_year) pairs from ALL enrollments
    # by looking at which SemesterSubjects exist for any of those enrollments.
    enr_ids = [e.id for e in all_enrollments]

    semesters = (
        EnhancedResult.objects
        .filter(enrollment_id__in=enr_ids)
        .values('semester_subject__semester', 'semester_subject__academic_year')
        .distinct()
        .order_by('semester_subject__academic_year', 'semester_subject__semester')
    )
    # Reshape into dicts with keys matching the template
    semesters = [
        {
            'semester':      s['semester_subject__semester'],
            'academic_year': s['semester_subject__academic_year'],
        }
        for s in semesters
    ]

    sel_sem  = request.GET.get('sem', '')
    sel_year = request.GET.get('year', '')

    results  = []
    summary  = None
    sections = {}

    if sel_sem and sel_year:
        # Fetch results across ALL enrollments for the selected semester+year
        results = list(
            EnhancedResult.objects
            .filter(
                enrollment_id__in=enr_ids,
                semester_subject__semester=sel_sem,
                semester_subject__academic_year=sel_year,
            )
            .select_related('semester_subject', 'semester_subject__subject', 'enrollment')
            .order_by('semester_subject__subject__name')
        )

        # Find the matching SemesterSummary — look across all enrollments
        summary = SemesterSummary.objects.filter(
            enrollment_id__in=enr_ids,
            semester=sel_sem,
            academic_year=sel_year,
        ).first()

        # Split into tabbed sections
        for r in results:
            ss = r.semester_subject
            if ss.has_ia:
                sections.setdefault('Internal Assessment', []).append(r)
            if ss.has_sem:
                sections.setdefault('Semester End Exam', []).append(r)
            if ss.has_tw:
                sections.setdefault('Term Work', []).append(r)
            if ss.has_oral:
                sections.setdefault('Oral / Practical', []).append(r)



    # Use the most recent enrollment for display in header
    current_enrollment = all_enrollments[-1] if all_enrollments else None

    return render(request, 'core/result_engine/student_explorer.html', {
        'student':      student,
        'enrollment':   current_enrollment,  # only for header display
        'semesters':    semesters,
        'sel_sem':      sel_sem,
        'sel_year':     sel_year,
        'results':      results,
        'summary':      summary,
        'sections':     sections,
    })


@student_required
def student_subject_detail_enhanced(request, ss_id):
    """
    Detailed progress-bar card for one subject.
    Uses Enrollment to look up the EnhancedResult.
    """
    student    = _get_current_student(request)
    enrollment = student.current_enrollment

    if not enrollment:
        return redirect('student_dashboard')

    ss = get_object_or_404(SemesterSubject, pk=ss_id)
    er = get_object_or_404(EnhancedResult, enrollment=enrollment, semester_subject=ss)

    def pct(marks, max_marks):
        if marks is None or max_marks == 0:
            return 0
        return round(float(marks) / max_marks * 100, 1)

    bars = []
    if ss.has_ia:
        ia_fail = er.is_fail_ia
        bars.append({'label': 'IA-1', 'marks': er.ia1, 'max': ss.max_ia1,
                     'pct': pct(er.ia1, ss.max_ia1), 'fail': ia_fail})
        bars.append({'label': 'IA-2', 'marks': er.ia2, 'max': ss.max_ia2,
                     'pct': pct(er.ia2, ss.max_ia2), 'fail': ia_fail})
    if ss.has_tw:
        bars.append({'label': 'Term Work', 'marks': er.tw, 'max': ss.max_tw,
                     'pct': pct(er.tw, ss.max_tw), 'fail': er.is_fail_tw})
    if ss.has_oral:
        bars.append({'label': 'Oral/Practical', 'marks': er.oral, 'max': ss.max_oral,
                     'pct': pct(er.oral, ss.max_oral), 'fail': er.is_fail_oral})
    if ss.has_sem:
        bars.append({'label': 'SEM Exam', 'marks': er.sem, 'max': ss.max_sem,
                     'pct': pct(er.sem, ss.max_sem), 'fail': er.is_fail_sem})

    return render(request, 'core/result_engine/subject_detail.html', {
        'student':    student,
        'enrollment': enrollment,
        'ss':         ss,
        'er':         er,
        'bars':       bars,
        'total_pct':  pct(er.total, ss.max_total),
    })


@student_required
def student_marksheet(request, semester, academic_year, student_pk=None):
    """
    University-style printable marksheet.
    Resolves Enrollment from the logged-in student.
    """
    student    = _get_current_student(request)
    enrollment = student.current_enrollment

    if not enrollment:
        messages.warning(request, 'No active enrollment found.')
        return redirect('student_dashboard')

    data = services.get_student_marksheet(enrollment, semester, academic_year)
    return render(request, 'core/result_engine/marksheet.html', data)


@student_required
def student_marksheet_pdf(request, semester, academic_year, student_pk):
    """Print-trigger version of the marksheet (opens browser print dialog)."""
    student    = _get_current_student(request)
    if student.pk != student_pk:
        return HttpResponseForbidden('You can only view your own marksheet.')

    enrollment = student.current_enrollment
    if not enrollment:
        return redirect('student_dashboard')

    data = services.get_student_marksheet(enrollment, semester, academic_year)
    data['auto_print'] = True
    return render(request, 'core/result_engine/marksheet.html', data)





# ═══════════════════════════════════════════════════════════════════════════════
# AJAX helpers
# ═══════════════════════════════════════════════════════════════════════════════

@teacher_required
def ajax_semester_subjects(request):
    """Return semester subjects for a class+semester+year."""
    cls_id = request.GET.get('class_id')
    sem    = request.GET.get('sem')
    year   = request.GET.get('year')
    qs = SemesterSubject.objects.filter(
        student_class_id=cls_id, semester=sem, academic_year=year
    ).values('id', 'subject__name', 'credits')
    return JsonResponse({'items': list(qs)})


@teacher_required
def ajax_academic_years_for_class(request):
    """Return available academic years for a given class (for enrollment form)."""
    cls_id = request.GET.get('class_id')
    years = (
        Enrollment.objects
        .filter(student_class_id=cls_id)
        .values_list('academic_year', flat=True)
        .distinct()
        .order_by('-academic_year')
    )
    return JsonResponse({'years': list(years)})

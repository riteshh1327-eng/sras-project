"""
SRAS — Result Engine Services (Phase-Aware Edition)
=====================================================
ALL grading/SGPA/pass-fail logic lives here.
Views and models must NEVER replicate any of this logic.

Public API
----------
  get_grade_for_percentage(pct)             → (grade, points, is_pass)
  phase_aware_status(er)                    → status string
  compute_result(er, save=True)             → mutates EnhancedResult in-place
  compute_bulk(semester_subject, enrollment_marks) → {created, updated, errors}
  compute_semester_summary(enrollment, sem, ay)    → SemesterSummary
  get_cgpa(student)                         → float
  get_student_marksheet(enrollment, sem, ay)→ dict
  get_class_analytics(student_class, sem, ay) → dict
  seed_grade_scale()                        → int (rows seeded)
  authenticate_student(email, password)     → Student | None
"""

from decimal import Decimal, ROUND_HALF_UP
import logging

logger = logging.getLogger(__name__)


# ── Lazy model imports (avoids circular import at module load time) ────────────

def _m():
    from .result_models import GradeScale, SemesterSubject, EnhancedResult, SemesterSummary
    from .models import Student, StudentClass, Enrollment
    return GradeScale, SemesterSubject, EnhancedResult, SemesterSummary, Student, StudentClass, Enrollment

def _clamp(value, lo, hi):
    """Clamp numeric value safely between lo and hi."""
    if value is None:
        return None
    try:
        v = float(value)
        return max(lo, min(hi, v))
    except (TypeError, ValueError):
        return None
# ═══════════════════════════════════════════════════════════════════════════════
# 1. GRADE LOOKUP
# ═══════════════════════════════════════════════════════════════════════════════

# Hardcoded fallback so the engine works even before GradeScale is seeded
_FALLBACK_SCALE = [
    (75, 'O',  10.0, True),
    (65, 'A+',  9.0, True),
    (55, 'A',   8.0, True),
    (50, 'B+',  7.0, True),
    (45, 'B',   6.0, True),
    (40, 'C',   5.0, True),
    ( 0, 'F',   0.0, False),
]


def get_grade_for_percentage(percentage: float) -> tuple:
    """
    Return (grade_str, grade_points, is_pass) for a percentage.
    Reads from GradeScale table; falls back to hardcoded MU scale.
    """
    GradeScale, *_ = _m()
    pct = Decimal(str(percentage))
    for row in GradeScale.objects.order_by('-min_percentage'):
        if pct >= row.min_percentage:
            return row.grade, float(row.grade_points), row.is_pass
    # Fallback
    for threshold, grade, gp, is_pass in _FALLBACK_SCALE:
        if percentage >= threshold:
            return grade, gp, is_pass
    return 'F', 0.0, False


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PHASE-AWARE PASS/FAIL ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def phase_aware_status(er) -> str:
    """
    Determine pass/fail status based on which marks are currently present.
    This is the core of the Phase-Aware Grading Engine.

    Phase logic (for subjects that have IA and SEM):

      PHASE 0 — no marks at all → 'Pending'

      PHASE 1 — only IA1 present (IA2 and SEM both absent):
        PASS if ia1 >= 40% of max_ia1  (default: 8/20)
        FAIL otherwise
        Status: 'Phase1 Pass' or 'Phase1 Fail'

      PHASE 2 — IA1+IA2 present, SEM absent:
        PASS if (ia1+ia2) >= 40% of (max_ia1+max_ia2)  (default: 16/40)
        FAIL otherwise
        Status: 'Phase2 Pass' or 'Phase2 Fail'

      FINAL — SEM present (or subject has no SEM component):
        IA_PASS  = (ia1+ia2) >= 40% of (max_ia1+max_ia2)
        SEM_PASS = sem >= 40% of max_sem
        TW_PASS  = tw  >= 40% of max_tw   (if active)
        ORAL_PASS= oral>= 40% of max_oral (if active)
        OVERALL  = total >= 40% of max_total

        FINAL_PASS = IA_PASS AND SEM_PASS AND TW_PASS AND ORAL_PASS AND OVERALL
        If absent → 'Absent'
        Status: 'Pass' or 'Fail'
    """
    ss = er.semester_subject

    if er.is_absent:
        return 'Absent'

    ia1_val  = er.ia1
    ia2_val  = er.ia2
    sem_val  = er.sem
    tw_val   = er.tw
    oral_val = er.oral

    has_ia   = ss.has_ia
    has_sem  = ss.has_sem
    has_tw   = ss.has_tw
    has_oral = ss.has_oral

    # ── Phase 0: no marks entered ────────────────────────────────────────────
    no_ia   = (ia1_val is None and ia2_val is None)
    no_sem  = (sem_val is None or not has_sem)
    no_tw   = (tw_val  is None or not has_tw)
    no_oral = (oral_val is None or not has_oral)

    if no_ia and no_sem and no_tw and no_oral:
        return 'Pending'

    # ── Phase 1: only IA1 entered (IA2 absent, SEM absent) ──────────────────
    if has_ia and ia1_val is not None and ia2_val is None and (not has_sem or sem_val is None):
        if float(ia1_val) >= ss.min_ia1:
            return 'Phase1 Pass'
        return 'Phase1 Fail'

    # ── Phase 2: IA1+IA2 present, SEM absent ────────────────────────────────
    if has_ia and ia1_val is not None and ia2_val is not None and (has_sem and sem_val is None):
        if float(ia1_val) >= ss.min_ia1 and float(ia2_val) >= ss.min_ia2:
            return 'Phase2 Pass'
        return 'Phase2 Fail'

    # ── Final phase: SEM entered (or no-SEM subject fully entered) ───────────
    # Component checks. For all enabled, they must meet their min marks.
    if has_ia:
        if float(ia1_val or 0) < ss.min_ia1 or float(ia2_val or 0) < ss.min_ia2:
            return 'Fail'

    if has_sem and sem_val is not None:
        if float(sem_val) < ss.min_sem:
            return 'Fail'

    if has_tw and tw_val is not None:
        if float(tw_val) < ss.min_tw:
            return 'Fail'

    if has_oral and oral_val is not None:
        if float(oral_val) < ss.min_oral:
            return 'Fail'

    # No overall percentage check anymore. If all components pass, the result is Pass.
    return 'Pass'


# ═══════════════════════════════════════════════════════════════════════════════
# 3. COMPONENT TOTALS (private helper)
# ═══════════════════════════════════════════════════════════════════════════════

def _calculate_total(er) -> tuple:
    """Return (ia_total, grand_total, max_total) for an EnhancedResult."""
    ss = er.semester_subject
    ia_t = 0.0
    total = 0.0
    max_t = 0.0

    if ss.has_ia:
        ia_t   = float(er.ia1 or 0) + float(er.ia2 or 0)
        total += ia_t
        max_t += ss.max_ia1 + ss.max_ia2

    if ss.has_tw:
        total += float(er.tw or 0)
        max_t += ss.max_tw

    if ss.has_oral:
        total += float(er.oral or 0)
        max_t += ss.max_oral

    if ss.has_sem:
        total += float(er.sem or 0)
        max_t += ss.max_sem

    return round(ia_t, 1), round(total, 1), max_t


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SINGLE RESULT COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

from decimal import Decimal


def compute_result(er, save=False):
    """
    Safe computation using Decimal ONLY
    """

    ss = er.semester_subject

    def d(val):
        if val is None:
            return Decimal('0')
        return Decimal(str(val))

    ia1 = d(er.ia1)
    ia2 = d(er.ia2)
    sem = d(er.sem)
    tw  = d(er.tw)
    oral= d(er.oral)

    # TOTAL
    er.total = ia1 + ia2 + sem + tw + oral

    # ───────── PASS LOGIC ─────────

    def is_pass(val, min_val):
        if val is None:
            return True
        return d(val) >= d(min_val)

    checks = []

    if ss.has_ia:
        checks.append(is_pass(er.ia1, ss.min_ia1))
        checks.append(is_pass(er.ia2, ss.min_ia2))

    if ss.has_sem:
        checks.append(is_pass(er.sem, ss.min_sem))

    if ss.has_tw:
        checks.append(is_pass(er.tw, ss.min_tw))

    if ss.has_oral:
        checks.append(is_pass(er.oral, ss.min_oral))

    er.status = "Pass" if all(checks) else "Fail"

    if save:
        er.save()

    return er
# ═══════════════════════════════════════════════════════════════════════════════
# 5. BULK RESULT ENTRY
# ═══════════════════════════════════════════════════════════════════════════════

def compute_bulk(semester_subject, enrollment_marks: list) -> dict:
    """
    Safe partial-update for EnhancedResult.

    ✔ Only updates submitted component
    ✔ Never overwrites existing values
    ✔ Supports independent IA1 / IA2 / SEM saves
    ✔ Handles absent safely
    """

    _, _, EnhancedResult, _, _, _, Enrollment = _m()

    created = updated = 0
    errors = []

    for entry in enrollment_marks:
        enr_id = entry.get('enrollment_id')

        try:
            enr = Enrollment.objects.get(pk=enr_id)
        except Enrollment.DoesNotExist:
            errors.append(f"Enrollment id={enr_id} not found")
            continue

        er, was_created = EnhancedResult.objects.get_or_create(
            enrollment=enr,
            semester_subject=semester_subject,
            defaults={'status': 'Pending'},
        )

        absent = bool(entry.get('is_absent', False))

        # ─────────────────────────────────────────────
        # ABSENT HANDLING
        # ─────────────────────────────────────────────
        if absent:
            er.is_absent = True

            # Only clear the component being submitted (NOT all fields)
            if 'ia1' in entry:
                er.ia1 = None
            if 'ia2' in entry:
                er.ia2 = None
            if 'tw' in entry:
                er.tw = None
            if 'oral' in entry:
                er.oral = None
            if 'sem' in entry:
                er.sem = None

            er.save()
            updated += 1
            continue

        er.is_absent = False

        ss = semester_subject

        # ─────────────────────────────────────────────
        # SAFE PARTIAL UPDATE (CORE FIX)
        # ─────────────────────────────────────────────

        if ss.has_ia:
            if 'ia1' in entry and entry['ia1'] not in [None, ""]:
                er.ia1 = _clamp(entry['ia1'], 0, ss.max_ia1)

            if 'ia2' in entry and entry['ia2'] not in [None, ""]:
                er.ia2 = _clamp(entry['ia2'], 0, ss.max_ia2)

        if ss.has_tw:
            if 'tw' in entry and entry['tw'] not in [None, ""]:
                er.tw = _clamp(entry['tw'], 0, ss.max_tw)

        if ss.has_oral:
            if 'oral' in entry and entry['oral'] not in [None, ""]:
                er.oral = _clamp(entry['oral'], 0, ss.max_oral)

        if ss.has_sem:
            if 'sem' in entry and entry['sem'] not in [None, ""]:
                er.sem = _clamp(entry['sem'], 0, ss.max_sem)

        # ─────────────────────────────────────────────

        compute_result(er, save=True)

        if was_created:
            created += 1
        else:
            updated += 1

    return {
        'created': created,
        'updated': updated,
        'errors': errors
    }

# ═══════════════════════════════════════════════════════════════════════════════
# 6. SGPA
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_sgpa(results: list) -> float:
    """
    SGPA = Σ(grade_points × credits) / Σ(credits)
    Only counts results that are in the final Pass/Fail phase.
    """
    total_gp = Decimal('0')
    total_cr = Decimal('0')

    for r in results:
        if r.status not in ('Pass', 'Fail', 'Absent'):
            continue  # skip non-final phases
        credits = Decimal(str(r.credits))
        gp      = Decimal(str(r.grade_points))
        total_gp += gp * credits
        total_cr += credits

    if total_cr == 0:
        return 0.0
    return float((total_gp / total_cr).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def get_cgpa(student) -> float:
    """
    CGPA = mean of all semester SGPAs for this student (across all enrollments).
    """
    _, _, _, SemesterSummary, _, _, _ = _m()
    summaries = SemesterSummary.objects.filter(
        enrollment__student=student
    ).exclude(sgpa=0)
    if not summaries.exists():
        return 0.0
    total = sum(float(s.sgpa) for s in summaries)
    return round(total / summaries.count(), 2)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SEMESTER SUMMARY COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

def compute_semester_summary(enrollment, semester: str, academic_year: str):
    """
    Rebuild SemesterSummary for enrollment × semester.
    Called after any result is saved.
    """
    _, _, EnhancedResult, SemesterSummary, _, _, _ = _m()

    results = list(
        EnhancedResult.objects.filter(
            enrollment=enrollment,
            semester_subject__semester=semester,
            semester_subject__academic_year=academic_year,
        ).select_related('semester_subject')
    )

    total_credits   = sum(r.credits for r in results)
    earned_credits  = sum(r.credits for r in results if r.status == 'Pass')
    total_marks     = sum(float(r.total) for r in results)
    max_marks       = sum(r.semester_subject.max_total for r in results)
    subjects_failed = sum(1 for r in results if r.status in ('Fail', 'Absent'))

    pct      = round(total_marks / max_marks * 100, 2) if max_marks else 0.0
    sgpa     = calculate_sgpa(results)
    cgpa     = get_cgpa(enrollment.student)
    result_s = 'Pass' if subjects_failed == 0 and results else 'Fail'

    summary, _ = SemesterSummary.objects.update_or_create(
        enrollment=enrollment,
        semester=semester,
        academic_year=academic_year,
        defaults={
            'total_credits':  total_credits,
            'earned_credits': earned_credits,
            'total_marks':    total_marks,
            'max_marks':      max_marks,
            'percentage':     pct,
            'sgpa':           sgpa,
            'cgpa':           cgpa,
            'result':         result_s,
            'subjects_failed':subjects_failed,
        }
    )
    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# 8. MARKSHEET DATA BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def get_student_marksheet(enrollment, semester: str, academic_year: str) -> dict:
    """
    Return all data needed to render a university marksheet.

    Returns:
    {
        'enrollment': Enrollment,
        'student': Student,
        'semester': str,
        'academic_year': str,
        'results': [EnhancedResult],
        'summary': SemesterSummary | None,
        'cgpa': float,
        'grade_scale': [GradeScale],
    }
    """
    GradeScale, _, EnhancedResult, SemesterSummary, _, _, _ = _m()

    results = list(
        EnhancedResult.objects.filter(
            enrollment=enrollment,
            semester_subject__semester=semester,
            semester_subject__academic_year=academic_year,
        )
        .select_related('semester_subject', 'semester_subject__subject')
        .order_by('semester_subject__subject__name')
    )

    summary = SemesterSummary.objects.filter(
        enrollment=enrollment, semester=semester, academic_year=academic_year
    ).first()

    if not summary and results:
        summary = compute_semester_summary(enrollment, semester, academic_year)

    return {
        'enrollment':    enrollment,
        'student':       enrollment.student,
        'semester':      semester,
        'academic_year': academic_year,
        'results':       results,
        'summary':       summary,
        'cgpa':          get_cgpa(enrollment.student),
        'grade_scale':   list(GradeScale.objects.all()),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 9. CLASS ANALYTICS  (no ranking/topper logic)
# ═══════════════════════════════════════════════════════════════════════════════

def get_class_analytics(student_class, semester: str, academic_year: str) -> dict:
    """
    Aggregate analytics for a teacher's class view.

    Intentionally omits topper / ranking logic (Section 4 of spec).
    Sorts by roll_id ascending throughout.

    Returns:
    {
        'pass_count': int,
        'fail_count': int,
        'pass_pct': float,
        'total_students': int,
        'class_avg_sgpa': float,
        'at_risk': [SemesterSummary],   # subjects_failed >= 2
        'subject_stats': [{subject, avg_marks, pass_count, fail_count, fail_pct}],
        'grade_dist': {'O':n, 'A+':n, ...},
        'summaries': [SemesterSummary],  # sorted by roll_id asc
    }
    """
    from .result_models import EnhancedResult, SemesterSummary
    from .models import Enrollment

    # All enrollments for this class+year, sorted by roll_id
    enrollments = list(
        Enrollment.objects.filter(
            student_class=student_class,
            academic_year=academic_year,
        ).order_by('roll_id').select_related('student')
    )
    enr_ids = [e.id for e in enrollments]

    summaries = list(
        SemesterSummary.objects.filter(
            enrollment_id__in=enr_ids,
            semester=semester,
            academic_year=academic_year,
        )
        .select_related('enrollment__student')
        .order_by('enrollment__roll_id')   # roll_id ascending, no rank
    )

    pass_count = sum(1 for s in summaries if s.result == 'Pass')
    fail_count = sum(1 for s in summaries if s.result == 'Fail')
    total      = len(summaries)
    pass_pct   = round(pass_count / total * 100, 1) if total else 0

    at_risk    = [s for s in summaries if s.subjects_failed >= 2]
    avg_sgpa   = round(sum(float(s.sgpa) for s in summaries) / total, 2) if total else 0

    # Subject-level stats
    results_qs = EnhancedResult.objects.filter(
        enrollment_id__in=enr_ids,
        semester_subject__semester=semester,
        semester_subject__academic_year=academic_year,
    ).select_related('semester_subject__subject')

    subject_map = {}
    for r in results_qs:
        sname = r.semester_subject.subject.display_name
        subject_map.setdefault(sname, {'marks': [], 'pass': 0, 'fail': 0})
        subject_map[sname]['marks'].append(float(r.total))
        if r.status == 'Pass':
            subject_map[sname]['pass'] += 1
        else:
            subject_map[sname]['fail'] += 1

    subject_stats = []
    for sname, data in sorted(subject_map.items()):
        cnt = len(data['marks'])
        avg = round(sum(data['marks']) / cnt, 1) if cnt else 0
        fp  = round(data['fail'] / cnt * 100, 1) if cnt else 0
        subject_stats.append({
            'subject':    sname,
            'avg_marks':  avg,
            'pass_count': data['pass'],
            'fail_count': data['fail'],
            'fail_pct':   fp,
        })

    # Grade distribution
    grade_dist = {g: 0 for g in ['O', 'A+', 'A', 'B+', 'B', 'C', 'F']}
    for r in results_qs:
        if r.grade in grade_dist:
            grade_dist[r.grade] += 1

    return {
        'pass_count':     pass_count,
        'fail_count':     fail_count,
        'pass_pct':       pass_pct,
        'total_students': total,
        'class_avg_sgpa': avg_sgpa,
        'at_risk':        at_risk,
        'subject_stats':  subject_stats,
        'grade_dist':     grade_dist,
        'summaries':      summaries,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 10. AUTHENTICATION SERVICE
# ═══════════════════════════════════════════════════════════════════════════════

def authenticate_student(email: str, password: str):
    """
    Authenticate a student by email + password.

    Password priority:
      1. DOB formatted as DDMMYYYY  (12 Aug 2005 → '12082005')
      2. roll_id from current Enrollment  (legacy fallback)

    Returns Student instance on success, None on failure.
    """
    from .models import Student
    student = Student.objects.filter(email__iexact=email).first()
    if student and student.check_auth_password(password):
        return student
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# 11. GRADE SCALE SEEDER
# ═══════════════════════════════════════════════════════════════════════════════

def seed_grade_scale() -> int:
    """Seed GradeScale with University of Mumbai defaults. Safe to call multiple times."""
    from .result_models import GradeScale
    defaults = [
        ('O',  75, 100, 10.0, True),
        ('A+', 65,  74,  9.0, True),
        ('A',  55,  64,  8.0, True),
        ('B+', 50,  54,  7.0, True),
        ('B',  45,  49,  6.0, True),
        ('C',  40,  44,  5.0, True),
        ('F',   0,  39,  0.0, False),
    ]
    for grade, mn, mx, gp, is_pass in defaults:
        GradeScale.objects.get_or_create(
            grade=grade,
            defaults={'min_percentage': mn, 'max_percentage': mx,
                      'grade_points': gp, 'is_pass': is_pass}
        )
    return len(defaults)

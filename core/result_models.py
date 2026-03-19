"""
SRAS — Result Engine Models (University-grade)

Enrollment-centric architecture:

  Enrollment (per student per year)
    └─ EnhancedResult (one row per Enrollment × SemesterSubject)
         └─ SemesterSummary (one row per Enrollment × semester)

GradeScale   — configurable grade boundaries (seeded with MU defaults)
SemesterSubject — subject+credits+components assigned to a class+semester
EnhancedResult  — 5-component result (IA1, IA2, TW, Oral, SEM)
SemesterSummary — cached SGPA / CGPA per enrollment+semester
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


def _models():
    """Lazy imports to avoid circular import."""
    from .models import StudentClass, Subject, Enrollment
    return StudentClass, Subject, Enrollment


# ═══════════════════════════════════════════════════════════════════════════════
# GRADE SCALE
# ═══════════════════════════════════════════════════════════════════════════════

class GradeScale(models.Model):
    """
    Configurable grade boundary table (University of Mumbai style).
    Seeded in migration 0003; editable via admin.

    Grade | Min% | Max% | Points | Pass?
    O     |  75  | 100  |  10    | Yes
    A+    |  65  |  74  |   9    | Yes
    ...
    F     |   0  |  39  |   0    | No
    """
    GRADE_CHOICES = [
        ('O', 'Outstanding'), ('A+', 'Excellent'), ('A', 'Very Good'),
        ('B+', 'Good'), ('B', 'Above Average'), ('C', 'Average'), ('F', 'Fail'),
    ]

    grade           = models.CharField(max_length=3, choices=GRADE_CHOICES, unique=True)
    min_percentage  = models.DecimalField(max_digits=5, decimal_places=2,
                          validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_percentage  = models.DecimalField(max_digits=5, decimal_places=2,
                          validators=[MinValueValidator(0), MaxValueValidator(100)])
    grade_points    = models.DecimalField(max_digits=4, decimal_places=1,
                          validators=[MinValueValidator(0), MaxValueValidator(10)])
    is_pass         = models.BooleanField(default=True)

    class Meta:
        ordering = ['-min_percentage']
        verbose_name = 'Grade Scale'
        verbose_name_plural = 'Grade Scale'

    def __str__(self):
        return f"{self.grade} ({self.min_percentage}%–{self.max_percentage}%) = {self.grade_points} pts"


# ═══════════════════════════════════════════════════════════════════════════════
# SEMESTER SUBJECT
# ═══════════════════════════════════════════════════════════════════════════════

class SemesterSubject(models.Model):
    """
    Assigns a Subject to a class for a specific semester with credits
    and component configuration.

    One SemesterSubject = one column in a marksheet.
    """
    SEMESTER_CHOICES = [(str(i), f'Semester {i}') for i in range(1, 9)]

    student_class = models.ForeignKey(
        'core.StudentClass', on_delete=models.CASCADE,
        related_name='semester_subjects', verbose_name='Class'
    )
    subject = models.ForeignKey(
        'core.Subject', on_delete=models.CASCADE,
        related_name='semester_subjects', verbose_name='Subject'
    )
    semester      = models.CharField(max_length=1, choices=SEMESTER_CHOICES)
    academic_year = models.CharField(max_length=10, help_text='e.g. 2024-25')
    credits       = models.PositiveSmallIntegerField(default=4,
                        validators=[MinValueValidator(1), MaxValueValidator(10)])

    # Component toggles
    has_ia   = models.BooleanField(default=True,  verbose_name='Has IA')
    has_tw   = models.BooleanField(default=False, verbose_name='Has TW')
    has_oral = models.BooleanField(default=False, verbose_name='Has Oral')
    has_sem  = models.BooleanField(default=True,  verbose_name='Has SEM')

    # Max marks per component
    max_ia1  = models.PositiveSmallIntegerField(default=20)
    max_ia2  = models.PositiveSmallIntegerField(default=20)
    max_tw   = models.PositiveSmallIntegerField(default=25)
    max_oral = models.PositiveSmallIntegerField(default=25)
    max_sem  = models.PositiveSmallIntegerField(default=60)

    # Min passing marks per component
    min_ia1  = models.PositiveSmallIntegerField(default=8)
    min_ia2  = models.PositiveSmallIntegerField(default=8)
    min_tw   = models.PositiveSmallIntegerField(default=10)
    min_oral = models.PositiveSmallIntegerField(default=10)
    min_sem  = models.PositiveSmallIntegerField(default=24)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student_class', 'subject', 'semester', 'academic_year')
        ordering = ['semester', 'subject__name']
        verbose_name = 'Semester Subject'
        verbose_name_plural = 'Semester Subjects'
        indexes = [
            models.Index(fields=['student_class', 'semester', 'academic_year'],
                         name='ss_class_sem_year_idx'),
        ]

    def __str__(self):
        return (f"{self.subject.display_name} | {self.student_class.display_name} "
                f"| Sem {self.semester} | {self.academic_year}")

    @property
    def max_total(self):
        """Sum of max marks across active components."""
        t = 0
        if self.has_ia:   t += self.max_ia1 + self.max_ia2
        if self.has_tw:   t += self.max_tw
        if self.has_oral: t += self.max_oral
        if self.has_sem:  t += self.max_sem
        return t


# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED RESULT  (Enrollment-centric)
# ═══════════════════════════════════════════════════════════════════════════════

class EnhancedResult(models.Model):
    """
    Full university-style result.
    One row = one Enrollment × one SemesterSubject.

    Computed fields (total, grade, grade_points, status, ia_total)
    are always written by services.py — NEVER set manually.

    Phase-aware status values (set by services.phase_aware_status):
      'Pending'     — no marks entered yet
      'Phase1 Pass' / 'Phase1 Fail'  — only IA1 entered
      'Phase2 Pass' / 'Phase2 Fail'  — IA1+IA2 entered, no SEM
      'Pass' / 'Fail' / 'Absent'     — final (SEM entered)
    """
    GRADE_CHOICES = [
        ('O', 'Outstanding'), ('A+', 'Excellent'), ('A', 'Very Good'),
        ('B+', 'Good'), ('B', 'Above Average'), ('C', 'Average'),
        ('F', 'Fail'), ('-', 'Not Graded'),
    ]

    # Core FK: Enrollment (not Student directly)
    enrollment = models.ForeignKey(
        'core.Enrollment', on_delete=models.CASCADE,
        related_name='enhanced_results', verbose_name='Enrollment'
    )
    semester_subject = models.ForeignKey(
        SemesterSubject, on_delete=models.CASCADE,
        related_name='results', verbose_name='Semester Subject'
    )

    # Raw marks (nullable = not yet entered)
    ia1  = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    ia2  = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    tw   = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    oral = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    sem  = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    # Computed fields — written by services.compute_result()
    ia_total     = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    total        = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    percentage   = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade        = models.CharField(max_length=3, choices=GRADE_CHOICES, default='-')
    grade_points = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    status       = models.CharField(max_length=12, default='Pending')

    is_absent    = models.BooleanField(default=False)

    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('enrollment', 'semester_subject')
        ordering = ['enrollment__roll_id', 'semester_subject__subject__name']
        verbose_name = 'Enhanced Result'
        verbose_name_plural = 'Enhanced Results'
        indexes = [
            models.Index(fields=['enrollment', 'semester_subject'],
                         name='er_enr_ss_idx'),
            models.Index(fields=['status'], name='er_status_idx'),
        ]

    def __str__(self):
        return (f"{self.enrollment.student.name} | "
                f"{self.semester_subject.subject.display_name} | "
                f"Sem {self.semester_subject.semester} | {self.grade}")

    # ── Convenience shortcuts (read-only) ─────────────────────────────────────

    @property
    def student(self):
        return self.enrollment.student

    @property
    def subject(self):
        return self.semester_subject.subject

    @property
    def semester(self):
        return self.semester_subject.semester

    @property
    def credits(self):
        return self.semester_subject.credits

    # ── Component fail checks (used by services + templates) ─────────────────

    @property
    def is_fail_ia(self):
        ss = self.semester_subject
        if not ss.has_ia:
            return False
        # Rule: Pass ONLY IF ia1 >= min_ia1 AND ia2 >= min_ia2
        # If either is None, treat as 0
        return float(self.ia1 or 0) < ss.min_ia1 or float(self.ia2 or 0) < ss.min_ia2

    @property
    def is_fail_sem(self):
        ss = self.semester_subject
        if not ss.has_sem:
            return False
        return float(self.sem or 0) < ss.min_sem

    @property
    def is_fail_tw(self):
        ss = self.semester_subject
        if not ss.has_tw:
            return False
        return float(self.tw or 0) < ss.min_tw

    @property
    def is_fail_oral(self):
        ss = self.semester_subject
        if not ss.has_oral:
            return False
        return float(self.oral or 0) < ss.min_oral

    @property
    def is_final(self):
        """True when SEM marks have been entered (final phase)."""
        return self.sem is not None or not self.semester_subject.has_sem


# ═══════════════════════════════════════════════════════════════════════════════
# SEMESTER SUMMARY  (Enrollment-centric, cached SGPA)
# ═══════════════════════════════════════════════════════════════════════════════

class SemesterSummary(models.Model):
    """
    Cached SGPA and stats for one Enrollment × semester.
    Rebuilt by services.compute_semester_summary() whenever marks change.
    """
    enrollment    = models.ForeignKey(
        'core.Enrollment', on_delete=models.CASCADE,
        related_name='semester_summaries', verbose_name='Enrollment'
    )
    semester      = models.CharField(max_length=1)
    academic_year = models.CharField(max_length=10)

    total_credits  = models.PositiveSmallIntegerField(default=0)
    earned_credits = models.PositiveSmallIntegerField(default=0)
    total_marks    = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    max_marks      = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    percentage     = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sgpa           = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    cgpa           = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    result         = models.CharField(max_length=4, default='Fail')   # Pass / Fail
    subjects_failed= models.PositiveSmallIntegerField(default=0)

    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('enrollment', 'semester', 'academic_year')
        ordering = ['enrollment', 'semester']
        verbose_name = 'Semester Summary'
        verbose_name_plural = 'Semester Summaries'
        indexes = [
            models.Index(fields=['enrollment', 'semester'],
                         name='sem_sum_enr_sem_idx'),
        ]

    def __str__(self):
        return (f"{self.enrollment.student.name} | "
                f"Sem {self.semester} | SGPA {self.sgpa}")

    @property
    def student(self):
        return self.enrollment.student

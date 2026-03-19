"""
SRAS — Core Models
Student Result Analysis System

Architecture: Permanent Identity Pattern
  Teacher        — staff account, hashed password
  StudentClass   — class/batch definition (FE-A 2024-25)
  Subject        — academic subject (permanent, no duplication)
  SubjectCombination — legacy class-subject mapping
  Student        — PERMANENT person identity (no class, no roll_id)
  Enrollment     — NEW: bridges Student + StudentClass for one academic year
  Result         — legacy 3-component result (kept for old views)
  Notice         — announcements
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.hashers import make_password, check_password as django_check_password


from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Teacher(models.Model):
    """Teacher account used for SRAS teacher login."""

    name = models.CharField(max_length=150, verbose_name="Full Name")
    email = models.EmailField(unique=True, verbose_name="Email")

    # Stores hashed password
    password = models.CharField(max_length=255, verbose_name="Password (hashed)")

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Teacher"
        verbose_name_plural = "Teachers"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.email})"

    # ---------- Password Helpers ----------

    def set_password(self, raw_password):
        """Hash and store password."""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Verify password."""
        return check_password(raw_password, self.password)

    def save(self, *args, **kwargs):
        """
        No automatic hashing in save() to prevent double-hashing.
        Use set_password() explicitly.
        """
        super().save(*args, **kwargs)


class StudentClass(models.Model):
    """Class/batch definition (e.g. SE-B 2024-25)."""
    CLASS_YEAR_CHOICES = [
        ('FE', 'First Year (FE)'), ('SE', 'Second Year (SE)'),
        ('TE', 'Third Year (TE)'), ('BE', 'Fourth Year (BE)'),
    ]
    class_year    = models.CharField(max_length=2, choices=CLASS_YEAR_CHOICES, verbose_name='Class Year')
    section       = models.CharField(max_length=5, verbose_name='Section', help_text='e.g. A, B, C')
    academic_year = models.CharField(max_length=10, verbose_name='Academic Year', help_text='e.g. 2024-25')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('class_year', 'section', 'academic_year')
        ordering = ['class_year', 'section', 'academic_year']
        verbose_name = 'Student Class'
        verbose_name_plural = 'Student Classes'

    def __str__(self):
        return f"{self.class_year}-{self.section} ({self.academic_year})"

    @property
    def display_name(self):
        return f"{self.class_year}-{self.section}"

    def get_student_count(self):
        return self.enrollments.count()

    def get_subjects(self):
        return Subject.objects.filter(subjectcombination__student_class=self).distinct()


class Subject(models.Model):
    """Academic subject — permanent, never duplicated."""
    name        = models.CharField(max_length=100, unique=True, verbose_name='Subject Name')
    code        = models.CharField(max_length=20, blank=True, verbose_name='Subject Code')
    description = models.TextField(blank=True, verbose_name='Description')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name

    @property
    def display_name(self):
        return self.name


class SubjectCombination(models.Model):
    """Legacy class-subject mapping (kept for pattern analysis)."""
    student_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE,
                                       related_name='subject_combinations')
    subject       = models.ForeignKey(Subject, on_delete=models.CASCADE,
                                       related_name='subject_combinations')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student_class', 'subject')
        ordering = ['student_class', 'subject__name']
        verbose_name = 'Subject Combination'
        verbose_name_plural = 'Subject Combinations'

    def __str__(self):
        return f"{self.student_class} — {self.subject.display_name}"


class Student(models.Model):
    """
    Permanent person identity.

    Fields removed vs old model: student_class, roll_id
    These now live in Enrollment.

    Auth password priority:
      1. DOB formatted as DDMMYYYY  (new default)
      2. roll_id from current enrollment  (legacy fallback)
    """
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]

    name          = models.CharField(max_length=150, verbose_name='Full Name')
    email         = models.EmailField(blank=True, verbose_name='Email Address')
    gender        = models.CharField(max_length=10, choices=GENDER_CHOICES, verbose_name='Gender')
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='Date of Birth')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Student'
        verbose_name_plural = 'Students'

    def __str__(self):
        return self.name

    @property
    def current_enrollment(self):
        """Most recent Enrollment for backward-compat shims."""
        return self.enrollments.select_related('student_class').order_by('-academic_year').first()

    @property
    def roll_id(self):
        """Shim: roll_id from most recent enrollment."""
        enr = self.current_enrollment
        return enr.roll_id if enr else ''

    @property
    def student_class(self):
        """Shim: StudentClass from most recent enrollment."""
        enr = self.current_enrollment
        return enr.student_class if enr else None

    def dob_password(self):
        """DOB as DDMMYYYY string, e.g. '12082005'. Empty string if no DOB."""
        if self.date_of_birth:
            return self.date_of_birth.strftime('%d%m%Y')
        return ''

    def check_auth_password(self, raw):
        """
        Verify student login password.
        Accepts ONLY DOB (DDMMYYYY).
        """
        dob_pw = self.dob_password()
        if dob_pw and raw == dob_pw:
            return True
        return False


class Enrollment(models.Model):
    """
    Bridge between Student and StudentClass for one academic year.

    Constraints:
      unique_student_per_year  : one enrollment per student per year
      unique_roll_in_class_year: roll_id unique within class+year
    """
    student       = models.ForeignKey(Student, on_delete=models.CASCADE,
                                       related_name='enrollments', verbose_name='Student')
    student_class = models.ForeignKey(StudentClass, on_delete=models.CASCADE,
                                       related_name='enrollments', verbose_name='Class')
    academic_year = models.CharField(max_length=10, verbose_name='Academic Year',
                                      help_text='e.g. 2024-25')
    roll_id       = models.CharField(max_length=30, verbose_name='Roll ID')
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'
        ordering = ['academic_year', 'roll_id']
        constraints = [
            models.UniqueConstraint(fields=['student', 'academic_year'],
                                    name='unique_student_per_year'),
            models.UniqueConstraint(fields=['student_class', 'academic_year', 'roll_id'],
                                    name='unique_roll_in_class_year'),
        ]
        indexes = [
            models.Index(fields=['student_class', 'academic_year']),
            models.Index(fields=['academic_year', 'roll_id']),
        ]

    def __str__(self):
        return (f"{self.student.name} | {self.student_class.display_name} "
                f"| {self.academic_year} | Roll {self.roll_id}")

    @property
    def student_name(self):
        return self.student.name

    @property
    def class_display(self):
        return self.student_class.display_name


class Result(models.Model):
    """
    Legacy 3-component result — kept intact so old views compile.
    Deprecated: new result entry uses EnhancedResult via Enrollment.
    """
    GRADE_CHOICES = [
        ('O', 'Outstanding'), ('A+', 'Excellent'), ('A', 'Very Good'),
        ('B+', 'Good'), ('B', 'Average'), ('F', 'Fail'),
    ]
    STATUS_CHOICES = [('Pass', 'Pass'), ('Fail', 'Fail')]

    student   = models.ForeignKey(Student, on_delete=models.CASCADE,
                                   related_name='results', verbose_name='Student')
    subject   = models.ForeignKey(Subject, on_delete=models.CASCADE,
                                   related_name='results', verbose_name='Subject')
    ia1_marks = models.DecimalField(max_digits=4, decimal_places=1, default=0,
                    validators=[MinValueValidator(0), MaxValueValidator(20)])
    ia2_marks = models.DecimalField(max_digits=4, decimal_places=1, default=0,
                    validators=[MinValueValidator(0), MaxValueValidator(20)])
    sem_marks = models.DecimalField(max_digits=4, decimal_places=1, default=0,
                    validators=[MinValueValidator(0), MaxValueValidator(60)])
    total     = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    grade     = models.CharField(max_length=3, choices=GRADE_CHOICES, default='F')
    status    = models.CharField(max_length=4, choices=STATUS_CHOICES, default='Fail')
    created_at= models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject')
        ordering = ['subject__name']
        verbose_name = 'Result (Legacy)'
        verbose_name_plural = 'Results (Legacy)'

    def __str__(self):
        return f"{self.student.name} — {self.subject.display_name}"

    @property
    def total_marks(self):
        return float(self.ia1_marks) + float(self.ia2_marks) + float(self.sem_marks)

    @property
    def max_marks(self):
        return 100

    @property
    def percentage(self):
        return round(self.total_marks / self.max_marks * 100, 2)

    @property
    def is_fail_ia1(self):
        return float(self.ia1_marks) < 8

    @property
    def is_fail_ia2(self):
        return float(self.ia2_marks) < 8

    @property
    def is_fail_sem(self):
        return float(self.sem_marks) < 24

    @property
    def is_overall_fail(self):
        return self.is_fail_ia1 or self.is_fail_ia2 or self.is_fail_sem

    @property
    def grade_label(self):
        return {'O': 'Outstanding', 'A+': 'Excellent', 'A': 'Very Good',
                'B+': 'Good', 'B': 'Average', 'F': 'Fail'}.get(self.grade, '')

    @staticmethod
    def compute_grade(pct):
        if pct >= 75: return 'O'
        if pct >= 65: return 'A+'
        if pct >= 55: return 'A'
        if pct >= 45: return 'B+'
        if pct >= 40: return 'B'
        return 'F'

    def save(self, *args, **kwargs):
        self.total  = round(self.total_marks, 1)
        self.grade  = self.compute_grade(self.percentage)
        self.status = 'Fail' if self.is_overall_fail else 'Pass'
        super().save(*args, **kwargs)


class Notice(models.Model):
    """System-wide announcements."""
    title      = models.CharField(max_length=200, verbose_name='Notice Title')
    content    = models.TextField(verbose_name='Content')
    is_active  = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notice'
        verbose_name_plural = 'Notices'

    def __str__(self):
        return self.title

    @property
    def short_content(self):
        return self.content[:200] + '...' if len(self.content) > 200 else self.content


# Re-export result engine models so Django discovers them via this app
from .result_models import (  # noqa: F401, E402
    GradeScale, SemesterSubject, EnhancedResult, SemesterSummary
)

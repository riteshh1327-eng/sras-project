"""
SRAS — Django Admin registrations
Covers all models including Enrollment and result engine.
"""

from django.contrib import admin
from django.contrib.auth.hashers import make_password

from .models import (
    Teacher, StudentClass, Subject, SubjectCombination,
    Student, Enrollment, Result, Notice,
)
from .result_models import GradeScale, SemesterSubject, EnhancedResult, SemesterSummary


# ── Inline: Enrollments shown inside Student admin ───────────────────────────

class EnrollmentInline(admin.TabularInline):
    model   = Enrollment
    extra   = 1
    fields  = ['student_class', 'academic_year', 'roll_id']
    ordering= ['-academic_year']


# ── Teacher ───────────────────────────────────────────────────────────────────

from django import forms
from django.contrib.auth.hashers import make_password
from .models import Teacher





# ---------------------------
# Custom Admin Form
# ---------------------------
class TeacherAdminForm(forms.ModelForm):
    raw_password = forms.CharField(
        label="Password",
        required=False,
        widget=forms.PasswordInput,
        help_text="Enter a new password. Leave blank to keep current password."
    )

    class Meta:
        model = Teacher
        fields = ['name', 'email', 'is_active']


# ---------------------------
# Admin Panel
# ---------------------------
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):

    form = TeacherAdminForm

    list_display = ['name', 'email', 'is_active', 'created_at']
    search_fields = ['name', 'email']
    list_filter = ['is_active']

    def save_model(self, request, obj, form, change):
        raw_password = form.cleaned_data.get("raw_password")

        if raw_password:
            obj.set_password(raw_password)
        elif not obj.password:
            obj.set_password("changeme123")

        super().save_model(request, obj, form, change)

# ── StudentClass ──────────────────────────────────────────────────────────────

@admin.register(StudentClass)
class StudentClassAdmin(admin.ModelAdmin):
    list_display  = ['__str__', 'class_year', 'section', 'academic_year', 'get_student_count']
    list_filter   = ['class_year', 'academic_year']
    search_fields = ['section', 'academic_year']


# ── Subject ───────────────────────────────────────────────────────────────────

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code', 'created_at']
    search_fields = ['name', 'code']


# ── SubjectCombination ────────────────────────────────────────────────────────

@admin.register(SubjectCombination)
class SubjectCombinationAdmin(admin.ModelAdmin):
    list_display = ['student_class', 'subject']
    list_filter  = ['student_class']


# ── Student (permanent identity) ──────────────────────────────────────────────

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display  = ['name', 'email', 'gender', 'date_of_birth',
                     '_current_class', '_current_roll']
    search_fields = ['name', 'email']
    list_filter   = ['gender']
    inlines       = [EnrollmentInline]

    @admin.display(description='Current Class')
    def _current_class(self, obj):
        enr = obj.current_enrollment
        return str(enr.student_class) if enr else '—'

    @admin.display(description='Current Roll')
    def _current_roll(self, obj):
        enr = obj.current_enrollment
        return enr.roll_id if enr else '—'


# ── Enrollment ────────────────────────────────────────────────────────────────

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display  = ['student', 'student_class', 'academic_year', 'roll_id', 'created_at']
    list_filter   = ['student_class', 'academic_year']
    search_fields = ['student__name', 'roll_id', 'student__email']
    ordering      = ['academic_year', 'student_class', 'roll_id']


# ── Result (legacy) ───────────────────────────────────────────────────────────

@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display  = ['student', 'subject', 'ia1_marks', 'ia2_marks', 'sem_marks', 'total', 'grade', 'status']
    list_filter   = ['status', 'grade', 'subject']
    search_fields = ['student__name']


# ── Notice ────────────────────────────────────────────────────────────────────

@admin.register(Notice)
class NoticeAdmin(admin.ModelAdmin):
    list_display  = ['title', 'is_active', 'created_at']
    list_filter   = ['is_active']
    search_fields = ['title']


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

@admin.register(GradeScale)
class GradeScaleAdmin(admin.ModelAdmin):
    list_display = ['grade', 'min_percentage', 'max_percentage', 'grade_points', 'is_pass']
    ordering     = ['-min_percentage']


@admin.register(SemesterSubject)
class SemesterSubjectAdmin(admin.ModelAdmin):
    list_display  = ['subject', 'student_class', 'semester', 'academic_year', 'credits',
                     'has_ia', 'has_tw', 'has_oral', 'has_sem']
    list_editable = ['has_ia', 'has_tw', 'has_oral', 'has_sem']
    list_filter   = ['semester', 'academic_year', 'student_class']
    search_fields = ['subject__name']


@admin.register(EnhancedResult)
class EnhancedResultAdmin(admin.ModelAdmin):
    list_display   = ['_student', '_roll', '_subject', '_sem', 'ia1', 'ia2', 'sem',
                      'total', 'grade', 'status']
    list_filter    = ['status', 'grade', 'semester_subject__semester']
    search_fields  = ['enrollment__student__name', 'enrollment__roll_id']
    readonly_fields= ['ia_total', 'total', 'percentage', 'grade', 'grade_points', 'status']

    @admin.display(description='Student', ordering='enrollment__student__name')
    def _student(self, obj):
        return obj.enrollment.student.name

    @admin.display(description='Roll', ordering='enrollment__roll_id')
    def _roll(self, obj):
        return obj.enrollment.roll_id

    @admin.display(description='Subject')
    def _subject(self, obj):
        return obj.semester_subject.subject.display_name

    @admin.display(description='Sem')
    def _sem(self, obj):
        return obj.semester_subject.semester


@admin.register(SemesterSummary)
class SemesterSummaryAdmin(admin.ModelAdmin):
    list_display   = ['_student', '_roll', 'semester', 'academic_year',
                      'sgpa', 'cgpa', 'percentage', 'result', 'subjects_failed']
    list_filter    = ['semester', 'result', 'academic_year']
    search_fields  = ['enrollment__student__name', 'enrollment__roll_id']
    readonly_fields= ['sgpa', 'cgpa', 'percentage', 'total_marks', 'max_marks', 'computed_at']

    @admin.display(description='Student')
    def _student(self, obj):
        return obj.enrollment.student.name

    @admin.display(description='Roll')
    def _roll(self, obj):
        return obj.enrollment.roll_id

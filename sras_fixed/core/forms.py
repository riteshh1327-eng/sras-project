"""
SRAS — Forms
All form definitions for the Student Result Analysis System.

StudentForm now covers only the permanent identity fields (no class/roll).
EnrollmentForm handles class placement per academic year.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import StudentClass, Subject, SubjectCombination, Student, Enrollment, Result, Notice


class StudentClassForm(forms.ModelForm):
    class Meta:
        model = StudentClass
        fields = ['class_year', 'section', 'academic_year']
        widgets = {
            'class_year':   forms.Select(attrs={'class': 'form-control'}),
            'section':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. A, B, C'}),
            'academic_year':forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2024-25'}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'description']
        widgets = {
            'name':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Mathematics'}),
            'code':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CS301 (optional)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class SubjectCombinationForm(forms.ModelForm):
    class Meta:
        model = SubjectCombination
        fields = ['student_class', 'subject']
        widgets = {
            'student_class': forms.Select(attrs={'class': 'form-control'}),
            'subject':       forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data  = super().clean()
        student_class = cleaned_data.get('student_class')
        subject       = cleaned_data.get('subject')
        if student_class and subject:
            qs = SubjectCombination.objects.filter(
                student_class=student_class, subject=subject
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    f"Subject '{subject}' is already added to class '{student_class}'."
                )
        return cleaned_data


class StudentForm(forms.ModelForm):
    """
    Permanent identity form — name, email, gender, DOB only.
    roll_id and student_class have moved to EnrollmentForm.
    """
    class Meta:
        model = Student
        fields = ['name', 'email', 'gender', 'date_of_birth']
        widgets = {
            'name':          forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'email':         forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'student@email.com'}),
            'gender':        forms.Select(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        help_texts = {
            'date_of_birth': 'Used as login password (DDMMYYYY format).',
        }


class EnrollmentForm(forms.ModelForm):
    """
    Enroll a student in a class for an academic year.
    Used on the enrollment_create view.
    """
    class Meta:
        model = Enrollment
        fields = ['student', 'student_class', 'academic_year', 'roll_id']
        widgets = {
            'student':       forms.Select(attrs={'class': 'form-control'}),
            'student_class': forms.Select(attrs={'class': 'form-control'}),
            'academic_year': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. 2024-25',
            }),
            'roll_id':       forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. SE001',
            }),
        }

    def clean(self):
        cleaned_data  = super().clean()
        student       = cleaned_data.get('student')
        student_class = cleaned_data.get('student_class')
        academic_year = cleaned_data.get('academic_year', '').strip()
        roll_id       = cleaned_data.get('roll_id', '').strip()

        if student and academic_year:
            qs = Enrollment.objects.filter(student=student, academic_year=academic_year)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    f"This student already has an enrollment for {academic_year}."
                )

        if student_class and academic_year and roll_id:
            qs = Enrollment.objects.filter(
                student_class=student_class,
                academic_year=academic_year,
                roll_id=roll_id,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError(
                    f"Roll ID '{roll_id}' is already taken in {student_class} for {academic_year}."
                )

        return cleaned_data


class ExcelUploadForm(forms.Form):
    """Upload student data via Excel. Students are created as permanent identities."""
    student_class = forms.ModelChoiceField(
        queryset=StudentClass.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select Class',
        help_text='Enrollments will be created for this class.',
    )
    excel_file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'}),
        label='Excel File (.xlsx)',
        help_text='Columns: Name | RollID | Email | Gender | DOB (YYYY-MM-DD)',
    )

    def clean_excel_file(self):
        f = self.cleaned_data['excel_file']
        if f.name.split('.')[-1].lower() not in ('xlsx', 'xls'):
            raise ValidationError('Only .xlsx and .xls files are allowed.')
        if f.size > 10 * 1024 * 1024:
            raise ValidationError('File must not exceed 10 MB.')
        return f


class ResultForm(forms.ModelForm):
    """Legacy result entry form (IA1, IA2, SEM)."""
    class Meta:
        model = Result
        fields = ['ia1_marks', 'ia2_marks', 'sem_marks']
        widgets = {
            'ia1_marks': forms.NumberInput(attrs={
                'class': 'form-control marks-input',
                'min': '0', 'max': '20', 'step': '0.5', 'placeholder': '0-20',
            }),
            'ia2_marks': forms.NumberInput(attrs={
                'class': 'form-control marks-input',
                'min': '0', 'max': '20', 'step': '0.5', 'placeholder': '0-20',
            }),
            'sem_marks': forms.NumberInput(attrs={
                'class': 'form-control marks-input',
                'min': '0', 'max': '60', 'step': '0.5', 'placeholder': '0-60',
            }),
        }

    def clean_ia1_marks(self):
        m = self.cleaned_data.get('ia1_marks')
        if m is not None and not (0 <= m <= 20):
            raise ValidationError('IA-1 marks must be between 0 and 20.')
        return m

    def clean_ia2_marks(self):
        m = self.cleaned_data.get('ia2_marks')
        if m is not None and not (0 <= m <= 20):
            raise ValidationError('IA-2 marks must be between 0 and 20.')
        return m

    def clean_sem_marks(self):
        m = self.cleaned_data.get('sem_marks')
        if m is not None and not (0 <= m <= 60):
            raise ValidationError('Semester marks must be between 0 and 60.')
        return m


class ResultFilterForm(forms.Form):
    """Filter form for the legacy result list."""
    student_class = forms.ModelChoiceField(
        queryset=StudentClass.objects.all(), required=False,
        empty_label='All Classes',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(), required=False,
        empty_label='All Subjects',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    student_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student name...'}),
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Default'),
            ('total_asc',  'Marks: Low → High'),
            ('total_desc', 'Marks: High → Low'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    fail_filter = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Students'),
            ('fail_ia1', 'Failed IA-1'),
            ('fail_ia2', 'Failed IA-2'),
            ('fail_sem', 'Failed Semester'),
            ('fail_any', 'Failed Any'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
    )


class NoticeForm(forms.ModelForm):
    class Meta:
        model = Notice
        fields = ['title', 'content', 'is_active']
        widgets = {
            'title':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notice title'}),
            'content':   forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

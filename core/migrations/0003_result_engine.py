"""
Migration 0003 — University-grade Result Engine
Creates: GradeScale, SemesterSubject, EnhancedResult, SemesterSummary
Seeds:   GradeScale with University of Mumbai defaults
"""

from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_teacher_result_computed'),
    ]

    operations = [
        # ── GradeScale ─────────────────────────────────────────────────────────
        migrations.CreateModel(
            name='GradeScale',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('grade', models.CharField(choices=[
                    ('O','Outstanding'),('A+','Excellent'),('A','Very Good'),
                    ('B+','Good'),('B','Above Average'),('C','Average'),('F','Fail')
                ], max_length=3, unique=True, verbose_name='Grade')),
                ('min_percentage', models.DecimalField(decimal_places=2, max_digits=5,
                    validators=[django.core.validators.MinValueValidator(0),
                                django.core.validators.MaxValueValidator(100)],
                    verbose_name='Min %')),
                ('max_percentage', models.DecimalField(decimal_places=2, max_digits=5,
                    validators=[django.core.validators.MinValueValidator(0),
                                django.core.validators.MaxValueValidator(100)],
                    verbose_name='Max %')),
                ('grade_points', models.DecimalField(decimal_places=1, max_digits=4,
                    validators=[django.core.validators.MinValueValidator(0),
                                django.core.validators.MaxValueValidator(10)],
                    verbose_name='Grade Points')),
                ('is_pass', models.BooleanField(default=True, verbose_name='Is Passing Grade')),
            ],
            options={'ordering': ['-min_percentage'], 'verbose_name': 'Grade Scale'},
        ),

        # ── SemesterSubject ────────────────────────────────────────────────────
        migrations.CreateModel(
            name='SemesterSubject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('semester', models.CharField(max_length=1,
                    choices=[(str(i), f'Semester {i}') for i in range(1,9)],
                    verbose_name='Semester')),
                ('academic_year', models.CharField(max_length=10, verbose_name='Academic Year')),
                ('credits', models.PositiveSmallIntegerField(default=4,
                    validators=[django.core.validators.MinValueValidator(1),
                                django.core.validators.MaxValueValidator(10)],
                    verbose_name='Credits')),
                ('has_ia',   models.BooleanField(default=True)),
                ('has_tw',   models.BooleanField(default=False)),
                ('has_oral', models.BooleanField(default=False)),
                ('has_sem',  models.BooleanField(default=True)),
                ('max_ia1',  models.PositiveSmallIntegerField(default=20)),
                ('max_ia2',  models.PositiveSmallIntegerField(default=20)),
                ('max_tw',   models.PositiveSmallIntegerField(default=25)),
                ('max_oral', models.PositiveSmallIntegerField(default=25)),
                ('max_sem',  models.PositiveSmallIntegerField(default=60)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='semester_subjects', to='core.studentclass')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='semester_subjects', to='core.subject')),
            ],
            options={
                'verbose_name': 'Semester Subject',
                'ordering': ['semester', 'subject__name'],
                'unique_together': {('student_class', 'subject', 'semester', 'academic_year')},
            },
        ),
        migrations.AddIndex(
            model_name='semestersubject',
            index=models.Index(fields=['student_class', 'semester', 'academic_year'],
                               name='core_semstr_cls_sem_idx'),
        ),

        # ── EnhancedResult ─────────────────────────────────────────────────────
        migrations.CreateModel(
            name='EnhancedResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('ia1',   models.DecimalField(decimal_places=1, max_digits=5, null=True, blank=True)),
                ('ia2',   models.DecimalField(decimal_places=1, max_digits=5, null=True, blank=True)),
                ('tw',    models.DecimalField(decimal_places=1, max_digits=5, null=True, blank=True)),
                ('oral',  models.DecimalField(decimal_places=1, max_digits=5, null=True, blank=True)),
                ('sem',   models.DecimalField(decimal_places=1, max_digits=5, null=True, blank=True)),
                ('ia_total',    models.DecimalField(decimal_places=1, max_digits=5, default=0)),
                ('total',       models.DecimalField(decimal_places=1, max_digits=6, default=0)),
                ('percentage',  models.DecimalField(decimal_places=2, max_digits=5, default=0)),
                ('grade',       models.CharField(default='-', max_length=3)),
                ('grade_points',models.DecimalField(decimal_places=1, max_digits=4, default=0)),
                ('status',      models.CharField(default='Fail', max_length=7)),
                ('is_absent',   models.BooleanField(default=False)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='enhanced_results', to='core.student')),
                ('semester_subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='results', to='core.semestersubject')),
            ],
            options={
                'verbose_name': 'Enhanced Result',
                'ordering': ['student__roll_id', 'semester_subject__subject__name'],
                'unique_together': {('student', 'semester_subject')},
            },
        ),
        migrations.AddIndex(
            model_name='enhancedresult',
            index=models.Index(fields=['student', 'semester_subject'],
                               name='core_enh_stu_ss_idx'),
        ),
        migrations.AddIndex(
            model_name='enhancedresult',
            index=models.Index(fields=['status'], name='core_enh_status_idx'),
        ),

        # ── SemesterSummary ────────────────────────────────────────────────────
        migrations.CreateModel(
            name='SemesterSummary',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('semester',       models.CharField(max_length=1)),
                ('academic_year',  models.CharField(max_length=10)),
                ('total_credits',  models.PositiveSmallIntegerField(default=0)),
                ('earned_credits', models.PositiveSmallIntegerField(default=0)),
                ('total_marks',    models.DecimalField(decimal_places=1, max_digits=8, default=0)),
                ('max_marks',      models.DecimalField(decimal_places=1, max_digits=8, default=0)),
                ('percentage',     models.DecimalField(decimal_places=2, max_digits=5, default=0)),
                ('sgpa',           models.DecimalField(decimal_places=2, max_digits=4, default=0)),
                ('result',         models.CharField(default='Fail', max_length=4)),
                ('subjects_failed',models.PositiveSmallIntegerField(default=0)),
                ('computed_at',    models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name='semester_summaries', to='core.student')),
            ],
            options={
                'verbose_name': 'Semester Summary',
                'ordering': ['student', 'semester'],
                'unique_together': {('student', 'semester', 'academic_year')},
            },
        ),
        migrations.AddIndex(
            model_name='semestersummary',
            index=models.Index(fields=['student', 'semester'],
                               name='core_sem_sum_idx'),
        ),

        # ── Seed GradeScale ────────────────────────────────────────────────────
        migrations.RunPython(
            code=lambda apps, schema_editor: _seed_grade_scale(apps),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def _seed_grade_scale(apps):
    GradeScale = apps.get_model('core', 'GradeScale')
    rows = [
        ('O',  75, 100, 10.0, True),
        ('A+', 65,  74,  9.0, True),
        ('A',  55,  64,  8.0, True),
        ('B+', 50,  54,  7.0, True),
        ('B',  45,  49,  6.0, True),
        ('C',  40,  44,  5.0, True),
        ('F',   0,  39,  0.0, False),
    ]
    for grade, mn, mx, gp, ip in rows:
        GradeScale.objects.get_or_create(
            grade=grade,
            defaults={'min_percentage': mn, 'max_percentage': mx,
                      'grade_points': gp, 'is_pass': ip}
        )

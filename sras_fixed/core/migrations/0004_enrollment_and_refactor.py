"""
Migration 0004 — Enrollment model + safe data migration
=========================================================

Order of operations (critical for SQLite + PostgreSQL):

  1.  Create Enrollment table + constraints + indexes
  2.  Backfill Enrollment from Student.student_class + roll_id
  3.  Remove unique_together from Student

  EnhancedResult:
  4.  Fix ordering (remove student__roll_id ref) BEFORE any field removal
  5.  RemoveIndex core_enh_stu_ss_idx  (references student FK)
  6.  Add nullable enrollment FK
  7.  Backfill enrollment FK
  8.  Make non-nullable; fix unique_together; remove student FK; new index+ordering

  SemesterSummary:
  9.  Fix ordering BEFORE any field removal
  10. RemoveIndex core_sem_sum_idx  (references student FK)
  11. Add nullable enrollment FK
  12. Backfill enrollment FK
  13. Make non-nullable; fix unique_together; remove student FK; new index+ordering

  Student:
  14. Remove student_class FK + roll_id field

  Misc:
  15. Add cgpa to SemesterSummary
  16. Fix Result ordering (student__roll_id removed from Student)
"""

from django.db import migrations, models
import django.db.models.deletion


# ─────────────────────────────────────────────────────────────────────────────
# DATA MIGRATION HELPERS  — defined BEFORE Migration class (required for RunPython)
# ─────────────────────────────────────────────────────────────────────────────

def _backfill_enrollments(apps, schema_editor):
    Student    = apps.get_model('core', 'Student')
    Enrollment = apps.get_model('core', 'Enrollment')
    seen = {}
    for student in Student.objects.select_related('student_class').order_by('pk'):
        sc = student.student_class
        if sc is None:
            continue
        ay   = sc.academic_year
        roll = str(student.roll_id).strip() if student.roll_id else str(student.pk)
        key  = (sc.pk, ay, roll)
        if key in seen:
            seen[key] += 1
            roll = f"{roll}-{seen[key]}"
        else:
            seen[key] = 0
        Enrollment.objects.get_or_create(
            student=student,
            academic_year=ay,
            defaults={'student_class': sc, 'roll_id': roll},
        )


def _backfill_er_enrollment(apps, schema_editor):
    EnhancedResult = apps.get_model('core', 'EnhancedResult')
    Enrollment     = apps.get_model('core', 'Enrollment')
    to_update, to_delete = [], []
    for er in EnhancedResult.objects.select_related('student', 'semester_subject').order_by('pk'):
        ay  = er.semester_subject.academic_year
        enr = Enrollment.objects.filter(student=er.student, academic_year=ay).first()
        if enr is None:
            to_delete.append(er.pk)
        else:
            er.enrollment_id = enr.pk
            to_update.append(er)
    if to_update:
        EnhancedResult.objects.bulk_update(to_update, ['enrollment_id'])
    if to_delete:
        EnhancedResult.objects.filter(pk__in=to_delete).delete()


def _backfill_summary_enrollment(apps, schema_editor):
    SemesterSummary = apps.get_model('core', 'SemesterSummary')
    Enrollment      = apps.get_model('core', 'Enrollment')
    to_update, to_delete = [], []
    for ss in SemesterSummary.objects.select_related('student').order_by('pk'):
        enr = Enrollment.objects.filter(student=ss.student, academic_year=ss.academic_year).first()
        if enr is None:
            to_delete.append(ss.pk)
        else:
            ss.enrollment_id = enr.pk
            to_update.append(ss)
    if to_update:
        SemesterSummary.objects.bulk_update(to_update, ['enrollment_id'])
    if to_delete:
        SemesterSummary.objects.filter(pk__in=to_delete).delete()


# ─────────────────────────────────────────────────────────────────────────────
# MIGRATION
# ─────────────────────────────────────────────────────────────────────────────

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_result_engine'),
    ]

    operations = [

        # ══════════════════════════════════════════════
        # 1. Create Enrollment table
        # ══════════════════════════════════════════════
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('academic_year', models.CharField(max_length=10, verbose_name='Academic Year')),
                ('roll_id', models.CharField(max_length=30, verbose_name='Roll ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='enrollments', to='core.student', verbose_name='Student')),
                ('student_class', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='enrollments', to='core.studentclass', verbose_name='Class')),
            ],
            options={
                'verbose_name': 'Enrollment',
                'verbose_name_plural': 'Enrollments',
                'ordering': ['academic_year', 'roll_id'],
            },
        ),
        migrations.AddConstraint(
            model_name='enrollment',
            constraint=models.UniqueConstraint(
                fields=['student', 'academic_year'], name='unique_student_per_year'),
        ),
        migrations.AddConstraint(
            model_name='enrollment',
            constraint=models.UniqueConstraint(
                fields=['student_class', 'academic_year', 'roll_id'], name='unique_roll_in_class_year'),
        ),
        migrations.AddIndex(
            model_name='enrollment',
            index=models.Index(fields=['student_class', 'academic_year'], name='enr_class_year_idx'),
        ),
        migrations.AddIndex(
            model_name='enrollment',
            index=models.Index(fields=['academic_year', 'roll_id'], name='enr_year_roll_idx'),
        ),

        # ══════════════════════════════════════════════
        # 2. Backfill Enrollments from Student data
        # ══════════════════════════════════════════════
        migrations.RunPython(_backfill_enrollments, migrations.RunPython.noop),

        # ══════════════════════════════════════════════
        # 3. Remove Student unique_together
        # ══════════════════════════════════════════════
        migrations.AlterUniqueTogether(name='student', unique_together=set()),

        # ══════════════════════════════════════════════
        # EnhancedResult refactor
        # CRITICAL: fix ordering + remove index BEFORE removing student FK
        # ══════════════════════════════════════════════

        # 4. Fix ordering to remove reference to student__roll_id
        migrations.AlterModelOptions(
            name='enhancedresult',
            options={
                'ordering': ['pk'],
                'verbose_name': 'Enhanced Result',
                'verbose_name_plural': 'Enhanced Results',
            },
        ),

        # 5. Remove index that references student FK (must happen before RemoveField)
        migrations.RemoveIndex(model_name='enhancedresult', name='core_enh_stu_ss_idx'),

        # 6. Add nullable enrollment FK
        migrations.AddField(
            model_name='enhancedresult',
            name='enrollment',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='enhanced_results', to='core.enrollment', verbose_name='Enrollment',
            ),
        ),

        # 7. Backfill
        migrations.RunPython(_backfill_er_enrollment, migrations.RunPython.noop),

        # 8. Make non-null; clear unique_together; drop student FK; add new UC + index
        migrations.AlterField(
            model_name='enhancedresult',
            name='enrollment',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='enhanced_results', to='core.enrollment', verbose_name='Enrollment',
            ),
        ),
        migrations.AlterUniqueTogether(name='enhancedresult', unique_together=set()),
        migrations.RemoveField(model_name='enhancedresult', name='student'),
        migrations.AlterUniqueTogether(
            name='enhancedresult',
            unique_together={('enrollment', 'semester_subject')},
        ),
        migrations.AddIndex(
            model_name='enhancedresult',
            index=models.Index(fields=['enrollment', 'semester_subject'], name='er_enr_ss_idx'),
        ),
        migrations.AlterModelOptions(
            name='enhancedresult',
            options={
                'ordering': ['enrollment__roll_id', 'semester_subject__subject__name'],
                'verbose_name': 'Enhanced Result',
                'verbose_name_plural': 'Enhanced Results',
            },
        ),

        # ══════════════════════════════════════════════
        # SemesterSummary refactor
        # CRITICAL: fix ordering + remove index BEFORE removing student FK
        # ══════════════════════════════════════════════

        # 9. Fix ordering to remove reference to student field
        migrations.AlterModelOptions(
            name='semestersummary',
            options={
                'ordering': ['pk'],
                'verbose_name': 'Semester Summary',
                'verbose_name_plural': 'Semester Summaries',
            },
        ),

        # 10. Remove index that references student FK
        migrations.RemoveIndex(model_name='semestersummary', name='core_sem_sum_idx'),

        # 11. Add nullable enrollment FK
        migrations.AddField(
            model_name='semestersummary',
            name='enrollment',
            field=models.ForeignKey(
                null=True, blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='semester_summaries', to='core.enrollment', verbose_name='Enrollment',
            ),
        ),

        # 12. Backfill
        migrations.RunPython(_backfill_summary_enrollment, migrations.RunPython.noop),

        # 13. Make non-null; clear unique_together; drop student FK; add new UC + index
        migrations.AlterField(
            model_name='semestersummary',
            name='enrollment',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='semester_summaries', to='core.enrollment', verbose_name='Enrollment',
            ),
        ),
        migrations.AlterUniqueTogether(name='semestersummary', unique_together=set()),
        migrations.RemoveField(model_name='semestersummary', name='student'),
        migrations.AlterUniqueTogether(
            name='semestersummary',
            unique_together={('enrollment', 'semester', 'academic_year')},
        ),
        migrations.AddIndex(
            model_name='semestersummary',
            index=models.Index(fields=['enrollment', 'semester'], name='sem_sum_enr_sem_idx'),
        ),
        migrations.AlterModelOptions(
            name='semestersummary',
            options={
                'ordering': ['enrollment', 'semester'],
                'verbose_name': 'Semester Summary',
                'verbose_name_plural': 'Semester Summaries',
            },
        ),

        # ══════════════════════════════════════════════
        # 14. Remove student_class + roll_id from Student
        #     (safe now — all dependent indexes/FKs from other models removed above)
        # ══════════════════════════════════════════════
        migrations.RemoveField(model_name='student', name='student_class'),
        migrations.RemoveField(model_name='student', name='roll_id'),

        # ══════════════════════════════════════════════
        # 15. Add cgpa to SemesterSummary
        # ══════════════════════════════════════════════
        migrations.AddField(
            model_name='semestersummary',
            name='cgpa',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=4, verbose_name='CGPA'),
        ),

        # ══════════════════════════════════════════════
        # 16. Fix Result.Meta.ordering
        #     (student__roll_id is invalid after Student.roll_id removed)
        # ══════════════════════════════════════════════
        migrations.AlterModelOptions(
            name='result',
            options={
                'ordering': ['subject__name'],
                'verbose_name': 'Result (Legacy)',
                'verbose_name_plural': 'Results (Legacy)',
            },
        ),

        # ══════════════════════════════════════════════
        # 17. Fix Student.Meta.ordering to safe value
        # ══════════════════════════════════════════════
        migrations.AlterModelOptions(
            name='student',
            options={
                'ordering': ['name'],
                'verbose_name': 'Student',
                'verbose_name_plural': 'Students',
            },
        ),
    ]

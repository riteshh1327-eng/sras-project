from django.db import migrations, models
import django.core.validators
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Notice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Notice Title')),
                ('content', models.TextField(verbose_name='Content')),
                ('is_active', models.BooleanField(default=True, help_text='Active notices are shown on public board', verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Notice',
                'verbose_name_plural': 'Notices',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='StudentClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_year', models.CharField(choices=[('FE', 'First Year (FE)'), ('SE', 'Second Year (SE)'), ('TE', 'Third Year (TE)'), ('BE', 'Fourth Year (BE)')], max_length=2, verbose_name='Class Year')),
                ('section', models.CharField(help_text='e.g., A, B, C', max_length=5, verbose_name='Section')),
                ('academic_year', models.CharField(help_text='e.g., 2023-24', max_length=10, verbose_name='Academic Year')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Student Class',
                'verbose_name_plural': 'Student Classes',
                'ordering': ['class_year', 'section', 'academic_year'],
                'unique_together': {('class_year', 'section', 'academic_year')},
            },
        ),
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Subject Name')),
                ('code', models.CharField(blank=True, help_text='Optional subject code (e.g., CS301)', max_length=20, verbose_name='Subject Code')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Subject',
                'verbose_name_plural': 'Subjects',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='Full Name')),
                ('roll_id', models.CharField(help_text='Unique roll number/ID', max_length=30, verbose_name='Roll ID')),
                ('email', models.EmailField(blank=True, verbose_name='Email Address')),
                ('gender', models.CharField(choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], max_length=10, verbose_name='Gender')),
                ('date_of_birth', models.DateField(blank=True, null=True, verbose_name='Date of Birth')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='students', to='core.studentclass', verbose_name='Class')),
            ],
            options={
                'verbose_name': 'Student',
                'verbose_name_plural': 'Students',
                'ordering': ['roll_id', 'name'],
                'unique_together': {('roll_id', 'student_class')},
            },
        ),
        migrations.CreateModel(
            name='SubjectCombination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('student_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subject_combinations', to='core.studentclass', verbose_name='Student Class')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subject_combinations', to='core.subject', verbose_name='Subject')),
            ],
            options={
                'verbose_name': 'Subject Combination',
                'verbose_name_plural': 'Subject Combinations',
                'ordering': ['student_class', 'subject__name'],
                'unique_together': {('student_class', 'subject')},
            },
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ia1_marks', models.DecimalField(decimal_places=1, default=0, help_text='Internal Assessment 1 (max 20)', max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(20)], verbose_name='IA-1 Marks')),
                ('ia2_marks', models.DecimalField(decimal_places=1, default=0, help_text='Internal Assessment 2 (max 20)', max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(20)], verbose_name='IA-2 Marks')),
                ('sem_marks', models.DecimalField(decimal_places=1, default=0, help_text='Semester Final Exam (max 60)', max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(60)], verbose_name='Semester Final Marks')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='core.student', verbose_name='Student')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='results', to='core.subject', verbose_name='Subject')),
            ],
            options={
                'verbose_name': 'Result',
                'verbose_name_plural': 'Results',
                'ordering': ['student__roll_id', 'subject__name'],
                'unique_together': {('student', 'subject')},
            },
        ),
    ]

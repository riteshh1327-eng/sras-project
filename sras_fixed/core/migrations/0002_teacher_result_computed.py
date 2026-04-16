from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # ── Teacher model ──────────────────────────────────────────────────────
        migrations.CreateModel(
            name='Teacher',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='Full Name')),
                ('email', models.EmailField(unique=True, verbose_name='Email')),
                ('password', models.CharField(max_length=255, verbose_name='Password (hashed)')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Teacher',
                'verbose_name_plural': 'Teachers',
                'ordering': ['name'],
            },
        ),

        # ── Stored computed fields on Result ───────────────────────────────────
        migrations.AddField(
            model_name='result',
            name='total',
            field=models.DecimalField(decimal_places=1, default=0, max_digits=5, verbose_name='Total'),
        ),
        migrations.AddField(
            model_name='result',
            name='grade',
            field=models.CharField(
                choices=[('O', 'Outstanding'), ('A+', 'Excellent'), ('A', 'Very Good'),
                         ('B+', 'Good'), ('B', 'Average'), ('F', 'Fail')],
                default='F', max_length=3, verbose_name='Grade'
            ),
        ),
        migrations.AddField(
            model_name='result',
            name='status',
            field=models.CharField(
                choices=[('Pass', 'Pass'), ('Fail', 'Fail')],
                default='Fail', max_length=4, verbose_name='Status'
            ),
        ),

        # ── Make Student email not blank (login requirement) ──────────────────
        migrations.AlterField(
            model_name='student',
            name='email',
            field=models.EmailField(blank=True, verbose_name='Email Address'),
        ),
    ]

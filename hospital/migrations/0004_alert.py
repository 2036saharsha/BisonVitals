# Generated by Django 5.1.7 on 2025-03-23 07:09

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hospital', '0003_auto_20250323_0457'),
    ]

    operations = [
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('alert_time', models.DateTimeField()),
                ('urgency', models.CharField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], max_length=10)),
                ('status', models.CharField(choices=[('new', 'New'), ('viewed', 'Viewed'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved')], default='new', max_length=15)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('vital_signs_data', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='hospital.doctor')),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='hospital.issue')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='hospital.patient')),
            ],
            options={
                'ordering': ['-alert_time', '-urgency'],
                'indexes': [models.Index(fields=['-alert_time'], name='hospital_al_alert_t_d91339_idx'), models.Index(fields=['status'], name='hospital_al_status_579d98_idx'), models.Index(fields=['doctor', 'status'], name='hospital_al_doctor__a50025_idx')],
            },
        ),
    ]

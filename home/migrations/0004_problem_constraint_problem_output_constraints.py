# Generated by Django 5.0.6 on 2024-06-10 05:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_problem_examples_problem_input_constraints'),
    ]

    operations = [
        migrations.AddField(
            model_name='problem',
            name='constraint',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='problem',
            name='output_constraints',
            field=models.TextField(blank=True, null=True),
        ),
    ]

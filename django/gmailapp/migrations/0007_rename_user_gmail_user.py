# Generated by Django 5.1.4 on 2025-01-01 10:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gmailapp', '0006_gmail_user'),
    ]

    operations = [
        migrations.RenameField(
            model_name='gmail',
            old_name='User',
            new_name='user',
        ),
    ]
# Generated by Django 5.1.3 on 2025-01-22 08:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Sociales', '0020_remove_post_notification_delete_notification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='members',
            field=models.ManyToManyField(blank=True, related_name='group', to='Sociales.account'),
        ),
    ]

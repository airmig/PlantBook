# Generated by Django 5.1.7 on 2025-04-06 20:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_plant_external_id_plant_source_alter_plant_image'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='profile_photo',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
    ]

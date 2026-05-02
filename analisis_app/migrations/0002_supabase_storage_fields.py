from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analisis_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='imagenanalisis',
            name='imagen',
            field=models.ImageField(blank=True, null=True, upload_to='uploads/'),
        ),
        migrations.AddField(
            model_name='imagenanalisis',
            name='imagen_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='imagenanalisis',
            name='imagen_storage_path',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='imagenanalisis',
            name='overlay_vih_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='imagenanalisis',
            name='overlay_vih_storage_path',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='imagenanalisis',
            name='overlay_skin_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='imagenanalisis',
            name='overlay_skin_storage_path',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='imagenanalisis',
            name='overlay_combined_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='imagenanalisis',
            name='overlay_combined_storage_path',
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='imagenanalisis',
            name='resultado_detalle',
            field=models.JSONField(blank=True, null=True),
        ),
    ]

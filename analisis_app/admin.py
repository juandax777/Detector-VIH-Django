from django.contrib import admin

from .models import ImagenAnalisis


@admin.register(ImagenAnalisis)
class ImagenAnalisisAdmin(admin.ModelAdmin):
    list_display = ('id', 'resultado', 'confianza', 'fecha_subida', 'imagen_url')
    list_filter = ('fecha_subida',)
    search_fields = ('resultado',)
    readonly_fields = (
        'fecha_subida',
        'imagen_url',
        'imagen_storage_path',
        'overlay_vih_url',
        'overlay_vih_storage_path',
        'overlay_skin_url',
        'overlay_skin_storage_path',
        'overlay_combined_url',
        'overlay_combined_storage_path',
        'resultado_detalle',
    )

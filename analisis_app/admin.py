from django.contrib import admin

from .models import ImagenAnalisis


@admin.register(ImagenAnalisis)
class ImagenAnalisisAdmin(admin.ModelAdmin):
    list_display = ('id', 'resultado', 'confianza', 'fecha_subida')
    list_filter = ('fecha_subida',)
    search_fields = ('resultado',)
    readonly_fields = ('fecha_subida',)

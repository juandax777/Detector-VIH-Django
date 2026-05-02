from django.db import models


class ImagenAnalisis(models.Model):
    imagen = models.ImageField(upload_to='uploads/', blank=True, null=True)
    imagen_url = models.URLField(blank=True, null=True)
    imagen_storage_path = models.CharField(max_length=500, blank=True, null=True)
    overlay_vih_url = models.URLField(blank=True, null=True)
    overlay_vih_storage_path = models.CharField(max_length=500, blank=True, null=True)
    overlay_skin_url = models.URLField(blank=True, null=True)
    overlay_skin_storage_path = models.CharField(max_length=500, blank=True, null=True)
    overlay_combined_url = models.URLField(blank=True, null=True)
    overlay_combined_storage_path = models.CharField(max_length=500, blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    resultado = models.TextField(blank=True, null=True)
    confianza = models.FloatField(blank=True, null=True)
    resultado_detalle = models.JSONField(blank=True, null=True)

    @property
    def imagen_public_url(self):
        if self.imagen_url:
            return self.imagen_url
        if self.imagen:
            return self.imagen.url
        return ''

    class Meta:
        verbose_name = 'Imagen de Análisis'
        verbose_name_plural = 'Imágenes de Análisis'
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"Análisis #{self.pk} - {self.fecha_subida.strftime('%d/%m/%Y %H:%M')}"

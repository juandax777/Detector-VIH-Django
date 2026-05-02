from django.db import models


class ImagenAnalisis(models.Model):
    imagen = models.ImageField(upload_to='uploads/')
    fecha_subida = models.DateTimeField(auto_now_add=True)
    resultado = models.TextField(blank=True, null=True)
    confianza = models.FloatField(blank=True, null=True)

    class Meta:
        verbose_name = 'Imagen de Análisis'
        verbose_name_plural = 'Imágenes de Análisis'
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"Análisis #{self.pk} - {self.fecha_subida.strftime('%d/%m/%Y %H:%M')}"
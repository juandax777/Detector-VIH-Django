from django import forms
from .models import ImagenAnalisis


class ImagenForm(forms.ModelForm):
    class Meta:
        model = ImagenAnalisis
        fields = ['imagen']
        widgets = {
            'imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            })
        }
        labels = {
            'imagen': 'Selecciona una imagen de la lesion cutanea'
        }
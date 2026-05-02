from django import forms


class ImagenForm(forms.Form):
    imagen = forms.ImageField(
        label='Selecciona una imagen de la lesion cutanea',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
    )

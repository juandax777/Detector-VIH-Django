from django.urls import path
from . import views

app_name = 'analisis'

urlpatterns = [
    path('', views.subir_imagen, name='subir_imagen'),
    path('historial/', views.historial, name='historial'),
    path('terminos/', views.terminos, name='terminos'),
    path('aceptar-terminos/', views.aceptar_terminos, name='aceptar_terminos'),
]
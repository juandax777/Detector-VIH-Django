from urllib.parse import urlencode

from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import ImagenForm
from .models import ImagenAnalisis
from .predictor import predecir


TERMINOS_SESSION_KEY = 'consentimiento_datos_aceptado'


def _obtener_url_terminos(request):
    destino = request.get_full_path()
    url_terminos = reverse('analisis:terminos')
    if destino and destino != url_terminos:
        return f"{url_terminos}?{urlencode({'next': destino})}"
    return url_terminos


def _debe_aceptar_terminos(request):
    return not request.session.get(TERMINOS_SESSION_KEY, False)


def terminos(request):
    return render(request, 'analisis/terminos.html', {'next': request.GET.get('next', '')})


def aceptar_terminos(request):
    next_url = request.POST.get('next', '')
    if request.method != 'POST':
        return redirect('analisis:terminos')

    if not request.POST.get('acepto'):
        return render(request, 'analisis/terminos.html', {
            'next': next_url,
            'error': 'Debes aceptar los terminos y condiciones para continuar.',
        })

    request.session[TERMINOS_SESSION_KEY] = True
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect('analisis:subir_imagen')


def subir_imagen(request):
    if _debe_aceptar_terminos(request):
        return redirect(_obtener_url_terminos(request))

    if request.method == 'POST':
        form = ImagenForm(request.POST, request.FILES)
        if form.is_valid():
            imagen_obj = form.save()
            try:
                resultado = predecir(imagen_obj.imagen.path)
                imagen_obj.resultado = resultado['diagnostico']
                imagen_obj.confianza = resultado['confianza']
                imagen_obj.save()

                return render(request, 'analisis/resultado.html', {
                    'imagen': imagen_obj,
                    'resultado': resultado,
                })
            except Exception as e:
                return render(request, 'analisis/upload.html', {
                    'form': form,
                    'error': f'Error al analizar la imagen: {str(e)}',
                })
    else:
        form = ImagenForm()
    return render(request, 'analisis/upload.html', {'form': form})


def historial(request):
    if _debe_aceptar_terminos(request):
        return redirect(_obtener_url_terminos(request))

    analisis_lista = ImagenAnalisis.objects.all()
    return render(request, 'analisis/historial.html', {'analisis': analisis_lista})
from urllib.parse import urlencode
import os
import tempfile

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import ImagenForm
from .models import ImagenAnalisis
from .predictor import predecir
from .supabase_storage import build_storage_path, upload_bytes, upload_django_file


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
            archivo = form.cleaned_data['imagen']
            try:
                max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
                if archivo.size > max_bytes:
                    raise ValueError(f'La imagen supera el limite de {settings.MAX_UPLOAD_SIZE_MB} MB.')

                subida_original = upload_django_file(archivo, folder='originales')
                temp_path = _guardar_temporal_para_analisis(archivo)
                try:
                    resultado = predecir(temp_path)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

                overlays = _subir_overlays_a_supabase(resultado)
                resultado_publico = _resultado_sin_binarios(resultado)
                resultado_publico.update(overlays['urls'])

                imagen_obj = ImagenAnalisis(
                    imagen_url=subida_original['url'],
                    imagen_storage_path=subida_original['path'],
                    overlay_vih_url=overlays['urls'].get('overlay_vih_path'),
                    overlay_vih_storage_path=overlays['paths'].get('overlay_vih_path'),
                    overlay_skin_url=overlays['urls'].get('overlay_skin_path'),
                    overlay_skin_storage_path=overlays['paths'].get('overlay_skin_path'),
                    overlay_combined_url=overlays['urls'].get('overlay_combined_path'),
                    overlay_combined_storage_path=overlays['paths'].get('overlay_combined_path'),
                    resultado=resultado_publico['diagnostico'],
                    confianza=resultado_publico['confianza'],
                    resultado_detalle=resultado_publico,
                )
                imagen_obj.save()

                return render(request, 'analisis/resultado.html', {
                    'imagen': imagen_obj,
                    'resultado': resultado_publico,
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


def _guardar_temporal_para_analisis(archivo):
    if hasattr(archivo, 'seek'):
        archivo.seek(0)

    _, extension = os.path.splitext(archivo.name or '')
    with tempfile.NamedTemporaryFile(delete=False, suffix=extension or '.img') as temporal:
        for chunk in archivo.chunks():
            temporal.write(chunk)
        return temporal.name


def _subir_overlays_a_supabase(resultado):
    mapping = {
        'overlay_vih_file': 'overlay_vih_path',
        'overlay_skin_file': 'overlay_skin_path',
        'overlay_combined_file': 'overlay_combined_path',
    }
    urls = {}
    paths = {}
    for file_key, url_key in mapping.items():
        overlay = resultado.get(file_key)
        if not overlay:
            continue
        path = build_storage_path('overlays', overlay.get('filename', 'overlay.png'), '.png')
        subida = upload_bytes(path, overlay['content'], overlay.get('content_type', 'image/png'))
        urls[url_key] = subida['url']
        paths[url_key] = subida['path']
    return {'urls': urls, 'paths': paths}


def _resultado_sin_binarios(resultado):
    limpio = resultado.copy()
    limpio.pop('overlay_vih_file', None)
    limpio.pop('overlay_skin_file', None)
    limpio.pop('overlay_combined_file', None)
    return limpio
